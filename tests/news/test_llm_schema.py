# -*- coding: utf-8 -*-
"""LLM structured-output parsing: strict JSON, bounded fields, no guess."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from news.llm.analyzer import _parse_json
from news.llm.prompts import PROMPT_VERSION, SYSTEM_PROMPT, USER_TEMPLATE


GOOD = ('{"event_type": "share_buyback", "sentiment": 0.8, '
        '"importance": 0.7, "novelty": 0.5, "financial_impact": 0.6, '
        '"risk": 0.1, "confidence": 0.9}')


def test_valid_json_parsed():
    out = _parse_json(GOOD)
    assert out["event_type"] == "share_buyback"
    assert out["sentiment"] == pytest.approx(0.8)
    assert out["financial_impact"] == pytest.approx(0.6)


def test_json_embedded_in_chatter_extracted():
    out = _parse_json(f"分析结果如下：{GOOD}")
    assert out is not None and out["importance"] == pytest.approx(0.7)


def test_out_of_bounds_rejected():
    bad = GOOD.replace('"sentiment": 0.8', '"sentiment": 1.7')
    assert _parse_json(bad) is None


def test_bad_event_type_rejected():
    bad = GOOD.replace("share_buyback", "moon_landing")
    assert _parse_json(bad) is None


def test_unparseable_returns_none():
    for text in ("", "这是一段自由文本，没有任何 JSON。", "{not json",
                 '{"event_type": "earnings"}'):
        assert _parse_json(text) is None


def test_missing_required_fields_rejected():
    assert _parse_json('{"sentiment": 0.5}') is None


def test_prompt_versioned_and_secret_free():
    assert PROMPT_VERSION
    assert "api" not in SYSTEM_PROMPT.lower()
    assert "{title}" in USER_TEMPLATE and "{symbol}" in USER_TEMPLATE
