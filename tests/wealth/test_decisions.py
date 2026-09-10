# -*- coding: utf-8 -*-
"""STEP 7G: recommendation -> decision -> execution trail (spec §33/§34/§36)."""

import pytest

from wealth import decisions as dec
from wealth import repository as repo


@pytest.fixture
def plan(basic):
    return {
        "as_of": "2026-09-04", "capital": 500_000.0,
        "rows": [
            {"symbol": "600519.SH", "name": "贵州茅台", "action": "BUY",
             "recommended_entry_price": 1700.0, "entry_low": 1666.0,
             "entry_high": 1725.0, "shares": 200, "target_price": 1850.0,
             "stop_loss": 1550.0, "expected_return": 0.064, "raw_rank": 1,
             "target_weight": 0.095},
            {"symbol": "000001.SZ", "name": "平安银行", "action": "BUY",
             "recommended_entry_price": 11.0, "entry_low": 10.8,
             "entry_high": 11.2, "shares": 4300, "target_price": 12.0,
             "stop_loss": 10.0, "expected_return": 0.03, "raw_rank": 2,
             "target_weight": 0.095},
        ],
        "total_buy_value": 47300.0,
    }


def test_save_recommendation_idempotent(basic, plan):
    conn = basic["conn"]
    n1 = dec.save_recommendation(conn, plan)
    n2 = dec.save_recommendation(conn, plan)          # same date -> update
    assert n1 == n2 == 2
    rows = dec.list_recommendations(conn, "2026-09-04")
    assert len(rows) == 2
    assert rows[0]["symbol"] == "600519.SH"           # ordered by rank


def test_decision_validation(basic, plan):
    conn = basic["conn"]
    dec.save_recommendation(conn, plan)
    rid = dec.list_recommendations(conn, "2026-09-04")[0]["recommendation_id"]
    with pytest.raises(ValueError):
        dec.record_decision(conn, rid, "maybe")
    with pytest.raises(ValueError):
        dec.record_decision(conn, rid, "modify")      # no change specified
    dec.record_decision(conn, rid, "accept")
    dec.record_decision(conn, rid, "modify", modified_price=1690.0,
                        modified_shares=100, note="partial fill planned")
    dec.record_decision(conn, rid, "reject", note="too expensive for me")
    s = dec.decision_summary(conn, "2026-09-04")
    assert s == {"accept": 1, "modify": 1, "reject": 1}


def test_decisions_are_audited(basic, plan):
    conn = basic["conn"]
    dec.save_recommendation(conn, plan)
    rid = dec.list_recommendations(conn, "2026-09-04")[0]["recommendation_id"]
    dec.record_decision(conn, rid, "reject", note="cash needed elsewhere")
    audits = repo.list_audit(conn, object_type="recommendations")
    assert any(a["action"] == "decision" for a in audits)
    assert any("cash needed" in (a["reason"] or "") for a in audits)


def test_execution_slippage(basic, plan):
    conn = basic["conn"]
    dec.save_recommendation(conn, plan)
    rid = dec.list_recommendations(conn, "2026-09-04")[0]["recommendation_id"]
    dec.record_execution(conn, "2026-09-05", price=1707.0, shares=200,
                         fees=43.0, recommendation_id=rid,
                         note="filled at open")
    slip = dec.execution_slippage(conn, "2026-09-04")
    assert len(slip) == 1
    s = slip[0]
    assert s["slippage"] == pytest.approx(7.0)
    assert s["slippage_pct"] == pytest.approx(7.0 / 1700.0)
    assert s["inside_band"] is True               # 1707 within 1666-1725


def test_execution_outside_band_is_flagged(basic, plan):
    conn = basic["conn"]
    dec.save_recommendation(conn, plan)
    rid = dec.list_recommendations(conn, "2026-09-04")[0]["recommendation_id"]
    dec.record_execution(conn, "2026-09-05", price=1780.0, shares=200,
                         recommendation_id=rid)
    assert dec.execution_slippage(conn)[0]["inside_band"] is False


def test_portfolio_gap_reports_underweight(basic, plan):
    """Model wants 9.5% in 600519.SH; the real account holds none."""
    conn = basic["conn"]
    repo.upsert_snapshot(conn, "2026-09-04", basic["fund"],
                         market_value=100000.0)
    gaps = dec.portfolio_gap(conn, plan)
    by_sym = {g["symbol"]: g for g in gaps}
    assert by_sym["600519.SH"]["model_weight"] == pytest.approx(0.095)
    assert by_sym["600519.SH"]["actual_weight"] == pytest.approx(0.0)
    assert by_sym["600519.SH"]["status"] == "Underweight"


def test_portfolio_gap_on_target(basic, plan):
    conn = basic["conn"]
    # a stock product with a matching ticker, valued to the model weight
    pid = repo.create_product(conn, basic["stock_acct"], "贵州茅台 持仓",
                              "stock", ticker="600519.SH", market="SH")
    repo.upsert_snapshot(conn, "2026-09-04", pid, units=200, nav=1750.0,
                         market_value=350000.0)
    repo.upsert_snapshot(conn, "2026-09-04", basic["fund"],
                         market_value=100000.0)
    plan = {"as_of": "2026-09-04", "capital": 1.0,
            "rows": [{"symbol": "600519.SH", "target_weight": 350000 / 450000}]}
    gaps = dec.portfolio_gap(conn, plan)
    row = [g for g in gaps if g["symbol"] == "600519.SH"][0]
    assert abs(row["gap"]) < 0.005
    assert row["status"] == "On target"


def test_gap_without_plan_lists_actual_only(basic):
    conn = basic["conn"]
    pid = repo.create_product(conn, basic["stock_acct"], "某 ETF", "etf",
                              ticker="510300.SH", market="SH")
    repo.upsert_snapshot(conn, "2026-09-04", pid, market_value=1000.0)
    gaps = dec.portfolio_gap(conn, None)
    assert gaps and all(g["model_weight"] is None for g in gaps)
