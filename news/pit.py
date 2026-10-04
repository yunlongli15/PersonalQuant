# -*- coding: utf-8 -*-
"""News PIT availability rules (docs/步骤5-新闻时点规则.md).

All times Asia/Shanghai (timezone-aware; naive datetimes are rejected
upstream by the schema). Rules for a publication time p:

- p on a trading day with time <= 15:00  -> available AT p (usable for the
  same day's 15:00 close signal; the market genuinely had it intraday)
- p on a trading day after 15:00, or on a non-trading day (weekend /
  holiday) -> available at the NEXT trading day 09:30
- date-only publications (time unknown) -> available the NEXT trading day
  09:30 (never assume intraday knowledge)
- publication date unknown -> availability_unknown, excluded in strict mode

A signal at date T (15:00 close) may use a news item iff
availability_at <= T 15:00.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from personal_quant import PROJECT_ROOT

from .schema import CLOSE_TIME, MARKET_TZ, NewsDocument

CALENDAR_CACHE = PROJECT_ROOT / "data" / "derived" / "factors" / "calendar.parquet"

_calendar: Optional[pd.DatetimeIndex] = None


def trading_calendar() -> pd.DatetimeIndex:
    global _calendar
    if _calendar is not None:
        return _calendar
    if CALENDAR_CACHE.exists():
        days = pd.read_parquet(CALENDAR_CACHE)["trade_date"]
        _calendar = pd.DatetimeIndex(pd.to_datetime(days))
        return _calendar
    from personal_quant import db

    days = db.connect().execute(
        "SELECT trade_date FROM trading_calendar WHERE is_open "
        "ORDER BY trade_date"
    ).fetch_df()
    _calendar = pd.DatetimeIndex(days["trade_date"])
    return _calendar


def _is_trading_day(d) -> bool:
    # the trading calendar is tz-naive (plain dates); compare naive
    return pd.Timestamp(d).tz_localize(None).normalize() in trading_calendar()


def next_trading_day(d) -> Optional[pd.Timestamp]:
    cal = trading_calendar()
    nxt = cal[cal > pd.Timestamp(d).tz_localize(None).normalize()]
    if len(nxt) == 0:
        # beyond the calendar end (e.g. very recent publications): the
        # availability is treated as unknown, never fabricated
        return None
    return pd.Timestamp(nxt[0])


def availability_time(published_at, time_known: bool = True
                      ) -> Optional[pd.Timestamp]:
    """First usable timestamp for a publication (see module docstring)."""
    if published_at is None or pd.isna(published_at):
        return None
    ts = pd.Timestamp(published_at)
    if ts.tzinfo is None:
        ts = ts.tz_localize(MARKET_TZ)
    day = ts.normalize()
    if time_known and _is_trading_day(day) and ts.time() <= CLOSE_TIME:
        return ts
    nxt = next_trading_day(day)
    if nxt is None:
        return None
    return pd.Timestamp(f"{nxt.date()} 09:30").tz_localize(MARKET_TZ)


def document_availability(doc: NewsDocument) -> tuple:
    """(availability_at, availability_unknown) for a document."""
    if doc.published_at is None or pd.isna(doc.published_at):
        return None, True
    avail = availability_time(doc.published_at, doc.time_known)
    return avail, avail is None


def usable_at_signal(doc: NewsDocument, signal_date) -> bool:
    """True when the document is usable for a signal at `signal_date`
    (T close). Strict: unknown availability -> False."""
    avail, unknown = document_availability(doc)
    if unknown or avail is None:
        return False
    t_close = pd.Timestamp(signal_date).normalize() + pd.Timedelta(hours=15)
    if t_close.tzinfo is None:
        t_close = t_close.tz_localize(MARKET_TZ)
    return avail <= t_close
