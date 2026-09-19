# -*- coding: utf-8 -*-
"""§6 / §36：PIT 审计。审计的是**消费了什么**，不是"库里有什么"。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

from paper_live import audit as A


class Provider:
    def __init__(self, bar_consumed, db_bar=None):
        self._bar = bar_consumed
        self._db = db_bar or bar_consumed

    def latest_bar_date(self, symbols=None, on_or_before=None):
        return self._bar if on_or_before is not None else self._db

    def financial_availability(self, symbols):
        return pd.DataFrame(columns=["symbol", "availability_date"])

    def news_availability(self, symbols, on_or_before=None):
        return pd.DataFrame({"symbol": list(symbols),
                             "published_at": [on_or_before] * len(symbols)})


def _run(p, d, factors=None):
    return A.pit_audit(p, pd.Timestamp(d), ["A.SH"],
                       pd.DataFrame({"f": [1.0]}, index=["A.SH"]),
                       pd.DataFrame({"g": [1.0]}, index=["A.SH"]),
                       consumed_factors=factors or [])


def test_consuming_a_bar_after_the_signal_date_is_invalid():
    p = Provider(pd.Timestamp("2025-06-02"), pd.Timestamp("2026-09-17"))
    r = _run(p, "2025-06-01")
    assert r.status == A.INVALID
    assert any(c.name == "price_pit" and c.status == A.INVALID
               for c in r.checks)


def test_a_newer_bar_in_the_db_is_not_a_violation_when_not_consumed():
    """历史回放时库里当然有更新的数据——只要没被消费就不是违规。"""
    p = Provider(pd.Timestamp("2025-06-02"), pd.Timestamp("2026-09-17"))
    r = _run(p, "2025-06-02")
    check = [c for c in r.checks if c.name == "price_pit"][0]
    assert check.status == A.VALID
    assert "未消费" in check.detail
    assert r.metrics["db_latest_bar"] == "2026-09-17"


def test_empty_universe_is_invalid():
    p = Provider(pd.Timestamp("2025-06-02"))
    r = A.pit_audit(p, pd.Timestamp("2025-06-02"), [], None, None)
    assert r.status == A.INVALID


def test_empty_features_is_invalid():
    p = Provider(pd.Timestamp("2025-06-02"))
    r = A.pit_audit(p, pd.Timestamp("2025-06-02"), ["A.SH"],
                    pd.DataFrame(), pd.DataFrame())
    assert r.status == A.INVALID


def test_financial_check_is_skipped_when_no_financial_factor_consumed():
    p = Provider(pd.Timestamp("2025-06-02"))
    r = _run(p, "2025-06-02", factors=["momentum_60"])
    c = [c for c in r.checks if c.name == "financial_pit"][0]
    assert c.status == A.VALID and "未消费" in c.detail


def test_news_check_runs_when_a_news_factor_is_consumed():
    p = Provider(pd.Timestamp("2025-06-02"))
    r = _run(p, "2025-06-02", factors=["news_risk_20d"])
    names = [c.name for c in r.checks]
    assert "news_pit" in names
    assert r.metrics["news_covered_30d"] == 1


def test_stale_news_is_a_warning_not_invalid():
    class StaleProvider(Provider):
        def news_availability(self, symbols, on_or_before=None):
            return pd.DataFrame({"symbol": list(symbols),
                                 "published_at": [pd.Timestamp("2020-01-01")]})

    r = _run(StaleProvider(pd.Timestamp("2025-06-02")), "2025-06-02",
             factors=["news_risk_20d"])
    c = [c for c in r.checks if c.name == "news_pit"][0]
    assert c.status == A.WARNING


def test_replay_mode_downgrades_freshness_warnings_only():
    assert A.replay_mode(A.WARNING, "2025-06-02", "2026-09-18") == A.VALID
    assert A.replay_mode(A.INVALID, "2025-06-02", "2026-09-18") == A.INVALID
    # 真正的 forward 日不做降级
    assert A.replay_mode(A.WARNING, "2026-09-18", "2026-09-18") == A.WARNING


def test_label_never_enters_the_signal_path():
    p = Provider(pd.Timestamp("2025-06-02"))
    r = _run(p, "2025-06-02")
    c = [c for c in r.checks if c.name == "label_isolation"][0]
    assert c.status == A.VALID
