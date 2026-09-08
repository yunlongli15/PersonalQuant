# -*- coding: utf-8 -*-
"""T+1 execution model.

Signal at close of T -> orders executed at open of T+1 (next trading day).
Execution rules (conservative; never assume a fill):
  - no bar on T+1 (suspension)            -> NO_TRADE
  - buy  at open >= prev_close*(1+limit)  -> NO_TRADE (limit up)
  - sell at open <= prev_close*(1-limit)  -> NO_TRADE (limit down)
  - fills happen at T+1 open (raw price) with slippage applied by the cost
    model on traded value
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import pandas as pd

from .. import db


class TradeStatus(str, Enum):
    FILLED = "FILLED"
    NO_TRADE = "NO_TRADE"          # no bar / limit / insufficient data


@dataclass
class OrderResult:
    symbol: str
    status: TradeStatus
    shares: int = 0
    fill_price: Optional[float] = None
    reason: Optional[str] = None


def next_trading_day(date: pd.Timestamp) -> Optional[pd.Timestamp]:
    r = db.connect().execute(
        "SELECT MIN(trade_date) d FROM trading_calendar "
        "WHERE is_open AND trade_date > ?",
        [date],
    ).fetchone()
    return pd.Timestamp(r[0]) if r and r[0] is not None else None


def t1_open_and_prev_close(
    symbol: str, signal_date: pd.Timestamp
) -> tuple[Optional[pd.Timestamp], Optional[float], Optional[float]]:
    """Return (t1_date, t1_open_raw, prev_close_raw) or Nones if no bar."""
    df = db.connect().execute(
        "SELECT trade_date, open, close FROM daily_bars "
        "WHERE symbol=? AND trade_date BETWEEN ? AND ? ORDER BY trade_date "
        "LIMIT 2",
        [symbol, signal_date, signal_date + pd.Timedelta(days=10)],
    ).fetch_df()
    if df.empty:
        return None, None, None
    # first row is T (or the last bar <= T+1 window); we need T and T+1
    t1 = next_trading_day(signal_date)
    if t1 is None:
        return None, None, None
    row_t = df[df["trade_date"] == signal_date]
    row_t1 = df[df["trade_date"] == t1]
    if row_t1.empty:
        return t1, None, None
    prev_close = float(row_t["close"].iloc[0]) if not row_t.empty else None
    return t1, float(row_t1["open"].iloc[0]), prev_close


def execute_order(
    symbol: str,
    signal_date: pd.Timestamp,
    side: str,                  # "BUY" | "SELL"
    shares: int,
    limit_threshold: float,
) -> OrderResult:
    """Execute one order at T+1 open under the conservative rules.

    Returns an OrderResult; shares are integers (lots already applied by the
    caller for buys).
    """
    if shares <= 0:
        return OrderResult(symbol, TradeStatus.NO_TRADE, 0, None, "zero shares")
    t1, open_price, prev_close = t1_open_and_prev_close(symbol, signal_date)
    if t1 is None or open_price is None:
        return OrderResult(symbol, TradeStatus.NO_TRADE, 0, None,
                           "no T+1 bar (suspended/halted)")
    if prev_close is None:
        return OrderResult(symbol, TradeStatus.NO_TRADE, 0, None,
                           "no prev close")
    if side == "BUY" and open_price >= prev_close * (1 + limit_threshold):
        return OrderResult(symbol, TradeStatus.NO_TRADE, 0, None, "limit up")
    if side == "SELL" and open_price <= prev_close * (1 - limit_threshold):
        return OrderResult(symbol, TradeStatus.NO_TRADE, 0, None, "limit down")
    # signed shares: positive = buy, negative = sell
    signed = shares if side == "BUY" else -shares
    return OrderResult(symbol, TradeStatus.FILLED, signed, open_price)
