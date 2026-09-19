# -*- coding: utf-8 -*-
"""§15：基准必须各自声明 weighting convention，绝不混用。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from paper_live.config import load_config


def test_every_benchmark_declares_its_weighting():
    for b in load_config()["paper_live"]["benchmarks"]:
        assert set(b) >= {"symbol", "label", "weighting"}, b
        assert b["weighting"] in ("buy_and_hold_index",
                                  "daily_rebalanced_equal_weight_liquid")


def test_required_benchmarks_are_present():
    labels = {b["label"] for b in load_config()["paper_live"]["benchmarks"]}
    assert {"CSI300", "CSI500", "CSI1000", "等权全市场"} <= labels


def test_index_benchmarks_are_buy_and_hold():
    for b in load_config()["paper_live"]["benchmarks"]:
        if b["symbol"] != "EW_MARKET":
            assert b["weighting"] == "buy_and_hold_index"


def test_equal_weight_benchmark_is_declared_separately():
    ew = [b for b in load_config()["paper_live"]["benchmarks"]
          if b["symbol"] == "EW_MARKET"][0]
    assert ew["weighting"] == "daily_rebalanced_equal_weight_liquid"


def test_benchmark_alignment_in_performance_is_pit_safe():
    """基准按策略净值日期对齐并前向填充，不给未来值。

    这一条**不碰数据库** —— forward 单测必须在无 DB 争用下可跑
    （真实指数的取数校验放在 scripts/verify_step10.py）。
    """
    from paper_live import metrics as pm

    idx = pd.bdate_range("2026-01-01", periods=40)
    nav = pd.Series(np.linspace(1.0, 1.1, 40), index=idx)
    bench = pd.Series(np.linspace(1.0, 1.05, 30),
                      index=idx[:30])           # 基准更短
    perf = pm.performance(nav, {"CSI300": bench})
    # 更短也不该产生 NaN/异常：ffill 后再对齐
    assert perf["CSI300_cumulative"] == pytest.approx(0.05, abs=1e-6)
    assert np.isfinite(perf["CSI300_active"])


def test_benchmark_weights_come_only_from_config():
    """基准定义不得散落在代码里。"""
    import re
    root = Path(__file__).resolve().parents[2] / "paper_live"
    for f in root.glob("*.py"):
        text = f.read_text(encoding="utf-8")
        assert not re.search(r"000300\.SH", text), f"{f.name} 硬编码了 CSI300"
