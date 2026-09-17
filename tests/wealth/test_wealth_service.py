# -*- coding: utf-8 -*-
"""STEP 7B service layer: the Daily Update flow (spec §6/§8.3)."""

import pytest

from wealth import repository as repo
from wealth import service
from wealth.service import UpdateEntry, record_daily_update


def test_first_entry_creates_opening_deposit(basic):
    conn = basic["conn"]
    res = service.snapshot_from_amount(conn, "2026-09-01", basic["fund"],
                                       10000.0)
    assert res.updated[0]["market_value"] == 10000.0
    txns = repo.list_transactions(conn, product_id=basic["fund"])
    assert [t["txn_type"] for t in txns] == ["deposit"]
    assert txns[0]["cash_flow"] == 10000.0


def test_money_market_income_is_derived(basic):
    conn = basic["conn"]
    service.snapshot_from_amount(conn, "2026-09-01", basic["mm"], 10000.0)
    service.snapshot_from_amount(conn, "2026-09-02", basic["mm"], 10001.5)
    rows = repo.list_income(conn, basic["mm"])
    assert len(rows) == 1                       # only the second day derives
    r = rows[0]
    assert r["daily_income"] == pytest.approx(1.5)
    assert r["income_per_10000"] == pytest.approx(1.5)
    # no external flow that day -> effective units are unambiguous (exact)
    assert r["calculation_method"] == "exact"


def test_same_day_deposit_does_not_dilute_yield(basic):
    """Spec §8.3 acceptance scenario."""
    conn = basic["conn"]
    service.snapshot_from_amount(conn, "2026-09-01", basic["mm"], 10000.0)
    # today: deposit 5,000 (recorded in the ledger), end value 15,001.5
    repo.create_transaction(conn, "2026-09-02", basic["mm"], "deposit",
                            amount=5000, cash_flow=5000)
    service.snapshot_from_amount(conn, "2026-09-02", basic["mm"], 15001.5,
                                 cash_flow=5000.0)
    r = repo.list_income(conn, basic["mm"])[0]
    assert r["daily_income"] == pytest.approx(1.5)
    # with effective units 12,500 the yield is 1.2 per 10,000, NOT the
    # diluted 1.0 that using ending units would produce
    assert r["income_per_10000"] == pytest.approx(1.5 / 12500 * 10000)
    assert r["income_per_10000"] > 1.5 / 15000 * 10000
    assert r["calculation_method"] == "estimated"   # flow timing unknown


def test_bond_fund_gets_no_income_record(basic):
    conn = basic["conn"]
    service.snapshot_from_amount(conn, "2026-09-01", basic["fund"], 10000.0)
    service.snapshot_from_amount(conn, "2026-09-02", basic["fund"], 10050.0)
    assert repo.list_income(conn, basic["fund"]) == []


def test_gap_warning_is_recorded(basic):
    conn = basic["conn"]
    service.snapshot_from_amount(conn, "2026-09-01", basic["fund"], 10000.0)
    res = service.snapshot_from_amount(conn, "2026-10-15", basic["fund"],
                                       10200.0)
    assert any("距上次录入" in w for w in res.warnings)


def test_units_and_nav_derivation(basic):
    conn = basic["conn"]
    res = record_daily_update(conn, "2026-09-01", [
        UpdateEntry(product_id=basic["stock"], market_value=17000.0,
                    nav=1700.0)])
    row = res.updated[0]
    assert row["units"] == pytest.approx(10.0)
    assert row["nav"] == 1700.0
    # units given, no nav -> nav derived
    res2 = record_daily_update(conn, "2026-09-02", [
        UpdateEntry(product_id=basic["stock"], market_value=17500.0,
                    units=10.0)])
    assert res2.updated[0]["nav"] == pytest.approx(1750.0)


def test_latest_summary_shape(basic):
    conn = basic["conn"]
    service.snapshot_from_amount(conn, "2026-09-01", basic["fund"], 10000.0)
    service.snapshot_from_amount(conn, "2026-09-02", basic["fund"], 10150.0)
    s = service.latest_summary(conn)
    assert s["net_worth"] == pytest.approx(10150.0)
    assert s["total_pnl"] == pytest.approx(150.0)
    assert s["day_pnl"] == pytest.approx(150.0)
    assert s["twr"] == pytest.approx(0.015, abs=1e-9)
    assert s["invested_capital"] == pytest.approx(10000.0)


def test_latest_summary_empty_db(seeded):
    s = service.latest_summary(seeded)
    assert s["net_worth"] == 0.0 and s["twr"] is None


def test_decompose_period(basic):
    conn = basic["conn"]
    repo.create_transaction(conn, "2026-09-01", basic["fund"], "deposit",
                            amount=10000, cash_flow=10000)
    service.snapshot_from_amount(conn, "2026-09-01", basic["fund"], 10000.0)
    service.snapshot_from_amount(conn, "2026-09-30", basic["fund"], 10250.0)
    d = service.decompose_period(conn, "2026-09-01", "2026-09-30")
    assert d["external_contributions"] == pytest.approx(10000.0)
    assert d["investment_pnl"] == pytest.approx(250.0)
    # account starts empty inside the window: net worth 0 -> 10,250
    assert d["net_change"] == pytest.approx(10250.0)
    assert d["reconciliation_error"] == pytest.approx(0.0, abs=1e-9)
