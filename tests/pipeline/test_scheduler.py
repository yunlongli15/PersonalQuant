# -*- coding: utf-8 -*-
"""STEP 7G: scheduler (spec §37) — manual + daily implemented, weekly and
monthly declared; due-ness comes from the job store, so repeated calls
do not repeat work."""

from datetime import datetime

from pipeline import jobs, scheduler


def test_manual_tasks_are_never_auto_due(jobstore):
    manual = [t for t in scheduler.SCHEDULE if t.cadence == "manual"]
    assert manual, "the spec requires an explicitly manual task"
    for t in manual:
        assert scheduler.is_due(t, jobstore) is False


def test_daily_task_due_then_not_due(jobstore):
    daily = next(t for t in scheduler.SCHEDULE if t.cadence == "daily")
    assert scheduler.is_due(daily, jobstore) is True      # never ran
    jobs.run_job(daily.job, lambda: "ok", conn=jobstore)
    now = datetime.now()
    assert scheduler.is_due(daily, jobstore, now=now) is False


def test_failed_run_does_not_mark_done(jobstore):
    daily = next(t for t in scheduler.SCHEDULE if t.cadence == "daily")

    def boom():
        raise RuntimeError("nope")

    try:
        jobs.run_job(daily.job, boom, conn=jobstore)
    except RuntimeError:
        pass
    assert scheduler.is_due(daily, jobstore) is True


def test_weekly_due_across_iso_weeks(jobstore):
    weekly = next(t for t in scheduler.SCHEDULE if t.cadence == "weekly")
    jobs.run_job(weekly.job, lambda: "ok", conn=jobstore)
    # same ISO week -> not due; a later week -> due
    #
    # 这里原本写的是 `["finished_at"][:10]`，即直接截字符串当成日期用。
    # 记录是 UTC 且带 `T` 分隔符，`[:10]` 拿到的是 **UTC 日期**，而
    # is_due 比较的是**市场日**（Asia/Shanghai）—— 沪 00:00–08:00 之间
    # 两者差一天。测试之所以一直绿，只是因为 10-05 和 10-06 恰好同属
    # ISO 第 41 周；换成周一凌晨运行就会失败。这不是"改测试让它通过"，
    # 是那一行的前提本身有错：它假设了被修掉的那个 UTC/本地混淆。
    last = scheduler.utc_to_market_day(
        jobs.last_run(jobstore, weekly.job)["finished_at"])
    y, w, _ = last.isocalendar()
    same = datetime.fromisocalendar(y, w, 1)
    assert scheduler.is_due(weekly, jobstore, now=same) is False
    later = datetime.fromisocalendar(y, w + 1 if w < 52 else 1, 1)
    if later.year == y and later.month == same.month and w < 52:
        assert scheduler.is_due(weekly, jobstore, now=later) is True


def test_monthly_rollover(jobstore):
    monthly = next(t for t in scheduler.SCHEDULE if t.cadence == "monthly")
    jobs.run_job(monthly.job, lambda: "ok", conn=jobstore)
    assert scheduler.is_due(monthly, jobstore) is False
    future = datetime(2099, 1, 2)
    assert scheduler.is_due(monthly, jobstore, now=future) is True


def test_run_due_executes_only_due_tasks(jobstore):
    calls = []

    def fake(name):
        def _f():
            calls.append(name)
            return f"{name} done"
        return _f

    due = scheduler.due_tasks(jobstore)
    table = {t.job: fake(t.job) for t in scheduler.SCHEDULE}
    out = scheduler.run_due(jobstore, jobs=table)
    assert len(out) == len(due)
    assert set(calls) == {t.job for t in due}
    # a second immediate call finds nothing due
    assert scheduler.run_due(jobstore, jobs=table) == []


def test_schedule_view_shape(jobstore):
    view = scheduler.schedule_view(jobstore)
    assert len(view) == len(scheduler.SCHEDULE)
    assert all({"task", "cadence", "due"} <= set(r) for r in view)
