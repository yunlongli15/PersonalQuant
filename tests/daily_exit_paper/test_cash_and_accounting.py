# -*- coding: utf-8 -*-
"""现金核算与对账（spec §21-§25 / §36）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

from conftest import SESSIONS, SYMS, build_market, day, make_signals
from daily_exit_paper import config as C, engine, ledger as L, state as S

A, B = SYMS[0], SYMS[1]
CAP = 66_000.0
D0, D1, D2 = day(SESSIONS, 0), day(SESSIONS, 1), day(SESSIONS, 2)


def _cost(cfg):
    from personal_quant.strategy.costs import TransactionCostModel

    return TransactionCostModel.from_config(
        {"transaction_costs": C.spec(cfg)["transaction_costs"]})


def _open_position(cfg, store):
    mkt = build_market({}, {D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    limit = S.pending_list(store.read_state())[0]["limit_price"]
    mkt.set_bar(A, D1, o=limit - 0.30, h=limit, l=limit - 0.40)
    engine.run(run_date=D1, cfg=cfg, store=store, market=mkt)
    return mkt


# ---------------------------------------------------------------------------
# 预留 / 释放（§22）
# ---------------------------------------------------------------------------

def test_reserve_holds_worst_case_cash_then_releases(cfg, store):
    mkt = build_market({}, {D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    st = store.read_state()
    o = S.pending_list(st)[0]

    assert st["cash"] == pytest.approx(CAP)                  # 钱还在账上
    assert st["reserved_cash"] == pytest.approx(o["reserved_cash"])
    # 预留在**限价**上算，覆盖"最坏情况也买得起"
    assert o["reserved_cash"] >= o["quantity"] * o["limit_price"]

    limit = o["limit_price"]
    mkt.set_bar(A, D1, o=limit + 1.0, h=limit + 1.2, l=limit + 0.5)  # 不成交
    engine.run(run_date=D1, cfg=cfg, store=store, market=mkt)
    st = store.read_state()
    assert st["reserved_cash"] == 0.0
    assert st["cash"] == pytest.approx(CAP)
    assert S.available_cash(st) == pytest.approx(st["cash"])


def test_available_cash_never_counts_reserved(cfg, store):
    mkt = build_market({}, {D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    st = store.read_state()
    assert S.available_cash(st) == pytest.approx(
        st["cash"] - st["reserved_cash"])
    assert S.available_cash(st) < st["cash"]


# ---------------------------------------------------------------------------
# 买卖的现金流（§21 / §23）
# ---------------------------------------------------------------------------

def test_buy_moves_exactly_value_plus_fee(cfg, store):
    cost = _cost(cfg)
    mkt = build_market({}, {D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    limit = S.pending_list(store.read_state())[0]["limit_price"]
    fill_px = round(limit - 0.30, 2)
    mkt.set_bar(A, D1, o=fill_px, h=limit, l=fill_px - 0.10)
    engine.run(run_date=D1, cfg=cfg, store=store, market=mkt)

    st = store.read_state()
    pos = S.open_positions(st)[A]
    value = pos["entry_shares"] * fill_px
    assert st["cash"] == pytest.approx(CAP - value - pos["entry_fee"])
    assert pos["entry_fee"] == pytest.approx(cost.buy_cost(value))


def test_sell_moves_exactly_proceeds_minus_fee(cfg, store):
    cost = _cost(cfg)
    mkt = _open_position(cfg, store)
    st = store.read_state()
    pos = S.open_positions(st)[A]
    cash_before = st["cash"]

    tgt = pos["target_price"]
    mkt.set_bar(A, D2, o=tgt - 0.10, h=tgt + 0.30, l=tgt - 0.20)
    engine.run(run_date=D2, cfg=cfg, store=store, market=mkt)

    st = store.read_state()
    closed = st["positions"][A]
    value = closed["exit_shares"] * closed["exit_price"]
    assert st["cash"] == pytest.approx(cash_before + value - closed["exit_fee"])
    assert closed["exit_fee"] == pytest.approx(cost.sell_cost(value))
    assert closed["exit_fee"] > 0


def test_net_pnl_is_gross_minus_both_fees(cfg, store):
    mkt = _open_position(cfg, store)
    pos = S.open_positions(store.read_state())[A]
    entry_value = pos["entry_value"]
    entry_fee = pos["entry_fee"]
    tgt = pos["target_price"]
    mkt.set_bar(A, D2, o=tgt - 0.10, h=tgt + 0.30, l=tgt - 0.20)
    engine.run(run_date=D2, cfg=cfg, store=store, market=mkt)

    p = store.read_state()["positions"][A]
    gross = p["exit_value"] - entry_value
    assert p["realized_pnl"] == pytest.approx(
        gross - entry_fee - p["exit_fee"], abs=0.01)


# ---------------------------------------------------------------------------
# 预估口径 vs 账本口径（§24）
# ---------------------------------------------------------------------------

def test_estimated_fee_matches_the_ledger_fee(cfg, store):
    """下单时的预估费用与实际扣费必须一致 —— 同一个 cost model，不是抄一份。"""
    cost = _cost(cfg)
    mkt = build_market({}, {D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    o = S.pending_list(store.read_state())[0]

    # 成交在**限价**上（最坏情况），预估与实际应逐分一致
    limit = o["limit_price"]
    mkt.set_bar(A, D1, o=limit + 0.5, h=limit + 0.6, l=limit - 0.05)
    engine.run(run_date=D1, cfg=cfg, store=store, market=mkt)

    pos = S.open_positions(store.read_state())[A]
    assert pos["entry_fee"] == pytest.approx(o["estimated_fee"], abs=0.01)
    assert pos["entry_fee"] == pytest.approx(
        cost.buy_cost(o["quantity"] * limit), abs=0.01)

    ledger_fee = [e for e in store.read_ledger()
                  if e["type"] == "ORDER_FILLED"][0]["fee"]
    assert ledger_fee == pytest.approx(pos["entry_fee"], abs=1e-9)


def test_fee_events_match_the_position_fees(cfg, store):
    mkt = _open_position(cfg, store)
    tgt = S.open_positions(store.read_state())[A]["target_price"]
    mkt.set_bar(A, D2, o=tgt - 0.10, h=tgt + 0.30, l=tgt - 0.20)
    engine.run(run_date=D2, cfg=cfg, store=store, market=mkt)

    fees = [e for e in store.read_ledger() if e["type"] == "FEE"]
    p = store.read_state()["positions"][A]
    assert sum(e["fee"] for e in fees) == pytest.approx(
        p["entry_fee"] + p["exit_fee"], abs=0.01)


# ---------------------------------------------------------------------------
# 对账（§36）
# ---------------------------------------------------------------------------

def test_ledger_recomputes_the_same_cash(cfg, store):
    mkt = _open_position(cfg, store)
    st = store.read_state()
    events = store.read_ledger()
    assert L.cash_from_ledger(events, CAP) == pytest.approx(st["cash"],
                                                            abs=0.01)


def test_reconcile_raises_on_a_tampered_state(cfg, store):
    """state 被人改过 -> 报错，**绝不自动改账**。"""
    mkt = _open_position(cfg, store)
    st = store.read_state()
    st["cash"] += 123.45
    with pytest.raises(L.ReconciliationError) as e:
        L.reconcile(st, store.read_ledger(), {})
    assert "不自动改账" in str(e.value)


def test_negative_cash_is_refused(cfg, store):
    st = S.empty_state(CAP, as_of=None)
    st["cash"] = -1.0
    with pytest.raises(L.ReconciliationError):
        L.check_invariants(st, {})


def test_reserved_exceeding_cash_is_refused(cfg, store):
    st = S.empty_state(CAP, as_of=None)
    st["reserved_cash"] = CAP + 1.0
    with pytest.raises(L.ReconciliationError) as e:
        L.check_invariants(st, {})
    assert "available_cash" in str(e.value)


def test_negative_position_is_refused():
    st = S.empty_state(CAP, as_of=None)
    st["positions"] = {"X.SH": {"status": "OPEN", "entry_shares": -100,
                                "entry_price": 10.0}}
    with pytest.raises(L.ReconciliationError):
        L.check_invariants(st, {"X.SH": 10.0})


def test_portfolio_value_identity_holds_through_a_full_cycle(cfg, store):
    mkt = _open_position(cfg, store)
    tgt = S.open_positions(store.read_state())[A]["target_price"]
    mkt.set_bar(A, D2, o=tgt - 0.10, h=tgt + 0.30, l=tgt - 0.20)
    st = store.read_state()
    engine.run(run_date=D2, cfg=cfg, store=store, market=mkt)
    st = store.read_state()
    totals = L.check_invariants(st, {})
    assert totals["portfolio_value"] == pytest.approx(
        st["cash"] + totals["position_value"])
    assert totals["portfolio_value"] == pytest.approx(
        CAP + st["positions"][A]["realized_pnl"], abs=0.02)


def test_cash_never_goes_negative_across_a_busy_day(cfg, store):
    """同一天多笔挂单争抢现金 -> 预留总额不得超过账面现金。"""
    mkt = build_market({}, {D0: make_signals(D0, SYMS)},
                       {D0: {s: 0.05 for s in SYMS}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    st = store.read_state()
    assert st["reserved_cash"] <= st["cash"] + 1e-9
    assert S.available_cash(st) >= -1e-9
