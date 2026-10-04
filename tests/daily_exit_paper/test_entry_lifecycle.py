# -*- coding: utf-8 -*-
"""入场生命周期：挂单 → T+1 限价判定 → 成交 / 未成交（spec §7-§11）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

from conftest import SESSIONS, SYMS, build_market, day, make_signals
from daily_exit_paper import engine, state as S
from daily_exit_paper import store as ST

A = SYMS[0]
CAP = 66_000.0
D0, D1, D2 = day(SESSIONS, 0), day(SESSIONS, 1), day(SESSIONS, 2)


def _market(bars=None, signals=None, forecasts=None):
    return build_market(bars or {}, signals or {D0: make_signals(D0, [A])},
                        forecasts or {D0: {A: 0.05}})


def _first_order(store):
    return S.pending_list(store.read_state())[0]


def _enter(cfg, store, mkt):
    """跑到 D0：只挂单，不成交。"""
    return engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store,
                      market=mkt)


def test_order_is_pending_before_t1_and_not_a_failure(cfg, store):
    """T 日晚上只挂单：PENDING，不是失败，且预留了最坏情况的现金。"""
    r = _enter(cfg, store, _market())
    rep = r.reports[0]
    assert len(rep.new_orders) == 1
    assert rep.entries_filled == [] and rep.entries_no_fill == []
    o = _first_order(store)
    assert o["status"] == S.OrderStatus.PENDING.value
    assert o["resolved_exec_date"] is None
    assert o["exec_rule"] == "NEXT_SESSION_OPEN"
    assert o["quantity"] > 0
    assert o["reserved_cash"] == pytest.approx(
        o["quantity"] * o["limit_price"] + o["estimated_fee"], abs=0.01)
    st = store.read_state()
    assert st["reserved_cash"] == pytest.approx(o["reserved_cash"])
    assert S.available_cash(st) < st["cash"]


def test_fill_uses_the_next_session_never_the_signal_day(cfg, store):
    """T+1 铁律：成交价只可能来自 T+1 的 bar（**不是** T 日的价格）。"""
    mkt = _market()
    _enter(cfg, store, mkt)
    limit = _first_order(store)["limit_price"]
    mkt.set_bar(A, D1, o=limit - 0.30, h=limit, l=limit - 0.50)

    engine.run(run_date=D1, cfg=cfg, store=store, market=mkt)
    pos = S.open_positions(store.read_state())[A]
    assert pos["entry_exec_date"] == str(D1.date())
    assert pos["entry_price"] == pytest.approx(limit - 0.30)


def test_price_improvement_fills_at_the_open(cfg, store):
    """开盘低于限价 -> 按开盘价成交，并记录相对计划价的滑点。"""
    mkt = _market()
    _enter(cfg, store, mkt)
    o = _first_order(store)
    open_px = round(o["limit_price"] - 0.40, 2)
    mkt.set_bar(A, D1, o=open_px, h=o["limit_price"], l=open_px - 0.10)

    r = engine.run(run_date=D1, cfg=cfg, store=store, market=mkt)
    fill = r.reports[0].entries_filled[0]
    assert fill["fill_price"] == pytest.approx(open_px)
    assert fill["fill_price"] < fill["limit_price"]
    # 滑点是相对**计划价**算的，落库时保留 4 位
    assert fill["entry_slippage"] == pytest.approx(
        open_px - fill["planned_entry_price"], abs=1e-3)


def test_intraday_touch_fills_at_the_limit(cfg, store):
    mkt = _market()
    _enter(cfg, store, mkt)
    limit = _first_order(store)["limit_price"]
    mkt.set_bar(A, D1, o=limit + 1.00, h=limit + 1.20, l=limit - 0.05)

    r = engine.run(run_date=D1, cfg=cfg, store=store, market=mkt)
    fill = r.reports[0].entries_filled[0]
    assert fill["fill_price"] == pytest.approx(limit)


def test_limit_not_touched_is_a_terminal_no_fill(cfg, store):
    mkt = _market()
    _enter(cfg, store, mkt)
    limit = _first_order(store)["limit_price"]
    mkt.set_bar(A, D1, o=limit + 1.00, h=limit + 1.50, l=limit + 0.50)

    r = engine.run(run_date=D1, cfg=cfg, store=store, market=mkt)
    assert r.reports[0].entries_filled == []
    assert len(r.reports[0].entries_no_fill) == 1
    st = store.read_state()
    assert S.pending_list(st) == []                 # 终态：不重试
    assert st["reserved_cash"] == 0.0               # 预留已释放
    assert S.available_cash(st) == pytest.approx(st["cash"])
    # 账本里留下终态事件
    types = [e["type"] for e in store.read_ledger()]
    assert "ORDER_NO_FILL" in types and "CASH_RELEASE" in types


def test_halted_symbol_on_the_exec_day_is_no_fill(cfg, store):
    """执行日已经在日历里、但这只票没有 bar -> 可判定的停牌 NO_FILL。"""
    mkt = _market()
    _enter(cfg, store, mkt)
    mkt.set_bar(SYMS[1], D1, 10, 10, 10)            # 只有别的票有 bar

    r = engine.run(run_date=D1, cfg=cfg, store=store, market=mkt)
    nf = r.reports[0].entries_no_fill
    assert len(nf) == 1 and "停牌" in nf[0]["reason"]
    assert store.read_state()["reserved_cash"] == 0.0


def test_partial_fill_is_explicitly_unsupported(cfg, store):
    """明确声明不支持部分成交：成交股数恰好等于计划股数。"""
    assert S.PARTIAL_FILL_SUPPORTED is False
    mkt = _market()
    _enter(cfg, store, mkt)
    qty = _first_order(store)["quantity"]
    limit = _first_order(store)["limit_price"]
    mkt.set_bar(A, D1, o=limit - 0.20, h=limit, l=limit - 0.30)

    engine.run(run_date=D1, cfg=cfg, store=store, market=mkt)
    pos = S.open_positions(store.read_state())[A]
    assert pos["entry_shares"] == qty               # 0 股或全量，没有中间值


def test_no_signal_snapshot_means_no_new_orders(cfg, store):
    """没有当天的信号快照就不建单 —— 绝不拿过期信号下单。"""
    mkt = build_market({}, signals={D2: make_signals(D2, [A])},
                       forecasts={D2: {A: 0.05}})
    r = engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    assert r.reports[0].new_orders == []
    assert any("没有信号快照" in n for n in r.reports[0].notes)


def test_missing_forecast_is_skipped_not_faked(cfg, store):
    """没有预期收益就跳过 —— 否则 target 会退化成"目标=成本"，一开盘就触发。"""
    mkt = build_market({}, signals={D0: make_signals(D0, [A])},
                       forecasts={D0: {}})
    r = engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    assert r.reports[0].new_orders == []
    assert r.reports[0].skipped[0]["reason"] == "no_forecast"


def test_held_symbols_are_not_entered_again(cfg, store):
    """已持有的标的在退出前不再加仓。"""
    mkt = _market()
    _enter(cfg, store, mkt)
    limit = _first_order(store)["limit_price"]
    mkt.set_bar(A, D1, o=limit - 0.30, h=limit, l=limit - 0.40)
    engine.run(run_date=D1, cfg=cfg, store=store, market=mkt)
    assert A in S.open_positions(store.read_state())

    # D1 又有 A 的信号（价格没到目标也没到止损）
    mkt.set_bar(A, D1, o=limit, h=limit + 0.10, l=limit - 0.05)
    mkt._signals[D1] = make_signals(D1, [A])
    mkt._forecasts[D1] = {A: 0.05}
    r = engine.run(run_date=D1, cfg=cfg, store=store, market=mkt)
    assert r.noop is True                            # 同一天重跑 -> 无操作
    assert S.pending_list(store.read_state()) == []


def test_run_date_in_the_future_is_refused(cfg, store):
    with pytest.raises(engine.EngineError) as e:
        engine.run(run_date="2030-01-01", capital=CAP, cfg=cfg, store=store,
                   market=_market())
    assert "还没有行情" in str(e.value)


def test_rewinding_the_experiment_is_refused(cfg, store):
    mkt = _market()
    _enter(cfg, store, mkt)
    mkt.set_bar(A, D1, o=10, h=10, l=10)
    engine.run(run_date=D1, cfg=cfg, store=store, market=mkt)
    with pytest.raises(engine.EngineError) as e:
        engine.run(run_date=D0, cfg=cfg, store=store, market=mkt)
    assert "只能向前" in str(e.value)
