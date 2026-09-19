# -*- coding: utf-8 -*-
"""§13：交易流水是唯一真相；外部流/内部流不变量由 DB 层强制。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from wealth import repository as repo


def test_internal_flow_must_not_carry_cash_flow(conn, make_product):
    pid = make_product()
    with pytest.raises(repo.ValidationError):
        repo.create_transaction(conn, "2026-09-01", pid, "buy", units=100,
                                price=10.0, amount=1000.0, cash_flow=1000.0)


def test_external_flow_must_carry_cash_flow(conn, make_product):
    pid = make_product()
    with pytest.raises(repo.ValidationError):
        repo.create_transaction(conn, "2026-09-01", pid, "deposit",
                                amount=10000.0, cash_flow=0.0)


def test_deposit_with_cash_flow_is_accepted(conn, make_product):
    pid = make_product(ptype="cash", ticker=None)
    tid = repo.create_transaction(conn, "2026-09-01", pid, "deposit",
                                  amount=10000.0, cash_flow=10000.0)
    assert tid > 0


def test_every_write_is_audited(conn, make_product):
    pid = make_product()
    repo.create_transaction(conn, "2026-09-01", pid, "buy", units=100,
                            price=10.0, amount=1000.0)
    logs = repo.list_audit(conn, limit=10)
    assert any(l["object_type"] == "transactions" for l in logs)


def test_update_and_delete_require_a_reason(conn, make_product):
    pid = make_product()
    tid = repo.create_transaction(conn, "2026-09-01", pid, "buy", units=100,
                                  price=10.0, amount=1000.0)
    with pytest.raises(Exception):
        repo.update_transaction(conn, tid, reason="", amount=2000.0)
    with pytest.raises(Exception):
        repo.delete_transaction(conn, tid, reason="")
    repo.delete_transaction(conn, tid, reason="录入错误，重录")
    assert repo.list_transactions(conn, product_id=pid) == []


def test_ledger_is_ordered_by_date(conn, make_product):
    pid = make_product()
    for d in ("2026-09-03", "2026-09-01", "2026-09-02"):
        repo.create_transaction(conn, d, pid, "buy", units=100, price=10.0,
                                amount=1000.0)
    dates = [t["txn_date"] for t in repo.list_transactions(conn)]
    assert dates == sorted(dates)
