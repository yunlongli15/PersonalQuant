# -*- coding: utf-8 -*-
"""News factors must not change when FUTURE events are added/removed
(PIT invariance): corrupting events after date t leaves factor(t)
untouched."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from factors.base import FactorData
from factors.registry import FACTORS
from factors import news_factors  # noqa: F401


def make_data():
    # start in 2019-10: rolling windows (20/60/120d) need warm-up rows
    cal = pd.date_range("2019-10-01", periods=120, freq="B")
    syms = ["AAA.SH", "BBB.SZ"]
    close = pd.DataFrame(10.0, index=cal, columns=syms)
    vol = pd.DataFrame(1e6, index=cal, columns=syms)
    events = pd.DataFrame([
        {"symbol": "AAA.SH", "event_type": "share_buyback",
         "availability_time": "2020-01-10 10:00", "direction": "positive",
         "importance": 0.5, "sentiment": None, "novelty": 0.9,
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


def future_events():
    return pd.DataFrame([
        {"symbol": "AAA.SH", "event_type": "penalty",
         "availability_time": "2020-03-10 10:00", "direction": "negative",
         "importance": 0.9, "sentiment": None, "novelty": 0.1,
         "confidence": None, "risk": None, "extraction_method": "rule"},
        {"symbol": "BBB.SZ", "event_type": "earnings_forecast",
         "availability_time": "2020-03-11 10:00", "direction": "neutral",
         "importance": 0.6, "sentiment": None, "novelty": 0.2,
         "confidence": None, "risk": None, "extraction_method": "rule"},
    ])


@pytest.mark.parametrize("name", [
    "news_count_1d", "news_count_5d", "news_count_20d",
    "negative_news_count_5d", "positive_news_count_5d",
    "major_event_count_20d", "news_attention_5d", "news_sentiment_5d",
    "news_sentiment_20d", "news_positive_negative_ratio",
    "event_sentiment_shock", "news_risk_20d", "news_importance_5d",
    "event_shock",
])
def test_factor_invariant_to_future_events(name):
    d = pd.Timestamp("2020-01-20")
    base = make_data()
    before = FACTORS[name](base, dates=[d])
    extended = make_data()
    extended.news = pd.concat([extended.news, future_events()],
                              ignore_index=True)
    after = FACTORS[name](extended, dates=[d])
    for sym in ["AAA.SH", "BBB.SZ"]:
        a, b = before.loc[d, sym], after.loc[d, sym]
        if np.isnan(a) and np.isnan(b):
            continue
        assert a == pytest.approx(b, rel=1e-9), \
            f"{name} changed at {d.date()} for {sym} after future events"


def test_future_event_cannot_affect_counts():
    d = pd.Timestamp("2020-01-20")
    base = make_data()
    before = FACTORS["news_count_5d"](base, dates=[d])
    # an event published the evening OF d is PIT-available only the next
    # trading day (news.pit), so it cannot count for d itself
    ev = pd.DataFrame([
        {"symbol": "AAA.SH", "event_type": "dividend",
         "availability_time": "2020-01-21 09:30", "direction": "positive",
         "importance": 0.4, "sentiment": None, "novelty": 0.5,
         "confidence": None, "risk": None, "extraction_method": "rule"}])
    base.news = pd.concat([base.news, ev], ignore_index=True)
    after = FACTORS["news_count_5d"](base, dates=[d])
    assert after.loc[d, "AAA.SH"] == before.loc[d, "AAA.SH"]
