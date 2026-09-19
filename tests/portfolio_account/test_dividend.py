# -*- coding: utf-8 -*-
"""§10 / §15：分红是已实现收益，不改股数。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from wealth import engine, repository as repo


def test_dividend_is_realized_income_and_keeps_units(conn, make_product):
    pid = make_product()
    repo.create_transaction(conn, "2026-09-01", pid, "buy", units=100,
                            price=10.0, amount=1000.0)
    repo.create_transaction(conn, "2026-09-05", pid, "dividend",
                            amount=250.0)
    h = engine.holdings_from_ledger(repo.list_transactions(conn))
    assert h.units == 100                      # 股数不变
    assert h.dividends == pytest.approx(250.0)
    assert h.realized_pnl == pytest.approx(250.0)


def test_dividend_is_internal_flow(conn, make_product):
    pid = make_product()
    tid = repo.create_transaction(conn, "2026-09-05", pid, "dividend",
                                  amount=250.0)
    row = [t for t in repo.list_transactions(conn) if t["txn_id"] == tid][0]
    assert row["cash_flow"] == 0.0             # 内部流


def test_dividends_view_lists_them(conn, make_product):
    pid = make_product()
    repo.create_transaction(conn, "2026-09-05", pid, "dividend",
                            amount=250.0)
    rows = conn.execute("SELECT * FROM dividends").fetchall()
    assert len(rows) == 1
    assert float(rows[0]["amount"]) == pytest.approx(250.0)


def test_dividend_adds_to_cash(conn, make_product):
    pid = make_product()
    repo.create_transaction(conn, "2026-09-01", pid, "deposit",
                            amount=1000.0, cash_flow=1000.0)
    repo.create_transaction(conn, "2026-09-05", pid, "dividend",
                            amount=250.0)
    assert engine.cash_balance(conn)["implied"] == pytest.approx(1250.0)


def test_capital_flow_and_investment_return_are_separate():
    """§15：存入 10 万不能让当天收益变成 +10 万。"""
    pnl = engine.investment_pnl(beginning_value=0.0, ending_value=100000.0,
                                external_net_flow=100000.0)
    assert pnl == pytest.approx(0.0)
