# -*- coding: utf-8 -*-
"""§52 / §53：对账与持仓一致性。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from wealth import engine, repository as repo


def test_reconcile_sums_to_total(conn, make_product):
    a = make_product("A", "stock", "600519.SH")
    repo.upsert_snapshot(conn, "2026-09-01", a, market_value=1000.0)
    r = engine.reconcile(conn)
    assert r["ok"] is True
    assert r["sum_of_parts"] == pytest.approx(r["total_value"])


def test_reconcile_reports_zero_on_empty_db(conn):
    r = engine.reconcile(conn)
    assert r["total_value"] == 0.0 and r["ok"] is True


def test_consistency_flags_a_mismatch(conn, make_product):
    """手改 positions 表后必须被发现 —— 账本才是真相。"""
    pid = make_product()
    repo.create_transaction(conn, "2026-09-01", pid, "buy", units=100,
                            price=10.0, amount=1000.0)
    repo.replace_positions(conn, "2026-09-01", [
        {"product_id": pid, "units": 999, "avg_cost": 10.0,
         "market_value": 9990.0, "source": "manual"}])
    rows = engine.position_consistency(conn)
    hit = [r for r in rows if r["product_id"] == pid][0]
    assert hit["status"] == "manual_override"
    assert hit["derived_units"] == 100
    assert hit["stored_units"] == 999


def test_consistency_ok_when_materialised_from_ledger(conn, make_product):
    pid = make_product()
    repo.create_transaction(conn, "2026-09-01", pid, "buy", units=100,
                            price=10.0, amount=1000.0)
    engine.write_positions(conn, "2026-09-01", {pid: 10.0})
    rows = engine.position_consistency(conn)
    hit = [r for r in rows if r["product_id"] == pid][0]
    assert hit["status"] == "ok"


def test_consistency_reports_unmaterialised_products(conn, make_product):
    pid = make_product()
    repo.create_transaction(conn, "2026-09-01", pid, "buy", units=100,
                            price=10.0, amount=1000.0)
    rows = engine.position_consistency(conn)
    assert [r for r in rows if r["product_id"] == pid][0]["status"] == \
        "not_materialised"


def test_cash_plus_assets_equals_total_after_import(conn, tmp_path):
    """端到端：导入一批成交后，对账仍然成立。"""
    from wealth import importer

    p = tmp_path / "t.csv"
    p.write_text("date,symbol,side,quantity,price,fees,account\n"
                 "2026-09-01,,DEPOSIT,100000,0,0,券商\n"
                 "2026-09-02,600519.SH,BUY,100,10.0,5,券商\n",
                 encoding="utf-8")
    importer.import_transactions_csv(conn, p)
    v = engine.value_positions(conn, prices={"600519.SH": 11.0})
    assert v["market_value"] == pytest.approx(1100.0)
    assert v["cash_implied"] == pytest.approx(100000.0 - 1005.0)
