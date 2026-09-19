# -*- coding: utf-8 -*-
"""§21：失败传播与重试纪律。有限重试、绝不无限循环、绝不静默。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from pipeline import daily as D


def test_exception_in_a_task_is_captured_not_raised(run):
    _, panel = run(force=True)
    panel.set("data_quality", D.FAILED, exc=RuntimeError("boom"))
    res, _ = run()
    t = res.task("data_quality")
    assert t.status == D.FAILED
    assert "boom" in t.detail
    assert res.status in (D.FAILED, D.INVALID)


def test_failed_task_does_not_stop_the_pipeline(run):
    """一个任务失败，其余仍然跑完（用户要能看到全部情况）。"""
    _, panel = run(force=True)
    panel.set("news", D.FAILED, "provider down")
    res, _ = run()
    assert res.task("news").status == D.FAILED
    assert res.task("report").status == D.OK      # 仍然出报告


def test_errors_are_collected_for_the_report(run):
    _, panel = run(force=True)
    panel.set("market_data", D.INVALID, "行情为空")
    res, _ = run()
    assert any("market_data" in e for e in res.errors)


def test_no_infinite_retry_in_source():
    """源码里不得出现无限重试（while True / retry 无上限）。"""
    src = (D.PROJECT_ROOT / "pipeline" / "daily.py").read_text(
        encoding="utf-8")
    assert "while True" not in src
    assert "Retry(" not in src or "stop_after_attempt" in src


def test_pipeline_status_reflects_worst_outcome(run):
    _, panel = run(force=True)
    panel.set("source_health", D.WARNING, "有点旧")
    res, _ = run()
    assert res.status == D.WARNING
    _, panel = run(force=True)
    panel.set("source_health", D.WARNING, "有点旧")
    panel.set("data_quality", D.INVALID, "坏了")
    res, _ = run()
    assert res.status in (D.FAILED, D.INVALID)
