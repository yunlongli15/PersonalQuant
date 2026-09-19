# -*- coding: utf-8 -*-
"""§21 / §37：重试有限、失败有 fallback、日志分级正确。"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from pipeline import daily as D

SRC = (D.PROJECT_ROOT / "pipeline" / "daily.py").read_text(encoding="utf-8")


def test_no_unbounded_retry_loops():
    assert "while True" not in SRC
    # 任何 while 循环都必须有明确的上界
    whiles = re.findall(r"while .*:", SRC)
    for w in whiles:
        assert "taken" in w or "<" in w, f"可疑的无界循环：{w}"


def test_market_data_falls_back_when_upstream_unavailable(run, monkeypatch):
    """取不到上游快照信息时只告警 + 沿用本地数据，不能让流水线挂掉。"""
    monkeypatch.setattr(D, "_snapshot_check", lambda: None)
    monkeypatch.setattr(D, "duckdb_available", lambda: (True, "test"))
    import pandas as pd

    from pipeline import freshness
    monkeypatch.setattr(freshness, "market_latest",
                        lambda: pd.Timestamp("2026-06-01"))
    monkeypatch.setattr(freshness, "last_trading_day",
                        lambda on_or_before=None: pd.Timestamp("2026-09-17"))
    st, detail = D.task_market_data(D.Ctx(
        D.DailyRun(run_id="x", date="2026-09-17"),
        pd.Timestamp("2026-09-17")))
    assert st == D.WARNING
    assert "沿用本地行情" in detail


def test_subprocess_calls_have_timeouts():
    """所有 subprocess 调用必须有 timeout，否则会永久挂住。"""
    for m in re.finditer(r"subprocess\.run\((.*?)\)\n", SRC, re.S):
        assert "timeout=" in m.group(1), f"缺少 timeout：{m.group(1)[:60]}"


def test_logging_levels_are_used():
    """INFO / WARNING / ERROR 三档都要用到（§37）。"""
    assert "log.info(" in SRC
    assert "log.warning(" in SRC
    assert "log.error(" in SRC


def test_retry_does_not_log_error_for_transient_network():
    """普通 API 重试不能打成 ERROR —— 只有任务失败才 ERROR。"""
    src = (D.PROJECT_ROOT / "pipeline" / "refresh.py").read_text(
        encoding="utf-8")
    assert "log.error" not in src or "retry" not in src.lower()
