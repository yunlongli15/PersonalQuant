# -*- coding: utf-8 -*-
"""Weekend PIT handling: publications on non-trading days are available
at the next trading day 09:30."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

from news.pit import availability_time


def ts(s):
    return pd.Timestamp(s).tz_localize("Asia/Shanghai")


def test_saturday_publication_available_monday():
    # 2025-06-07 is a Saturday; next trading day is 2025-06-09
    avail = availability_time(ts("2025-06-07 10:00"), time_known=True)
    assert avail == ts("2025-06-09 09:30")


def test_sunday_publication_available_monday():
    avail = availability_time(ts("2025-06-08 23:00"), time_known=True)
    assert avail == ts("2025-06-09 09:30")


def test_friday_after_close_skips_weekend():
    avail = availability_time(ts("2025-06-06 19:00"), time_known=True)
    assert avail == ts("2025-06-09 09:30")


def test_weekend_date_only():
    avail = availability_time(ts("2025-06-07"), time_known=False)
    assert avail == ts("2025-06-09 09:30")


def test_friday_intraday_stays_friday():
    avail = availability_time(ts("2025-06-06 10:00"), time_known=True)
    assert avail == ts("2025-06-06 10:00")
    assert avail.dayofweek == 4
