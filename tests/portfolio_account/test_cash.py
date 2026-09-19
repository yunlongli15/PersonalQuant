# -*- coding: utf-8 -*-
"""§14：现金余额两种口径（已记录 / 流水推导）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from wealth import engine, repository as repo


def _tx(conn, pid, d, t, amount=0.0, units=0.0, price=0.0, fee=0.0,
        cash_flow=0.0):
    return repo.create_transaction(conn, d, pid, t, units=units, price=price,
                                   amount=amount, fee=fee, cash_flow=cash_flow)


def test_implied_cash_is_zero_without_flows(conn, make_product):
    pid = make_product()
    _tx(conn, pid, "2026-09-01", "buy", units=100, price=10.0, amount=1000.0)
    c = engine.cash_balance(conn)
    assert c["implied"] == pytest.approx(-1000.0)


def test_deposit_then_buy_leaves_the_remainder(conn, make_product):
    pid = make_product()
    _tx(conn, pid, "2026-09-01", "deposit", amount=50000.0,
        cash_flow=50000.0)
    _tx(conn, pid, "2026-09-02", "buy", units=100, price=10.0, amount=1000.0,
        fee=5.0)
    c = engine.cash_balance(conn)
    assert c["implied"] == pytest.approx(50000.0 - 1005.0)


def test_sell_proceeds_and_dividends_add_cash(conn, make_product):
    pid = make_product()
    _tx(conn, pid, "2026-09-01", "deposit", amount=10000.0,
        cash_flow=10000.0)
    _tx(conn, pid, "2026-09-02", "sell", units=100, price=12.0,
        amount=1200.0, fee=6.0)
    _tx(conn, pid, "2026-09-03", "dividend", amount=200.0)
    c = engine.cash_balance(conn)
    assert c["implied"] == pytest.approx(10000.0 + 1194.0 + 200.0)


def test_withdrawal_reduces_cash(conn, make_product):
    pid = make_product()
    _tx(conn, pid, "2026-09-01", "deposit", amount=10000.0,
        cash_flow=10000.0)
    _tx(conn, pid, "2026-09-02", "withdrawal", amount=3000.0,
        cash_flow=-3000.0)
    assert engine.cash_balance(conn)["implied"] == pytest.approx(7000.0)


def test_recorded_cash_comes_from_money_market_products(conn, make_product):
    pid = make_product(name="天天盈", ptype="money_fund", ticker=None)
    repo.upsert_snapshot(conn, "2026-09-01", pid, units=1.0, nav=1.0,
                         market_value=8888.0)
    c = engine.cash_balance(conn)
    assert c["recorded"] == pytest.approx(8888.0)


def test_cash_balance_is_scoped_by_account(conn, acct, make_product):
    other = repo.create_account(conn, 1, "另一个账户")
    p1 = repo.create_product(conn, acct, "A", "stock", ticker="600519.SH")
    p2 = repo.create_product(conn, other, "B", "stock", ticker="000001.SZ")
    _tx(conn, p1, "2026-09-01", "deposit", amount=1000.0, cash_flow=1000.0)
    _tx(conn, p2, "2026-09-01", "deposit", amount=500.0, cash_flow=500.0)
    assert engine.cash_balance(conn, acct)["implied"] == pytest.approx(1000.0)
