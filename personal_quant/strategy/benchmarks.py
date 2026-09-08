# -*- coding: utf-8 -*-
"""Strategy baselines: buy & hold indexes, momentum, equal-weight market."""

from __future__ import annotations

from typing import Dict, List

import pandas as pd

from .. import db
from .rebalance import trading_days


def index_nav(symbol: str, start: str, end: str, initial: float = 1.0) -> pd.Series:
    """Buy & hold NAV of an index (raw index level; dividends not reinvested)."""
    df = db.connect().execute(
        "SELECT trade_date, close FROM daily_bars WHERE symbol=? "
        "AND trade_date BETWEEN ? AND ? ORDER BY trade_date",
        [symbol, start, end],
    ).fetch_df()
    if df.empty:
        return pd.Series(dtype=float)
    s = df.set_index("trade_date")["close"]
    return s / s.iloc[0] * initial


def equal_weight_market_nav(start: str, end: str, exchanges=(("SH", "SZ")),
                            min_amount: float = 100_000) -> pd.Series:
    """Daily equal-weight return of the liquid universe (gross NAV).

    Rebalanced daily (standard EW index convention); serves as a broad-market
    comparison, not a tradable portfolio.
    """
    days = list(trading_days(start, end))
    conn = db.connect()
    rets = conn.execute(
        """
        WITH u AS (
            SELECT symbol FROM securities
            WHERE exchange IN (SELECT unnest(?::VARCHAR[]))
        ),
        px AS (
            SELECT b.symbol, b.trade_date, b.close,
                   LAG(b.close) OVER (PARTITION BY b.symbol ORDER BY b.trade_date) prev
            FROM daily_bars b JOIN u USING (symbol)
            WHERE b.trade_date BETWEEN ? AND ?
        ),
        liq AS (
            SELECT symbol, AVG(amount) amt FROM daily_bars
            WHERE trade_date BETWEEN ? AND ?
            GROUP BY symbol HAVING AVG(amount) >= ?
        )
        SELECT px.trade_date, AVG(px.close / NULLIF(px.prev, 0) - 1) ret
        FROM px JOIN liq USING (symbol)
        WHERE px.prev IS NOT NULL
        GROUP BY px.trade_date
        """,
        [list(exchanges), start, end, start, end, min_amount],
    ).fetch_df()
    if rets.empty:
        return pd.Series(dtype=float)
    s = rets.set_index("trade_date")["ret"]
    return (1.0 + s).cumprod()


def momentum_scores(
    date: pd.Timestamp, symbols: List[str], lookback_days: int = 60
) -> pd.Series:
    """Momentum baseline: adjusted return over the past `lookback_days`."""
    if not symbols:
        return pd.Series(dtype=float)
    df = db.connect().execute(
        """
        WITH px AS (
            SELECT symbol, trade_date, close * factor AS adj,
                   ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date DESC) rn
            FROM daily_bars
            WHERE symbol IN (SELECT unnest(?::VARCHAR[])) AND trade_date <= ?
        )
        SELECT symbol,
               MAX(CASE WHEN rn = 1 THEN adj END) last_adj,
               MAX(CASE WHEN rn = ? THEN adj END) prev_adj
        FROM px GROUP BY symbol
        """,
        [list(symbols), date, lookback_days + 1],
    ).fetch_df()
    if df.empty:
        return pd.Series(dtype=float)
    s = (df["last_adj"] / df["prev_adj"] - 1.0)
    s.index = df["symbol"]
    return s.dropna()
