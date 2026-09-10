# -*- coding: utf-8 -*-
"""Portfolio-optimization backtest engine (STEP 6 spec §25/§27/§43).

T（最后一个交易日）收盘：alpha 排名 -> Top-K 候选 -> allocator 目标权重
（sum = invest_target；现金 = 1 - invest_target）-> T+1 开盘按 strategy_v1
冻结执行规则成交（涨跌停/停牌 NO_TRADE、100 股手数、共享
TransactionCostModel）-> 逐日收盘盯市 NAV。

执行语义逐行对照 MonthlyBacktest（strategy_v1）：
  - 卖单先于买单（被清出的持仓全卖，再逐候选调 delta）；
  - 买单向下取整到 100 股整数倍、减仓向上取整；
  - 无 T+1 K 线/涨停买入/跌停卖出 -> NO_TRADE（本轮放弃，下月自然补单）；
  - NAV 用 <=d 的最后收盘价（停牌向前填充）盯市；
  - 换手口径沿用冻结引擎（turnover = 候选调仓成交额/(2×期初权益)），
    同时额外记录含清仓卖出的 turnover_full（如实报告两种口径）。
因此等权配置下的运行必须复现 strategy_v1_news（锚点检查，见
scripts/portfolio/research_portfolio.py）。

每次调仓额外落盘（spec §40/§42/§44）：
  - explainability：symbol/prediction/raw_rank/volatility/target_weight/
    industry/marginal_risk/contribution_to_risk/turnover_from_previous/
    action/optimizer_status/fallback_reason；
  - allocation audit：权重和=invest_target、现金缓冲、个股上限、行业上限、
    无做空、无杠杆、可交易、手数、成交后现金、回退记录。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from personal_quant.strategy.costs import TransactionCostModel
from personal_quant.strategy.execution import TradeStatus, execute_order
from personal_quant.strategy.universe import build_universe, load_securities

from factors.base import load_calendar

from .allocator import (AllocationFailure, AllocationInput, AllocationResult,
                        allocate)
from .constraints import PortfolioConstraints
from .covariance import CovarianceResult, estimate_covariance
from . import portfolio_metrics as pm
from .rebalance import rebalance_dates

LOT = 100


def effective_target(n_cand: int, top_k: int, invest_target: float) -> float:
    """Frozen under-invest semantics when candidates are scarce: each pick
    targets invest_target/top_k, so with n < top_k the portfolio invests
    less and the rest stays in cash (MonthlyBacktest behavior)."""
    if top_k <= 0:
        return 0.0
    return min(invest_target, n_cand * (invest_target / top_k))


def lot_floor(value: float, price: float, lot_size: int = LOT) -> int:
    """A-share buy lots: floor to an integer multiple of the lot size."""
    if price is None or not math.isfinite(price) or price <= 0:
        return 0
    return int(math.floor(value / price / lot_size)) * lot_size


@dataclass
class PortfolioBacktestResult:
    nav: pd.Series                       # daily NAV
    cash: pd.Series                      # daily cash
    positions: pd.DataFrame              # date x symbol shares
    daily_weights: pd.DataFrame          # date x symbol ACTUAL weights
    trades: pd.DataFrame                 # executed trades (with fees)
    weights: pd.DataFrame                # explainability rows per rebalance
    audit: pd.DataFrame                  # per-rebalance allocation audit
    turnover: pd.Series                  # frozen-turnover口径（不含清仓卖出）
    turnover_full: pd.Series             # 含清仓卖出的完整换手
    metrics: dict = field(default_factory=dict)
    config: dict = field(default_factory=dict)


class PortfolioBacktest:
    def __init__(
        self,
        strategy_config: dict,
        cost_model: TransactionCostModel,
        allocation_cfg: dict,
        initial_capital: float = 1_000_000.0,
    ):
        """
        allocation_cfg: {
            method, params, top_k, frequency,
            constraints: PortfolioConstraints,
            risk_window, cov_method, ewma_halflife,
        }
        """
        self.cfg = strategy_config
        self.cost = cost_model
        self.alloc_cfg = allocation_cfg
        self.capital0 = initial_capital
        self.cons = allocation_cfg["constraints"]
        self.top_k = allocation_cfg["top_k"]
        self.limit_threshold = strategy_config["execution"]["limit_threshold"]
        self._securities = None

    # ------------------------------------------------------------------
    # price / equity helpers (DB-free, same semantics as MonthlyBacktest)
    # ------------------------------------------------------------------

    def _px(self, data, symbols, d: pd.Timestamp) -> pd.Series:
        """Last available close <= d per symbol (forward-fills suspension
        days — held names never NaN the NAV)."""
        if not symbols:
            return pd.Series(dtype=float)
        cols = [s for s in symbols if s in data.close_raw.columns]
        if not cols:
            return pd.Series(dtype=float)
        sub = data.close_raw.loc[:d, cols]
        if sub.empty:
            return pd.Series(dtype=float)
        return sub.ffill().iloc[-1]

    def _equity(self, data, positions, cash, d) -> float:
        if not positions:
            return cash
        px = self._px(data, list(positions.keys()), d)
        return cash + float((px * pd.Series(positions)).sum())

    # ------------------------------------------------------------------
    # main loop
    # ------------------------------------------------------------------

    def run(
        self,
        start,
        end,
        predictions: pd.DataFrame,     # long: date, symbol, prediction
        data,                          # factors.base.FactorData
        bench_nav: Optional[pd.Series] = None,
        verbose: bool = True,
    ) -> PortfolioBacktestResult:
        """Backtest over [start, end] with monthly/quarterly rebalances."""
        cfg = self.alloc_cfg
        cons = self.cons
        method = cfg["method"]
        params = dict(cfg.get("params", {}))
        freq = cfg.get("frequency", "monthly")
        risk_window = cfg.get("risk_window", 60)
        cov_method = cfg.get("cov_method", "sample")
        halflife = cfg.get("ewma_halflife")

        cal = load_calendar()
        days = cal[(cal >= pd.Timestamp(start)) & (cal <= pd.Timestamp(end))]
        if len(days) == 0:
            raise ValueError("empty trading calendar for the period")
        rbs = rebalance_dates(start, end, freq)
        pred_wide = predictions.pivot_table(index="date", columns="symbol",
                                            values="prediction")
        if self._securities is None:
            self._securities = load_securities()

        fills_by_date: Dict[pd.Timestamp, List[dict]] = {}
        trades: List[dict] = []
        weight_rows: List[dict] = []
        audit_rows: List[dict] = []
        turnover: Dict[pd.Timestamp, float] = {}
        turnover_full: Dict[pd.Timestamp, float] = {}
        actions: Dict[pd.Timestamp, Dict[str, str]] = {}
        cash = self.capital0
        positions: Dict[str, int] = {}

        for t in rbs:
            t1 = self._next_day(cal, t)
            if t1 is None or t1 > days[-1]:
                continue
            universe = build_universe(t, self.cfg, self._securities)
            univ = set(universe["symbol"])
            if not univ:
                audit_rows.append({"date": t, "check": "universe",
                                   "status": "FAIL", "value": 0,
                                   "note": "empty universe"})
                continue
            if t not in pred_wide.index:
                continue
            # universe LIST order (not sorted): the frozen predictor
            # reindexes to build_universe's row order, and sort_values'
            # quicksort tie-breaking depends on the input order
            scores = pred_wide.loc[t].reindex(
                universe["symbol"].tolist()).dropna()
            if scores.empty:
                continue
            scores = scores.sort_values(ascending=False)
            cand = scores.head(self.top_k)
            cand = cand[cand.index.isin(univ)]
            if cand.empty:
                continue

            equity = self._equity(data, positions, cash, t)
            if equity <= 0:
                continue
            px_t = self._px(data, list(set(positions) | set(cand.index)), t)

            # scarce candidates: mirror the frozen MonthlyBacktest semantics
            # — each pick targets invest_target/top_k, so with n < top_k the
            # portfolio under-invests (rest stays in cash) instead of
            # concentrating. The allocator therefore works with a scaled
            # effective target.
            n_cand = len(cand)
            eff_target = effective_target(n_cand, self.top_k,
                                          cons.invest_target)
            eff_cons = cons
            target_scaled = False
            if eff_target < cons.invest_target - 1e-12:
                import dataclasses

                eff_cons = dataclasses.replace(
                    cons, invest_target=eff_target,
                    cash_buffer=1.0 - eff_target)
                target_scaled = True

            # previous ACTUAL weights (T 日持仓按 T 日价)
            prev_w = pd.Series(dtype=float)
            for s, sh in positions.items():
                p = px_t.get(s)
                if p is not None and not math.isnan(p):
                    prev_w[s] = sh * p / equity

            # PIT covariance + vols (<= T only)
            covres = estimate_covariance(data.close_raw, cand.index, t,
                                         risk_window, cov_method, halflife)
            cand_df = pd.DataFrame({"prediction": cand,
                                    "raw_rank": range(1, len(cand) + 1)})
            cand_df["vol"] = covres.vols.reindex(cand_df.index)
            cand_df["industry"] = data.industries.reindex(cand_df.index)
            if cons.liquidity_frac:
                amt = data.amount_cny.loc[:t, cand_df.index].tail(20).mean()
                cand_df["liq_cap"] = (cons.liquidity_frac * amt / equity
                                      ).clip(upper=cons.max_weight)
            else:
                cand_df["liq_cap"] = np.nan

            inp = AllocationInput(
                date=t, candidates=cand_df, cov=covres, prev_weights=prev_w,
                constraints=eff_cons, cost_model=self.cost, method=method,
                params=params)
            try:
                alloc = allocate(inp)
            except AllocationFailure as e:
                audit_rows.append({
                    "date": t, "check": "allocator", "status": "FAIL",
                    "value": 0, "note": f"failed_all: {e}"})
                if verbose:
                    print(f"[{t.date()}] allocator failed_all: {e}")
                continue
            target = alloc.weights

            # ---- explainability rows (spec §40) ---------------------------
            mr = alloc.extras.get("marginal_risk")
            cr = alloc.extras.get("component_risk")
            tfp = alloc.extras.get("turnover_from_previous")
            for sym in target.index:
                weight_rows.append({
                    "date": t, "symbol": sym,
                    "prediction": float(cand_df.loc[sym, "prediction"]),
                    "raw_rank": int(cand_df.loc[sym, "raw_rank"]),
                    "volatility": (float(cand_df.loc[sym, "vol"])
                                   if not math.isnan(cand_df.loc[sym, "vol"])
                                   else None),
                    "target_weight": float(target[sym]),
                    "liq_cap": (float(cand_df.loc[sym, "liq_cap"])
                                if not pd.isna(cand_df.loc[sym, "liq_cap"])
                                else None),
                    "industry": cand_df.loc[sym, "industry"],
                    "marginal_risk": (float(mr[sym]) if mr is not None
                                      and sym in mr.index else None),
                    "contribution_to_risk": (float(cr[sym])
                                             if cr is not None
                                             and sym in cr.index else None),
                    "turnover_from_previous": (float(tfp[sym])
                                               if tfp is not None
                                               and sym in tfp.index else None),
                    "optimizer_status": alloc.optimizer_status,
                    "fallback_reason": alloc.fallback_reason,
                })

            # ---- orders (mirror MonthlyBacktest ordering) -----------------
            act: Dict[str, str] = {}
            traded_value = 0.0
            full_value = 0.0

            # 1) full sells for held names that dropped out of the targets
            for sym in [s for s in list(positions) if s not in target.index]:
                sell = positions[sym]
                res = execute_order(sym, t, "SELL", sell,
                                    self.limit_threshold)
                if res.status != TradeStatus.FILLED:
                    act[sym] = f"NO_TRADE({res.reason})"
                    continue
                value = sell * res.fill_price
                fee = self.cost.sell_cost(value)
                cash += value - fee
                del positions[sym]
                full_value += value
                fills_by_date.setdefault(t1, []).append(
                    {"symbol": sym, "shares": -sell, "price": res.fill_price,
                     "cash_delta": value - fee})
                trades.append({
                    "signal_date": t, "exec_date": t1, "symbol": sym,
                    "side": "SELL", "shares": sell, "price": res.fill_price,
                    "value": value, "fee": fee, "target_weight": 0.0,
                    "action": "SELL"})
                act[sym] = "SELL"

            # 2) per-candidate deltas to the target weights
            for sym, w in target.items():
                est_px = px_t.get(sym)
                if est_px is None or math.isnan(est_px):
                    act[sym] = "NO_TRADE(no price)"
                    continue
                target_value = equity * w
                cur_shares = positions.get(sym, 0)
                delta = target_value - cur_shares * est_px
                res = None
                if delta > 0:
                    raw = lot_floor(delta, est_px, cons.lot_size)
                    if raw >= cons.lot_size:
                        res = execute_order(sym, t, "BUY", raw,
                                            self.limit_threshold)
                elif delta < 0:
                    sell = min(int(math.ceil(abs(delta) / est_px)),
                               cur_shares)
                    if sell > 0:
                        res = execute_order(sym, t, "SELL", sell,
                                            self.limit_threshold)
                if res is None or res.status != TradeStatus.FILLED:
                    act[sym] = (f"NO_TRADE({res.reason})"
                                if res is not None
                                else "HOLD")
                    continue
                value = abs(res.shares) * res.fill_price
                if res.shares > 0:
                    fee = self.cost.buy_cost(value)
                    cash_delta = -value - fee
                    side = "BUY"
                else:
                    fee = self.cost.sell_cost(value)
                    cash_delta = value - fee
                    side = "SELL"
                cash += cash_delta
                positions[sym] = positions.get(sym, 0) + res.shares
                if positions[sym] == 0:
                    del positions[sym]
                traded_value += value
                full_value += value
                fills_by_date.setdefault(t1, []).append(
                    {"symbol": sym, "shares": res.shares,
                     "price": res.fill_price, "cash_delta": cash_delta})
                trades.append({
                    "signal_date": t, "exec_date": t1, "symbol": sym,
                    "side": side, "shares": abs(res.shares),
                    "price": res.fill_price, "value": value, "fee": fee,
                    "target_weight": float(w), "action": side})
                act[sym] = side
            for sym in target.index:
                act.setdefault(sym, "HOLD")
            actions[t] = act
            if equity > 0:
                turnover[t] = traded_value / (2.0 * equity)   # 冻结口径
                turnover_full[t] = full_value / (2.0 * equity)

            # ---- allocation audit (spec §42) ------------------------------
            audit_rows.extend(self._audit(t, target, cand_df, eff_cons, univ,
                                          alloc, positions, cash,
                                          fills_by_date.get(t1, []),
                                          turnover.get(t), turnover_full.get(t),
                                          method))
            audit_rows.append({"date": t, "check": "n_candidates",
                               "status": "INFO", "value": str(n_cand),
                               "note": f"top_k={self.top_k}"})
            if target_scaled:
                audit_rows.append({
                    "date": t, "check": "target_scaled", "status": "INFO",
                    "value": f"{eff_target:.4f}",
                    "note": "scarce candidates: frozen under-invest "
                            "semantics (per-pick target fixed)"})

        # ---- phase 2: daily NAV / positions / weights walk ----------------
        nav_records: Dict[pd.Timestamp, float] = {}
        cash_records: Dict[pd.Timestamp, float] = {}
        pos_rows: List[dict] = []
        w_rows: List[dict] = []
        positions = {}
        cash = self.capital0
        for d in days:
            if d in fills_by_date:
                for f in fills_by_date[d]:
                    cash += f["cash_delta"]
                    positions[f["symbol"]] = positions.get(f["symbol"], 0) \
                        + f["shares"]
                    if positions[f["symbol"]] == 0:
                        del positions[f["symbol"]]
            eq = self._equity(data, positions, cash, d)
            nav_records[d] = eq
            cash_records[d] = cash
            pos_rows.append({"date": d, **positions})
            if positions and eq > 0:
                px_d = self._px(data, list(positions.keys()), d)
                w_rows.append({"date": d,
                               **{s: sh * px_d.get(s, 0.0) / eq
                                  for s, sh in positions.items()}})
            else:
                w_rows.append({"date": d})

        pos_all = pd.DataFrame(pos_rows).set_index("date").fillna(0.0)
        w_all = pd.DataFrame(w_rows).set_index("date").fillna(0.0)
        nav = pd.Series(nav_records)
        trades_df = pd.DataFrame(trades)
        weights_df = pd.DataFrame(weight_rows)
        audit_df = pd.DataFrame(audit_rows)
        if not audit_df.empty:
            audit_df["value"] = audit_df["value"].astype("string")
        turnover_s = pd.Series(turnover)
        metrics = self._final_metrics(nav, trades_df, w_all, data, bench_nav,
                                      turnover_s)
        return PortfolioBacktestResult(
            nav=nav, cash=pd.Series(cash_records), positions=pos_all,
            daily_weights=w_all, trades=trades_df, weights=weights_df,
            audit=audit_df, turnover=turnover_s,
            turnover_full=pd.Series(turnover_full), metrics=metrics,
            config=dict(self.alloc_cfg, constraints=cons.to_dict()),
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _next_day(cal: pd.DatetimeIndex, t: pd.Timestamp
                  ) -> Optional[pd.Timestamp]:
        pos = cal.searchsorted(t)
        if pos >= 0 and pos < len(cal) and cal[pos] == t and pos + 1 < len(cal):
            return pd.Timestamp(cal[pos + 1])
        return None

    @staticmethod
    def _audit(t, target, cand_df, cons, univ, alloc, positions, cash,
               t1_fills, turnover_t, turnover_full_t,
               method: str) -> List[dict]:
        rows = []
        def add(check, status, value, note=None):
            rows.append({"date": t, "check": check, "status": status,
                         "value": str(value), "note": note})

        s = float(target.sum())
        add("weight_sum", "PASS" if abs(s - cons.invest_target) <= 1e-4
            else "FAIL", s)
        add("cash_buffer", "PASS"
            if 1.0 - s >= cons.cash_buffer - 1e-4 else "FAIL", 1.0 - s)
        add("max_weight", "PASS"
            if float(target.max()) <= cons.max_weight + 1e-6 else "FAIL",
            float(target.max()))
        ind = cand_df["industry"].reindex(target.index)
        sec = float(target.groupby(ind.fillna("UNKNOWN")).sum().max())
        if method == "equal_weight":
            # P0 = frozen baseline allocation: sector cap not enforced
            add("sector_cap", "SKIP", sec,
                "not enforced for P0 equal_weight (frozen baseline)")
        else:
            add("sector_cap", "PASS" if sec <= cons.sector_cap + 1e-6
                else "FAIL", sec)
        add("no_short", "PASS" if float(target.min()) >= -1e-9 else "FAIL",
            float(target.min()))
        add("no_leverage", "PASS" if s <= 1.0 + 1e-9 else "FAIL", s)
        bad = [x for x in target.index if x not in univ]
        add("tradable", "PASS" if not bad else "FAIL", len(bad),
            str(bad) if bad else None)
        buys = [f for f in t1_fills if f["shares"] > 0]
        bad_lot = [f for f in buys if f["shares"] % cons.lot_size != 0]
        add("lot_size", "PASS" if not bad_lot else "FAIL", len(bad_lot))
        add("execution_cash_nonneg", "PASS" if cash >= 0 else "FAIL", cash)
        add("fallback_recorded", "PASS"
            if alloc.optimizer_status and (
                alloc.optimizer_status == "optimal"
                or alloc.fallback_reason) else "FAIL",
            alloc.optimizer_status, alloc.fallback_reason)
        add("turnover", "INFO", turnover_t if turnover_t is not None
            else float("nan"))
        add("turnover_full", "INFO", turnover_full_t if turnover_full_t
            is not None else float("nan"))
        return rows

    def _final_metrics(self, nav, trades_df, w_all, data, bench_nav,
                       turnover_s) -> dict:
        out = pm.extend_summary(nav, bench_nav, turnover_s, len(trades_df),
                                self.alloc_cfg["method"])
        out.update(pm.weight_metrics(w_all, data.industries))
        out.update(pm.fee_metrics(trades_df, self.capital0))
        return out
