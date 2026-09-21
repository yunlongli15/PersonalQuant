# -*- coding: utf-8 -*-
"""Job store + runner (spec §20/§21/§38).

Every refresh is recorded: what ran, when, how long, whether it worked,
and what it changed. Stored in a small SQLite DB
(data/quant/jobs.db) separate from both the research DuckDB and the
wealth SQLite.

The runner never swallows an exception: a failing job is recorded as
FAILED with the error text and re-raised to the caller, which is what
lets refresh_all stop instead of silently producing recommendations from
stale data.
"""

from __future__ import annotations

import sqlite3
import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JOBS_DB = PROJECT_ROOT / "data" / "quant" / "jobs.db"

_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    job_name    TEXT NOT NULL,
    started_at  TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT,
    status      TEXT NOT NULL DEFAULT 'running',
    duration_s  REAL,
    detail      TEXT,
    error       TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_name ON jobs(job_name, job_id DESC);
"""


def connect(path: Optional[Path] = None) -> sqlite3.Connection:
    if path is None:
        conn = getattr(_local, "conn", None)
        if conn is not None:
            return conn
    p = Path(path) if path else JOBS_DB
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    if path is None:
        _local.conn = conn
    return conn


def close() -> None:
    conn = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
        _local.conn = None


@dataclass
class JobRun:
    job_id: int
    job_name: str
    status: str
    detail: Optional[str] = None
    error: Optional[str] = None
    duration_s: Optional[float] = None
    finished_at: Optional[str] = None


def run_job(name: str, fn: Callable[[], object],
            conn: Optional[sqlite3.Connection] = None,
            skip: bool = False) -> JobRun:
    """Run `fn`, recording start/finish/status. Re-raises on failure."""
    c = conn or connect()
    cur = c.execute("INSERT INTO jobs (job_name, status) VALUES (?, 'running')",
                    (name,))
    c.commit()
    job_id = int(cur.lastrowid)
    t0 = time.time()
    if skip:
        return _finish(c, job_id, "SKIPPED", "skipped by caller", None, 0.0)
    try:
        detail = fn()
    except Exception as e:                       # noqa: BLE001 - recorded
        c.execute("UPDATE jobs SET finished_at=datetime('now'), "
                  "status='FAILED', duration_s=?, error=? WHERE job_id=?",
                  (time.time() - t0, f"{type(e).__name__}: {e}\n"
                   + traceback.format_exc(limit=3), job_id))
        c.commit()
        raise
    return _finish(c, job_id, "SUCCESS",
                   str(detail) if detail is not None else None, None,
                   time.time() - t0)


def mark_interrupted(conn: Optional[sqlite3.Connection] = None) -> int:
    """把上次被强杀的作业从 'running' 改成 'INTERRUPTED'。

    进程一被杀，那行记录就永远停在 'running'，看起来像"还在跑"，
    实际上什么都没在跑（2026-09-21 用户就是这样被误导的）。
    """
    c = conn or connect()
    cur = c.execute(
        "UPDATE jobs SET status='INTERRUPTED', finished_at=datetime('now'), "
        "detail='进程中断，未正常结束（不是失败，是没有跑完）' "
        "WHERE status='running'")
    c.commit()
    return int(cur.rowcount)


def skip_job(name: str, reason: str,
             conn: Optional[sqlite3.Connection] = None) -> JobRun:
    """Record a job that was deliberately not run (e.g. offline mode)."""
    c = conn or connect()
    cur = c.execute("INSERT INTO jobs (job_name, status) VALUES (?, ?)",
                    (name, "SKIPPED"))
    c.commit()
    return _finish(c, int(cur.lastrowid), "SKIPPED", reason, None, 0.0)


def _finish(conn, job_id: int, status: str, detail, error,
            duration: float) -> JobRun:
    conn.execute("UPDATE jobs SET finished_at=datetime('now'), status=?, "
                 "detail=?, error=?, duration_s=? WHERE job_id=?",
                 (status, detail, error, duration, job_id))
    conn.commit()
    row = conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    return JobRun(job_id=row["job_id"], job_name=row["job_name"],
                  status=row["status"], detail=row["detail"],
                  error=row["error"], duration_s=row["duration_s"],
                  finished_at=row["finished_at"])


def history(conn: Optional[sqlite3.Connection] = None, limit: int = 50,
            job_name: Optional[str] = None) -> List[dict]:
    c = conn or connect()
    if job_name:
        rows = c.execute("SELECT * FROM jobs WHERE job_name=? "
                         "ORDER BY job_id DESC LIMIT ?",
                         (job_name, limit)).fetchall()
    else:
        rows = c.execute("SELECT * FROM jobs ORDER BY job_id DESC LIMIT ?",
                         (limit,)).fetchall()
    return [dict(r) for r in rows]


def last_run(conn: Optional[sqlite3.Connection] = None,
             job_name: Optional[str] = None) -> Optional[dict]:
    rows = history(conn, limit=1, job_name=job_name)
    return rows[0] if rows else None


def status_summary(conn: Optional[sqlite3.Connection] = None) -> Dict[str, dict]:
    """Latest status per job name — the GUI's job panel."""
    c = conn or connect()
    rows = c.execute(
        "SELECT job_name, MAX(job_id) AS jid FROM jobs GROUP BY job_name"
    ).fetchall()
    out = {}
    for r in rows:
        row = c.execute("SELECT * FROM jobs WHERE job_id=?",
                        (r["jid"],)).fetchone()
        out[r["job_name"]] = dict(row)
    return out
