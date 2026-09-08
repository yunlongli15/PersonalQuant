# -*- coding: utf-8 -*-
"""Rebalance calendar generation (configurable frequency)."""

from __future__ import annotations

from typing import List, Optional

import pandas as pd

from .. import db

FREQ_MAP = {
    "monthly": "ME",
    "weekly": "W-FRI",
}


def trading_days(start: Optional[str] = None, end: Optional[str] = None) -> pd.DatetimeIndex:
    sql = "SELECT trade_date FROM trading_calendar WHERE is_open"
    params = []
    if start:
        sql += " AND trade_date >= ?"
        params.append(start)
    if end:
        sql += " AND trade_date <= ?"
        params.append(end)
    sql += " ORDER BY trade_date"
    df = db.connect().execute(sql, params).fetch_df()
    return pd.DatetimeIndex(df["trade_date"])


def rebalance_dates(
    start: str,
    end: str,
    frequency: str = "monthly",
    rule: str = "last_trading_day",
) -> List[pd.Timestamp]:
    """Signal dates (T): the last trading day of each period in [start, end].

    T 日收盘生成信号 -> T+1 日执行（见 execution.py）。
    """
    if frequency not in FREQ_MAP:
        raise ValueError(f"unsupported frequency {frequency}")
    days = trading_days(start, end)
    if len(days) == 0:
        return []
    offset = pd.tseries.frequencies.to_offset(FREQ_MAP[frequency])
    groups = days.to_series().groupby(days.to_period(offset))
    if rule == "last_trading_day":
        out = [g.iloc[-1] for _, g in groups]
    elif rule == "first_trading_day":
        out = [g.iloc[0] for _, g in groups]
    else:
        raise ValueError(f"unsupported rule {rule}")
    return [pd.Timestamp(t) for t in out]
