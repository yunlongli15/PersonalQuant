# -*- coding: utf-8 -*-
"""Timestamp normalization: everything Asia/Shanghai, tz-aware, no naive."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

from news.schema import MARKET_TZ, NewsDocument


def test_naive_datetime_localized():
    d = NewsDocument(document_id="x", source="sse", source_url="u",
                     title="t", published_at="2025-04-01 19:30")
    assert d.published_at.tzinfo is not None


def test_tz_aware_kept():
    ts = pd.Timestamp("2025-04-01 19:30", tz="Asia/Shanghai")
    d = NewsDocument(document_id="x", source="sse", source_url="u",
                     title="t", published_at=ts)
    assert str(d.published_at.tzinfo) == "Asia/Shanghai"


def test_fetched_at_defaults_to_now_shanghai():
    d = NewsDocument(document_id="x", source="sse", source_url="u",
                     title="t")
    assert d.fetched_at is not None and d.fetched_at.tzinfo is not None


def test_market_timezone_constant():
    assert MARKET_TZ == "Asia/Shanghai"


def test_updated_at_not_published_at():
    d = NewsDocument(document_id="x", source="sse", source_url="u",
                     title="t", published_at="2025-03-01 08:00",
                     updated_at="2025-03-03 08:00")
    # later update must never be mistaken for first publication
    assert d.published_at < d.updated_at
