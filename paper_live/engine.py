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
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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

def _period_offset(frequency: str):
    """周期偏移，与 `rebalance_dates` 用同一张表（单一来源）。"""
    from personal_quant.strategy.rebalance import FREQ_MAP
    if frequency not in FREQ_MAP:
        raise ValueError(f"unsupported frequency {frequency!r}")
    return pd.tseries.frequencies.to_offset(FREQ_MAP[frequency])


def _as_calendar(calendar) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(sorted({pd.Timestamp(x) for x in calendar}))


def is_rebalance_date(date: pd.Timestamp, cfg: dict,
                      calendar: pd.DatetimeIndex) -> bool:
    """d 是不是**本周期**（月/周，由配置决定）的最后一个交易日。

    语义与 `rebalance_dates(完整区间)` 一致 —— 但差一处，而且这一处是
    必需的：**日历里还没有 d 之后的交易日时，无法确认 d 所在周期是否已经
    结束，此时保守返回 False，而不是猜。**

    为什么不能直接判定："d 是不是本月最后一个交易日"需要知道 d 之后同月
    还有没有交易日，而 `trading_calendar` 只装**已经发生**的交易日
    （2026-10-01 实测：最大 2026-09-29）。旧实现把窗口取成 `[d-70天, d]`
    再比较 `dates[-1] == d`，而该窗口每个周期分组的最后一个元素**恒等于 d**
    —— 于是只要 d 是交易日就返回 True（2026-08 全月 21 个交易日里 20 个
    被误判，见 reports/daily_exit_paper_v1_audit.md §3.2）。

    `calendar` 必须是**真实交易日历**（provider.trading_calendar()）。
    旧实现虽然收了这个形参却完全没用、直接去查 DB，与 run_day 里
    "日历必须来自 provider" 的注释自相矛盾。
    """
    s = spec(cfg)
    rb = s["portfolio"]["rebalance"]
    rule = rb["rule"]
    if rule not in ("last_trading_day", "first_trading_day"):
        raise ValueError(f"unsupported rule {rule!r}")
    offset = _period_offset(rb["frequency"])

    d = pd.Timestamp(date)
    cal = _as_calendar(calendar)
    if d not in cal:
        return False                                  # 非交易日
    if rule == "last_trading_day":
        later = cal[cal > d]
        if len(later) == 0:
            return False                              # 本周期是否结束尚不可知
        return later[0].to_period(offset) != d.to_period(offset)
    earlier = cal[cal < d]
    if len(earlier) == 0:
        return False
    return earlier[-1].to_period(offset) != d.to_period(offset)


def rebalance_signal_date(run_date, cfg: dict,
                          calendar: pd.DatetimeIndex) -> Optional[pd.Timestamp]:
    """在 run_date 运行时**应当补做**的那次调仓的**信号日**；没有则 None。

    调仓日当天无法确认自己是调仓日（见 `is_rebalance_date`）。等到下一个
    周期的第一个交易日，上一个交易日就被确认为调仓日了 —— 这时以**上一个
    交易日**为信号日补做这次调仓。

    执行正好落在今天开盘：`execute_order` 内部算的是
    `next_trading_day(signal_date)`，而它 == run_date。因此：

      * 信号日仍然是**上个月最后一个交易日**（没有被挪到下个月第一天）；
      * 特征与预测只用 <= signal_date 的数据；
      * 成交价是今天**已经发生**的开盘价，不涉及任何未来数据。

    代价（有意为之）：**错过那一天就是错过这次调仓**，不回溯补单 ——
    回溯会把"用一个已经过去很久的开盘价成交"变成编造。
    """
    cal = _as_calendar(calendar)
    d = pd.Timestamp(run_date)
    earlier = cal[cal < d]
    if len(earlier) == 0:
        return None
    prev = pd.Timestamp(earlier[-1])
    return prev if is_rebalance_date(prev, cfg, cal) else None


# ---------------------------------------------------------------------------
# C1：挂单生命周期
#
# 铁律：**"T+1 行情还没到"不是失败**。T 日收盘后运行时，T+1 必然还不存在
# （交易日历只装已经发生的交易日），此时订单必须保持 PENDING，等下一次
# 运行再看 —— 而不是被判成 NO_FILL / FAILED，更不能被下一次运行覆盖掉。
# ---------------------------------------------------------------------------

#: pending_orders.json 的结构版本。旧文件没有这个标记 -> 一律按"遗留"处理，
#: 既不结算也不覆盖，归档留证（它的 exec_date 是 null、信号早已过期）。
PENDING_FORMAT = "paper_live.pending/2"

_PENDING_STATE = "pending_orders"


class Availability(str, Enum):
    READY = "READY"        # T+1 已存在 -> 可以判成交
    NOT_YET = "NOT_YET"    # T+1 尚未出现 -> 保持 PENDING（正常，不是失败）
    ERROR = "ERROR"        # 查询本身出错 -> 必须 raise，不能吞


class PendingError(RuntimeError):
    """结算挂单时遇到的**系统级**错误（DB / schema / SQL / 类型 / 文件）。

    与 NOT_YET（"T+1 还没到"，正常状态）严格区分：这里必须让上层看见。
    """


def next_observed_session(calendar, after) -> Optional[pd.Timestamp]:
    """已观测交易日历里 strictly after `after` 的第一个交易日。"""
    cal = _as_calendar(calendar)
    later = cal[cal > pd.Timestamp(after)]
    return pd.Timestamp(later[0]) if len(later) else None


def t1_availability(provider, signal_date
                    ) -> Tuple[Availability, Optional[pd.Timestamp], str]:
    """T+1 的行情到货了吗？三态判定，完全显式。

    READY   —— 日历里存在 signal_date 之后的交易日。此时**单只股票没有
               bar 是可判定的 NO_FILL（停牌）**，不是"再等等"：那一天出现
               在日历里说明市场有成交、数据已经入库，那么这只票当天就是
               没交易，真实挂单同样不会成交。
    NOT_YET —— 日历里还没有 signal_date 之后的交易日。保持 PENDING。
    ERROR   —— 读取失败。抛 PendingError，**绝不 return False 吞掉**。

    旧实现用 `except Exception: return False`，于是
    `pd.Timestamp(None) -> NaT` 引起的 DuckDB 类型错误被静默吞掉，
    挂单永远不结算、也不报错（reports/daily_exit_paper_v1_audit.md §3.1）。
    这里刻意不写任何兜底 except。
    """
    try:
        cal = provider.trading_calendar()
    except Exception as e:                                   # noqa: BLE001
        # 这一层 except 是**为了抛**，不是为了吞：包成 PendingError 并带上
        # 原始异常，让 job store 记 FAILED、让用户看见。
        raise PendingError(
            f"读取交易日历失败：{type(e).__name__}: {e}") from e
    nxt = next_observed_session(cal, signal_date)
    if nxt is None:
        last = _as_calendar(cal)[-1]
        return (Availability.NOT_YET, None,
                f"已观测交易日历止于 {last.date()}，尚无 "
                f"{pd.Timestamp(signal_date).date()} 之后的交易日")
    return Availability.READY, nxt, f"下一个交易日 {nxt.date()}"


def order_id(strategy_version: str, signal_date, symbol: str, side: str) -> str:
    """挂单唯一键：同一 (版本, 信号日, 标的, 方向) 不得重复创建。"""
    return (f"{strategy_version}:{pd.Timestamp(signal_date).date()}:"
            f"{symbol}:{side}")


def load_pending(store: ForwardStore) -> dict:
    """读挂单文件的结构化视图。

    只做读取与形状归一，**不做任何结算或清理** —— 是否遗留由调用方判断。
    """
    raw = store.read_state(_PENDING_STATE) or {}
    return {
        "format": raw.get("format"),
        "orders": [dict(r) for r in (raw.get("orders") or [])],
        "attempts": list(raw.get("attempts") or []),
        "legacy": bool(raw) and raw.get("format") != PENDING_FORMAT,
        "raw": raw,
    }


def archive_legacy_pending(store: ForwardStore, raw: dict,
                           dry_run: bool = False) -> Optional[Path]:
    """把**旧格式**挂单文件原样另存一份，绝不覆盖它。

    为什么归档而不是结算：旧文件的 `execution_date` 是 null，信号日可能
    已经在几个月前。拿今天的日历去"补成交"，等于用一个早已过去很久的
    开盘价编造一笔历史成交 —— 那不是观察，是伪造。
    """
    if dry_run:
        return None
    p = store.state_path(_PENDING_STATE)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dst = p.with_name(f"{_PENDING_STATE}.legacy-{stamp}.json")
    dst.write_text(json.dumps(raw, ensure_ascii=False, indent=2,
                              default=str), encoding="utf-8")
    print(f"[paper_live] 旧格式挂单已归档为 {dst.name}"
          f"（不结算：execution_date 为空、信号已过期）；"
          f"新一批挂单从本次运行重新开始", flush=True)
    return dst


def _pending_payload(orders: List[dict], attempts: List[dict]) -> dict:
    return {
        "format": PENDING_FORMAT,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "orders": orders,
        "attempts": attempts[-200:],      # 审计留痕，但不无限增长
    }


def record_attempt(attempts: List[dict], run_date, signal_date,
                   exec_date, availability: Availability, result: str,
                   error: Optional[str] = None) -> dict:
    """一次挂单处理尝试的完整留痕。"""
    rec = {
        "attempt_timestamp": datetime.now(timezone.utc).isoformat(),
        "observed_run_date": str(pd.Timestamp(run_date).date()),
        "signal_date": str(pd.Timestamp(signal_date).date()),
        "resolved_exec_date": (str(pd.Timestamp(exec_date).date())
                               if exec_date is not None else None),
        "availability_state": availability.value,
        "result": result,
        "error_if_any": error,
    }
    attempts.append(rec)
    return rec


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


class LedgerMismatch(RuntimeError):
    """现金与账本重算值不一致 —— 说明状态与记录已经对不上。"""


def ledger_cash(store: ForwardStore, capital_initial: float) -> float:
    """从 append-only 的成交与费用记录重算现金：**账本是真相**。

        期末现金 = 初始本金 − Σ(成交现金流) − Σ(当日交易费用)

    `filled_shares` 买正卖负，所以 `filled_shares × fill_price` 本身就是
    带符号的现金流。`paper_portfolio.json` 只是这份账的缓存指针。
    """
    cash = float(capital_initial)
    trades_dir = store.root / "trades"
    if trades_dir.exists():
        for p in sorted(trades_dir.glob("*.parquet")):
            if "__rev" in p.stem:
                continue
            df = pd.read_parquet(p)
            need = {"status", "filled_shares", "fill_price"}
            if df.empty or not need.issubset(df.columns):
                continue
            ok = df[df["status"] == "FILLED"]
            if ok.empty:
                continue
            cash -= float((ok["filled_shares"].astype(float)
                           * ok["fill_price"].astype(float)).sum())
    metrics_dir = store.root / "metrics"
    if metrics_dir.exists():
        for p in sorted(metrics_dir.glob("*.parquet")):
            if "__rev" in p.stem:
                continue
            df = pd.read_parquet(p)
            if df.empty or "transaction_cost" not in df.columns:
                continue
            v = df["transaction_cost"].iloc[-1]
            cash -= 0.0 if v is None or pd.isna(v) else float(v)
    return cash


def assert_portfolio_matches_ledger(store: ForwardStore, pf: PaperPortfolio,
                                    tol: float = 0.01) -> float:
    """`paper_portfolio.json` 是缓存，账本是真相；对不上 -> raise。

    **绝不自动改账**：自动修补会把"账错了"变成"账悄悄被改了"，
    而那正是这个系统最不该发生的事。宁可停下来让人核对。
    """
    expected = ledger_cash(store, pf.capital_initial)
    if abs(expected - float(pf.cash)) > tol:
        raise LedgerMismatch(
            f"现金对账失败：账本重算 {expected:,.2f}，"
            f"paper_portfolio.json 记的是 {float(pf.cash):,.2f}，"
            f"差 {expected - float(pf.cash):+,.2f}。"
            f"不自动改账 —— 请人工核对 trades/ 与 metrics/。")
    return expected


def run_day(date, cfg: dict, store: ForwardStore, provider,
            dry_run: bool = False, force_rebalance: Optional[bool] = None,
            alerts_fn=None, force_rerun: bool = False,
            signal_date=None) -> DayResult:
    """跑一天。

    两个日期必须分开（C2 的产物）：

      * `date`        —— **运行日**：观测文件写在哪天、时间线推进到哪天。
      * `signal_date` —— **信号日**：模型打分与下单所依据的截面是哪天。

    通常两者相同。只有在"补做上月调仓"时不同：月初第一个交易日运行时，
    上一个交易日才刚被确认为上月最后一个交易日（见 `rebalance_signal_date`），
    此时 `signal_date` = 上一个交易日，而执行正好落在今天的开盘。
    """
    from personal_quant.strategy.costs import TransactionCostModel

    s = spec(cfg)
    run_d = pd.Timestamp(date)
    sig_d = pd.Timestamp(signal_date) if signal_date is not None else run_d
    res = DayResult(date=str(run_d.date()), signal_date=str(sig_d.date()),
                    execution_date=None, is_rebalance=False,
                    status=audit_mod.VALID, dry_run=dry_run)
    if sig_d > run_d:
        raise ValueError(
            f"signal_date {sig_d.date()} 不得晚于运行日 {run_d.date()}")

    # 0. 时间线：forward 运行不得回填（历史验证走另一个 root）
    if not dry_run:
        store.assert_time_order(run_d)

    # 0.1 幂等：同一天已经记录过就直接返回，绝不重新交易。
    # 调度器重复触发、手滑重跑，都不应该让 paper 账户被交易两次。
    if not dry_run and not force_rerun:
        prev = store.read_json("observations", run_d)
        if prev is not None:
            met = store.read_frame("metrics", run_d)
            res.status = prev.get("status", audit_mod.VALID)
            res.is_rebalance = bool(prev.get("is_rebalance"))
            res.n_predictions = int(prev.get("n_predictions", 0))
            res.n_orders = int(prev.get("n_orders", 0))
            res.n_fills = int(prev.get("n_fills", 0))
            res.idempotent = True
            if met is not None and not met.empty:
                res.metrics = met.iloc[-1].to_dict()
            res.writes = [{"kind": "idempotent", "date": str(run_d.date()),
                           "reason": "该日已记录，本次为无操作重跑"}]
            return res

    cost_model = TransactionCostModel.from_config(
        {"transaction_costs": s["transaction_costs"]})
    pf = _load_state(store, cfg)
    if not dry_run:
        # 状态是缓存、账本是真相：动手之前先确认两者一致。
        assert_portfolio_matches_ledger(store, pf)

    # 0.5 先结掉上一次挂起的订单。
    pend = load_pending(store)
    if pend["legacy"]:
        # 旧格式（execution_date=null、无逐单 signal_date）：**不结算**，
        # 归档留证后从零开始 —— 拿今天的日历补一笔几个月前的成交是伪造。
        archived = archive_legacy_pending(store, pend["raw"], dry_run=dry_run)
        if not dry_run:
            # 归档副本已经拿到，工作文件清空成新格式 —— 否则每次运行
            # 都会把同一份旧文件再归档一遍。
            store.write_state(_PENDING_STATE, _pending_payload([], []))
        pend = {"format": PENDING_FORMAT, "orders": [], "attempts": [],
                "legacy": False, "raw": {}}
        res.writes.append({"kind": "legacy_pending_archived",
                           "path": str(archived) if archived else None,
                           "reason": "旧格式挂单不结算，只归档"})
    settled = None
    batch_frames: List[pd.DataFrame] = []
    if pend["orders"]:
        settled = _settle_pending(
            store, provider, cost_model, pf, pend,
            float(s["execution"]["limit_threshold"]),
            lot_size=int(s["portfolio"]["constraints"]["lot_size"]),
            run_date=run_d, dry_run=dry_run)
        if settled.n_trades:
            res.n_fills = int(settled.n_trades)
            res.execution_date = settled.exec_dates[-1]
        batch_frames.extend(settled.frames)
        res.writes.extend(settled.writes)

    # 1. 股票池 + 特征 + 预测（全部以**信号日**为准）
    symbols = provider.universe(sig_d)
    features = provider.feature_matrix(sig_d, symbols)
    custom = provider.custom_factors(sig_d, symbols)
    prices = provider.prices(symbols, sig_d).to_dict()
    names = provider.names(symbols)

    # 2. PIT 审计
    audit = audit_mod.pit_audit(
        provider, sig_d, symbols, features, custom,
        consumed_factors=getattr(provider.stats, "consumed_factors", None))
    res.audit = audit.as_dict()
    completeness = audit_mod.data_completeness(features, custom, symbols)
    res.audit["completeness"] = completeness

    predictions = provider.predict(features, custom)
    res.n_predictions = int(len(predictions))
    pred_df = pd.DataFrame({
        "prediction_date": str(sig_d.date()),
        "signal_date": str(sig_d.date()),
        "symbol": predictions.index,
        "predicted_return": predictions.to_numpy(),
    })
    pred_df["rank"] = pred_df["predicted_return"].rank(ascending=False) \
        .astype(int)
    pred_df["model_version"] = "s3"
    pred_df["strategy_version"] = s["strategy_version"]
    pred_df["data_snapshot_id"] = provider.stats.data_snapshot_id or \
        str(sig_d.date())
    pred_df["feature_version"] = "alpha158"

    # 3. 调仓判断
    # 日历必须来自 provider：引擎不该绕过数据源去读全局文件，
    # 否则 T+1 判定会用错日历（测试用假数据源时尤其明显）。
    try:
        calendar = pd.DatetimeIndex(provider.trading_calendar())
    except Exception:                                        # pragma: no cover
        calendar = pd.DatetimeIndex([sig_d])
    # signal_date 被显式指定 = 这次是"补做已确认的上月调仓"；
    # 否则按已观测日历判断 sig_d 本身是不是调仓日。
    is_reb = (is_rebalance_date(sig_d, cfg, calendar)
              if force_rebalance is None else bool(force_rebalance))
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

    # 4. 组合市值（按信号日收盘）
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
        avail, exec_date, detail = t1_availability(provider, sig_d)
        if avail is Availability.READY:
            res.execution_date = str(exec_date.date())
            fills = execute_orders(
                orders, pf.holdings, pf.cash, sig_d,
                float(s["execution"]["limit_threshold"]), cost_model,
                executor=provider.execute,
                lot_size=int(s["portfolio"]["constraints"]["lot_size"]))
            pf.holdings = fills.new_holdings
            pf.cash = fills.cash
            res.n_fills += int(fills.n_trades)
            if not fills.orders.empty:
                batch_frames.append(fills.orders)
        else:
            # T+1 还没到（实盘当天收盘后运行的常态）-> 挂单，保持 PENDING。
            # 这不是失败：绝不判 NO_FILL，也绝不被下一次运行覆盖。
            res.pending = True
            res.execution_date = None
            if not dry_run:
                _append_pending(store, pend, orders, sig_d, run_d,
                                avail, detail, s["strategy_version"])
                res.writes.append({"kind": "pending_orders",
                                   "state": "PENDING",
                                   "signal_date": str(sig_d.date()),
                                   "n_orders": len(orders)})

    # 6. 收盘估值
    mark_prices = dict(prices)
    mark_date = exec_date if exec_date is not None else sig_d
    if not dry_run and res.execution_date is not None:
        try:
            mark_prices.update(
                provider.prices(list(pf.holdings), mark_date).to_dict())
        except Exception:                                    # noqa: BLE001
            # 标记价拿不到只是估值口径回退到信号日收盘，不影响账目；
            # 但要让它在日志里留下痕迹，而不是完全无声。
            print(f"[paper_live] WARNING 取不到 {mark_date.date()} 的标记价，"
                  f"组合估值回退到信号日收盘", flush=True)
    nav_after = _nav(pf.holdings, pf.cash, mark_prices)
    pf.as_of = str(pd.Timestamp(mark_date).date())
    pf.nav = nav_after
    pf.peak_nav = max(pf.peak_nav or nav_after, nav_after)
    pf.strategy_version = s["strategy_version"]
    if pf.capital_initial <= 0:
        pf.capital_initial = float(s["capital"]["initial"])

    traded = (fills.traded_value if fills is not None else 0.0) + \
        (settled.traded_value if settled is not None else 0.0)
    fees = (fills.fees if fills is not None else 0.0) + \
        (settled.fees if settled is not None else 0.0)
    turnover = traded / nav_before if nav_before else 0.0
    res.metrics = {
        "signal_date": str(sig_d.date()),
        "run_date": str(run_d.date()),
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
        "pending": res.pending,
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
    res.manifest = _build_manifest(run_d, sig_d, provider, pf, cfg, res, is_reb)

    # 11. 落盘
    if not dry_run:
        if res.status != audit_mod.INVALID:
            res.writes.append(store.write_frame("predictions", run_d, pred_df)
                              .as_dict())
            res.writes.append(store.write_frame(
                "portfolio", run_d,
                _holdings_frame(pf, mark_prices)).as_dict())
            res.writes.append(store.write_frame(
                "metrics", run_d, pd.DataFrame([res.metrics])).as_dict())
            # 结算批次与本次立即成交批次都进同一天的 trades/ ——
            # 账本必须完整，否则"现金 = 账本重算值"这条对账（§1.6）不成立。
            if batch_frames:
                res.writes.append(store.write_frame(
                    "trades", run_d,
                    pd.concat(batch_frames, ignore_index=True)).as_dict())
        else:
            res.writes.append({"kind": "skipped", "reason":
                               "INVALID_RUN: 不写正式 forward metrics"})
        res.writes.append(store.write_json("manifests", run_d, res.manifest
                                           ).as_dict())
        res.writes.append(store.write_json("observations", run_d, {
            "date": str(run_d.date()),
            "signal_date": str(sig_d.date()),
            "status": res.status,
            "is_rebalance": is_reb, "n_predictions": res.n_predictions,
            "n_orders": res.n_orders, "n_fills": res.n_fills,
            "pending": res.pending,
            "audit_status": audit.status,
            "drift": {k: v.get("status") for k, v in res.drift.items()},
            "alerts": [a["code"] for a in res.alerts],
            "manifest": res.manifest,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).as_dict())
        if res.alerts:
            res.writes.append(store.write_json("alerts", run_d,
                                               {"alerts": res.alerts}
                                               ).as_dict())
        # INVALID 的运行**不推进账户指针**：现金变了却没有对应的 trades/，
        # 账本与实际就永久对不上了。账本一致性（§1.6）靠这一条成立。
        if res.status != audit_mod.INVALID:
            res.writes.append(store.write_state("paper_portfolio",
                                                pf.as_dict()).as_dict())
    return res


def _planned_from_row(r: dict):
    """把挂单文件里的一行还原成 PlannedOrder。"""
    from .execution import PlannedOrder

    return PlannedOrder(
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
        note=r.get("note", ""))


def _row_from_order(order, strategy_version: str,
                    signal_date) -> dict:
    """PlannedOrder -> 挂单文件里的一行（带稳定 order_id）。"""
    side = "BUY" if order.estimated_shares > 0 else "SELL"
    row = dict(order.as_row())
    row["order_id"] = order_id(strategy_version, signal_date,
                               order.symbol, side)
    row["signal_date"] = str(pd.Timestamp(signal_date).date())
    row["exec_rule"] = "NEXT_SESSION_OPEN"
    row["status"] = "PENDING"
    row["resolved_exec_date"] = None
    return row


def _append_pending(store: ForwardStore, pend: dict, orders, signal_date,
                    run_date, availability: Availability, detail: str,
                    strategy_version: str) -> None:
    """读-改-写：保留仍然 PENDING 的单，追加新单，按 order_id 去重。

    旧实现每次运行都写一个**全新的 payload**，于是上一批还没成交的挂单
    无声消失（2026-09 实际发生：09-18 / 09-24 两批被 09-29 那批覆盖）。
    这里反过来：先读、再并、最后写，order_id 相同的一律不重复创建。
    """
    existing = list(pend.get("orders") or [])
    seen = {r.get("order_id") for r in existing}
    for o in orders:
        row = _row_from_order(o, strategy_version, signal_date)
        if row["order_id"] in seen:
            continue
        seen.add(row["order_id"])
        existing.append(row)
    attempts = list(pend.get("attempts") or [])
    record_attempt(attempts, run_date, signal_date, None, availability,
                   "KEEP_PENDING", detail)
    store.write_state(_PENDING_STATE, _pending_payload(existing, attempts))


@dataclass
class Settlement:
    """一次运行里"结算挂单"的结果汇总。"""
    n_trades: int = 0
    fees: float = 0.0
    traded_value: float = 0.0
    exec_dates: List[str] = field(default_factory=list)
    frames: List[pd.DataFrame] = field(default_factory=list)
    writes: List[dict] = field(default_factory=list)


def _settle_pending(store, provider, cost_model, pf, pend: dict,
                    limit_threshold: float, lot_size: int = 100,
                    run_date=None, dry_run: bool = False) -> Settlement:
    """结算挂单：**只有 READY 才判成交**，NOT_YET 一律保持 PENDING。

    按 signal_date 分组（正常情况下只会有一组）：每组各自问一次
    "T+1 到了吗"，所以一组还没到不会拖住另一组。

    ERROR（读数据本身失败）时先落一条 attempt 再把异常抛出去 ——
    留痕与"不吞"同时做到。
    """
    out = Settlement()
    remaining: List[dict] = []
    groups: Dict[str, List[dict]] = {}
    for r in pend["orders"]:
        groups.setdefault(str(r.get("signal_date") or ""), []).append(r)
    attempts = list(pend.get("attempts") or [])

    for sig in sorted(groups):
        rows = groups[sig]
        signal_date = pd.Timestamp(sig)
        try:
            avail, exec_date, detail = t1_availability(provider, signal_date)
        except PendingError as e:
            record_attempt(attempts, run_date, signal_date, None,
                           Availability.ERROR, "RAISED", str(e))
            if not dry_run:
                store.write_state(
                    _PENDING_STATE,
                    _pending_payload(remaining + rows, attempts))
            raise
        if avail is Availability.NOT_YET:
            record_attempt(attempts, run_date, signal_date, None, avail,
                           "KEEP_PENDING", detail)
            remaining.extend(rows)
            continue
        fills = execute_orders(
            [_planned_from_row(r) for r in rows], pf.holdings, pf.cash,
            signal_date, limit_threshold, cost_model,
            executor=provider.execute, lot_size=lot_size)
        pf.holdings = fills.new_holdings
        pf.cash = fills.cash
        out.n_trades += int(fills.n_trades)
        out.fees += float(fills.fees)
        out.traded_value += float(fills.traded_value)
        out.exec_dates.append(str(exec_date.date()))
        if not fills.orders.empty:
            out.frames.append(fills.orders)
        record_attempt(attempts, run_date, signal_date, exec_date, avail,
                       "SETTLED",
                       f"{fills.n_trades} 笔成交 / 未成交 "
                       f"{len(fills.orders) - fills.n_trades} 笔")

    if not dry_run:
        store.write_state(_PENDING_STATE,
                          _pending_payload(remaining, attempts))
        out.writes.append({
            "kind": "pending_orders",
            "state": "SETTLED" if not remaining else "PARTIAL",
            "remaining": len(remaining), "n_trades": out.n_trades,
        })
    return out


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


def _build_manifest(d: pd.Timestamp, sig_d: pd.Timestamp, provider,
                    pf: PaperPortfolio, cfg: dict,
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
        "run_date": str(d.date()),
        "signal_date": str(sig_d.date()),
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
