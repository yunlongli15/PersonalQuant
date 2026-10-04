# -*- coding: utf-8 -*-
"""端到端场景（spec §41 / §42 / §50）。

手工构造合成行情，逐日推进，检查整条
signal → order → fill → position → exit → cash → ledger
是否**完整可追溯**，且事后无法因为知道结果而改变当时的状态。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

from conftest import SESSIONS, SYMS, bar, build_market, day, make_signals
from daily_exit_paper import engine, execution as X, state as S

A, B = SYMS[0], SYMS[1]
CAP = 66_000.0
D0, D1, D2, D3, D4, D5 = (day(SESSIONS, i) for i in range(6))


def _mkt(signals=None, forecasts=None):
    return build_market({}, signals or {}, forecasts or {})


# ---------------------------------------------------------------------------
# §41 主场景：建仓 → 持有 → 目标价卖出 → 现金回流 → 再建仓 → 未成交
# ---------------------------------------------------------------------------

def test_full_cycle_is_traceable_end_to_end(cfg, store):
    mkt = _mkt({D0: make_signals(D0, [A])}, {D0: {A: 0.05}})

    # ---- DAY 0：生成 BUY A ------------------------------------------------
    r = engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    assert len(r.reports[0].new_orders) == 1
    assert r.reports[0].entries_filled == []
    order = S.pending_list(store.read_state())[0]
    limit = order["limit_price"]
    entry_px = round(limit - 0.30, 2)

    # ---- DAY 1：价格触及限价 -> FILLED ------------------------------------
    mkt.set_bar(A, D1, o=entry_px, h=limit, l=entry_px - 0.10)
    r = engine.run(run_date=D1, cfg=cfg, store=store, market=mkt)
    fill = r.reports[0].entries_filled[0]
    assert fill["fill_price"] == pytest.approx(entry_px)
    pos = S.open_positions(store.read_state())[A]
    tgt, stp = pos["target_price"], pos["stop_loss"]
    assert pos["entry_exec_date"] == str(D1.date())
    cash_after_entry = store.read_state()["cash"]

    # ---- DAY 2：价格在区间内 -> HOLD --------------------------------------
    mid = (tgt + stp) / 2
    mkt.set_bar(A, D2, o=mid, h=mid * 1.001, l=mid * 0.999)
    r = engine.run(run_date=D2, cfg=cfg, store=store, market=mkt)
    assert r.reports[0].exits == []
    assert A in S.open_positions(store.read_state())

    # ---- DAY 3：high 打到目标价 -> SELL，当晚现金回流并生成 BUY B ---------
    mkt.set_bar(A, D3, o=tgt - 0.10, h=tgt + 0.40, l=tgt - 0.20)
    mkt._signals[D3] = make_signals(D3, [B])
    mkt._forecasts[D3] = {B: 0.05}
    r = engine.run(run_date=D3, cfg=cfg, store=store, market=mkt)
    assert r.reports[0].exits[0]["reason"] == X.TARGET_HIT
    assert A not in S.open_positions(store.read_state())
    closed = store.read_state()["positions"][A]
    assert closed["exit_date"] == str(D3.date())
    assert store.read_state()["cash"] > cash_after_entry   # 卖出所得已入账
    assert [o["symbol"] for o in r.reports[0].new_orders] == [B]

    # ---- DAY 4：B 未触及限价 -> NO_FILL -----------------------------------
    b_limit = S.pending_list(store.read_state())[0]["limit_price"]
    mkt.set_bar(B, D4, o=b_limit + 2.0, h=b_limit + 2.5, l=b_limit + 1.5)
    r = engine.run(run_date=D4, cfg=cfg, store=store, market=mkt)
    assert r.reports[0].entries_filled == []
    assert r.reports[0].entries_no_fill[0]["symbol"] == B
    assert S.pending_list(store.read_state()) == []
    assert store.read_state()["reserved_cash"] == 0.0

    # ---- DAY 5：新的一天，账户回到全现金 ----------------------------------
    r = engine.run(run_date=D5, cfg=cfg, store=store, market=mkt)
    st = store.read_state()
    assert S.available_cash(st) == pytest.approx(st["cash"])
    assert S.open_positions(st) == {}

    # ---- 整条链在账本里完整可追溯 -----------------------------------------
    events = store.read_ledger()
    kinds = [e["type"] for e in events]
    for k in ("ORDER_CREATED", "ORDER_FILLED", "POSITION_OPENED",
              "POSITION_CLOSED", "ORDER_NO_FILL", "CASH_RESERVE",
              "CASH_RELEASE", "FEE", "RUN_SUMMARY"):
        assert k in kinds, k
    filled = [e for e in events if e["type"] == "POSITION_CLOSED"][0]
    assert filled["reason"] == X.TARGET_HIT
    opened = [e for e in events if e["type"] == "POSITION_OPENED"][0]
    assert opened["entry_exec_date"] == str(D1.date())
    assert filled["run_date"] == str(D3.date())         # 出场日期可追溯


# ---------------------------------------------------------------------------
# §41 变体：限价未触及 / 触发止损
# ---------------------------------------------------------------------------

def test_no_fill_variant(cfg, store):
    mkt = _mkt({D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    limit = S.pending_list(store.read_state())[0]["limit_price"]
    mkt.set_bar(A, D1, o=limit + 1.0, h=limit + 1.5, l=limit + 0.5)

    r = engine.run(run_date=D1, cfg=cfg, store=store, market=mkt)
    assert r.reports[0].entries_no_fill[0]["reason"]
    st = store.read_state()
    assert st["cash"] == pytest.approx(CAP)             # 一分钱没动
    assert st["positions"] == {}
    assert st["reserved_cash"] == 0.0


def test_stop_hit_variant(cfg, store):
    mkt = _mkt({D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    limit = S.pending_list(store.read_state())[0]["limit_price"]
    entry = round(limit - 0.30, 2)
    mkt.set_bar(A, D1, o=entry, h=limit, l=entry - 0.10)
    engine.run(run_date=D1, cfg=cfg, store=store, market=mkt)
    stp = S.open_positions(store.read_state())[A]["stop_loss"]

    mkt.set_bar(A, D2, o=stp + 0.05, h=stp + 0.10, l=stp - 0.20)
    r = engine.run(run_date=D2, cfg=cfg, store=store, market=mkt)
    assert r.reports[0].exits[0]["reason"] == X.STOP_HIT
    assert store.read_state()["positions"][A]["realized_pnl"] < 0


# ---------------------------------------------------------------------------
# §42 追赶：漏跑几天也不会跳过停损
# ---------------------------------------------------------------------------

def test_catch_up_replays_every_session(cfg, store):
    """从 D0 直接跳到 D4：中间三个交易日必须**逐日**补上，不能整体跳过。"""
    mkt = _mkt({D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    limit = S.pending_list(store.read_state())[0]["limit_price"]
    entry = round(limit - 0.30, 2)

    mkt.set_bar(A, D1, o=entry, h=limit, l=entry - 0.10)   # 成交
    mkt.set_bar(A, D2, o=entry, h=entry * 1.001, l=entry * 0.999)
    mkt.set_bar(A, D3, o=entry, h=entry * 1.001, l=entry * 0.999)
    mkt.set_bar(A, D4, o=entry, h=entry * 1.001, l=entry * 0.999)

    r = engine.run(run_date=D4, cfg=cfg, store=store, market=mkt)
    assert r.sessions == [str(d.date()) for d in (D1, D2, D3, D4)]
    pos = S.open_positions(store.read_state())[A]
    assert pos["entry_exec_date"] == str(D1.date())        # 成交仍在正确的日子
    assert pos["holding_sessions"] == 3                    # D1→D4 过了 3 个交易日


def test_catch_up_catches_a_stop_that_fired_while_skipped(cfg, store):
    """漏跑期间触发的止损，追赶时必须补上 —— 漏跑不能"躲过"亏损。"""
    mkt = _mkt({D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    limit = S.pending_list(store.read_state())[0]["limit_price"]
    entry = round(limit - 0.30, 2)
    mkt.set_bar(A, D1, o=entry, h=limit, l=entry - 0.10)
    mkt.set_bar(A, D2, o=entry, h=entry * 1.001, l=entry * 0.999)
    mkt.set_bar(A, D3, o=entry, h=entry * 1.001, l=entry * 0.999)
    mkt.set_bar(A, D4, o=entry, h=entry * 1.001, l=entry * 0.999)
    # 先跑 D1 拿到 stop
    engine.run(run_date=D1, cfg=cfg, store=store, market=mkt)
    stp = S.open_positions(store.read_state())[A]["stop_loss"]
    # D2 这一天盘中砸穿止损
    mkt.set_bar(A, D2, o=stp + 0.10, h=stp + 0.20, l=stp - 0.30)

    r = engine.run(run_date=D4, cfg=cfg, store=store, market=mkt)
    exits = [e for rep in r.reports for e in rep.exits]
    assert len(exits) == 1
    assert exits[0]["reason"] == X.STOP_HIT
    assert exits[0]["exit_date"] == str(D2.date())         # 补在了正确的日子
    assert A not in S.open_positions(store.read_state())


# ---------------------------------------------------------------------------
# 冷启动边界（spec PHASE 6 §13 / §26）：第一次启动绝不许补历史
# ---------------------------------------------------------------------------

def test_fresh_start_processes_only_the_run_date(cfg, store):
    """**正式实验第一天必须是"干净初始化"**。

    日历里有 8 个交易日、每一天都有信号；第一次运行时已经"晚"了好几天。
    引擎只允许处理 run_date 这一天 —— 绝不能把前面 5 天的信号一路补成
    历史交易，那等于事后伪造一批从来没真实发生过的挂单与成交。
    """
    all_sigs = {d: make_signals(d, [A]) for d in SESSIONS}
    all_fcs = {d: {A: 0.05} for d in SESSIONS}
    mkt = build_market({}, all_sigs, all_fcs)

    r = engine.run(run_date=D4, capital=CAP, cfg=cfg, store=store, market=mkt)

    assert r.sessions == [str(D4.date())]          # 只跑了这一天
    assert len(store.snapshot_dates("recommendations")) == 1
    assert store.snapshot_dates("recommendations") == [str(D4.date())]
    # 挂单挂在 D4 的信号上，等 D5 —— 不是挂在 D0 上等 D1
    orders = S.pending_list(store.read_state())
    assert orders and all(o["signal_date"] == str(D4.date()) for o in orders)
    assert all(o["resolved_exec_date"] is None for o in orders)


def test_fresh_start_does_not_replay_past_signals(cfg, store):
    """即使过去几天的信号看起来"更便宜"，也一笔都不补。"""
    mkt = build_market({(A, D1): bar(1.0, 1.0, 1.0),
                        (A, D2): bar(1.0, 1.0, 1.0)},
                       {d: make_signals(d, [A]) for d in SESSIONS},
                       {d: {A: 0.05} for d in SESSIONS})
    engine.run(run_date=D4, capital=CAP, cfg=cfg, store=store, market=mkt)
    events = store.read_ledger()
    assert not [e for e in events if e["type"] == "ORDER_FILLED"]
    assert not [e for e in events if e["type"] == "POSITION_OPENED"]
    assert {e["run_date"] for e in events} == {str(D4.date())}


def test_already_started_experiment_does_catch_up(cfg, store):
    """已经起跑的实验漏跑几天 -> 补齐（Case A）。这与冷启动是两回事。"""
    mkt = build_market({}, {D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    limit = S.pending_list(store.read_state())[0]["limit_price"]
    mkt.set_bar(A, D1, o=limit - 0.30, h=limit, l=limit - 0.40)
    mkt.set_bar(A, D2, o=limit - 0.30, h=limit, l=limit - 0.40)
    mkt.set_bar(A, D3, o=limit - 0.30, h=limit, l=limit - 0.40)

    r = engine.run(run_date=D3, cfg=cfg, store=store, market=mkt)
    assert r.sessions == [str(d.date()) for d in (D1, D2, D3)]
    pos = S.open_positions(store.read_state())[A]
    assert pos["entry_exec_date"] == str(D1.date())


# ---------------------------------------------------------------------------
# §50：成交必须来自当时可知的信息
# ---------------------------------------------------------------------------

def test_fill_price_can_never_come_from_a_later_session(cfg, store):
    mkt = _mkt({D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    limit = S.pending_list(store.read_state())[0]["limit_price"]
    mkt.set_bar(A, D1, o=limit - 0.30, h=limit, l=limit - 0.40)
    # 后面几天放一个极端价格 —— 它绝不该影响 D1 的成交价
    mkt.set_bar(A, D2, o=999.0, h=1000.0, l=998.0)
    engine.run(run_date=D1, cfg=cfg, store=store, market=mkt)
    pos = S.open_positions(store.read_state())[A]
    assert pos["entry_price"] == pytest.approx(limit - 0.30)
    assert pos["entry_price"] < 100


def test_a_recommendation_cannot_be_rewritten_after_the_fact(cfg, store):
    """事后重算同一天的推荐必须撞上不可变铁律（结果已知也不能改当时的状态）。"""
    from daily_exit_paper import store as ST

    mkt = _mkt({D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    snap = store.read_snapshot("recommendations", D0)
    assert snap["entries"][0]["symbol"] == A

    tampered = dict(snap)
    tampered["entries"] = [dict(snap["entries"][0], quantity=999)]
    with pytest.raises(ST.AlreadyWritten):
        store.write_immutable("recommendations", D0, tampered)
