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
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
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


#: 调度器使用的时区 = **市场时区**，写死，不跟随机器。
#
# 2026-10-06 事故：作业记录里的 `finished_at` 是 UTC（SQLite `datetime('now')`），
# 而这里拿 `datetime.now()` 的本地日期去比。CST 00:00–08:00 之间 UTC 还停在
# 前一天，于是"今天跑过没有"永远被判成没跑过，日常任务会重复执行。
# 只在深夜复现，白天怎么测都是绿的。
#
# 修法不是"改成 UTC"也不是"改成机器本地"—— 两者都还是隐式的。定死成市场
# 时区：任务的"今天"就是**上海的一天**，与机器在哪个时区无关。
MARKET_TZ = ZoneInfo("Asia/Shanghai")


def utc_to_market_day(ts: Optional[str]) -> Optional[date]:
    """把作业记录里的时刻换算成市场时区的**日历日**。

    记录可能是带偏移的 ISO8601（新写入，`2026-10-05T16:02:52+00:00`），
    也可能是老格式的无标记 UTC（`2026-10-05 16:02:52`）。前者按标记走，
    后者按 UTC 解释 —— SQLite 的 `datetime('now')` 写的就是 UTC，
    这一点是确定的，不需要猜。
    """
    if not ts:
        return None
    t = datetime.fromisoformat(ts)
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.astimezone(MARKET_TZ).date()


def _market_now(now: Optional[datetime]) -> datetime:
    """把 `now` 归一到市场时区。

    朴素时间按**市场时区**解释，不按机器时区 —— 否则同一份代码在两台
    时区不同的机器上会给出不同的调度判定。
    """
    if now is None:
        return datetime.now(MARKET_TZ)
    if now.tzinfo is None:
        return now.replace(tzinfo=MARKET_TZ)
    return now.astimezone(MARKET_TZ)


def _last_success(conn, job_name: str) -> Optional[date]:
    last = jobstore.last_run(conn, job_name)
    if not last or last["status"] != "SUCCESS":
        return None
    return utc_to_market_day(last.get("finished_at"))


def is_due(task: Task, conn=None, now: Optional[datetime] = None) -> bool:
    """Whether a task should run now (manual tasks are never auto-due)."""
    if task.cadence == "manual":
        return False
    today = _market_now(now).date()
    last = _last_success(conn, task.job)
    if task.cadence == "daily":
        return last != today
    if task.cadence == "weekly":
        # due again once a new week has started (ISO week changes)
        if last is None:
            return True
        return last.isocalendar()[:2] != today.isocalendar()[:2]
    if task.cadence == "monthly":
        if last is None:
            return True
        return (last.month, last.year) != (today.month, today.year)
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
