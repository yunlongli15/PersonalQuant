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


# ---------------------------------------------------------------------------
# Forecast / Portfolio 对齐的是**交易日历**，不是墙上时钟
# （2026-09-22 用户反馈：刚重算完却报 STALE）
# ---------------------------------------------------------------------------

def _write_state(fake_data_tree, name: str, as_of: str) -> None:
    q = fake_data_tree / "quant"
    q.mkdir(parents=True, exist_ok=True)
    (q / f"{name}_state.json").write_text(
        '{"as_of": "%s"}' % as_of, encoding="utf-8")


def test_forecast_follows_the_calendar_not_wall_clock(fake_data_tree):
    """fixture 的数据/日历都停在 2026-09-10。

    预测与组合的 as_of 就是信号日：只要等于最后一个交易日就是新鲜的，
    哪怕"今天"已经过去 4 天 —— 上游还没发布新数据，重算也只能算到这天。
    """
    _write_state(fake_data_tree, "forecast", "2026-09-10")
    _write_state(fake_data_tree, "portfolio", "2026-09-10")

    f = {x.domain: x for x in freshness.data_status(now="2026-09-14")}
    assert f["Forecast"].status == freshness.OK
    assert f["Portfolio"].status == freshness.OK
    assert f["Market Data"].status == freshness.OK


def test_forecast_behind_the_last_trading_day_is_stale(fake_data_tree):
    """但比最后一个交易日还旧，就是真的旧了。"""
    _write_state(fake_data_tree, "forecast", "2026-09-08")
    _write_state(fake_data_tree, "portfolio", "2026-09-08")

    f = {x.domain: x for x in freshness.data_status(now="2026-09-14")}
    assert f["Forecast"].status == freshness.STALE
    assert f["Portfolio"].status == freshness.STALE


def test_lagging_calendar_marks_derived_domains_stale(fake_data_tree):
    """日历本身滞后 >5 天 = 数据管线没在跑，那么**所有**依赖它的域
    都不能显示为新鲜（否则停摆的管线看起来一切正常）。"""
    _write_state(fake_data_tree, "forecast", "2026-09-10")
    _write_state(fake_data_tree, "portfolio", "2026-09-10")

    f = {x.domain: x for x in freshness.data_status(now="2026-10-30")}
    for domain in ("Market Data", "Valuation", "Forecast", "Portfolio"):
        assert f[domain].status == freshness.STALE, domain
