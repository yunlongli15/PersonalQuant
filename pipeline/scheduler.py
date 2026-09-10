# -*- coding: utf-8 -*-
"""Task scheduling (STEP 7G, spec §37).

First version per the spec: Manual + Daily implemented, Weekly/Monthly
declared. There is deliberately NO daemon in this version: the schedule
is *evaluated*, so it works equally well from the GUI's "Run due tasks"
button, from `scripts/quant/refresh_all.py --due`, or from Windows Task
Scheduler calling that command once a day. A long-running background
process would have to be supervised, restarted and made idempotent —
none of which the first version needs.

Due-ness is recorded in the job store (pipeline/jobs.py): a task that
already succeeded today is not due again, so calling `run_due` ten times
still performs one day's work.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable, Dict, List, Optional

from . import jobs as jobstore


@dataclass
class Task:
    name: str
    cadence: str                 # manual | daily | weekly | monthly
    job: str                     # a job name in pipeline.refresh
    description: str = ""
    weekday: int = 0             # weekly: 0=Monday
    day: int = 1                 # monthly


#: 日程表（spec §37）。manual 任务只由用户触发，永远 not-due。
SCHEDULE: List[Task] = [
    Task("daily_data_update", "daily", "market_update",
         "incremental market data"),
    Task("daily_news_update", "daily", "news_update",
         "公告增量（只推进已 settle 的日期）"),
    Task("daily_wealth_snapshot", "manual", "wealth_snapshot",
         "录入当日资产（Daily Update 页面）"),
    Task("weekly_research", "weekly", "factor_refresh",
         "重算因子缓存并复核研究状态", weekday=5),
    Task("monthly_rebalance", "monthly", "portfolio_refresh",
         "月度调仓：重建交易计划", day=1),
]


def _last_success(conn, job_name: str) -> Optional[str]:
    last = jobstore.last_run(conn, job_name)
    if not last or last["status"] != "SUCCESS":
        return None
    return (last.get("finished_at") or "")[:10]


def is_due(task: Task, conn=None, now: Optional[datetime] = None) -> bool:
    """Whether a task should run now (manual tasks are never auto-due)."""
    if task.cadence == "manual":
        return False
    now = now or datetime.now()
    today = now.date().isoformat()
    last = _last_success(conn, task.job)
    if task.cadence == "daily":
        return last != today
    if task.cadence == "weekly":
        # due again once a new week has started (ISO week changes)
        if last is None:
            return True
        return date.fromisoformat(last).isocalendar()[:2] != \
            now.date().isocalendar()[:2]
    if task.cadence == "monthly":
        if last is None:
            return True
        return date.fromisoformat(last).month != now.date().month or \
            date.fromisoformat(last).year != now.date().year
    return False


def due_tasks(conn=None, now: Optional[datetime] = None) -> List[Task]:
    return [t for t in SCHEDULE if is_due(t, conn, now)]


def run_due(conn=None, now: Optional[datetime] = None,
            jobs: Optional[Dict[str, Callable]] = None,
            continue_on_error: bool = True) -> List[dict]:
    """Run every due task, recording results in the job store."""
    from . import refresh

    table = jobs or {name: fn for name, fn in refresh.REFRESH_JOBS}
    out = []
    for task in due_tasks(conn, now):
        fn = table.get(task.job)
        if fn is None:
            out.append({"task": task.name, "job": task.job,
                        "status": "NO_JOB"})
            continue
        try:
            run = jobstore.run_job(task.job, fn, conn=conn)
            out.append({"task": task.name, "job": task.job,
                        "status": run.status, "detail": run.detail})
        except Exception as e:                               # noqa: BLE001
            out.append({"task": task.name, "job": task.job,
                        "status": "FAILED", "error": f"{type(e).__name__}: "
                                                     f"{e}"})
            if not continue_on_error:
                raise
    return out


def schedule_view(conn=None, now: Optional[datetime] = None) -> List[dict]:
    """For the GUI: each task with its cadence and last run."""
    now = now or datetime.now()
    rows = []
    for t in SCHEDULE:
        last = jobstore.last_run(conn, t.job)
        rows.append({"task": t.name, "cadence": t.cadence,
                     "description": t.description,
                     "last_status": (last or {}).get("status"),
                     "last_finished": (last or {}).get("finished_at"),
                     "due": is_due(t, conn, now)})
    return rows
