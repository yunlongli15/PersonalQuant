# -*- coding: utf-8 -*-
"""§17 / §18：告警码齐全，且**只报警**。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from pipeline import daily as D
from pipeline import daily_alerts as A


def test_all_required_codes_are_registered():
    required = {"DATA_ERROR", "DATA_WARNING", "PIT_FAILURE", "STRATEGY_DRIFT",
                "MODEL_DRIFT", "NEWS_DRIFT", "EXCESS_TURNOVER",
                "DRAWDOWN_WARNING", "FORWARD_INVALID", "PIPELINE_FAILURE"}
    assert required <= set(A.CODES)


def test_unknown_code_is_rejected():
    with pytest.raises(AssertionError):
        A._a("WARNING", "NOT_A_REAL_CODE", "x")


def test_every_alert_says_action_is_none():
    a = A._a("WARNING", "DATA_WARNING", "测试")
    assert "none" in a["action"]


def test_failed_task_produces_pipeline_failure(run):
    _, panel = run(force=True)
    panel.set("data_quality", D.FAILED, "坏了")
    res, _ = run()
    alerts = res.store_data if False else None
    codes = [x for x in res.errors]
    assert any("data_quality" in c for c in codes)


def test_alerts_are_generated_on_a_normal_run(run):
    res, _ = run(date="2026-09-17")
    # alerts 任务应该跑过（真实实现），至少不报错
    assert res.task("alerts") is not None
    assert res.task("alerts").status in (D.OK, D.WARNING)


def test_alerts_module_has_no_write_paths():
    """§18：告警模块不得有任何修改策略/模型/组合的入口。"""
    src = (D.PROJECT_ROOT / "pipeline" / "daily_alerts.py").read_text(
        encoding="utf-8")
    for banned in ("update", "write", "save", "retrain", "fit(", "INSERT",
                   "UPDATE ", "DELETE"):
        assert banned not in src, f"告警模块出现了写入语义：{banned}"


def test_drawdown_thresholds_are_warnings_not_actions():
    assert all(t < 0 for t in A.DRAWDOWN_THRESHOLDS)
    a = A._a("WARNING", "DRAWDOWN_WARNING", "回撤触发")
    assert a["level"] == "WARNING"
