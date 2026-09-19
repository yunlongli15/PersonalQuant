# -*- coding: utf-8 -*-
"""Paper live 单日引擎（spec §5）。

    读取最新可用交易日
      → 检查数据完整性
      → 计算截至当日可获得的全部 feature
      → 运行冻结模型 → 生成预测
      → 非调仓日：HOLD / monitoring snapshot
      → 调仓日：新目标组合 → 交易 → 模拟 T+1 开盘执行 → 更新 paper portfolio
      → 保存结果（append-only）

这一段代码同时被两处使用，**同一条路径**：
  - 真实 forward 运行（date >= 2026-09-18，只记录）
  - 历史引擎验证（date < 2026-09-18，写进另一个 root，绝不碰 forward）

两者唯一差别是 root 和日期，因此"验证过的引擎"就是"将来跑的引擎"。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from . import audit as audit_mod
from . import drift as drift_mod
from .config import freeze_hashes, spec
from .execution import build_orders, execute_orders
from .store import ForwardStore, WriteResult


# ---------------------------------------------------------------------------
# 账户状态
# ---------------------------------------------------------------------------

@dataclass
class PaperPortfolio:
    as_of: Optional[str] = None
    cash: float = 0.0
    holdings: Dict[str, dict] = field(default_factory=dict)   # sym -> {shares,price}
    capital_initial: float = 0.0
    strategy_version: str = ""
    nav: float = 0.0
    peak_nav: float = 0.0

    def as_dict(self) -> dict:
        return {"as_of": self.as_of, "cash": self.cash,
                "holdings": self.holdings,
                "capital_initial": self.capital_initial,
                "strategy_version": self.strategy_version,
                "nav": self.nav, "peak_nav": self.peak_nav}

    @classmethod
    def from_dict(cls, d: dict) -> "PaperPortfolio":
        return cls(**{k: v for k, v in (d or {}).items()
                      if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# 结果
# ---------------------------------------------------------------------------

@dataclass
class DayResult:
    date: str
    signal_date: str
    execution_date: Optional[str]
    is_rebalance: bool
    status: str
    audit: dict = field(default_factory=dict)
    manifest: dict = field(default_factory=dict)
    drift: dict = field(default_factory=dict)
    alerts: List[dict] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    n_predictions: int = 0
    n_orders: int = 0
    n_fills: int = 0
    writes: List[dict] = field(default_factory=list)
    dry_run: bool = False
    pending: bool = False
    idempotent: bool = False
    portfolio: Optional[dict] = None

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


# ---------------------------------------------------------------------------
# 单日运行
# ---------------------------------------------------------------------------

def is_rebalance_date(date: pd.Timestamp, cfg: dict,
                      calendar: pd.DatetimeIndex) -> bool:
    from personal_quant.strategy.rebalance import rebalance_dates
    s = spec(cfg)
    rb = s["portfolio"]["rebalance"]
    d = pd.Timestamp(date)
    lo = (d - pd.Timedelta(days=70)).strftime("%Y-%m-%d")
    dates = rebalance_dates(lo, d.strftime("%Y-%m-%d"),
                            rb["frequency"], rb["rule"])
    return bool(dates) and pd.Timestamp(dates[-1]) == d


def _load_state(store: ForwardStore, cfg: dict) -> PaperPortfolio:
    raw = store.read_state("paper_portfolio")
    if raw is None:
        cap = float(spec(cfg)["capital"]["initial"])
        return PaperPortfolio(cash=cap, capital_initial=cap,
                              strategy_version=spec(cfg)["strategy_version"],
                              nav=cap, peak_nav=cap)
    return PaperPortfolio.from_dict(raw)


def _nav(holdings: Dict[str, dict], cash: float,
         prices: Dict[str, float]) -> float:
    v = cash
    for sym, h in holdings.items():
        px = prices.get(sym, h.get("price", 0.0))
        v += int(h.get("shares", 0)) * float(px or 0.0)
    return float(v)


def run_day(date, cfg: dict, store: ForwardStore, provider,
            dry_run: bool = False, force_rebalance: Optional[bool] = None,
            alerts_fn=None, force_rerun: bool = False) -> DayResult:
    """跑一天。date = 信号日（T）。成交发生在 T+1 开盘。"""
    from personal_quant.strategy.costs import TransactionCostModel

    s = spec(cfg)
    d = pd.Timestamp(date)
    res = DayResult(date=str(d.date()), signal_date=str(d.date()),
                    execution_date=None, is_rebalance=False,
                    status=audit_mod.VALID, dry_run=dry_run)

    # 0. 时间线：forward 运行不得回填（历史验证走另一个 root）
    if not dry_run:
        store.assert_time_order(d)

    # 0.1 幂等：同一天已经记录过就直接返回，绝不重新交易。
    # 调度器重复触发、手滑重跑，都不应该让 paper 账户被交易两次。
    if not dry_run and not force_rerun:
        prev = store.read_json("observations", d)
        if prev is not None:
            met = store.read_frame("metrics", d)
            res.status = prev.get("status", audit_mod.VALID)
            res.is_rebalance = bool(prev.get("is_rebalance"))
            res.n_predictions = int(prev.get("n_predictions", 0))
            res.n_orders = int(prev.get("n_orders", 0))
            res.n_fills = int(prev.get("n_fills", 0))
            res.idempotent = True
            if met is not None and not met.empty:
                res.metrics = met.iloc[-1].to_dict()
            res.writes = [{"kind": "idempotent", "date": str(d.date()),
                           "reason": "该日已记录，本次为无操作重跑"}]
            return res

    cost_model = TransactionCostModel.from_config(
        {"transaction_costs": s["transaction_costs"]})
    pf = _load_state(store, cfg)

    # 0.5 先结掉上一次挂起的订单（实盘：当天收盘后运行时 T+1 还没开盘，
    # 订单会挂在 pending，下次运行再按 T+1 开盘价成交）。
    pend = store.read_state("pending_orders")
    settled = None
    if pend and pend.get("orders"):
        settled = _settle_pending(
            store, provider, cost_model, pf, pend,
            float(s["execution"]["limit_threshold"]),
            lot_size=int(s["portfolio"]["constraints"]["lot_size"]),
            dry_run=dry_run)
        if settled is not None:
            res.n_fills = int(settled.n_trades)
            res.execution_date = pend.get("execution_date")

    # 1. 股票池 + 特征 + 预测
    symbols = provider.universe(d)
    features = provider.feature_matrix(d, symbols)
    custom = provider.custom_factors(d, symbols)
    prices = provider.prices(symbols, d).to_dict()
    names = provider.names(symbols)

    # 2. PIT 审计
    audit = audit_mod.pit_audit(
        provider, d, symbols, features, custom,
        consumed_factors=getattr(provider.stats, "consumed_factors", None))
    res.audit = audit.as_dict()
    completeness = audit_mod.data_completeness(features, custom, symbols)
    res.audit["completeness"] = completeness

    predictions = provider.predict(features, custom)
    res.n_predictions = int(len(predictions))
    pred_df = pd.DataFrame({
        "prediction_date": str(d.date()),
        "signal_date": str(d.date()),
        "symbol": predictions.index,
        "predicted_return": predictions.to_numpy(),
    })
    pred_df["rank"] = pred_df["predicted_return"].rank(ascending=False) \
        .astype(int)
    pred_df["model_version"] = "s3"
    pred_df["strategy_version"] = s["strategy_version"]
    pred_df["data_snapshot_id"] = provider.stats.data_snapshot_id or \
        str(d.date())
    pred_df["feature_version"] = "alpha158"

    # 3. 调仓判断
    # 日历必须来自 provider：引擎不该绕过数据源去读全局文件，
    # 否则 T+1 判定会用错日历（测试用假数据源时尤其明显）。
    try:
        calendar = pd.DatetimeIndex(provider.trading_calendar())
    except Exception:                                        # pragma: no cover
        calendar = pd.DatetimeIndex([d])
    is_reb = is_rebalance_date(d, cfg, calendar) if force_rebalance is None \
        else bool(force_rebalance)
    res.is_rebalance = is_reb

    top_k = int(s["portfolio"]["top_k"])
    if is_reb:
        cand = predictions.sort_values(ascending=False).head(top_k)
        invest = float(s["portfolio"]["constraints"]["invest_target"])
        tw = (invest / len(cand)) if len(cand) else 0.0
        target_weights = {sym: tw for sym in cand.index}
        pred_df["target_weight"] = pred_df["symbol"].map(target_weights) \
            .fillna(0.0)
    else:
        target_weights = {}
        pred_df["target_weight"] = np.nan

    # 4. 组合市值（按当日收盘）
    nav_before = _nav(pf.holdings, pf.cash, prices)

    # 5. 下单 + 执行
    orders, fills, exec_date = [], None, None
    if is_reb and len(target_weights):
        orders = build_orders(target_weights, predictions, names, prices,
                              pf.holdings, nav_before, pf.cash, cost_model,
                              lot_size=int(s["portfolio"]["constraints"]
                                           ["lot_size"]),
                              min_trade_value=float(
                                  s["execution"]["min_trade_value"]))
        exec_date = _next_trading_day(d, calendar)
        res.execution_date = str(pd.Timestamp(exec_date).date()) \
            if exec_date is not None else None
        # T+1 还没开盘（实盘当天收盘后运行）→ 挂单等下次运行再成交。
        # 不挂起的话，实盘每次调仓信号都会"报出去但永远不成交"。
        t1_ready = _t1_has_data(provider, orders, exec_date)
        if t1_ready:
            fills = execute_orders(
                orders, pf.holdings, pf.cash, d,
                float(s["execution"]["limit_threshold"]), cost_model,
                executor=provider.execute,
                lot_size=int(s["portfolio"]["constraints"]["lot_size"]))
            pf.holdings = fills.new_holdings
            pf.cash = fills.cash
            res.n_fills = int(fills.n_trades)
        else:
            res.pending = True
            if not dry_run:
                store.write_state("pending_orders", {
                    "signal_date": str(d.date()),
                    "execution_date": str(pd.Timestamp(exec_date).date())
                    if exec_date is not None else None,
                    "orders": [o.as_row() for o in orders],
                })

    # 6. 收盘估值
    mark_prices = dict(prices)
    if fills is not None and exec_date is not None:
        try:
            mark_prices.update(
                provider.prices(list(pf.holdings), exec_date).to_dict())
        except Exception:
            pass
    nav_after = _nav(pf.holdings, pf.cash, mark_prices)
    pf.as_of = str(pd.Timestamp(exec_date if exec_date is not None
                                else d).date())
    pf.nav = nav_after
    pf.peak_nav = max(pf.peak_nav or nav_after, nav_after)
    pf.strategy_version = s["strategy_version"]
    if pf.capital_initial <= 0:
        pf.capital_initial = float(s["capital"]["initial"])

    traded = fills.traded_value if fills is not None else 0.0
    fees = fills.fees if fills is not None else 0.0
    turnover = traded / nav_before if nav_before else 0.0
    res.metrics = {
        "signal_date": str(d.date()),
        "execution_date": res.execution_date,
        "is_rebalance": is_reb,
        "portfolio_value": nav_after,
        "cash": pf.cash,
        "cash_weight": pf.cash / nav_after if nav_after else np.nan,
        "n_positions": len(pf.holdings),
        "cumulative_return": nav_after / pf.capital_initial - 1.0
        if pf.capital_initial else np.nan,
        "drawdown": nav_after / pf.peak_nav - 1.0 if pf.peak_nav else np.nan,
        "turnover": turnover,
        "transaction_cost": fees,
        "traded_value": traded,
        "n_orders": len(orders),
        "n_fills": res.n_fills,
    }
    res.n_orders = len(orders)
    res.portfolio = pf.as_dict()

    # 7. 漂移
    res.drift = {
        "strategy": drift_mod.strategy_drift(cfg),
        "model": drift_mod.model_drift(predictions,
                                       drift_mod.load_model_baseline()),
        "concentration": drift_mod.prediction_concentration(
            predictions, float(s["alerts"]["concentration_top1_z"])),
    }

    # 8. 告警
    emit = alerts_fn if alerts_fn is not None else (lambda **kw: [])
    try:
        res.alerts = emit(metrics=res.metrics, drift=res.drift,
                          audit=res.audit, cfg=cfg)
    except Exception as e:                                   # pragma: no cover
        res.alerts = [{"level": "WARNING", "code": "ALERT_ERROR",
                       "detail": str(e)}]

    # 9. 状态汇总：PIT 违例 = INVALID
    if audit.status == audit_mod.INVALID or \
            res.drift["strategy"]["status"] == "DRIFT_DETECTED":
        res.status = audit_mod.INVALID
    elif audit.status == audit_mod.WARNING or \
            any(a.get("level") == "WARNING" for a in res.alerts):
        res.status = audit_mod.WARNING
    else:
        res.status = audit_mod.VALID

    # 10. manifest（§7：日后能复盘"当时系统知道什么"）
    res.manifest = _build_manifest(d, provider, pf, cfg, res, is_reb)

    # 11. 落盘
    if not dry_run:
        if res.status != audit_mod.INVALID:
            res.writes.append(store.write_frame("predictions", d, pred_df)
                              .as_dict())
            res.writes.append(store.write_frame(
                "portfolio", d, _holdings_frame(pf, mark_prices)).as_dict())
            res.writes.append(store.write_frame(
                "metrics", d, pd.DataFrame([res.metrics])).as_dict())
            if fills is not None and not fills.orders.empty:
                res.writes.append(store.write_frame("trades", d,
                                                    fills.orders).as_dict())
        else:
            res.writes.append({"kind": "skipped", "reason":
                               "INVALID_RUN: 不写正式 forward metrics"})
        res.writes.append(store.write_json("manifests", d, res.manifest
                                           ).as_dict())
        res.writes.append(store.write_json("observations", d, {
            "date": str(d.date()), "status": res.status,
            "is_rebalance": is_reb, "n_predictions": res.n_predictions,
            "n_orders": res.n_orders, "n_fills": res.n_fills,
            "audit_status": audit.status,
            "drift": {k: v.get("status") for k, v in res.drift.items()},
            "alerts": [a["code"] for a in res.alerts],
            "manifest": res.manifest,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).as_dict())
        if res.alerts:
            res.writes.append(store.write_json("alerts", d,
                                               {"alerts": res.alerts}
                                               ).as_dict())
        res.writes.append(store.write_state("paper_portfolio",
                                            pf.as_dict()).as_dict())
    return res


def _t1_has_data(provider, orders, exec_date) -> bool:
    """T+1 的行情到手了吗？没有就挂单等下一次运行。"""
    if exec_date is None or not orders:
        return False
    syms = [o.symbol for o in orders]
    try:
        px = provider.prices(syms, pd.Timestamp(exec_date))
    except Exception:                                        # pragma: no cover
        return False
    return px is not None and not px.empty


def _settle_pending(store, provider, cost_model, pf, pend: dict,
                    limit_threshold: float, lot_size: int = 100,
                    dry_run: bool = False):
    """把上一次挂起的订单在 T+1 开盘成交（如果行情已经到了）。"""
    from .execution import PlannedOrder

    d = pd.Timestamp(pend["signal_date"])
    orders = []
    for r in pend["orders"]:
        orders.append(PlannedOrder(
            symbol=r["symbol"], name=r.get("name", ""),
            rank=int(r.get("rank", 0) or 0),
            prediction=float(r.get("predicted_return", np.nan)),
            current_weight=float(r.get("current_weight", 0.0)),
            target_weight=float(r.get("target_weight", 0.0)),
            current_value=float(r.get("current_value", 0.0)),
            target_value=float(r.get("target_value", 0.0)),
            delta_value=float(r.get("delta_value", 0.0)),
            price=float(r.get("price", np.nan)),
            theoretical_shares=float(r.get("theoretical_shares", 0.0)),
            estimated_shares=int(r.get("estimated_shares", 0)),
            estimated_trade_value=float(r.get("estimated_trade_value", 0.0)),
            estimated_fee=float(r.get("estimated_fee", 0.0)),
            action=r.get("action", "NO_TRADE"),
            execution_rule=r.get("execution_rule", "T1_open"),
            note=r.get("note", "")))
    if not _t1_has_data(provider, orders, pd.Timestamp(pend["execution_date"])):
        return None
    fills = execute_orders(orders, pf.holdings, pf.cash, d, limit_threshold,
                           cost_model, executor=provider.execute,
                           lot_size=lot_size)
    pf.holdings = fills.new_holdings
    pf.cash = fills.cash
    if not dry_run:
        store.write_state("pending_orders", {"settled_at": str(
            pd.Timestamp(pend["execution_date"]).date()), "orders": []})
    return fills


def _next_trading_day(d: pd.Timestamp,
                      calendar: pd.DatetimeIndex) -> Optional[pd.Timestamp]:
    after = calendar[calendar > pd.Timestamp(d)]
    return pd.Timestamp(after[0]) if len(after) else None


def _holdings_frame(pf: PaperPortfolio, prices: Dict[str, float]
                    ) -> pd.DataFrame:
    rows = []
    for sym, h in pf.holdings.items():
        px = float(prices.get(sym, h.get("price", 0.0)) or 0.0)
        val = int(h.get("shares", 0)) * px
        rows.append({"symbol": sym, "shares": int(h.get("shares", 0)),
                     "price": px, "market_value": val})
    df = pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["symbol", "shares", "price", "market_value"])
    total = df["market_value"].sum() + pf.cash
    df["weight"] = df["market_value"] / total if total else 0.0
    df.attrs["cash"] = pf.cash
    return df.assign(cash=pf.cash, portfolio_value=total,
                     as_of=pf.as_of or "")


def _build_manifest(d: pd.Timestamp, provider, pf: PaperPortfolio, cfg: dict,
                    res: DayResult, is_reb: bool) -> dict:
    import platform
    import sys

    from .config import config_sha256
    s = spec(cfg)
    try:
        from factors.base import load_calendar
        cal = load_calendar()
        latest_data = str(pd.Timestamp(cal[-1]).date())
    except Exception:                                        # pragma: no cover
        latest_data = None
    return {
        "signal_date": str(d.date()),
        "latest_data_date": latest_data,
        "data_snapshot_id": provider.stats.data_snapshot_id or latest_data,
        "strategy_version": s["strategy_version"],
        "model_version": "s3",
        "feature_version": "alpha158",
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "git_commit": _git_commit(),
        "config_sha256": config_sha256(),
        "freeze_hashes": freeze_hashes(cfg),
        "is_rebalance": is_reb,
        "status": res.status,
        "provider_stats": provider.stats.__dict__,
        "capital_initial": pf.capital_initial,
        "rebalance_frequency": s["portfolio"]["rebalance"]["frequency"],
        "top_k": s["portfolio"]["top_k"],
    }


def _git_commit() -> str:
    import subprocess
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"],
                              capture_output=True, text=True,
                              cwd=Path(__file__).resolve().parents[1]
                              ).stdout.strip() or "unknown"
    except Exception:                                        # pragma: no cover
        return "unknown"
