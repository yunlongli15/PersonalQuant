# -*- coding: utf-8 -*-
"""§22：依赖图。上游失败，下游**不允许运行**。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from pipeline import daily as D


def test_data_failure_blocks_prediction(run):
    """Data 失败 → Prediction 不允许运行（最重要的一条）。"""
    _, panel = run(force=True)
    panel.set("market_data", D.INVALID, "行情为空")
    before = len(panel.calls)          # calls 会跨两次 run 累积，只看本次
    res, panel = run()
    assert res.task("market_data").status == D.INVALID
    assert res.task("data_quality").status == D.BLOCKED
    assert res.task("paper_prediction").status == D.BLOCKED
    this_run = panel.calls[before:]
    assert "paper_prediction" not in this_run
    assert "data_quality" not in this_run


def test_environment_failure_blocks_everything(run):
    _, panel = run()
    panel.set("environment", D.INVALID, "Python 版本不对")
    res, _ = run()
    assert res.task("environment").status == D.INVALID
    for name in ("source_health", "market_data", "data_quality",
                 "paper_prediction", "performance", "risk"):
        assert res.task(name).status == D.BLOCKED, name


def test_news_failure_does_not_block_prediction(run):
    """新闻 provider 失败只告警，不影响 prediction（§8）。"""
    _, panel = run()
    panel.set("news", D.FAILED, "provider 挂了")
    res, _ = run()
    assert res.task("news").status == D.FAILED
    assert res.task("paper_prediction").status == D.OK


def test_report_runs_even_when_alerts_warn(run):
    _, panel = run()
    panel.set("alerts", D.WARNING, "有告警")
    res, _ = run()
    assert res.task("report").status == D.OK


def test_blocked_chain_is_recorded(run):
    _, panel = run()
    panel.set("data_quality", D.INVALID, "价格异常")
    res, _ = run()
    assert "paper_prediction" in res.blocked()
    assert "drift" in res.blocked()


def test_task_declares_its_dependencies():
    """每个任务的依赖必须是已声明的任务名。"""
    names = {t[0] for t in D.TASKS}
    for name, _fn, deps, _blocking in D.TASKS:
        for d in deps:
            assert d in names, f"{name} 依赖了不存在的任务 {d}"
