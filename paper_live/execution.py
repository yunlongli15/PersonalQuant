# -*- coding: utf-8 -*-
"""Paper 执行：目标权重 → 实际下单 → T+1 开盘成交（spec §8 / §10 / §12）。

严格保持：**T 日收盘出信号 → T+1 开盘执行**。禁止 T 收盘信号 + T 收盘成交。

理论权重 ≠ 实际执行权重。这里把两者的差距全部显式记下来：

    target_value     目标金额
    theoretical_shares = target_value / price        （未取整）
    rounded_shares     100 股整数倍，向下取整
    actual_trade_value 实际成交金额（含滑点）
    residual_cash      因为取整而没投出去的钱

不能成交的情况（涨跌停 / 停牌 / 无开盘价 / 不足 1 手）一律 NO_TRADE，
并记录原因。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List

import pandas as pd

LOT = 100


def round_lots(shares: float, lot_size: int = LOT) -> int:
    """向下取整到整手。负值（卖出）也按绝对值取整。"""
    if shares is None or not math.isfinite(shares):
        return 0
    sign = -1 if shares < 0 else 1
    return sign * int(math.floor(abs(shares) / lot_size) * lot_size)


@dataclass
class PlannedOrder:
    symbol: str
    name: str
    rank: int
    prediction: float
    current_weight: float
    target_weight: float
    current_value: float
    target_value: float
    delta_value: float
    price: float
    theoretical_shares: float
    estimated_shares: int
    estimated_trade_value: float
    estimated_fee: float
    action: str                    # BUY / SELL / HOLD / NO_TRADE
    execution_rule: str            # T1_open
    note: str = ""

    def as_row(self) -> dict:
        return {
            "symbol": self.symbol, "name": self.name, "rank": self.rank,
            "predicted_return": self.prediction,
            "current_weight": self.current_weight,
            "target_weight": self.target_weight,
            "current_value": self.current_value,
            "target_value": self.target_value,
            "delta_value": self.delta_value,
            "price": self.price,
            "theoretical_shares": self.theoretical_shares,
            "estimated_shares": self.estimated_shares,
            "estimated_trade_value": self.estimated_trade_value,
            "estimated_fee": self.estimated_fee,
            "action": self.action,
            "execution_rule": self.execution_rule,
            "note": self.note,
        }


def build_orders(target_weights: Dict[str, float],
                 predictions: pd.Series,
                 names: Dict[str, str],
                 prices: Dict[str, float],
                 holdings: Dict[str, dict],
                 portfolio_value: float,
                 cash: float,
                 cost_model,
                 lot_size: int = LOT,
                 min_trade_value: float = 0.0) -> List[PlannedOrder]:
    """目标权重 → 下单计划（尚未成交）。

    holdings: {symbol: {"shares": int, "price": float}}
    """
    rows: List[PlannedOrder] = []
    symbols = sorted(set(target_weights) | set(holdings))

    for sym in symbols:
        # 当前市值必须按**当日市价**算。用上次成交价（=成本）会把 delta
        # 算错，进而超买/超卖，现金被打成负数。
        price = prices.get(sym) or holdings.get(sym, {}).get("price")
        cur_shares = int(holdings.get(sym, {}).get("shares", 0))
        cur_px = price if price else (holdings.get(sym, {}).get("price") or 0.0)
        cur_val = cur_shares * cur_px
        tw = float(target_weights.get(sym, 0.0))
        tgt_val = tw * portfolio_value
        delta = tgt_val - cur_val

        if price is None or price <= 0:
            rows.append(PlannedOrder(
                sym, names.get(sym, ""), int(predictions.rank(
                    ascending=False).get(sym, 0) or 0),
                float(predictions.get(sym, float("nan"))),
                cur_val / portfolio_value if portfolio_value else 0.0, tw,
                cur_val, tgt_val, delta, float("nan"), 0.0, 0, 0.0, 0.0,
                "NO_TRADE", "T1_open", "no price"))
            continue

        theo = delta / price
        shares = round_lots(theo, lot_size)
        trade_val = abs(shares) * price

        if shares == 0:
            action = "HOLD" if cur_shares else "NO_TRADE"
            note = "delta below one lot" if cur_shares else "below one lot"
            fee = 0.0
        elif abs(trade_val) < min_trade_value:
            action, shares, trade_val, fee = "NO_TRADE", 0, 0.0, 0.0
            note = f"trade value {abs(delta):.0f} < min {min_trade_value:.0f}"
        else:
            action = "BUY" if shares > 0 else "SELL"
            fee = cost_model.buy_cost(trade_val) if shares > 0 \
                else cost_model.sell_cost(trade_val)
            note = ""

        rows.append(PlannedOrder(
            sym, names.get(sym, ""),
            int(predictions.rank(ascending=False).get(sym, 0) or 0),
            float(predictions.get(sym, float("nan"))),
            cur_val / portfolio_value if portfolio_value else 0.0, tw,
            cur_val, tgt_val, delta, float(price), float(theo), int(shares),
            float(trade_val), float(fee), action, "T1_open", note))
    return rows


# ---------------------------------------------------------------------------
# T+1 成交
# ---------------------------------------------------------------------------

@dataclass
class FillResult:
    orders: pd.DataFrame
    new_holdings: Dict[str, dict]
    cash: float
    fees: float
    traded_value: float
    n_trades: int
    no_trade_reasons: Dict[str, int] = field(default_factory=dict)


def execute_orders(orders: List[PlannedOrder], holdings: Dict[str, dict],
                   cash: float, signal_date: pd.Timestamp,
                   limit_threshold: float, cost_model,
                   executor=None, lot_size: int = LOT) -> FillResult:
    """把下单计划送到 T+1 开盘成交。

    executor(symbol, signal_date, side, shares, limit_threshold) -> OrderResult
    默认用 personal_quant.strategy.execution.execute_order（真实行情）；
    测试可注入假实现。

    **现金守卫**：下单是按 T 日收盘价算的，成交却发生在 T+1 开盘。
    跳空高开时实际花费会超过计划金额 —— 不拦的话账户会被打成负数。
    真实系统也是如此：钱不够就减量或不下单，绝不透支。
    """
    if executor is None:
        from personal_quant.strategy.execution import execute_order
        executor = execute_order

    new_holdings = {k: dict(v) for k, v in holdings.items()}
    rows, fees, traded, n_trades = [], 0.0, 0.0, 0
    reasons: Dict[str, int] = {}

    # 先卖后买：卖出释放现金，买入才有钱。真实交易也是这个顺序，
    # 否则按代码顺序执行时中间现金会变成负数。
    ordered = sorted(orders, key=lambda o: 0 if o.action == "SELL" else 1)

    for o in ordered:
        if o.action not in ("BUY", "SELL"):
            rows.append({**o.as_row(), "status": "SKIPPED",
                         "filled_shares": 0, "fill_price": None,
                         "reason": o.note or o.action})
            continue
        side = "BUY" if o.estimated_shares > 0 else "SELL"
        want = abs(o.estimated_shares)
        res = executor(o.symbol, signal_date, side, want, limit_threshold)

        if getattr(res, "status", None) is None or \
                str(getattr(res.status, "value", res.status)) != "FILLED":
            reason = getattr(res, "reason", "unknown")
            reasons[reason] = reasons.get(reason, 0) + 1
            rows.append({**o.as_row(), "status": "NO_TRADE",
                         "filled_shares": 0, "fill_price": None,
                         "reason": reason})
            continue

        px = float(res.fill_price)
        filled = int(res.shares)          # 买正卖负

        # 现金守卫：跳空高开时买不起就减量（按整手），再买不起就不下单。
        if filled > 0:
            need = filled * px + cost_model.buy_cost(filled * px)
            if need > cash + 1e-9:
                affordable = round_lots((cash - 5.0) / px, lot_size)
                if affordable <= 0:
                    reasons["insufficient cash"] = \
                        reasons.get("insufficient cash", 0) + 1
                    rows.append({**o.as_row(), "status": "NO_TRADE",
                                 "filled_shares": 0, "fill_price": px,
                                 "reason": "insufficient cash"})
                    continue
                res = executor(o.symbol, signal_date, "BUY", affordable,
                               limit_threshold)
                if str(getattr(res.status, "value", res.status)) != "FILLED":
                    reason = getattr(res, "reason", "unknown")
                    reasons[reason] = reasons.get(reason, 0) + 1
                    rows.append({**o.as_row(), "status": "NO_TRADE",
                                 "filled_shares": 0, "fill_price": None,
                                 "reason": reason})
                    continue
                px = float(res.fill_price)
                filled = int(res.shares)
        value = abs(filled) * px
        fee = cost_model.buy_cost(value) if filled > 0 \
            else cost_model.sell_cost(value)
        cash -= filled * px
        cash -= fee
        fees += fee
        traded += value
        n_trades += 1

        h = new_holdings.setdefault(o.symbol, {"shares": 0, "price": px})
        h["shares"] = int(h.get("shares", 0)) + filled
        h["price"] = px
        if h["shares"] == 0:
            new_holdings.pop(o.symbol, None)
        rows.append({**o.as_row(), "status": "FILLED",
                     "filled_shares": filled, "fill_price": px,
                     "reason": ""})

    return FillResult(pd.DataFrame(rows), new_holdings, float(cash),
                      float(fees), float(traded), n_trades, reasons)
