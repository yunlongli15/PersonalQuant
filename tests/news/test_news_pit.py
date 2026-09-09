# -*- coding: utf-8 -*-
"""News PIT rules: pre-close / post-close / date-only / weekends /
holidays / availability_unknown (docs/step5_news_pit.md)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

from news.pit import availability_time, document_availability, usable_at_signal
from news.schema import NewsDocument

TZ = "Asia/Shanghai"


def ts(s):
    return pd.Timestamp(s).tz_localize(TZ)


def test_post_close_published_next_trading_day():
    # 2025-04-01 is a Tuesday; 19:30 is after the 15:00 close
    avail = availability_time(ts("2025-04-01 19:30"), time_known=True)
    assert avail == ts("2025-04-02 09:30")


def test_intraday_published_available_same_day():
    avail = availability_time(ts("2025-04-01 10:00"), time_known=True)
    assert avail == ts("2025-04-01 10:00")


def test_at_close_boundary_available_same_day():
    avail = availability_time(ts("2025-04-01 15:00"), time_known=True)
    assert avail == ts("2025-04-01 15:00")


def test_after_close_boundary_next_day():
    avail = availability_time(ts("2025-04-01 15:01"), time_known=True)
    assert avail == ts("2025-04-02 09:30")


def test_date_only_conservative_next_day():
    avail = availability_time(ts("2025-04-01"), time_known=False)
    assert avail == ts("2025-04-02 09:30")


def test_friday_evening_available_monday():
    # 2025-06-06 is a Friday; next trading day is Monday 2025-06-09
    avail = availability_time(ts("2025-06-06 19:00"), time_known=True)
    assert avail == ts("2025-06-09 09:30")


def test_signal_usability():
    d = NewsDocument(document_id="x", source="sse", source_url="u",
                     title="t", published_at="2025-04-01 19:30")
    assert not usable_at_signal(d, pd.Timestamp("2025-04-01"))
    assert usable_at_signal(d, pd.Timestamp("2025-04-02"))
    d2 = NewsDocument(document_id="y", source="sse", source_url="u",
                      title="t", published_at="2025-04-01 10:00")
    assert usable_at_signal(d2, pd.Timestamp("2025-04-01"))


def test_unknown_publication_never_usable():
    d = NewsDocument(document_id="z", source="sse", source_url="u",
                     title="t", published_at=None)
    avail, unknown = document_availability(d)
    assert unknown and avail is None
    assert not usable_at_signal(d, pd.Timestamp("2025-04-02"))
