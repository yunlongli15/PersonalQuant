# -*- coding: utf-8 -*-
"""STEP 7A: schema, CRUD, invariants, audit trail, backup/export."""

import json
import sqlite3

import pytest

from wealth import db as wdb
from wealth import repository as repo
from wealth.repository import ValidationError


def test_schema_tables_and_views(conn):
    names = set(wdb.table_names(conn))
    for t in ("platforms", "accounts", "products", "transactions",
              "daily_snapshots", "positions", "income_records",
              "benchmark_records", "wealth_categories", "audit_log"):
        assert t in names, f"missing table {t}"
    for v in ("cash_flows", "fees", "dividends", "v_latest_values"):
        assert v in names, f"missing view {v}"


def test_seed_idempotent(conn):
    from wealth import seed

    a = seed.seed(conn)
    b = seed.seed(conn)
    assert a["platforms"] > 0
    assert b["platforms"] == 0 and b["accounts"] == 0
    assert len(repo.list_platforms(conn)) == len(a and seed.DEFAULT_PLATFORMS)


def test_platform_kind_validated(conn):
    with pytest.raises(ValidationError):
        repo.create_platform(conn, "X", kind="crypto_exchange")


def test_product_type_validated(basic):
    with pytest.raises(ValidationError):
        repo.create_product(basic["conn"], basic["acct"], "weird",
                            "crypto")


def test_account_requires_existing_platform(conn):
    with pytest.raises(ValidationError):
        repo.create_account(conn, 99999, "ghost")


def test_ticker_normalisation_is_not_repo_business(basic):
    # repo stores the canonical '600519.SH' form verbatim; normalisation
    # belongs to personal_quant.symbols and is applied by the caller
    p = repo.get_product(basic["conn"], basic["stock"])
    assert p["ticker"] == "600519.SH"


def test_external_flow_requires_signed_cash_flow(basic):
    conn = basic["conn"]
    with pytest.raises(ValidationError):
        repo.create_transaction(conn, "2026-09-01", basic["fund"],
                                "deposit")           # no cash_flow
    tid = repo.create_transaction(conn, "2026-09-01", basic["fund"],
                                  "deposit", amount=10000.0, cash_flow=10000.0)
    assert tid > 0
    tid2 = repo.create_transaction(conn, "2026-09-02", basic["fund"],
                                   "withdrawal", amount=500.0,
                                   cash_flow=-500.0)
    assert tid2 > 0


def test_internal_flow_must_not_carry_external_cash_flow(basic):
    conn = basic["conn"]
    with pytest.raises(ValidationError) as e:
        repo.create_transaction(conn, "2026-09-03", basic["fund"], "buy",
                                units=100, price=1.2, amount=120.0,
                                cash_flow=120.0)
    assert "internal flow" in str(e.value)
    # internal buy with cash_flow = 0 is fine
    tid = repo.create_transaction(conn, "2026-09-03", basic["fund"], "buy",
                                  units=100, price=1.2, amount=120.0)
    assert tid > 0


def test_negative_amounts_rejected(basic):
    conn = basic["conn"]
    for kw in ({"amount": -1.0}, {"fee": -0.5}, {"units": -10}):
        with pytest.raises(ValidationError):
            repo.create_transaction(conn, "2026-09-04", basic["fund"],
                                    "buy", price=1.0, **kw)


def test_transaction_update_requires_reason(basic):
    conn = basic["conn"]
    tid = repo.create_transaction(conn, "2026-09-05", basic["stock"],
                                  "buy", units=100, price=1700.0,
                                  amount=170000.0, fee=45.0)
    with pytest.raises(ValidationError):
        repo.update_transaction(conn, tid, reason="", price=1690.0)
    repo.update_transaction(conn, tid, reason="broker confirmation",
                            price=1690.0)
    t = [r for r in repo.list_transactions(conn) if r["txn_id"] == tid][0]
    assert t["price"] == 1690.0


def test_transaction_delete_requires_reason(basic):
    conn = basic["conn"]
    tid = repo.create_transaction(conn, "2026-09-05", basic["stock"], "buy",
                                  units=100, price=1700.0, amount=170000.0)
    with pytest.raises(ValidationError):
        repo.delete_transaction(conn, tid, reason="")
    repo.delete_transaction(conn, tid, reason="duplicate entry")
    assert not [r for r in repo.list_transactions(conn)
                if r["txn_id"] == tid]


def test_snapshot_upsert_is_idempotent(basic):
    conn = basic["conn"]
    repo.upsert_snapshot(conn, "2026-09-09", basic["fund"], units=10000,
                         nav=1.02, market_value=10200.0)
    repo.upsert_snapshot(conn, "2026-09-09", basic["fund"], units=10000,
                         nav=1.021, market_value=10210.0)
    rows = repo.list_snapshots(conn, product_id=basic["fund"])
    assert len(rows) == 1
    assert rows[0]["market_value"] == 10210.0


def test_latest_values_view(basic):
    conn = basic["conn"]
    repo.upsert_snapshot(conn, "2026-09-08", basic["fund"], market_value=10000)
    repo.upsert_snapshot(conn, "2026-09-09", basic["fund"],
                         market_value=10250)
    repo.upsert_snapshot(conn, "2026-09-09", basic["stock"], units=200,
                         nav=1680.0, market_value=336000.0)
    rows = conn.execute("SELECT product_id, market_value FROM "
                        "v_latest_values ORDER BY product_id").fetchall()
    m = {r["product_id"]: r["market_value"] for r in rows}
    assert m[basic["fund"]] == 10250
    assert m[basic["stock"]] == 336000.0


def test_cash_flow_view_and_internal_exclusion(basic):
    conn = basic["conn"]
    repo.create_transaction(conn, "2026-09-01", basic["fund"], "deposit",
                            amount=10000, cash_flow=10000)
    repo.create_transaction(conn, "2026-09-02", basic["fund"], "buy",
                            units=9000, price=1.0, amount=9000)
    rows = conn.execute("SELECT txn_type FROM cash_flows").fetchall()
    assert [r["txn_type"] for r in rows] == ["deposit"]


def test_dividend_and_fee_views(basic):
    conn = basic["conn"]
    repo.create_transaction(conn, "2026-06-10", basic["stock"], "dividend",
                            amount=3200.0, fee=0.0)
    repo.create_transaction(conn, "2026-06-11", basic["stock"], "buy",
                            units=100, price=1700.0, amount=170000.0,
                            fee=45.0)
    assert len(conn.execute("SELECT * FROM dividends").fetchall()) == 1
    assert len(conn.execute("SELECT * FROM fees").fetchall()) == 1


def test_income_record_upsert_and_method_validation(basic):
    conn = basic["conn"]
    repo.upsert_income(conn, "2026-09-09", basic["mm"],
                       beginning_units=10000, ending_units=10000,
                       beginning_value=10000.0, ending_value=10001.5,
                       cash_flow=0.0, daily_income=1.5,
                       income_per_10000=1.5,
                       calculation_method="exact")
    repo.upsert_income(conn, "2026-09-09", basic["mm"],
                       beginning_units=10000, ending_units=10000,
                       beginning_value=10000.0, ending_value=10001.6,
                       cash_flow=0.0, daily_income=1.6,
                       income_per_10000=1.6, calculation_method="exact")
    rows = repo.list_income(conn, basic["mm"])
    assert len(rows) == 1 and rows[0]["income_per_10000"] == 1.6


def test_benchmark_validation_and_upsert(conn):
    repo.upsert_benchmark(conn, "2026-09-09", "CSI300", 4000.5)
    repo.upsert_benchmark(conn, "2026-09-09", "CSI300", 4010.0)
    repo.upsert_benchmark(conn, "2026-09-09", "custom:my_coal_index", 100.0)
    assert len(repo.list_benchmarks(conn, "CSI300")) == 1
    assert repo.list_benchmarks(conn, "CSI300")[0]["close"] == 4010.0
    with pytest.raises(ValidationError):
        repo.upsert_benchmark(conn, "2026-09-09", "DOGE", 1.0)


def test_audit_trail_records_create_and_update(basic):
    conn = basic["conn"]
    repo.update_product(conn, basic["fund"], name="债券基金 A (改名)",
                        reason="user renamed the product")
    rows = repo.list_audit(conn, object_type="products")
    actions = [r["action"] for r in rows]
    assert "create" in actions and "update" in actions
    upd = [r for r in rows if r["action"] == "update"][0]
    assert json.loads(upd["old_value"])["name"] == "债券基金 A"
    assert "user renamed" in (upd["reason"] or "")


def test_audit_log_is_append_only(basic):
    conn = basic["conn"]
    n0 = len(repo.list_audit(conn, limit=1000))
    repo.create_transaction(conn, "2026-09-06", basic["fund"], "buy",
                            units=100, price=1.0, amount=100.0)
    n1 = len(repo.list_audit(conn, limit=1000))
    assert n1 > n0


def test_backup_creates_restorable_file(basic, tmp_path):
    conn = basic["conn"]
    repo.create_transaction(conn, "2026-09-07", basic["fund"], "deposit",
                            amount=5000, cash_flow=5000)
    target = wdb.backup(tmp_path, conn=conn)
    assert target.exists() and target.suffix == ".db"
    restored = sqlite3.connect(str(target))
    n = restored.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    restored.close()
    assert n == 1


def test_export_csv_and_json(basic, tmp_path):
    conn = basic["conn"]
    repo.create_transaction(conn, "2026-09-08", basic["stock"], "buy",
                            units=100, price=1700.0, amount=170000.0,
                            fee=45.0)
    written = repo.export_csv(conn, tmp_path / "csv")
    assert written["transactions"] == 1
    (tmp_path / "csv" / "transactions.csv").exists()
    repo.export_json(conn, tmp_path / "dump.json")
    data = json.loads((tmp_path / "dump.json").read_text(encoding="utf-8"))
    assert len(data["transactions"]) == 1
    assert data["products"][0]["name"]


def test_positions_replace_and_read(basic):
    conn = basic["conn"]
    repo.replace_positions(conn, "2026-09-09", [
        {"product_id": basic["stock"], "units": 200, "avg_cost": 1650.0,
         "market_value": 336000.0, "realized_pnl": 0.0,
         "unrealized_pnl": 6000.0},
        {"product_id": basic["fund"], "units": 10000, "avg_cost": 1.0,
         "market_value": 10250.0},
    ])
    rows = repo.list_positions(conn, "2026-09-09")
    assert len(rows) == 2
    # replace with a shorter list on the same date -> old rows gone
    repo.replace_positions(conn, "2026-09-09", rows[:1])
    assert len(repo.list_positions(conn, "2026-09-09")) == 1


def test_money_market_flag(basic):
    from wealth.models import Product

    mm = Product(name="x", product_type="money_fund")
    bond = Product(name="y", product_type="bond_fund")
    assert mm.is_money_market and not bond.is_money_market


def test_wealth_db_path_is_under_data(tmp_path):
    assert "data" in str(wdb.WEALTH_DB).lower()
    assert str(wdb.WEALTH_DB).endswith("wealth.db")
