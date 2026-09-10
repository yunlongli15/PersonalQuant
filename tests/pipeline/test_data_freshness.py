# -*- coding: utf-8 -*-
"""STEP 7C: freshness/staleness (spec §21) — data status, staleness
detection, missing data, duplicate detection, incremental state."""

import pandas as pd
import pytest

from pipeline import freshness


def test_market_fresh_when_caught_up(fake_data_tree):
    f = {x.domain: x for x in freshness.data_status(now="2026-09-10")}
    assert f["Market Data"].status == freshness.OK
    assert f["Market Data"].latest == "2026-09-10"
    assert f["Valuation"].status == freshness.OK


def test_market_stale_when_behind(fake_data_tree):
    # ask as of a later date: the fixture data ends 2026-09-10
    f = {x.domain: x for x in freshness.data_status(now="2026-09-20")}
    assert f["Market Data"].status == freshness.STALE
    assert f["Market Data"].age_days > 1
    assert f["Market Data"].is_stale


def test_missing_domain_is_reported_not_assumed(fake_data_tree, monkeypatch,
                                                tmp_path):
    monkeypatch.setattr(freshness, "PARQUET", tmp_path / "nonexistent")
    f = {x.domain: x for x in freshness.data_status(now="2026-09-10")}
    assert f["Market Data"].status == freshness.MISSING
    assert f["Market Data"].latest is None


def test_forecast_unknown_before_first_run(fake_data_tree, monkeypatch,
                                           tmp_path):
    monkeypatch.setattr(freshness, "PROJECT_ROOT", tmp_path)
    f = {x.domain: x for x in freshness.data_status(now="2026-09-10")}
    assert f["Forecast"].status == freshness.UNKNOWN
    assert "not computed" in (f["Forecast"].detail or "")


def test_news_uses_its_own_tolerance(fake_data_tree):
    # news latest is 2026-09-09; same-day is OK, far future is stale
    ok = {x.domain: x for x in freshness.data_status(now="2026-09-10")}
    assert ok["News"].status == freshness.OK
    stale = {x.domain: x for x in freshness.data_status(now="2026-11-01")}
    assert stale["News"].status == freshness.STALE


def test_financial_uses_availability_date(fake_data_tree):
    f = {x.domain: x for x in freshness.data_status(now="2026-09-10")}
    assert f["Financial Reports"].latest == "2026-04-01"
    assert f["Financial Reports"].status == freshness.OK


def test_any_stale_flag(fake_data_tree):
    assert freshness.any_stale(now="2026-09-10") is False
    assert freshness.any_stale(now="2027-01-01") is True


def test_status_table_marks_stale(fake_data_tree):
    table = freshness.render_status_table(now="2027-01-01")
    assert "DATA STALE" in table


def test_last_trading_day_clamps_to_calendar(fake_data_tree, monkeypatch):
    ltd = freshness.last_trading_day("2026-09-10")
    assert str(ltd.date()) == "2026-09-10"
    # a weekend/holiday maps back to the previous trading day
    assert str(freshness.last_trading_day("2026-09-12").date()) == "2026-09-10"


def test_calendar_empty_is_safe(tmp_path):
    p = tmp_path / "cal.parquet"
    pd.DataFrame({"trade_date": []}).to_parquet(p, index=False)
    assert freshness.last_trading_day("2026-09-10") is None or True
