# -*- coding: utf-8 -*-
"""daily_exit_paper_v1 引擎：逐交易日推进的 forward paper 实验。

事件顺序（spec §30，**先处理历史 pending / exits，再产生新订单**）
---------------------------------------------------------------
每个交易日 s，按顺序做四件事：

    A. 结算挂出的限价买单（执行日 == s）：FILLED / NO_FILL
    B. 结算等待中的卖出（时间止损触发后等下一个开盘）
    C. 评估 OPEN 持仓的 target / stop / time-stop
    D. s 收盘后生成推荐 → 为下一个交易日挂单

**追赶（catch-up）**：若上次运行停在 s0，本次运行到 s1，则 s0 与 s1 之间
每一个交易日都会按上面的顺序被逐个重放 —— 漏跑的停损不会被跳过。
每一步都只使用 <= 该交易日的行情，因此追赶不是"回填未来"，是补齐历史。

不 import paper_live（spec §2）：order / position / cash / lifecycle 全部
由本包自己管理。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from . import config as C
from . import execution as X
from . import ledger as L
from . import state as S
from . import store as ST

INDEX_LIKE = {"000300.SH", "000852.SH", "000905.SH", "000906.SH",
              "000985.SH", "399300.SZ"}


class EngineError(RuntimeError):
    """实验运行被拒绝（本金变更、配置漂移、日期倒退等）。"""


# ---------------------------------------------------------------------------
# 市场数据（可注入；全部只读且永远带 as_of）
# ---------------------------------------------------------------------------

class LiveMarket:
    """真实数据源：canonical parquet + DuckDB，全部按日期取数。

    日历在一次运行里被反复用到（每评估一个持仓就要一次），所以在实例上
    记忆化 —— **只在本次进程内缓存**，不落盘、不跨运行复用。
    """

    def __init__(self):
        self._cal: Optional[pd.DatetimeIndex] = None

    def calendar(self) -> pd.DatetimeIndex:
        if self._cal is None:
            self._cal = X.observed_calendar()
        return self._cal

    def bars(self, symbols: List[str], date) -> Dict[str, dict]:
        return X.bars_on(symbols, date)

    def closes(self, symbols: List[str], as_of) -> Dict[str, float]:
        return X.last_close_on_or_before(symbols, as_of)

    def signals(self, session) -> Optional[pd.DataFrame]:
        """**该交易日**的信号快照（按日期一个文件，天生 PIT 安全）。"""
        p = (C.PROJECT_ROOT / "data" / "quant"
             / f"signals_{pd.Timestamp(session).date()}.parquet")
        if not p.exists():
            return None
        df = pd.read_parquet(p)
        want = pd.Timestamp(session)
        df = df[pd.to_datetime(df["signal_date"]) == want]
        return df if len(df) else None

    def forecasts(self, session, horizon: int) -> Dict[str, float]:
        p = (C.PROJECT_ROOT / "data" / "quant" / "forecasts"
             / f"forecast_{pd.Timestamp(session).date()}.parquet")
        if not p.exists():
            return {}
        df = pd.read_parquet(p)
        df = df[(df["horizon"] == horizon)
                & (pd.to_datetime(df["signal_date"]) == pd.Timestamp(session))]
        return dict(zip(df["symbol"], df["expected_return"]))

    def price_history(self, symbols: List[str], as_of) -> pd.DataFrame:
        from trade_plan.plan import load_price_history

        return load_price_history(symbols, str(pd.Timestamp(as_of).date()))


# ---------------------------------------------------------------------------
# 结果
# ---------------------------------------------------------------------------

@dataclass
class SessionReport:
    session: str
    entries_filled: List[dict] = field(default_factory=list)
    entries_no_fill: List[dict] = field(default_factory=list)
    exits: List[dict] = field(default_factory=list)
    new_orders: List[dict] = field(default_factory=list)
    skipped: List[dict] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    overrides: List[dict] = field(default_factory=list)
    fees: float = 0.0

    def as_dict(self) -> dict:
        return {"session": self.session,
                "entries_filled": self.entries_filled,
                "entries_no_fill": self.entries_no_fill,
                "exits": self.exits,
                "new_orders": self.new_orders,
                "skipped": self.skipped,
                "overrides": self.overrides,
                "notes": self.notes,
                "fees": round(self.fees, 4)}


@dataclass
class RunResult:
    run_date: str
    sessions: List[str]
    reports: List[SessionReport]
    totals: dict
    state: dict
    dry_run: bool
    noop: bool = False
    writes: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def fees(self) -> float:
        return float(sum(r.fees for r in self.reports))

    def as_dict(self) -> dict:
        return {"run_date": self.run_date, "sessions": self.sessions,
                "reports": [r.as_dict() for r in self.reports],
                "totals": self.totals, "dry_run": self.dry_run,
                "noop": self.noop, "writes": self.writes,
                "notes": self.notes}


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

def _cost_model(s_cfg: dict):
    from personal_quant.strategy.costs import TransactionCostModel

    return TransactionCostModel.from_config(
        {"transaction_costs": s_cfg["transaction_costs"]})


def _max_lots(limit_price: float, budget: float, cost_model,
              lot: int) -> int:
    """在预算内最多能买几手（**含费用**，且不超预算）。"""
    if limit_price <= 0 or budget <= 0:
        return 0
    n = int(budget / limit_price / lot)
    while n > 0:
        value = n * lot * limit_price
        if value + cost_model.buy_cost(value) <= budget + 1e-9:
            return n
        n -= 1
    return 0


def _daily_vol(prices: pd.DataFrame, symbol: str) -> Optional[float]:
    """日收益率标准差（60 日）——与 trade_plan 同一口径。"""
    if symbol not in prices.columns:
        return None
    s = prices[symbol].pct_change().tail(60).std()
    return float(s) if pd.notna(s) and s > 0 else None


def _exit_levels(entry_px: float, expected_return: float, vol: float,
                 profile: str, horizon: int) -> dict:
    """复用 trade_plan 里已验证的 target/stop 公式（不重新发明）。

    `plan_price` 传**实际成交价** —— 这是"入场成交时快照"的自然含义：
    出场线锚定在真实的持仓成本上，而不是信号日的计划价。
    """
    from trade_plan.plan import target_and_stop

    lv = target_and_stop(entry_px, entry_px, expected_return, vol, profile,
                         horizon=horizon)
    lv["risk_profile"] = profile
    return lv


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run(run_date=None, capital: Optional[float] = None, dry_run: bool = False,
        cfg: Optional[dict] = None, store: Optional[ST.ExperimentStore] = None,
        market=None, max_sessions: Optional[int] = None) -> RunResult:
    """把实验推进到 `run_date`（默认：数据里最后一个已观测交易日）。"""
    cfg = cfg if cfg is not None else C.load_config()
    s_cfg = C.validate(cfg)
    market = market or LiveMarket()

    cal = market.calendar()
    if len(cal) == 0:
        raise EngineError("交易日历为空")
    if run_date is None:
        run_d = X.last_observed_session(cal)
    else:
        run_d = pd.Timestamp(run_date)
        if run_d > pd.Timestamp(cal[-1]):
            raise EngineError(
                f"{run_d.date()} 还没有行情（已观测交易日历止于 "
                f"{pd.Timestamp(cal[-1]).date()}）—— 先刷新行情再运行")

    root = C.PROJECT_ROOT / s_cfg["paths"]["root"]
    store = store or ST.ExperimentStore(root)

    # ---- STEP 2：实验元数据（本金锁定 + 配置哈希 + 起始信号日）-----------
    exp = _ensure_experiment(store, s_cfg, capital, dry_run,
                             first_signal_date=str(run_d.date()))
    initial_capital = float(exp["initial_capital"])

    # ---- STEP 3：状态（新实验 = 零状态，绝不读别的 experiment）----------
    raw_state = store.read_state()
    if raw_state is None:
        prev = _previous_session(cal, run_d)
        state = S.empty_state(initial_capital, as_of=prev,
                              experiment_id=exp["experiment_id"])
        state["initial_capital"] = initial_capital
        if dry_run:
            state["as_of"] = prev
    else:
        state = raw_state
        if abs(float(state["initial_capital"]) - initial_capital) > 1e-6:
            raise EngineError(
                f"state 里的初始本金 {state['initial_capital']:,.2f} 与 "
                f"experiment.json 的 {initial_capital:,.2f} 不一致 —— "
                f"状态被外部改过，停在这里不继续")

    as_of = pd.Timestamp(state["as_of"]) if state.get("as_of") else None
    if as_of is not None and run_d < as_of:
        raise EngineError(
            f"运行日 {run_d.date()} 早于已处理到的最新交易日 {as_of.date()} "
            f"—— 实验时间只能向前。重跑同一天是无操作，回退不是")

    sessions = [pd.Timestamp(d) for d in cal
                if (as_of is None or d > as_of) and d <= run_d]
    if max_sessions is not None:
        sessions = sessions[:max_sessions]

    events: List[dict] = list(store.read_ledger())
    n_events_before = len(events)
    reports: List[SessionReport] = []

    if not sessions:
        notes = [f"已推进到 {run_d.date()}，没有新的交易日要处理（无操作）"]
        totals = L.reconcile(state, events,
                             market.closes(list(state.get("positions") or {}),
                                           run_d))
        res = RunResult(str(run_d.date()), [], [], totals, state, dry_run,
                        noop=True, notes=notes)
        _write_daily(store, res, exp, s_cfg, dry_run)
        return res

    for s in sessions:
        rep = _process_session(s, state, s_cfg, exp, market, events, dry_run,
                               capital=initial_capital, store=store)
        reports.append(rep)

    # ---- STEP 12：对账 --------------------------------------------------
    # **先对账，再落盘**：对不上就什么都不写，绝不留下半截状态。
    held = list(state.get("positions") or {})
    prices = market.closes(held, run_d) if held else {}
    totals = L.reconcile(state, events, prices)

    state["run_date"] = str(run_d.date())
    state["n_runs"] = int(state.get("n_runs") or 0) + 1
    events.append({
        "type": "RUN_SUMMARY", "run_date": str(run_d.date()),
        "sessions": [str(s.date()) for s in sessions],
        "cash": totals["cash"], "reserved_cash": totals["reserved_cash"],
        "position_value": totals["position_value"],
        "portfolio_value": totals["portfolio_value"],
        "fees_today": float(sum(r.fees for r in reports)),
        "n_positions": len(S.open_positions(state)),
        "n_pending": len(S.pending_list(state)),
    })
    # 落盘顺序：**先 state 再账本**。state 是进度标记；万一在这里崩了，
    # 账本会落在后面 —— 下一次运行的对账会大声报错，而不会重复记一笔。
    # 反过来先写账本，崩溃后会重放同一段交易日、导致整段被记两遍。
    if not dry_run:
        store.write_state(state)
        store.append_ledger(events[n_events_before:])

    res = RunResult(str(run_d.date()), [str(s.date()) for s in sessions],
                    reports, totals, state, dry_run)
    _write_daily(store, res, exp, s_cfg, dry_run)
    return res


def _previous_session(cal: pd.DatetimeIndex, d) -> Optional[str]:
    earlier = cal[cal < pd.Timestamp(d)]
    return str(pd.Timestamp(earlier[-1]).date()) if len(earlier) else None


def _ensure_experiment(store: ST.ExperimentStore, s_cfg: dict,
                       capital: Optional[float], dry_run: bool,
                       first_signal_date: Optional[str] = None) -> dict:
    """首次创建实验元数据；之后校验本金与配置哈希（**都不可变**）。

    元数据里 `first_signal_date` 记的是**实验第一天用的信号日**，
    不是"程序安装日"—— 这两件事完全不同，混起来事后就说不清实验从哪天算起。
    """
    exp = store.read_experiment()
    sha = C.config_sha256()
    if exp is None:
        if capital is None:
            raise EngineError(
                "首次运行必须显式给出 --capital（实验本金一旦确定就锁定；"
                "中途改本金 = 改仓位规模 = 违反「不得调参」）")
        if dry_run:
            return {"experiment_id": s_cfg["strategy_version"],
                    "initial_capital": float(capital), "config_sha256": sha,
                    "dry_run_placeholder": True}
        commit, dirty = _git_state()
        return store.create_experiment({
            "experiment_id": s_cfg["strategy_version"],
            "strategy_version": s_cfg["strategy_version"],
            "base_strategy": s_cfg["base_signal_strategy"],
            "initial_capital": float(capital),
            "first_signal_date": first_signal_date,
            "config_sha256": sha,
            "git_commit": commit,
            "git_dirty": dirty,
            "working_tree": "dirty" if dirty else "clean",
        })

    if capital is not None and abs(float(capital)
                                   - float(exp["initial_capital"])) > 1e-6:
        raise EngineError(
            f"实验本金已锁定为 {exp['initial_capital']:,.2f}，"
            f"不能改成 {float(capital):,.2f}。\n"
            f"需要不同本金 → 新建实验版本（例如 daily_exit_paper_v1.1），"
            f"新目录、新账本；绝不把改过本金的记录继续称作 v1")
    C.verify_config(expected_sha=exp.get("config_sha256"))
    return exp


def _git_state() -> Tuple[str, bool]:
    """(HEAD commit, 工作区是否有未提交改动)。

    启动实验时把这两件事一起记下来：日后要复盘"当时跑的到底是哪个版本的
    代码"，只看 commit 是不够的 —— 工作区脏着的话，commit 并不代表实际跑的代码。
    """
    import subprocess

    def run(*args):
        return subprocess.run(list(args), capture_output=True, text=True,
                              cwd=str(C.PROJECT_ROOT)).stdout.strip()

    try:
        commit = run("git", "rev-parse", "HEAD") or "unknown"
        dirty = bool(run("git", "status", "--porcelain"))
        return commit, dirty
    except Exception:                                        # noqa: BLE001
        return "unknown", True


# ---------------------------------------------------------------------------
# 单个交易日
# ---------------------------------------------------------------------------

def _process_session(s: pd.Timestamp, state: dict, s_cfg: dict, exp: dict,
                     market, events: List[dict], dry_run: bool,
                     capital: float,
                     store: Optional[ST.ExperimentStore] = None
                     ) -> SessionReport:
    rep = SessionReport(session=str(s.date()))
    run_s = str(s.date())

    # A. 结算挂出的限价买单（执行日 == s）---------------------------------
    _settle_entries(s, state, s_cfg, rep, market, events, dry_run)

    # B. 结算等待中的卖出（时间止损触发后等下一个开盘）--------------------
    _settle_pending_exits(s, state, s_cfg, rep, market, events, dry_run)

    # C. 评估 target / stop / time-stop -----------------------------------
    _evaluate_exits(s, state, s_cfg, rep, market, events, dry_run)

    # C2. 按当日收盘给**仍在持仓**的标的打标记（只碰可变字段）-------------
    _mark_positions(s, state, market)

    # D. s 收盘后：生成推荐 → 为下一个交易日挂单 ---------------------------
    _generate_recommendation(s, state, s_cfg, rep, market, events, dry_run,
                             capital=capital, store=store)

    state["as_of"] = run_s
    return rep


# --- A. 入场结算 -----------------------------------------------------------

def _settle_entries(s, state, s_cfg, rep, market, events, dry_run):
    cost = _cost_model(s_cfg)
    lot = int(s_cfg["sizing"]["lot_size"])
    still_pending = []
    for order in S.pending_list(state):
        if order.get("status") != S.OrderStatus.PENDING.value:
            continue
        sig = pd.Timestamp(order["signal_date"])
        if sig >= s:
            still_pending.append(order)      # T 日晚上挂的，T+1 才可能成交
            continue

        # 已观测日历里 sig 之后的第一个交易日就是它的执行日
        exec_date = X.next_session(market.calendar(), sig)
        if exec_date is None:                # 理论上到不了这里（s 已经存在）
            S.record_attempt(order, str(s.date()), "NOT_YET", "KEEP_PENDING")
            still_pending.append(order)
            continue

        sym = order["symbol"]
        bar = market.bars([sym], exec_date).get(sym)
        res = X.resolve_entry(bar, order["limit_price"])
        if res is None:
            # 执行日已经在日历里，但这只票当天没有 bar —— 可判定的停牌
            res = {"status": X.NO_FILL, "price": None,
                   "note": "执行日无有效 bar（停牌/退市）"}
        order["resolved_exec_date"] = str(pd.Timestamp(exec_date).date())

        if res["status"] != X.FILLED:
            S.record_attempt(order, str(s.date()), "READY", "NO_FILL",
                             order["resolved_exec_date"], res["note"])
            S.release(state, order["reserved_cash"])
            order["status"] = S.OrderStatus.NO_FILL.value
            rep.entries_no_fill.append({
                "order_id": order["order_id"], "symbol": sym,
                "name": order.get("name"), "signal_date": order["signal_date"],
                "exec_date": order["resolved_exec_date"],
                "reason": res["note"], "limit_price": order["limit_price"]})
            events.append({"type": "ORDER_NO_FILL", "run_date": str(s.date()),
                           "order_id": order["order_id"], "symbol": sym,
                           "exec_date": order["resolved_exec_date"],
                           "reason": res["note"]})
            events.append({"type": "CASH_RELEASE",
                           "run_date": str(s.date()),
                           "order_id": order["order_id"],
                           "amount": order["reserved_cash"]})
            continue

        # 成交 ---------------------------------------------------------
        px = float(res["price"])
        shares = int(order["quantity"])
        value = shares * px
        fee = cost.buy_cost(value)
        state["cash"] = float(state["cash"]) - value - fee
        S.release(state, order["reserved_cash"])
        order["status"] = S.OrderStatus.FILLED.value
        order["fill_price"] = px
        S.record_attempt(order, str(s.date()), "READY", "FILLED",
                         order["resolved_exec_date"], res["note"])

        ex_ret = order.get("expected_return")
        ex_ret = float(ex_ret) if ex_ret is not None and np.isfinite(
            ex_ret) else 0.0
        vol = float(order.get("vol") or 0.02)
        levels = _exit_levels(px, ex_ret, vol, s_cfg["risk_profile"],
                              int(s_cfg["signal_horizon_days"]))
        at_signal = {"target_price": order["target_price_at_signal"],
                     "stop_loss": order["stop_loss_at_signal"],
                     "plan_price": order.get("planned_entry_price"),
                     "close_at_signal": order.get("close_at_signal"),
                     "horizon_days": int(s_cfg["signal_horizon_days"])}
        pos = S.build_position(order, px, shares, levels, at_signal,
                               locked_at=str(pd.Timestamp(exec_date).date()))
        pos["entry_fee"] = fee
        state.setdefault("positions", {})[sym] = pos

        rep.entries_filled.append({
            "order_id": order["order_id"], "symbol": sym, "shares": shares,
            "limit_price": order["limit_price"], "fill_price": px,
            "planned_entry_price": order.get("planned_entry_price"),
            "entry_slippage": round(px - float(order.get("planned_entry_price")
                                               or px), 4),
            "value": round(value, 2), "fee": round(fee, 2),
            "signal_date": order["signal_date"],
            "exec_date": pos["entry_exec_date"],
            "target_price": levels["target_price"],
            "stop_loss": levels["stop_loss"],
            "note": res["note"]})
        rep.fees += fee
        events.append({"type": "ORDER_FILLED", "run_date": str(s.date()),
                       "order_id": order["order_id"], "symbol": sym,
                       "signal_date": order["signal_date"],
                       "exec_date": pos["entry_exec_date"], "shares": shares,
                       "price": px, "value": value, "fee": fee,
                       "limit_price": order["limit_price"]})
        events.append({"type": "CASH_RELEASE", "run_date": str(s.date()),
                       "order_id": order["order_id"],
                       "amount": order["reserved_cash"]})
        events.append({"type": "POSITION_OPENED", "run_date": str(s.date()),
                       "symbol": sym, "shares": shares, "price": px,
                       "value": value, "fee": fee,
                       "signal_date": order["signal_date"],
                       "target_price": levels["target_price"],
                       "stop_loss": levels["stop_loss"],
                       "time_stop_days": levels["time_stop_days"],
                       "entry_exec_date": pos["entry_exec_date"]})
        events.append({"type": "FEE", "run_date": str(s.date()),
                       "symbol": sym, "kind": "entry", "fee": fee})
    S.set_pending(state, still_pending)


# --- B. 卖出结算 -----------------------------------------------------------

def _settle_pending_exits(s, state, s_cfg, rep, market, events, dry_run):
    """时间止损触发后挂出的卖出，在**下一个交易日开盘**成交。

    为什么不在触发当天就以收盘价了结：时间止损是**收盘后**才做得了的决策，
    当天收盘价是观察值不是可成交价。挂到下一个开盘才是真能成交的价格。
    """
    cost = _cost_model(s_cfg)
    for sym, p in list(S.open_positions(state).items()):
        if p.get("status") != S.PositionStatus.PENDING_EXIT.value:
            continue
        since = pd.Timestamp(p["pending_exit_since"])
        if s <= since:
            continue                          # 触发当天不成交，等下一个交易日
        bar = market.bars([sym], s).get(sym)
        if bar is None:
            p["pending_exit_note"] = f"{s.date()} 无 bar（停牌），继续等"
            continue
        _close_position(state, p, price=float(bar["open"]), session=s,
                        reason=X.TIME_STOP, rep=rep, cost=cost, events=events,
                        market=market,
                        note="时间止损：下一交易日开盘卖出",
                        resolution=None, both=False)


# --- C. 出场评估 -----------------------------------------------------------

def _evaluate_exits(s, state, s_cfg, rep, market, events, dry_run):
    cost = _cost_model(s_cfg)
    ex = s_cfg["exit"]
    conflict = s_cfg["exit_resolution"]["intraday_conflict"]
    for sym, p in list(S.open_positions(state).items()):
        if p.get("status") == S.PositionStatus.PENDING_EXIT.value:
            continue                          # 已经在等成交
        entry_d = pd.Timestamp(p["entry_exec_date"])
        if s <= entry_d:
            continue                          # A 股 T+1：入场当日不可卖出
        bar = market.bars([sym], s).get(sym)
        if bar is None:
            continue                          # 停牌：当天不评估，不猜

        target = float(p["target_price"]) if ex["target_enabled"] \
            else float("inf")
        stop = float(p["stop_loss"]) if ex["stop_enabled"] \
            else float("-inf")
        hit = X.resolve_target_stop(bar, target, stop, conflict=conflict)
        if hit is not None:
            _close_position(state, p, price=hit["price"], session=s,
                            reason=hit["reason"], rep=rep, cost=cost,
                            events=events, market=market, note=hit["note"],
                            resolution=hit["resolution_applied"],
                            both=hit["both_hit_same_day"])
            continue

        # 时间止损：入场日 = 第 0 天，持有满 time_stop_days 个交易日触发
        if ex["time_stop_enabled"]:
            held = X.sessions_between(market.calendar(), entry_d, s)
            if held >= int(p["time_stop_days"]):
                p["status"] = S.PositionStatus.PENDING_EXIT.value
                p["pending_exit_since"] = str(s.date())
                p["pending_exit_reason"] = X.TIME_STOP
                rep.notes.append(
                    f"{sym} 持有 {held} 个交易日达到时间止损 "
                    f"{p['time_stop_days']}，下一交易日开盘卖出")
                events.append({"type": "ORDER_CREATED",
                               "run_date": str(s.date()), "symbol": sym,
                               "side": "SELL",
                               "reason": X.TIME_STOP,
                               "note": "时间止损，等下一交易日开盘"})


def _mark_positions(s, state, market):
    """按当日收盘给持仓打标记。

    **只写可变字段**（现价 / 市值 / 浮动盈亏 / 持有期数）—— target、stop、
    time_stop 与全部入场字段都锁死，`state.update_position` 会拒绝越界写入。
    """
    open_now = S.open_positions(state)
    if not open_now:
        return
    prices = market.closes(list(open_now), s)
    cal = market.calendar()
    sessions_held = {
        sym: X.sessions_between(cal, pd.Timestamp(p["entry_exec_date"]), s)
        for sym, p in open_now.items()}
    S.mark_positions(state, prices, str(s.date()), sessions_held)


def _close_position(state, p, price, session, reason, rep, cost, events,
                    market, note, resolution, both):
    sym = p["symbol"]
    shares = int(p["entry_shares"])
    value = shares * float(price)
    fee = cost.sell_cost(value)
    state["cash"] = float(state["cash"]) + value - fee
    entry_cost = float(p["entry_value"]) + float(p.get("entry_fee") or 0.0)
    realized = (value - fee) - entry_cost
    S.update_position(
        p, status=S.PositionStatus.CLOSED.value,
        exit_date=str(session.date()), exit_reason=reason,
        exit_price=float(price), exit_shares=shares, exit_value=value,
        exit_fee=fee, realized_pnl=realized,
        resolution_applied=resolution, both_hit_same_day=bool(both),
        closed_at=datetime.now(timezone.utc).isoformat())
    rep.exits.append({
        "symbol": sym, "name": p.get("name"), "shares": shares,
        "entry_exec_date": p["entry_exec_date"], "entry_price": p["entry_price"],
        "exit_date": str(session.date()), "exit_price": float(price),
        "reason": reason, "resolution_applied": resolution,
        "both_hit_same_day": bool(both),
        "holding_sessions": X.sessions_between(
            market.calendar(), pd.Timestamp(p["entry_exec_date"]), session),
        "value": round(value, 2), "fee": round(fee, 2),
        "realized_pnl": round(realized, 2), "note": note})
    rep.fees += fee
    events.append({"type": "POSITION_CLOSED", "run_date": str(session.date()),
                   "symbol": sym, "shares": shares, "price": float(price),
                   "value": value, "fee": fee, "realized_pnl": realized,
                   "reason": reason, "resolution_applied": resolution,
                   "both_hit_same_day": bool(both)})
    events.append({"type": "FEE", "run_date": str(session.date()),
                   "symbol": sym, "kind": "exit", "fee": fee})


# --- D. 推荐与挂单 ---------------------------------------------------------

def _generate_recommendation(s, state, s_cfg, rep, market, events, dry_run,
                             capital: float,
                             store: Optional[ST.ExperimentStore] = None):
    """s 收盘后：用 <= s 的数据生成推荐，并为下一个交易日挂限价买单。"""
    s_date = str(s.date())
    rec = _build_recommendation(s, state, s_cfg, market, rep, capital)
    rep.skipped = rec["skipped"]
    rep.notes.extend(rec.get("notes") or [])

    # 推荐是**不可变快照**：一天一份，后一天绝不覆盖前一天（spec §33）。
    if store is not None and not dry_run:
        snapshot = dict(rec)
        snapshot.update({
            "run_date": s_date,
            "strategy_version": s_cfg["strategy_version"],
            "base_signal_strategy": s_cfg["base_signal_strategy"],
            "capital_initial": capital,
            "available_cash_at_decision": S.available_cash(state),
            "n_open_positions": len(S.open_positions(state)),
            "n_slots": int(s_cfg["top_k"]) - len(S.open_positions(state)),
            "decision_layer": "system_recommendation",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        store.write_immutable("recommendations", s_date, snapshot)

    # 人工干预层（§26-§28）：缺省 = 全部采纳；有 decisions/ 文件就按它走。
    # **系统建议的快照已经写完且不会被改**，这里只决定"实际挂什么单"。
    from . import decisions as D

    dec = D.load_decision(store, s_date) if store is not None else None
    entries, skipped_by_user, overrides = D.apply_decisions(
        rec["entries"], dec, _cost_model(s_cfg),
        int(s_cfg["sizing"]["lot_size"]))
    rep.skipped.extend(skipped_by_user)
    rep.overrides = overrides

    for e in entries:
        order = S.pending_entry(
            order_id=e["order_id"], symbol=e["symbol"], name=e["name"],
            signal_date=s_date, order_date=s_date,
            planned_entry_price=e["planned_entry_price"],
            limit_price=e["limit_price"], quantity=e["quantity"],
            reserved_cash=e["reserved_cash"],
            planned={"target_price": e["target_price_at_signal"],
                     "stop_loss": e["stop_loss_at_signal"],
                     "expected_return": e["expected_return"],
                     "vol": e["vol"], "entry_low": e["entry_low"],
                     "entry_high": e["entry_high"],
                     "raw_rank": e["raw_rank"],
                     "estimated_fee": e["estimated_fee"]})
        order["close_at_signal"] = e["close_at_signal"]
        order["created_at"] = datetime.now(timezone.utc).isoformat()
        rep.new_orders.append(order)
    if rep.new_orders:
        S.set_pending(state, S.pending_list(state) + rep.new_orders)
        for o in rep.new_orders:
            S.reserve(state, o["reserved_cash"])
            events.append({"type": "ORDER_CREATED", "run_date": s_date,
                           "order_id": o["order_id"], "symbol": o["symbol"],
                           "side": "BUY", "quantity": o["quantity"],
                           "limit_price": o["limit_price"],
                           "reserved_cash": o["reserved_cash"],
                           "signal_date": o["signal_date"]})
            events.append({"type": "CASH_RESERVE", "run_date": s_date,
                           "order_id": o["order_id"],
                           "amount": o["reserved_cash"]})
    return rec


def _build_recommendation(s, state, s_cfg, market, rep, capital: float) -> dict:
    """候选 → 空缺席位等权 → 手数取整 → 限价挂单。"""
    s_date = str(s.date())
    out = {"signal_date": s_date, "entries": [], "skipped": [],
           "excluded_restricted": [], "notes": []}

    sig = market.signals(s)
    if sig is None or sig.empty:
        out["notes"].append(f"{s_date} 没有信号快照 —— 今天不生成新推荐")
        return out

    held = S.held_symbols(state)
    slots = int(s_cfg["top_k"]) - len(held)
    if slots <= 0:
        out["notes"].append(
            f"持仓已达上限 {s_cfg['top_k']} 只，不再新开仓")
        return out

    avail = S.available_cash(state)
    invest = avail * float(s_cfg["sizing"]["invest_target"])
    per_slot = invest / slots
    if per_slot <= 0:
        out["notes"].append("没有可用现金，不生成新推荐")
        return out

    cand, meta = _candidates(sig, s_cfg, held, out, capital)
    if not cand:
        out["notes"].append("没有可用候选（全部被排除或不满足条件）")
        return out

    forecasts = market.forecasts(s, int(s_cfg["signal_horizon_days"]))
    hist = market.price_history(cand, s)
    cost = _cost_model(s_cfg)
    lot = int(s_cfg["sizing"]["lot_size"])
    profile = s_cfg["risk_profile"]
    remaining = avail

    for sym in cand:
        if len(out["entries"]) >= slots:
            break
        px = _signal_close(hist, sym, s)
        if px is None or px <= 0:
            out["skipped"].append({"symbol": sym, "reason": "no_price"})
            continue
        exp_ret = forecasts.get(sym)
        if exp_ret is None or not np.isfinite(exp_ret):
            # 没有预期收益就没有可锚定的目标价（默认 0 会造出"目标=成本"
            # 的退化出场线）—— 宁可跳过，不编造
            out["skipped"].append({"symbol": sym, "reason": "no_forecast"})
            continue
        vol = _daily_vol(hist, sym)
        if vol is None:
            out["skipped"].append({"symbol": sym, "reason": "no_vol"})
            continue

        from trade_plan.plan import entry_band

        low, plan_px, high, _why = entry_band(px, vol, profile)
        limit = float(np.round(high, 2))
        budget = min(per_slot, remaining)
        lots = _max_lots(limit, budget, cost, lot)
        if lots <= 0:
            out["skipped"].append({
                "symbol": sym, "reason": "budget_below_one_lot",
                "limit_price": limit, "budget": round(budget, 2)})
            continue

        qty = lots * lot
        value_at_limit = qty * limit
        fee_est = cost.buy_cost(value_at_limit)
        need = value_at_limit + fee_est
        # 注意：这里锚的是**计划价**（区间中点），所以算出来的目标价完全可能
        # 低于 entry_high —— 那是"如果追到区间上沿买，目标就没多少空间了"，
        # 不是"目标低于成本"。真正生效的出场线在**入场成交时**以实际成交价
        # 重新锚定并锁定（见 _settle_entries → _exit_levels(px, ...)），
        # 因此 成交价 × (1+预期收益) 必然高于成交价本身。
        lv = _exit_levels(plan_px, float(exp_ret), vol, profile,
                          int(s_cfg["signal_horizon_days"]))
        out["entries"].append({
            "order_id": f"{s_cfg['strategy_version']}:{s_date}:{sym}:BUY",
            "symbol": sym,
            "name": meta["name"].get(sym, ""),
            "raw_rank": meta["rank"].get(sym, 0),
            "close_at_signal": float(px),
            "entry_low": float(low), "planned_entry_price": float(plan_px),
            "entry_high": float(high), "limit_price": limit,
            "quantity": qty, "estimated_value": float(value_at_limit),
            "estimated_fee": float(fee_est), "reserved_cash": float(need),
            "target_price_at_signal": lv["target_price"],
            "stop_loss_at_signal": lv["stop_loss"],
            "expected_return": float(exp_ret), "vol": float(vol),
        })
        remaining -= need
        if remaining <= 0:
            break

    out["per_slot_budget"] = float(per_slot)
    out["days_to_exec"] = int(s_cfg["entry"]["execution_lag_days"])
    return out


def _signal_close(hist: pd.DataFrame, sym: str, s) -> Optional[float]:
    if sym not in hist.columns:
        return None
    col = hist[sym].loc[:pd.Timestamp(s)].dropna()
    return float(col.iloc[-1]) if len(col) else None


def _candidates(sig: pd.DataFrame, s_cfg: dict, held: set, out: dict,
                capital: float) -> Tuple[List[str], dict]:
    """按 S3 排序取候选，剔除已持有 / 指数伪标的 / 板块受限。"""
    df = sig.copy().sort_values("prediction", ascending=False)
    meta = {"name": dict(zip(df["symbol"], df.get("name", "")))
            if "name" in df.columns else {},
            "rank": dict(zip(df["symbol"], df["raw_rank"]))
            if "raw_rank" in df.columns else {}}

    if s_cfg["universe"]["exclude_index_like"]:
        df = df[~df["symbol"].isin(INDEX_LIKE)]

    if s_cfg["universe"]["exclude_restricted"]:
        from trade_plan.boards import eligibility

        exp_m = s_cfg["universe"].get("experience_months")
        keep = []
        for sym in df["symbol"]:
            e = eligibility(sym, float(capital), exp_m)
            if e.can_buy:
                keep.append(sym)
            elif len(out["excluded_restricted"]) < 50:
                out["excluded_restricted"].append({
                    "symbol": sym, "board": e.board,
                    "board_name": e.board_name,
                    "capital_required": e.capital_required,
                    "reason": e.reason})
        df = df[df["symbol"].isin(keep)]

    return [s for s in df["symbol"] if s not in held], meta


def _write_daily(store, res: RunResult, exp: dict, s_cfg: dict,
                 dry_run: bool) -> None:
    if dry_run:
        return
    try:
        store.write_immutable("daily", res.run_date, {
            "run_date": res.run_date,
            "sessions": res.sessions,
            "status": "COMPLETE",
            "totals": res.totals,
            "fees": res.fees,
            "n_open": len(S.open_positions(res.state)),
            "n_pending": len(S.pending_list(res.state)),
            "reports": [r.as_dict() for r in res.reports],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except ST.AlreadyWritten as e:
        res.notes.append(f"daily 快照未覆盖：{e}")
