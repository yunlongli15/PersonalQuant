# -*- coding: utf-8 -*-
"""block bootstrap：置信区间必须尊重时间相关性，并覆盖真值。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pytest

from incremental.stats import block_bootstrap


def test_constant_series_has_degenerate_interval():
    r = block_bootstrap([0.01] * 40, block=3, n_resamples=300, seed=1)
    assert r["mean"] == pytest.approx(0.01)
    assert r["ci_low"] == pytest.approx(0.01)
    assert r["ci_high"] == pytest.approx(0.01)


def test_interval_covers_the_mean():
    rng = np.random.default_rng(0)
    x = rng.normal(0.02, 0.05, 80)
    r = block_bootstrap(x, block=3, n_resamples=1000, seed=2)
    assert r["ci_low"] < r["mean"] < r["ci_high"]


def test_block_interval_is_wider_than_iid_when_series_is_persistent():
    """正自相关序列上，block bootstrap 必须比 iid 更保守。

    这正是 §7 要求"不能忽略时间相关性"的原因：iid 会把区间做窄。
    """
    rng = np.random.default_rng(3)
    n = 240
    e = rng.normal(0, 1, n)
    x = np.zeros(n)
    for i in range(1, n):                 # AR(1)，强持续
        x[i] = 0.85 * x[i - 1] + e[i]
    r = block_bootstrap(x, block=6, n_resamples=1000, seed=4)
    assert r["ci_width"] > r["iid_ci_width"]


def test_iid_and_block_agree_when_block_is_one():
    rng = np.random.default_rng(5)
    x = rng.normal(0, 1, 60)
    r = block_bootstrap(x, block=1, n_resamples=500, seed=6)
    assert r["ci_low"] == pytest.approx(r["iid_ci_low"])
    assert r["ci_high"] == pytest.approx(r["iid_ci_high"])


def test_confirms_a_real_positive_shift():
    """真值为正时，区间下界应当 > 0（这里给 6 倍标准误的偏移）。"""
    rng = np.random.default_rng(7)
    x = rng.normal(0.03, 0.01, 60)
    r = block_bootstrap(x, block=3, n_resamples=1000, seed=8)
    assert r["ci_low"] > 0


def test_empty_input_is_handled():
    r = block_bootstrap([], block=3, n_resamples=10, seed=9)
    assert r["n"] == 0 and np.isnan(r["mean"])


def test_nan_values_are_dropped():
    r = block_bootstrap([0.01, np.nan, 0.01, np.nan, 0.01], block=2,
                        n_resamples=50, seed=10)
    assert r["n"] == 3
