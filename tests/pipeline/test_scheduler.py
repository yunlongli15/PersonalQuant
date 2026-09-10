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
    last = jobs.last_run(jobstore, weekly.job)["finished_at"][:10]
    y, w, _ = datetime.fromisoformat(last).date().isocalendar()
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
