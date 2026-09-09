# -*- coding: utf-8 -*-
"""Event-level aggregation (spec 37/38).

Multiple events for one symbol in a window are aggregated into scores —
NEVER collapsed into "3 independent positive news":
  positive_event_score  sum of positive-direction importance (or sentiment
                        when the LLM tier is present)
  negative_event_score  sum of negative-direction importance
  major_event_score     sum of importance of major events
  risk_event_score      sum of risk (rule tier: negative-direction
                        importance; LLM tier: model risk)
  net_score             positive - negative
Conflicts (same-day good news + bad news) keep BOTH sides — the model
learns the mix; nothing is zeroed out.
"""

from __future__ import annotations

import pandas as pd

SENTIMENT_MAP = {"positive": 0.5, "negative": -0.5, "neutral": 0.0}
MAJOR = 0.6


def aggregate(events: pd.DataFrame) -> dict:
    """Aggregate one (filtered) event frame into the five scores.

    events: columns direction, importance, sentiment (optional), risk
    (optional). Returns a dict of floats.
    """
    if events is None or events.empty:
        return {"positive_event_score": 0.0, "negative_event_score": 0.0,
                "major_event_score": 0.0, "risk_event_score": 0.0,
                "net_score": 0.0}
    pos = events[events["direction"] == "positive"]
    neg = events[events["direction"] == "negative"]
    pos_score = float(pos["importance"].fillna(0.15).sum())
    neg_score = float(neg["importance"].fillna(0.15).sum())
    major_score = float(events[events["importance"] >= MAJOR]
                        ["importance"].sum())
    if "risk" in events.columns and events["risk"].notna().any():
        risk_score = float(events["risk"].fillna(0.0).sum())
    else:
        risk_score = neg_score
    return {"positive_event_score": pos_score,
            "negative_event_score": neg_score,
            "major_event_score": major_score,
            "risk_event_score": risk_score,
            "net_score": pos_score - neg_score}


def aggregate_panels(events: pd.DataFrame, dates) -> dict:
    """Per-(date, symbol) score panels from an events long frame.

    events: symbol, availability_time, direction, importance, risk.
    Returns {score_name: DataFrame(dates x symbols)}; cells for symbols
    without events in the window are 0.0 (the caller applies coverage).
    """
    ev = events.copy()
    ev["avail"] = pd.to_datetime(ev["availability_time"], errors="coerce")
    ev = ev.dropna(subset=["avail"])
    ev["d"] = ev["avail"].dt.tz_localize(None).dt.normalize()
    if ev.empty:
        return {k: pd.DataFrame(index=pd.DatetimeIndex(dates))
                for k in ("positive_event_score", "negative_event_score",
                          "major_event_score", "risk_event_score",
                          "net_score")}
    pos = ev[ev["direction"] == "positive"]
    neg = ev[ev["direction"] == "negative"]
    maj = ev[ev["importance"] >= MAJOR]
    risk_col = "risk" if ev["risk"].notna().any() else None
    out = {}
    for name, sub, col in (("positive_event_score", pos, "importance"),
                           ("negative_event_score", neg, "importance"),
                           ("major_event_score", maj, "importance")):
        wide = sub.groupby(["d", "symbol"])[col].sum().unstack(fill_value=0.0)
        out[name] = wide.reindex(pd.DatetimeIndex(dates)).fillna(0.0)
    if risk_col:
        wide = ev.groupby(["d", "symbol"])["risk"].sum() \
            .unstack(fill_value=0.0)
        out["risk_event_score"] = wide.reindex(
            pd.DatetimeIndex(dates)).fillna(0.0)
    else:
        out["risk_event_score"] = out["negative_event_score"].copy()
    out["net_score"] = (out["positive_event_score"]
                        - out["negative_event_score"])
    # align every panel to the union of symbols (zero-score cells exist)
    all_syms = sorted(ev["symbol"].unique())
    for name in out:
        out[name] = out[name].reindex(columns=all_syms).fillna(0.0)
    return out
