# -*- coding: utf-8 -*-
"""§10：买卖记账（含费用对成本/损益的影响）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from wealth import engine, repository as repo


def test_buy_fee_enters_cost_basis(conn, make_product):
    pid = make_product()
    repo.create_transaction(conn, "2026-09-01", pid, "buy", units=100,
                            price=10.0, amount=1000.0, fee=5.0)
    h = engine.holdings_from_ledger(repo.list_transactions(conn))
    assert h.avg_cost == pytest.approx(10.05)      # (1000 + 5) / 100
    assert h.invested == pytest.approx(1005.0)


def test_sell_fee_reduces_realized_pnl(conn, make_product):
    pid = make_product()
    repo.create_transaction(conn, "2026-09-01", pid, "buy", units=100,
                            price=10.0, amount=1000.0, fee=0.0)
    repo.create_transaction(conn, "2026-09-02", pid, "sell", units=100,
                            price=12.0, amount=1200.0, fee=6.0)
    h = engine.holdings_from_ledger(repo.list_transactions(conn))
    assert h.realized_pnl == pytest.approx(1200.0 - 6.0 - 1000.0)


def test_fees_are_tracked_but_never_double_counted(conn, make_product):
    pid = make_product()
    repo.create_transaction(conn, "2026-09-01", pid, "buy", units=100,
                            price=10.0, amount=1000.0, fee=5.0)
    repo.create_transaction(conn, "2026-09-02", pid, "sell", units=100,
                            price=11.0, amount=1100.0, fee=6.0)
    h = engine.holdings_from_ledger(repo.list_transactions(conn))
    assert h.fees_paid == pytest.approx(11.0)
    # 已实现损益里已经扣过卖出手续费，fees_paid 只是单独统计
    assert h.realized_pnl == pytest.approx(1094.0 - 1005.0)


def test_partial_sell_keeps_remaining_cost(conn, make_product):
    pid = make_product()
    repo.create_transaction(conn, "2026-09-01", pid, "buy", units=200,
                            price=10.0, amount=2000.0)
    repo.create_transaction(conn, "2026-09-02", pid, "sell", units=100,
                            price=15.0, amount=1500.0)
    h = engine.holdings_from_ledger(repo.list_transactions(conn))
    assert h.units == 100
    assert h.avg_cost == pytest.approx(10.0)       # 均价不变
    assert h.realized_pnl == pytest.approx(500.0)


def test_buy_transaction_never_changes_pnl_by_itself(conn, make_product):
    """买/卖是内部流：cash_flow 必须为 0，否则会被算成收益。"""
    pid = make_product()
    tid = repo.create_transaction(conn, "2026-09-01", pid, "buy", units=100,
                                  price=10.0, amount=1000.0)
    row = [t for t in repo.list_transactions(conn) if t["txn_id"] == tid][0]
    assert row["cash_flow"] == 0.0
