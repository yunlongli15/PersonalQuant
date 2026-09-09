# -*- coding: utf-8 -*-
"""STEP 5 news/announcement factors (rule tier; LLM tier augments the
same events when enabled).

All factors are strict PIT: an event counts for signal date d only when
availability_time <= d 15:00 (see news/pit.py). Panels are computed by
daily aggregation + rolling windows over the trading calendar, then sliced
at the signal dates.

Coverage semantics: a (symbol, date) cell is covered when the symbol was
fetched (news_coverage) and date >= its dataset start. Covered cells with
zero events are 0 (real zero — the history was fetched); uncovered cells
are NaN (never silently zeroed). Sentiment in the rule tier comes from the
rule direction (positive +0.5 / negative -0.5 / neutral 0, documented);
the LLM tier replaces it with model sentiment where available.

Direction honesty: rule directions are candidates; empirical directions
are measured per factor by the evaluator on research dates only.
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd

from .base import FactorData
from .registry import register

SENTIMENT_MAP = {"positive": 0.5, "negative": -0.5, "neutral": 0.0}
MAJOR_THRESHOLD = 0.6
NOVEL_THRESHOLD = 0.8


def _events(data: FactorData) -> pd.DataFrame:
    ev = data.news
    if ev is None or ev.empty:
        return pd.DataFrame(columns=["symbol", "d", "event_type",
                                     "direction", "importance", "sentiment",
                                     "novelty", "confidence", "risk"])
    ev = ev.copy()
    ev["avail"] = pd.to_datetime(ev["availability_time"], errors="coerce")
    ev = ev.dropna(subset=["avail"])
    ev["d"] = ev["avail"].dt.tz_localize(None).dt.normalize()
    return ev


def _covered_columns(data: FactorData) -> Optional[list]:
    if data.news_cov is None or data.news_cov.empty:
        return None
    return list(data.news_cov["symbol"])


def _to_daily_calendar(wide: pd.DataFrame, data: FactorData) -> pd.DataFrame:
    """Reindex a trading-day panel onto the FULL daily calendar so that
    rolling(N) counts N CALENDAR days (factor windows are documented in
    calendar days; non-trading days have zero events)."""
    full = pd.date_range(data.calendar[0], data.calendar[-1], freq="D")
    return wide.reindex(full).fillna(0.0)


def _daily(data: FactorData, mask: Optional[pd.Series] = None,
           value: Optional[str] = None, agg: str = "count") -> pd.DataFrame:
    """Daily wide panel (calendar days x symbols) over the event subset.

    Columns cover ALL fetched symbols (covered symbols with zero events
    are real zeros); uncovered symbols are NaNed later by _slice_cov.
    """
    ev = _events(data)
    if mask is not None:
        ev = ev[mask]
    if ev.empty:
        wide = pd.DataFrame(index=data.calendar, dtype=float)
    elif value is None or agg == "count":
        g = ev.groupby(["d", "symbol"]).size()
        wide = g.unstack(fill_value=0)
    else:
        g = ev.groupby(["d", "symbol"])[value].agg(agg)
        wide = g.unstack(fill_value=0.0)
    wide = wide.reindex(pd.DatetimeIndex(data.calendar.tz_localize(None)))
    wide.index = data.calendar
    cols = _covered_columns(data)
    if cols:
        wide = wide.reindex(columns=cols)
    return _to_daily_calendar(wide.fillna(0.0), data)


def _slice_cov(panel: pd.DataFrame, data: FactorData, dates) -> pd.DataFrame:
    """Slice at signal dates and NaN out uncovered cells."""
    out = panel.reindex(pd.DatetimeIndex(dates))
    cov = data.news_cov
    if cov is None or cov.empty:
        return out
    cov = cov.set_index("symbol")["start_date"]
    for d in pd.DatetimeIndex(dates):
        ok = cov.index[cov <= d]
        cols = out.columns.intersection(ok)
        out.loc[d, out.columns.difference(cols)] = np.nan
    return out


def _out(panel, data, dates):
    return _slice_cov(panel, data, dates)


def _mask_typed(data, types):
    ev = _events(data)
    return ev["event_type"].isin(types)


def _mask_direction(data, direction):
    ev = _events(data)
    return ev["direction"] == direction


# --- counts -----------------------------------------------------------------

@register(dict(
    factor_name="news_count_1d", category="news",
    formula="count(events with availability in (d-1d, d])",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="neutral",
    description="announcement count, 1-day window",
    version="1.0", status="candidate",
))
def news_count_1d(data: FactorData, dates=None):
    return _out(_daily(data).rolling(1).sum(), data, dates)


@register(dict(
    factor_name="news_count_5d", category="news",
    formula="count(events with availability in (d-5d, d])",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="neutral",
    description="announcement count, 5-day window",
    version="1.0", status="candidate",
))
def news_count_5d(data: FactorData, dates=None):
    return _out(_daily(data).rolling(5).sum(), data, dates)


@register(dict(
    factor_name="news_count_20d", category="news",
    formula="count(events with availability in (d-20d, d])",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="neutral",
    description="announcement count, 20-day window",
    version="1.0", status="candidate",
))
def news_count_20d(data: FactorData, dates=None):
    return _out(_daily(data).rolling(20).sum(), data, dates)


@register(dict(
    factor_name="announcement_count_5d", category="news",
    formula="count(all announcements in 5d) — 与 news_count_5d 等价"
            "（v1 公告=全部文档；引入普通新闻后分开）",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="neutral",
    description="announcement count, 5-day window",
    version="1.0", status="candidate",
))
def announcement_count_5d(data: FactorData, dates=None):
    return _out(_daily(data).rolling(5).sum(), data, dates)


@register(dict(
    factor_name="announcement_count_20d", category="news",
    formula="count(all announcements in 20d)",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="neutral",
    description="announcement count, 20-day window",
    version="1.0", status="candidate",
))
def announcement_count_20d(data: FactorData, dates=None):
    return _out(_daily(data).rolling(20).sum(), data, dates)


@register(dict(
    factor_name="negative_news_count_5d", category="news",
    formula="count(rule-direction-negative events in 5d)",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="negative",
    description="negative announcement count (rule direction), 5d",
    version="1.0", status="candidate",
))
def negative_news_count_5d(data: FactorData, dates=None):
    return _out(_daily(data, _mask_direction(data, "negative")).rolling(5).sum(),
                data, dates)


@register(dict(
    factor_name="positive_news_count_5d", category="news",
    formula="count(rule-direction-positive events in 5d)",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="positive",
    description="positive announcement count (rule direction), 5d",
    version="1.0", status="candidate",
))
def positive_news_count_5d(data: FactorData, dates=None):
    return _out(_daily(data, _mask_direction(data, "positive")).rolling(5).sum(),
                data, dates)


@register(dict(
    factor_name="major_event_count_20d", category="news",
    formula="count(importance >= 0.6 events in 20d)",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="neutral",
    description="major event count, 20d",
    version="1.0", status="candidate",
))
def major_event_count_20d(data: FactorData, dates=None):
    ev = _events(data)
    m = ev["importance"] >= MAJOR_THRESHOLD
    return _out(_daily(data, m).rolling(20).sum(), data, dates)


@register(dict(
    factor_name="regulatory_event_count_20d", category="news",
    formula="count(regulatory/penalty/investigation events in 20d)",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="negative",
    description="regulatory-risk event count, 20d",
    version="1.0", status="candidate",
))
def regulatory_event_count_20d(data: FactorData, dates=None):
    return _out(_daily(data, _mask_typed(
        data, ("regulatory", "penalty", "investigation"))).rolling(20).sum(),
        data, dates)


@register(dict(
    factor_name="buyback_event_count_20d", category="news",
    formula="count(share_buyback events in 20d)",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="positive",
    description="buyback event count, 20d",
    version="1.0", status="candidate",
))
def buyback_event_count_20d(data: FactorData, dates=None):
    return _out(_daily(data, _mask_typed(data, ("share_buyback",)))
                .rolling(20).sum(), data, dates)


@register(dict(
    factor_name="shareholder_change_count_20d", category="news",
    formula="count(shareholder_change events in 20d)",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="neutral",
    description="shareholder-change event count, 20d",
    version="1.0", status="candidate",
))
def shareholder_change_count_20d(data: FactorData, dates=None):
    return _out(_daily(data, _mask_typed(data, ("shareholder_change",)))
                .rolling(20).sum(), data, dates)


@register(dict(
    factor_name="earnings_event_count_60d", category="news",
    formula="count(earnings/forecast/revision events in 60d)",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="neutral",
    description="earnings-related event count, 60d",
    version="1.0", status="candidate",
))
def earnings_event_count_60d(data: FactorData, dates=None):
    return _out(_daily(data, _mask_typed(
        data, ("earnings", "earnings_forecast",
               "earnings_revision"))).rolling(60).sum(), data, dates)


@register(dict(
    factor_name="novel_news_count_5d", category="news",
    formula="count(novelty >= 0.8 events in 5d)",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="neutral",
    description="novel announcement count, 5d",
    version="1.0", status="candidate",
))
def novel_news_count_5d(data: FactorData, dates=None):
    ev = _events(data)
    return _out(_daily(data, ev["novelty"] >= NOVEL_THRESHOLD).rolling(5).sum(),
                data, dates)


# --- attention / shock ------------------------------------------------------

def _attention(data, window, baseline=60):
    w = _daily(data).rolling(window).sum()
    b = _daily(data).rolling(baseline).mean()
    # attention with a zero baseline is UNDEFINED (ratio semantics) — NaN
    return w / b.replace(0, np.nan)


@register(dict(
    factor_name="news_attention_1d", category="news",
    formula="count(1d) / mean_count(60d)",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="neutral",
    description="1-day attention vs 60d baseline",
    version="1.0", status="candidate",
))
def news_attention_1d(data: FactorData, dates=None):
    return _out(_attention(data, 1), data, dates)


@register(dict(
    factor_name="news_attention_5d", category="news",
    formula="count(5d) / mean_count(60d)",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="neutral",
    description="5-day attention vs 60d baseline",
    version="1.0", status="candidate",
))
def news_attention_5d(data: FactorData, dates=None):
    return _out(_attention(data, 5), data, dates)


@register(dict(
    factor_name="news_attention_20d", category="news",
    formula="count(20d) / mean_count(60d)",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="neutral",
    description="20-day attention vs 60d baseline",
    version="1.0", status="candidate",
))
def news_attention_20d(data: FactorData, dates=None):
    return _out(_attention(data, 20), data, dates)


@register(dict(
    factor_name="announcement_attention_5d", category="news",
    formula="count(5d) / mean_count(60d) — 同 news_attention_5d"
            "（v1 公告=全部文档）",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="neutral",
    description="announcement attention, 5d vs 60d baseline",
    version="1.0", status="candidate",
))
def announcement_attention_5d(data: FactorData, dates=None):
    return _out(_attention(data, 5), data, dates)


@register(dict(
    factor_name="event_shock", category="news",
    formula="major_count(5d) / mean_major_count(120d)，极端值在归一化层处理",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="neutral",
    description="major-event shock vs 120d baseline",
    version="1.0", status="candidate",
))
def event_shock(data: FactorData, dates=None):
    ev = _events(data)
    m = ev["importance"] >= MAJOR_THRESHOLD
    w = _daily(data, m).rolling(5).sum()
    b = _daily(data, m).rolling(120).mean()
    raw = w / b.replace(0, np.nan)
    return _out(raw.clip(upper=10.0), data, dates)


# --- sentiment / importance / novelty / risk --------------------------------

def _window_mean(num: pd.DataFrame, den: pd.DataFrame, window: int,
                 empty: float = 0.0):
    """Event-weighted window mean: rolling sum(num)/rolling sum(den).

    empty: value when the window has no events — 0 (neutral) is the
    documented modeling choice for sentiment/importance/novelty/risk
    ("no events = neutral": the events dataset is complete for covered
    symbols, so zero events is real information, not missing data).
    Ratio factors (attention/shock) keep NaN semantics via empty=nan."""
    return (num.rolling(window).sum()
            / den.rolling(window).sum().replace(0, np.nan)).fillna(empty)


def _empty_panel(data):
    cols = _covered_columns(data) or []
    return pd.DataFrame(np.nan, index=data.calendar, columns=cols)


def _sentiment_daily(data):
    """Daily SUM of per-event sentiment (direction -> +0.5/-0.5/0, LLM
    overrides when present); windowed means divide by the event count."""
    ev = _events(data)
    if ev.empty:
        return _empty_panel(data)
    s = ev["sentiment"].where(ev["sentiment"].notna(),
                              ev["direction"].map(SENTIMENT_MAP))
    g = ev[["d", "symbol"]].assign(s=s).groupby(["d", "symbol"])["s"].sum()
    wide = g.unstack(fill_value=0.0).reindex(
        pd.DatetimeIndex(data.calendar.tz_localize(None)))
    wide.index = data.calendar
    cols = _covered_columns(data)
    if cols:
        wide = wide.reindex(columns=cols)
    return _to_daily_calendar(wide.fillna(0.0), data)


@register(dict(
    factor_name="news_sentiment_1d", category="news",
    formula="mean sentiment of events in 1d",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="positive",
    description="1-day mean event sentiment",
    version="1.0", status="candidate",
))
def news_sentiment_1d(data: FactorData, dates=None):
    return _out(_window_mean(_sentiment_daily(data), _daily(data), 1),
                data, dates)


@register(dict(
    factor_name="news_sentiment_5d", category="news",
    formula="mean sentiment of events in 5d",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="positive",
    description="5-day mean event sentiment",
    version="1.0", status="candidate",
))
def news_sentiment_5d(data: FactorData, dates=None):
    return _out(_window_mean(_sentiment_daily(data), _daily(data), 5),
                data, dates)


@register(dict(
    factor_name="news_sentiment_20d", category="news",
    formula="mean sentiment of events in 20d",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="positive",
    description="20-day mean event sentiment",
    version="1.0", status="candidate",
))
def news_sentiment_20d(data: FactorData, dates=None):
    return _out(_window_mean(_sentiment_daily(data), _daily(data), 20),
                data, dates)


@register(dict(
    factor_name="news_sentiment_weighted", category="news",
    formula="sum(sentiment*importance)/sum(importance) over 20d",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="positive",
    description="importance-weighted 20d sentiment",
    version="1.0", status="candidate",
))
def news_sentiment_weighted(data: FactorData, dates=None):
    ev = _events(data)
    if ev.empty:
        return _out(_empty_panel(data), data, dates)
    s = ev["sentiment"].where(ev["sentiment"].notna(),
                              ev["direction"].map(SENTIMENT_MAP))
    w = ev["importance"].fillna(0.15)
    g = ev[["d", "symbol"]].assign(sw=s * w, w=w).groupby(["d", "symbol"])
    sw = g["sw"].sum()
    wsum = g["w"].sum()
    wide_sw = sw.unstack(fill_value=0.0).reindex(
        pd.DatetimeIndex(data.calendar.tz_localize(None)))
    wide_w = wsum.unstack(fill_value=0.0).reindex(
        pd.DatetimeIndex(data.calendar.tz_localize(None)))
    wide_sw.index = data.calendar
    wide_w.index = data.calendar
    cols = _covered_columns(data)
    if cols:
        wide_sw = wide_sw.reindex(columns=cols)
        wide_w = wide_w.reindex(columns=cols)
    wide_sw = _to_daily_calendar(wide_sw.fillna(0.0), data)
    wide_w = _to_daily_calendar(wide_w.fillna(0.0), data)
    return _out(_window_mean(wide_sw, wide_w, 20), data, dates)


@register(dict(
    factor_name="news_importance_5d", category="news",
    formula="mean importance of events in 5d",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="neutral",
    description="5-day mean event importance",
    version="1.0", status="candidate",
))
def news_importance_5d(data: FactorData, dates=None):
    num = _daily(data, value="importance", agg="sum")
    return _out(_window_mean(num, _daily(data), 5), data, dates)


@register(dict(
    factor_name="news_novelty_5d", category="news",
    formula="mean novelty of events in 5d",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="neutral",
    description="5-day mean event novelty",
    version="1.0", status="candidate",
))
def news_novelty_5d(data: FactorData, dates=None):
    num = _daily(data, value="novelty", agg="sum")
    return _out(_window_mean(num, _daily(data), 5), data, dates)


@register(dict(
    factor_name="news_risk_20d", category="news",
    formula="mean risk of events in 20d (rule tier: risk = importance of "
            "negative-direction events)",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="negative",
    description="20-day mean event risk",
    version="1.0", status="candidate",
))
def news_risk_20d(data: FactorData, dates=None):
    ev = _events(data)
    risk = ev["risk"].where(ev["risk"].notna(),
                            ev["importance"].where(
                                ev["direction"] == "negative", 0.0))
    if ev.empty:
        return _out(pd.DataFrame(index=data.calendar, dtype=float),
                    data, dates)
    g = ev[["d", "symbol"]].assign(r=risk).groupby(["d", "symbol"])["r"].sum()
    wide = g.unstack(fill_value=0.0).reindex(
        pd.DatetimeIndex(data.calendar.tz_localize(None)))
    wide.index = data.calendar
    cols = _covered_columns(data)
    if cols:
        wide = wide.reindex(columns=cols)
    wide = _to_daily_calendar(wide.fillna(0.0), data)
    return _out(_window_mean(wide, _daily(data), 20), data, dates)


@register(dict(
    factor_name="news_positive_negative_ratio", category="news",
    formula="(1+pos_20d)/(1+neg_20d)",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="positive",
    description="positive/negative event ratio, 20d",
    version="1.0", status="candidate",
))
def news_positive_negative_ratio(data: FactorData, dates=None):
    pos = _daily(data, _mask_direction(data, "positive")).rolling(20).sum()
    neg = _daily(data, _mask_direction(data, "negative")).rolling(20).sum()
    return _out((1.0 + pos) / (1.0 + neg), data, dates)


@register(dict(
    factor_name="event_sentiment_shock", category="news",
    formula="sentiment_5d - sentiment_60d",
    source="news", required_fields=["news_events", "news_coverage"],
    pit=True, direction="positive",
    description="5d vs 60d sentiment deviation",
    version="1.0", status="candidate",
))
def event_sentiment_shock(data: FactorData, dates=None):
    s = _sentiment_daily(data)
    c = _daily(data)
    return _out(_window_mean(s, c, 5) - _window_mean(s, c, 60),
                data, dates)


@register(dict(
    factor_name="llm_confidence_20d", category="news",
    formula="mean LLM confidence of events in 20d (NaN when no LLM tier)",
    source="news_llm", required_fields=["news_events", "news_coverage"],
    pit=True, direction="neutral",
    description="20-day mean LLM confidence (LLM tier only)",
    version="1.0", status="candidate",
))
def llm_confidence_20d(data: FactorData, dates=None):
    ev = _events(data)
    llm = ev[ev["extraction_method"] == "llm"]
    if llm.empty:
        return _out(_empty_panel(data), data, dates)
    g = llm.groupby(["d", "symbol"])["confidence"].sum()
    wide = g.unstack(fill_value=0.0).reindex(
        pd.DatetimeIndex(data.calendar.tz_localize(None)))
    wide.index = data.calendar
    cnt = llm.groupby(["d", "symbol"]).size().unstack(fill_value=0).reindex(
        pd.DatetimeIndex(data.calendar.tz_localize(None)))
    cnt.index = data.calendar
    cols = _covered_columns(data)
    if cols:
        wide = wide.reindex(columns=cols)
        cnt = cnt.reindex(columns=cols)
    wide = _to_daily_calendar(wide.fillna(0.0), data)
    cnt = _to_daily_calendar(cnt.fillna(0.0), data)
    return _out(_window_mean(wide, cnt, 20), data, dates)
