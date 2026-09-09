# -*- coding: utf-8 -*-
"""Row-label matching semantics (STEP 2 extractor, extended in STEP 4 for
per-share metrics with CJK unit suffixes)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from personal_quant.financial.metrics import METRICS, MetricDef

EPS = METRICS["eps"]
BPS = METRICS["bps"]
REV = METRICS["revenue"]


def test_per_share_labels_with_unit_suffix_match():
    assert EPS.match_label("基本每股收益（元/股）")
    assert EPS.match_label("基本每股收益(元/股)")
    assert EPS.match_label("基本每股收益")
    assert BPS.match_label("归属于上市公司股东的每股净资产（元/股）")
    assert BPS.match_label("每股净资产")


def test_per_share_labels_reject_lookalikes():
    assert not EPS.match_label("稀释每股收益")       # exclude list
    assert not EPS.match_label("基本每股收益增长率")  # CJK suffix
    assert not BPS.match_label("每股净资产收益率")    # CJK suffix


def test_amount_labels_unchanged_semantics():
    assert REV.match_label("营业收入")
    assert REV.match_label("营业收入(万元)")
    assert not REV.match_label("营业收入增长率")
    assert not METRICS["net_profit"].match_label("归属于上市公司股东的净利润增长率")


def test_kind_metadata():
    assert EPS.kind == "per_share"
    assert BPS.kind == "per_share"
    assert REV.kind == "amount"


def test_generic_def_still_enforces_boundary():
    d = MetricDef("x", ("测试指标",), "amount")
    assert d.match_label("测试指标")
    assert d.match_label("测试指标(万元)")
    assert not d.match_label("测试指标变动")
    assert d.match_label("测试指标（元/股）")  # unit annotation allowed


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
