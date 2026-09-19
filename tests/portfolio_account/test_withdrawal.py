# -*- coding: utf-8 -*-
"""§15：提款是负向外部流，同样不能算成亏损。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from wealth import engine, repository as repo


def test_a_withdrawal_is_not_a_loss():
    pnl = engine.investment_pnl(beginning_value=100000.0,
                                ending_value=40000.0,
                                external_net_flow=-60000.0)
    assert pnl == pytest.approx(0.0)


def test_withdrawal_is_negative_and_deposit_positive(conn, make_product):
    pid = make_product(ptype="cash", ticker=None)
    repo.create_transaction(conn, "2026-09-01", pid, "deposit",
                            amount=10000.0, cash_flow=10000.0)
    repo.create_transaction(conn, "2026-09-02", pid, "withdrawal",
                            amount=4000.0, cash_flow=-4000.0)
    txns = repo.list_transactions(conn)
    assert engine.net_external_flow([dict(t) for t in txns]) == \
        pytest.approx(6000.0)


def test_transfer_between_accounts_is_external(tmp_path):
    """transfer_in/out 也是外部流 —— 账户之间搬钱不是收益。"""
    from wealth import db
    conn = db.connect(tmp_path / "t2.db")
    p1 = repo.create_platform(conn, "银行", kind="bank")
    a1 = repo.create_account(conn, p1, "账户1")
    a2 = repo.create_account(conn, p1, "账户2")
    x = repo.create_product(conn, a1, "现金A", "cash")
    y = repo.create_product(conn, a2, "现金B", "cash")
    repo.create_transaction(conn, "2026-09-01", x, "transfer_out",
                            amount=5000.0, cash_flow=-5000.0)
    repo.create_transaction(conn, "2026-09-01", y, "transfer_in",
                            amount=5000.0, cash_flow=5000.0)
    assert engine.net_external_flow(
        [dict(t) for t in repo.list_transactions(conn)]) == pytest.approx(0.0)


def test_withdrawal_reduces_implied_cash(conn, make_product):
    pid = make_product(ptype="cash", ticker=None)
    repo.create_transaction(conn, "2026-09-01", pid, "deposit",
                            amount=10000.0, cash_flow=10000.0)
    repo.create_transaction(conn, "2026-09-02", pid, "withdrawal",
                            amount=2500.0, cash_flow=-2500.0)
    assert engine.cash_balance(conn)["implied"] == pytest.approx(7500.0)
