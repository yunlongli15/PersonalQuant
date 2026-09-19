# -*- coding: utf-8 -*-
"""§15：存入资金是**外部流**，绝不能算成当日收益。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from wealth import engine, repository as repo, service


def test_a_deposit_is_not_income(conn, make_product):
    """这一条是个人记账最经典的 bug：存 10 万被记成赚 10 万。"""
    pid = make_product(ptype="cash", ticker=None)
    repo.upsert_snapshot(conn, "2026-09-01", pid, units=1000.0, nav=1.0,
                         market_value=1000.0)
    repo.create_transaction(conn, "2026-09-01", pid, "deposit",
                            amount=100000.0, cash_flow=100000.0,
                            source="opening")
    repo.upsert_snapshot(conn, "2026-09-02", pid, units=101000.0, nav=1.0,
                         market_value=101000.0, cash_flow=100000.0)
    pnl = engine.investment_pnl(beginning_value=1000.0,
                                ending_value=101000.0,
                                external_net_flow=100000.0)
    assert pnl == pytest.approx(0.0)


def test_external_flow_is_signed(conn, make_product):
    pid = make_product(ptype="cash", ticker=None)
    txns = [
        {"txn_type": "deposit", "cash_flow": 500.0},
        {"txn_type": "withdrawal", "cash_flow": -200.0},
        {"txn_type": "buy", "cash_flow": 0.0},          # 内部流，不计
    ]
    assert engine.net_external_flow(txns) == pytest.approx(300.0)


def test_deposit_requires_a_nonzero_amount(conn, make_product):
    pid = make_product(ptype="cash", ticker=None)
    with pytest.raises(repo.ValidationError):
        repo.create_transaction(conn, "2026-09-01", pid, "deposit",
                                amount=0.0, cash_flow=0.0)


def test_first_entry_creates_an_opening_deposit(conn, make_product):
    """首次录入自动补一笔期初投入，这样 P&L 从 0 开始而不是从"赚了本金"。"""
    pid = make_product(ptype="bond_fund", ticker=None)
    service.record_daily_update(conn, "2026-09-01", [
        service.UpdateEntry(product_id=pid, market_value=10000.0)])
    txns = repo.list_transactions(conn, product_id=pid)
    assert any(t["txn_type"] == "deposit" for t in txns)
