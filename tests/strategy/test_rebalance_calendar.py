# -*- coding: utf-8 -*-
"""Rebalance calendar tests."""

import pandas as pd

from personal_quant.strategy.rebalance import rebalance_dates, trading_days


def test_monthly_last_trading_day():
    dates = rebalance_dates("2024-01-01", "2024-12-31", "monthly", "last_trading_day")
    assert len(dates) == 12
    expected = [
        "2024-01-31", "2024-02-29", "2024-03-29", "2024-04-30",
        "2024-05-31", "2024-06-28", "2024-07-31", "2024-08-30",
        "2024-09-30", "2024-10-31", "2024-11-29", "2024-12-31",
    ]
    assert [str(d.date()) for d in dates] == expected


def test_rebalance_dates_are_trading_days():
    days = set(trading_days("2024-01-01", "2024-12-31"))
    for d in rebalance_dates("2024-01-01", "2024-12-31"):
        assert d in days, f"{d} is not a trading day"


def test_frequency_parameterized():
    monthly = rebalance_dates("2024-01-01", "2024-03-31", "monthly")
    weekly = rebalance_dates("2024-01-01", "2024-03-31", "weekly")
    assert len(monthly) == 3
    assert len(weekly) > 8  # ~13 weeks


def test_order_preserved():
    dates = rebalance_dates("2020-01-01", "2024-12-31")
    assert dates == sorted(dates)
