# -*- coding: utf-8 -*-
"""Rebalance calendar for portfolio research (DB-free).

Uses the DERIVED calendar cache (factors.base.load_calendar) so portfolio
research can run while another process holds the DuckDB lock. Frequencies:
monthly (same semantics as strategy.rebalance.rebalance_dates) and
quarterly (STEP 6 spec §50: monthly vs quarterly ONLY — the quarter-end
rebalance is the last trading day of Mar/Jun/Sep/Dec, i.e. the monthly
date whose month is in {3, 6, 9, 12}; no other frequencies are searched).
"""

from __future__ import annotations

from typing import List

import pandas as pd

from factors.base import cached_rebalance_dates as _monthly_dates

FREQUENCIES = ("monthly", "quarterly")


def rebalance_dates(start, end, frequency: str = "monthly",
                    rule: str = "last_trading_day") -> List[pd.Timestamp]:
    """Signal dates (T) in [start, end]; T 日收盘生成信号 → T+1 执行。"""
    if frequency not in FREQUENCIES:
        raise ValueError(f"unsupported frequency {frequency}")
    out = _monthly_dates(start, end, "monthly", rule)
    if frequency == "quarterly":
        out = [d for d in out if d.month in (3, 6, 9, 12)]
    return out
