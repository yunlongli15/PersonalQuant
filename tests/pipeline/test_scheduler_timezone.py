# -*- coding: utf-8 -*-
"""调度器的时区语义（PHASE 7 §十七）。

**2026-10-06 事故**：作业记录的时间戳是 UTC（SQLite `datetime('now')`），
而 `is_due` 拿 `datetime.now()` 的**本地**日期去比。CST 00:00–08:00 之间
UTC 还停在前一天，"今天跑过没有"永远被判成没跑过 —— 夜间任务会重复执行。
只在深夜复现，白天怎么测都是绿的（这也正是它活到今天的原因）。

修法：**任务的"今天" = 市场时区（Asia/Shanghai）的今天**，写死，
不跟随机器时区。记录可能是带偏移的新格式，也可能是无标记的旧格式
（旧格式按 UTC 解释 —— SQLite 写的就是 UTC，这一点是确定的）。

覆盖：UTC / Asia/Shanghai / 午夜边界 / 日期切换 / 机器时区无关性。
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from pipeline import jobs, scheduler

CST = ZoneInfo("Asia/Shanghai")
UTC = timezone.utc


# ---------------------------------------------------------------------------
# 1. 时刻 -> 市场日历日
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("stored,expect", [
    # 无标记的旧格式（SQLite datetime('now')）按 UTC 解释
    ("2026-10-05 16:02:52", "2026-10-06"),      # 沪 00:02 -> 已是次日
    ("2026-10-05 15:59:59", "2026-10-05"),      # 沪 23:59 -> 仍是当日
    ("2026-10-05 00:00:00", "2026-10-05"),      # 沪 08:00 -> 同日
    ("2026-10-04 16:00:00", "2026-10-05"),      # 沪 00:00 整 -> 次日
    # 带偏移的新格式：按标记走，与书写方式无关
    ("2026-10-05T16:02:52+00:00", "2026-10-06"),
    ("2026-10-06T00:02:52+08:00", "2026-10-06"),
    ("2026-10-05T23:59:59+08:00", "2026-10-05"),
])
def test_utc_timestamp_maps_to_market_day(stored, expect):
    assert str(scheduler.utc_to_market_day(stored)) == expect


def test_missing_timestamp_has_no_day():
    assert scheduler.utc_to_market_day(None) is None
    assert scheduler.utc_to_market_day("") is None


# ---------------------------------------------------------------------------
# 2. 午夜边界：跨过 UTC 日界但没过市场日界
# ---------------------------------------------------------------------------

def test_midnight_window_is_the_same_market_day():
    """沪 00:00 ~ 08:00 之间，UTC 日期比市场日期**早一天**。

    这正是 bug 的发作窗口：如果比较时用了 UTC 日期，这段时间里
    "今天跑过的作业"会被看成"昨天跑的"。
    """
    days = set()
    for h in range(0, 8):
        utc_naive = datetime(2026, 10, 5, 16 + h if 16 + h < 24 else h,
                             30)
        # 直接构造：沪时间 = UTC + 8
        sh = datetime(2026, 10, 6, h, 30, tzinfo=CST)
        stored = sh.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")
        days.add(str(scheduler.utc_to_market_day(stored)))
    assert days == {"2026-10-06"}, f"午夜窗口内被算成了多个市场日：{days}"


def test_just_before_and_after_midnight_differ():
    before = "2026-10-05 15:59:00"      # 沪 23:59
    after = "2026-10-05 16:01:00"       # 沪 00:01（次日）
    assert scheduler.utc_to_market_day(before) != \
        scheduler.utc_to_market_day(after)


# ---------------------------------------------------------------------------
# 3. 回归：夜间跑过的日常任务不能又被判成"该跑"
# ---------------------------------------------------------------------------

def _record(jobstore, job_name: str, finished_utc: str):
    run = jobs.run_job(job_name, lambda: "ok", conn=jobstore)
    jobstore.execute("UPDATE jobs SET finished_at=? WHERE job_id=?",
                     (finished_utc, run.job_id))
    jobstore.commit()
    return run


def test_daily_task_not_due_right_after_midnight(jobstore):
    """**这就是那个 bug 的回归测试**：沪 00:02，作业是我 00:01 跑完的。

    修复前：作业记录 UTC 日期是 10-05，本地日期是 10-06 -> 不等 -> 判成 due。
    修复后：两者都归到市场日 10-06 -> 不 due。
    """
    daily = next(t for t in scheduler.SCHEDULE if t.cadence == "daily")
    _record(jobstore, daily.job, "2026-10-05 16:01:00")   # 沪 00:01
    now = datetime(2026, 10, 6, 0, 2, tzinfo=CST)          # 沪 00:02
    assert scheduler.is_due(daily, jobstore, now=now) is False


def test_daily_task_due_on_the_next_market_day(jobstore):
    daily = next(t for t in scheduler.SCHEDULE if t.cadence == "daily")
    _record(jobstore, daily.job, "2026-10-05 16:01:00")   # 沪 10-06 00:01
    now = datetime(2026, 10, 6, 9, 30, tzinfo=CST)         # 沪 10-06 白天
    assert scheduler.is_due(daily, jobstore, now=now) is False
    nxt = datetime(2026, 10, 7, 9, 30, tzinfo=CST)         # 沪 10-07
    assert scheduler.is_due(daily, jobstore, now=nxt) is True


def test_naive_now_is_read_as_market_time(jobstore):
    """朴素时间按市场时区解释 —— 不按机器时区。

    两个写法（带时区 / 不带时区）必须给出同一个答案；否则同一份代码
    在两台时区不同的机器上调度结果不同。
    """
    daily = next(t for t in scheduler.SCHEDULE if t.cadence == "daily")
    _record(jobstore, daily.job, "2026-10-05 16:01:00")
    aware = datetime(2026, 10, 6, 0, 2, tzinfo=CST)
    naive = aware.replace(tzinfo=None)
    assert scheduler.is_due(daily, jobstore, now=naive) == \
        scheduler.is_due(daily, jobstore, now=aware)


def test_utc_supplied_now_gives_the_same_answer(jobstore):
    """显式给 UTC 时刻，结论必须与给沪时刻一致。"""
    daily = next(t for t in scheduler.SCHEDULE if t.cadence == "daily")
    _record(jobstore, daily.job, "2026-10-05 16:01:00")
    cst = datetime(2026, 10, 6, 0, 2, tzinfo=CST)
    assert scheduler.is_due(daily, jobstore, now=cst) is False
    assert scheduler.is_due(daily, jobstore,
                            now=cst.astimezone(UTC)) is False


# ---------------------------------------------------------------------------
# 4. 周 / 月的日期切换
# ---------------------------------------------------------------------------

def test_weekly_rolls_over_at_market_monday(jobstore):
    weekly = next(t for t in scheduler.SCHEDULE if t.cadence == "weekly")
    # 2026-10-04 是周日：沪 10-04 23:00 = UTC 10-04 15:00
    _record(jobstore, weekly.job, "2026-10-04 15:00:00")
    sun = datetime(2026, 10, 4, 23, 0, tzinfo=CST)
    mon = datetime(2026, 10, 5, 9, 0, tzinfo=CST)
    assert scheduler.is_due(weekly, jobstore, now=sun) is False
    assert scheduler.is_due(weekly, jobstore, now=mon) is True


def test_monthly_rolls_over_across_year_boundary(jobstore):
    monthly = next(t for t in scheduler.SCHEDULE if t.cadence == "monthly")
    # 沪 2026-12-31 23:30 = UTC 12-31 15:30
    _record(jobstore, monthly.job, "2026-12-31 15:30:00")
    assert scheduler.is_due(monthly, jobstore,
                            now=datetime(2026, 12, 31, 23, 30,
                                         tzinfo=CST)) is False
    assert scheduler.is_due(monthly, jobstore,
                            now=datetime(2027, 1, 1, 0, 30,
                                         tzinfo=CST)) is True


# ---------------------------------------------------------------------------
# 5. 新写入的记录必须带显式时区
# ---------------------------------------------------------------------------

def test_new_rows_carry_an_explicit_offset(jobstore):
    """新写入的时间戳必须自带偏移 —— 语义不靠约定。"""
    run = jobs.run_job("tz_probe", lambda: "ok", conn=jobstore)
    row = jobstore.execute("SELECT started_at, finished_at FROM jobs "
                           "WHERE job_id=?", (run.job_id,)).fetchone()
    for val in (row[0], row[1]):
        assert val is not None
        parsed = datetime.fromisoformat(val)
        assert parsed.tzinfo is not None, f"{val!r} 没有时区标记"
        assert parsed.utcoffset() == timedelta(0), f"{val!r} 不是 UTC"


def test_recording_and_reading_agree(jobstore):
    """写进去再读回来，市场日必须一致（端到端）。"""
    run = jobs.run_job("tz_probe2", lambda: "ok", conn=jobstore)
    stored = jobstore.execute("SELECT finished_at FROM jobs WHERE job_id=?",
                              (run.job_id,)).fetchone()[0]
    day = scheduler.utc_to_market_day(stored)
    assert day == datetime.now(CST).date() or \
        abs(day - datetime.now(CST).date()).days <= 1
