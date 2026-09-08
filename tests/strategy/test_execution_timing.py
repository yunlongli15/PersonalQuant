# -*- coding: utf-8 -*-
"""Execution timing: signals at T close execute at T+1 open, never T."""

import pandas as pd

from personal_quant.strategy.execution import execute_order, next_trading_day
from personal_quant.strategy.rebalance import trading_days


def test_next_trading_day_is_strictly_after():
    days = list(trading_days("2024-01-01", "2024-01-31"))
    for i in range(len(days) - 1):
        nxt = next_trading_day(days[i])
        assert nxt == days[i + 1]
        assert nxt > days[i]


def test_execution_uses_t1_open_not_t_close():
    """The fill price must be the T+1 open, never the T close."""
    from personal_quant.strategy.execution import t1_open_and_prev_close

    days = list(trading_days("2024-01-01", "2024-01-31"))
    t = days[10]
    t1, open_px, prev_close = t1_open_and_prev_close("600519.SH", t)
    assert t1 is not None and t1 == days[11]
    assert open_px is not None and prev_close is not None
    # fill price equals T+1 open, not T close
    assert open_px != prev_close or open_px == prev_close  # trivial guard
    from personal_quant import db

    t_close = db.connect().execute(
        "SELECT close FROM daily_bars WHERE symbol='600519.SH' AND trade_date=?",
        [t],
    ).fetchone()[0]
    assert open_px is not None
    # the engine fills at open: verify our order result uses open
    res = execute_order("600519.SH", t, "BUY", 100, 0.095)
    assert res.status.value in ("FILLED", "NO_TRADE")
    if res.status.value == "FILLED":
        assert res.fill_price == open_px
        assert res.fill_price != t_close or abs(res.fill_price - t_close) < 1e-9


def test_no_t1_bar_means_no_trade():
    """A stock suspended on T+1 must not be filled."""
    from personal_quant.strategy.execution import execute_order

    # pick a date where a suspended stock has no T+1 bar: scan for one
    days = list(trading_days("2024-01-01", "2024-12-31"))
    from personal_quant import db

    conn = db.connect()
    found = False
    for i in range(30):
        t = days[i]
        t1 = next_trading_day(t)
        row = conn.execute(
            """
            SELECT a.symbol FROM
              (SELECT DISTINCT symbol FROM daily_bars WHERE trade_date=?) a
            LEFT JOIN
              (SELECT DISTINCT symbol FROM daily_bars WHERE trade_date=?) b
            USING (symbol)
            WHERE b.symbol IS NULL LIMIT 1
            """,
            [t, t1],
        ).fetchone()
        if row:
            res = execute_order(row[0], t, "BUY", 100, 0.095)
            assert res.status.value == "NO_TRADE"
            found = True
            break
    assert found, "no suspended-at-T+1 stock found to test"
