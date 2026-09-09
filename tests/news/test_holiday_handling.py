# -*- coding: utf-8 -*-
"""Holiday PIT handling: spring festival week etc. Publications inside a
holiday span become available on the first trading day after the holiday."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

from news.pit import availability_time


def ts(s):
    return pd.Timestamp(s).tz_localize("Asia/Shanghai")


def test_spring_festival_publication_available_after_holiday():
    # 2025 春节休市：2025-01-28 .. 2025-02-04；首个交易日 2025-02-05
    avail = availability_time(ts("2025-01-29 10:00"), time_known=True)
    assert avail == ts("2025-02-05 09:30")


def test_day_before_holiday_after_close():
    # 2025-01-27 (last trading day before the holiday) evening
    avail = availability_time(ts("2025-01-27 19:00"), time_known=True)
    assert avail == ts("2025-02-05 09:30")


def test_national_day_holiday():
    # 2025 国庆：2025-10-01 .. 2025-10-08 休市，10-09 开市
    avail = availability_time(ts("2025-10-02 08:00"), time_known=True)
    assert avail == ts("2025-10-09 09:30")


def test_holiday_intraday_cannot_happen_on_closed_day():
    # a closed day is never a trading day: even 10:00 publications move to
    # the first open day
    avail = availability_time(ts("2025-10-01 10:00"), time_known=True)
    assert avail == ts("2025-10-09 09:30")
