# -*- coding: utf-8 -*-
"""§16 / §39：日报摘要（GUI 读它）。"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from pipeline import daily as D
from pipeline.daily_report import load_latest_summary

SECTIONS = ("summary", "portfolio", "strategy", "paper_live", "risk",
            "news", "alerts", "timestamps")


def test_summary_has_all_sections(mixed_run, sandbox):
    mixed_run(date="2026-09-17")
    p = sandbox / "reports" / "2026-09-17.json"
    assert p.exists()
    s = json.loads(p.read_text(encoding="utf-8"))
    missing = [k for k in SECTIONS if k not in s]
    assert not missing, f"摘要缺板块：{missing}"


def test_latest_summary_pointer(mixed_run, sandbox):
    mixed_run(date="2026-09-17")
    s = load_latest_summary()
    assert s is not None and s["date"] == "2026-09-17"


def test_markdown_report_has_seventeen_sections(mixed_run, sandbox):
    """§14 的 17 个板块都要在（有的合并成一节，按标题查而不是按编号）。"""
    mixed_run(date="2026-09-17")
    md = (sandbox / "reports" / "2026-09-17.md").read_text(encoding="utf-8")
    titles = ["Pipeline 状态", "数据更新", "Paper Live 状态", "个人账户与收益",
              "基准", "当前持仓", "当前建议", "风险", "新闻", "数据告警",
              "漂移告警", "版本与哈希", "Forward 观测状态", "告警",
              "事实与解释"]
    for t in titles:
        assert f"## " in md and t in md, f"日报缺板块：{t}"


def test_report_separates_fact_from_analysis(run, sandbox):
    """§15：事实与解释必须分开，且不得从单日数字推断模型有效性。"""
    run(date="2026-09-17")
    md = (sandbox / "reports" / "2026-09-17.md").read_text(encoding="utf-8")
    assert "FACT" in md and "ANALYSIS" in md
    assert "不得" in md


def test_summary_timestamps_present(mixed_run, sandbox):
    mixed_run(date="2026-09-17")
    s = json.loads((sandbox / "reports" / "2026-09-17.json").read_text(
        encoding="utf-8"))
    assert s["timestamps"]["started"] and s["timestamps"]["ended"]
