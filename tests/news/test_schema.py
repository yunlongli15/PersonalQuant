# -*- coding: utf-8 -*-
"""NewsDocument / NewsEvent schema validation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

from news.schema import (EVENT_TYPES, NewsDocument, NewsEvent, hash_text)


def test_document_validation():
    d = NewsDocument(document_id="x", source="sse", source_url="u",
                     title="t", symbol="600519.SH",
                     published_at="2025-04-01 19:30")
    assert d.published_at.tzinfo is not None
    assert str(d.published_at.tzinfo) == "Asia/Shanghai"
    assert d.document_type == "announcement"


def test_document_rejects_bad_symbol():
    with pytest.raises(ValueError):
        NewsDocument(document_id="x", source="sse", source_url="u",
                     title="t", symbol="600519")


def test_document_rejects_bad_type():
    with pytest.raises(ValueError):
        NewsDocument(document_id="x", source="sse", source_url="u",
                     title="t", document_type="tweet")


def test_market_wide_document_has_no_symbol():
    d = NewsDocument(document_id="x", source="sse", source_url="u",
                     title="t", symbol=None)
    assert d.symbol is None


def test_event_validation_bounds():
    with pytest.raises(ValueError):
        NewsEvent(event_id="e", document_id="d", symbol=None,
                  event_type="earnings", sentiment=1.5)
    with pytest.raises(ValueError):
        NewsEvent(event_id="e", document_id="d", symbol=None,
                  event_type="earnings", risk=-0.1)
    with pytest.raises(ValueError):
        NewsEvent(event_id="e", document_id="d", symbol=None,
                  event_type="nonsense")


def test_event_direction_values():
    for d in ("positive", "negative", "neutral", None):
        NewsEvent(event_id="e", document_id="d", symbol=None,
                  event_type="earnings", direction=d)


def test_event_time_vs_publication_time_separate():
    e = NewsEvent(event_id="e", document_id="d", symbol=None,
                  event_type="earnings",
                  publication_time="2025-04-01 19:30",
                  event_time="2025-03-31 20:00")
    assert e.publication_time != e.event_time
    assert e.publication_time.tzinfo is not None


def test_hash_stable_and_normalizing():
    assert hash_text("回购", "600519.SH", "2025-01-01") == \
        hash_text(" 回购 ", "600519.SH", "2025-01-01")
    assert hash_text("a", "b") != hash_text("a", "c")


def test_event_types_complete():
    required = {"earnings", "earnings_forecast", "earnings_revision",
                "dividend", "share_buyback", "shareholder_change",
                "management_change", "major_contract", "m_and_a",
                "financing", "refinancing", "asset_sale", "asset_purchase",
                "lawsuit", "regulatory", "penalty", "investigation",
                "pledge", "unpledge", "bankruptcy", "production_change",
                "product_launch", "capacity_expansion", "guidance",
                "government_policy", "other"}
    assert required <= EVENT_TYPES
