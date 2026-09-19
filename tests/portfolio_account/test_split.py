# -*- coding: utf-8 -*-
"""§10 / §50：拆股/送股（STEP 11 新实现，替换原来的显式空操作）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from wealth import engine, repository as repo


def test_two_for_one_doubles_units_and_halves_cost(conn, make_product):
    pid = make_product()
    repo.create_transaction(conn, "2026-09-01", pid, "buy", units=100,
                            price=10.0, amount=1000.0)
    repo.create_transaction(conn, "2026-09-02", pid, "split", units=2.0)
    h = engine.holdings_from_ledger(repo.list_transactions(conn))
    assert h.units == pytest.approx(200.0)
    assert h.avg_cost == pytest.approx(5.0)


def test_split_does_not_change_total_cost(conn, make_product):
    pid = make_product()
    repo.create_transaction(conn, "2026-09-01", pid, "buy", units=100,
                            price=10.0, amount=1000.0)
    repo.create_transaction(conn, "2026-09-02", pid, "split", units=4.0)
    h = engine.holdings_from_ledger(repo.list_transactions(conn))
    assert h.units * h.avg_cost == pytest.approx(1000.0)


def test_split_creates_no_cash_and_no_pnl(conn, make_product):
    pid = make_product()
    repo.create_transaction(conn, "2026-09-01", pid, "buy", units=100,
                            price=10.0, amount=1000.0)
    repo.create_transaction(conn, "2026-09-02", pid, "split", units=2.0)
    h = engine.holdings_from_ledger(repo.list_transactions(conn))
    assert h.realized_pnl == pytest.approx(0.0)
    assert engine.cash_balance(conn)["implied"] == pytest.approx(-1000.0)


def test_illegal_ratio_is_ignored_not_applied(conn, make_product):
    """比例 <= 0 是脏数据：忽略它，绝不把持仓算成 0 或负数。"""
    pid = make_product()
    repo.create_transaction(conn, "2026-09-01", pid, "buy", units=100,
                            price=10.0, amount=1000.0)
    repo.create_transaction(conn, "2026-09-02", pid, "split", units=0.0)
    h = engine.holdings_from_ledger(repo.list_transactions(conn))
    assert h.units == pytest.approx(100.0)
    assert h.avg_cost == pytest.approx(10.0)


def test_split_after_partial_sell(conn, make_product):
    pid = make_product()
    repo.create_transaction(conn, "2026-09-01", pid, "buy", units=200,
                            price=20.0, amount=4000.0)
    repo.create_transaction(conn, "2026-09-02", pid, "sell", units=100,
                            price=25.0, amount=2500.0)
    repo.create_transaction(conn, "2026-09-03", pid, "split", units=2.0)
    h = engine.holdings_from_ledger(repo.list_transactions(conn))
    assert h.units == pytest.approx(200.0)     # 剩 100，拆 2 倍
    assert h.avg_cost == pytest.approx(10.0)
    assert h.realized_pnl == pytest.approx(500.0)   # 拆股不影响已实现
