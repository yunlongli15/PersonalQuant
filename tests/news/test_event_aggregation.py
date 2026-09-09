# -*- coding: utf-8 -*-
"""Event aggregation + conflict handling (spec 37/38)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

from news.aggregation import aggregate, aggregate_panels


def make_events():
    return pd.DataFrame([
        {"symbol": "A.SH", "availability_time": "2025-01-06 10:00",
         "direction": "positive", "importance": 0.5, "risk": 0.0},
        {"symbol": "A.SH", "availability_time": "2025-01-07 10:00",
         "direction": "negative", "importance": 0.8, "risk": 0.7},
        {"symbol": "A.SH", "availability_time": "2025-01-07 12:00",
         "direction": "positive", "importance": 0.7, "risk": 0.0},
        {"symbol": "B.SH", "availability_time": "2025-01-07 10:00",
         "direction": "negative", "importance": 0.3, "risk": 0.2},
    ])


def test_aggregate_basic_scores():
    out = aggregate(make_events())
    assert out["positive_event_score"] == pytest.approx(1.2)
    assert out["negative_event_score"] == pytest.approx(1.1)
    assert out["net_score"] == pytest.approx(0.1)
    assert out["major_event_score"] == pytest.approx(1.5)  # 0.8 + 0.7
    assert out["risk_event_score"] == pytest.approx(0.9)   # 0.7 + 0.2


def test_conflict_same_day_keeps_both_sides():
    # same-day good news + bad news: nothing is zeroed out
    same_day = make_events()[1:3]
    out = aggregate(same_day)
    assert out["positive_event_score"] == pytest.approx(0.7)
    assert out["negative_event_score"] == pytest.approx(0.8)
    assert out["net_score"] == pytest.approx(-0.1)


def test_empty_aggregation_is_zero():
    out = aggregate(pd.DataFrame())
    assert out["net_score"] == 0.0 and out["risk_event_score"] == 0.0


def test_aggregate_panels_shape_and_values():
    events = make_events()
    dates = pd.DatetimeIndex([pd.Timestamp("2025-01-07")])
    panels = aggregate_panels(events, dates)
    assert set(panels) == {"positive_event_score", "negative_event_score",
                           "major_event_score", "risk_event_score",
                           "net_score"}
    # daily granularity: the 01-07 row holds 01-07 events only (A.SH:
    # positive 0.7 + negative 0.8 on that day); the earlier 01-06 event
    # lives on the previous day's row
    p = panels["positive_event_score"]
    assert p.loc[dates[0], "A.SH"] == pytest.approx(0.7)
    assert p.loc[dates[0], "B.SH"] == pytest.approx(0.0)
    n = panels["negative_event_score"]
    assert n.loc[dates[0], "A.SH"] == pytest.approx(0.8)
    assert panels["net_score"].loc[dates[0], "A.SH"] == pytest.approx(-0.1)
