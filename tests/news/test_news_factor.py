# -*- coding: utf-8 -*-
"""News factor computation: counts/attention/sentiment + coverage
semantics (uncovered cells NaN, covered zero-event cells 0)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from factors.base import FactorData
from factors.registry import FACTORS
from factors import news_factors  # noqa: F401  (registration)


def make_data():
    # start in 2019-10: rolling windows (20/60d) need warm-up rows
    cal = pd.date_range("2019-10-01", periods=110, freq="B")
    syms = ["AAA.SH", "BBB.SZ", "CCC.SH"]
    close = pd.DataFrame(10.0, index=cal, columns=syms)
    vol = pd.DataFrame(1e6, index=cal, columns=syms)
    events = pd.DataFrame([
        # AAA: 2 positive events available 01-03 (within 5d of 01-06)
        {"symbol": "AAA.SH", "event_type": "share_buyback",
         "availability_time": "2020-01-03 10:00", "direction": "positive",
         "importance": 0.5, "sentiment": None, "novelty": 0.9,
         "confidence": None, "risk": None, "extraction_method": "rule"},
        {"symbol": "AAA.SH", "event_type": "dividend",
         "availability_time": "2020-01-03 15:30", "direction": "positive",
         "importance": 0.4, "sentiment": None, "novelty": 0.3,
         "confidence": None, "risk": None, "extraction_method": "rule"},
        # BBB: 1 negative event published 01-06 evening -> PIT availability
        # is the next trading day 09:30 (computed by build_events)
        {"symbol": "BBB.SZ", "event_type": "penalty",
         "availability_time": "2020-01-07 09:30", "direction": "negative",
         "importance": 0.8, "sentiment": None, "novelty": 0.5,
         "confidence": None, "risk": None, "extraction_method": "rule"},
    ])
    cov = pd.DataFrame({"symbol": ["AAA.SH", "BBB.SZ"],
                        "start_date": [pd.Timestamp("2019-01-01")] * 2})
    return FactorData(calendar=cal, bars=pd.DataFrame(), adj_close=close,
                      close_raw=close, volume_raw=vol, volume_shares=vol,
                      amount_cny=vol * close, scale=pd.DataFrame(),
                      financial=pd.DataFrame(),
                      industries=pd.Series(dtype=object),
                      news=events, news_cov=cov, scale_available=False)


@pytest.fixture
def data():
    return make_data()


def test_count_factor_values(data):
    d = pd.Timestamp("2020-01-06")
    p = FACTORS["news_count_5d"](data, dates=[d])
    assert p.loc[d, "AAA.SH"] == 2          # both events within 5d
    assert p.loc[d, "BBB.SZ"] == 0          # published 19:00 -> not usable
    # never fetched -> absent from the panel entirely (NaN when joined to
    # the universe by the evaluator)
    assert "CCC.SH" not in p.columns


def test_negative_count_respects_availability(data):
    d = pd.Timestamp("2020-01-07")
    p = FACTORS["negative_news_count_5d"](data, dates=[d])
    assert p.loc[d, "BBB.SZ"] == 1          # available on 01-07
    assert p.loc[d, "AAA.SH"] == 0


def test_positive_count(data):
    d = pd.Timestamp("2020-01-06")
    p = FACTORS["positive_news_count_5d"](data, dates=[d])
    assert p.loc[d, "AAA.SH"] == 2


def test_sentiment_factor_rule_mapping(data):
    d = pd.Timestamp("2020-01-06")
    p = FACTORS["news_sentiment_5d"](data, dates=[d])
    # AAA: two positive events -> +0.5 mean
    assert p.loc[d, "AAA.SH"] == pytest.approx(0.5)


def test_attention_uses_baseline(data):
    d = pd.Timestamp("2020-01-06")
    p = FACTORS["news_attention_5d"](data, dates=[d])
    # count(5d)=2, mean_count(60d)=2/60 -> attention = 2/(2/60) = 60
    assert p.loc[d, "AAA.SH"] == pytest.approx(60.0)
    # BBB: zero events in both windows -> 0/0 -> NaN (undefined attention)
    assert np.isnan(p.loc[d, "BBB.SZ"])


def test_buyback_count(data):
    d = pd.Timestamp("2020-01-06")
    p = FACTORS["buyback_event_count_20d"](data, dates=[d])
    assert p.loc[d, "AAA.SH"] == 1


def test_llm_confidence_empty_without_llm(data):
    d = pd.Timestamp("2020-01-06")
    p = FACTORS["llm_confidence_20d"](data, dates=[d])
    assert np.isnan(p.loc[d, "AAA.SH"])
