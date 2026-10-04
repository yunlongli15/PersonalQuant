# -*- coding: utf-8 -*-
"""刷新反馈与"上游有没有新数据"的判定（2026-09-21 用户反馈）。

三件事：
1. 行情有没有更新，要看**上游 manifest 的数据日**，不是 release 名字，
   也不是"本地数据 vs 本地日历"（那两个同源，永远是 0 天）。
2. 作业被强杀后不能永远停在 'running'。
3. `_upstream_data_date` 的解析要老实，解析不出来就说不知道。
"""

import pytest

from pipeline import daily as D
from pipeline import jobs as J


# ---------------------------------------------------------------------------
# 1. 上游数据日解析
# ---------------------------------------------------------------------------

def test_parses_upstream_data_date():
    info = ("upstream release: 2026-09-20  (published 2026-09-19)\n"
            "upstream data ends: 2026-09-18\n"
            "local calendar ends: 2026-09-18")
    assert D._upstream_data_date(info) == "2026-09-18"


@pytest.mark.parametrize("info", [None, "", "no such line",
                                  "upstream data ends: 未知"])
def test_unknown_upstream_date_is_none(info):
    """取不到就说取不到 —— 不能编一个日期出来。"""
    assert D._upstream_data_date(info) is None


# ---------------------------------------------------------------------------
# 2. market_data 作业必须说真话
# ---------------------------------------------------------------------------

class _Run:
    dry_run = False


class _Ctx:
    def __init__(self):
        self.run = _Run()
        self.store_data = {}


def _check_output(up_to: str) -> str:
    return (f"upstream release: 2099-01-01  (published 2099-01-01)\n"
            f"upstream data ends: {up_to}\n"
            f"local calendar ends: 2026-09-18")


def test_market_task_says_up_to_date(monkeypatch):
    """上游数据日 == 本地最新 → 明确说"没有更新的数据"，而不是含糊的
    "落后 0 天"（用户会以为该更新却没更新）。"""
    from pipeline.freshness import market_latest

    monkeypatch.setattr(D, "_snapshot_check",
                        lambda: _check_output(str(market_latest())))
    status, detail = D.task_market_data(_Ctx())
    assert status == D.OK
    assert "已是最新" in detail


def test_market_task_warns_when_upstream_is_newer(monkeypatch):
    """上游确实更新了 → WARNING + 可执行的下一步，不能静默当没事。"""
    from pipeline.freshness import market_latest
    from pipeline.freshness import last_trading_day
    import pandas as pd

    newer = (pd.Timestamp(last_trading_day()) + pd.Timedelta("3D"))
    monkeypatch.setattr(D, "_snapshot_check",
                        lambda: _check_output(str(newer.date())))
    status, detail = D.task_market_data(_Ctx())
    assert status == D.WARNING
    assert "refresh_all" in detail
    assert str(market_latest()) in detail


# ---------------------------------------------------------------------------
# 3. 被强杀的作业不能永远 'running'
# ---------------------------------------------------------------------------

def test_mark_interrupted_flips_only_running(tmp_path):
    conn = J.connect(tmp_path / "jobs.db")
    c = conn.execute("INSERT INTO jobs (job_name, status) VALUES (?, 'running')",
                     ("killed_job",))
    conn.commit()
    killed = int(c.lastrowid)
    J.run_job("ok_job", lambda: "done", conn=conn)

    n = J.mark_interrupted(conn=conn)
    assert n == 1

    rows = {r["job_name"]: r for r in J.history(conn=conn)}
    assert rows["killed_job"]["status"] == "INTERRUPTED"
    assert rows["killed_job"]["finished_at"] is not None
    # 正常完成的作业不受影响
    assert rows["ok_job"]["status"] == "SUCCESS"
    conn.close()
