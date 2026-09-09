# -*- coding: utf-8 -*-
"""Quantile analysis properties."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from factors.evaluator import quantile_returns

N, D = 100, 12
IDX = pd.date_range("2020-01-31", periods=D, freq="ME")
SYMS = [f"{i:06d}.SH" for i in range(N)]
rng = np.random.default_rng(3)


def make_panels(signal: bool = True):
    """factor monotone in future return when signal=True."""
    factor = pd.DataFrame(index=IDX, columns=SYMS, dtype=float)
    label = pd.DataFrame(index=IDX, columns=SYMS, dtype=float)
    for i in range(D):
        alpha = np.linspace(-0.02, 0.02, N)
        rng.shuffle(alpha)
        noise = rng.normal(0, 0.005, N)
        f = alpha + noise if signal else rng.normal(0, 1, N)
        factor.iloc[i] = f
        label.iloc[i] = alpha + rng.normal(0, 0.005, N)
    return factor, label


def test_monotone_factor_gives_monotone_quantiles():
    factor, label = make_panels(signal=True)
    res = quantile_returns(factor, label, n_q=5)
    means = [res["quantile_means"][f"Q{i+1}"] for i in range(5)]
    assert means == sorted(means), f"quantile means not monotone: {means}"
    assert res["q5_q1_mean"] > 0
    assert res["n_dates"] == D


def test_pure_noise_factor_has_small_spread():
    factor, label = make_panels(signal=False)
    res = quantile_returns(factor, label, n_q=5)
    assert abs(res["q5_q1_mean"]) < 0.01


def test_nan_cells_are_excluded_not_zeroed():
    factor, label = make_panels(signal=True)
    factor.iloc[0, :50] = np.nan  # half the first row missing
    res = quantile_returns(factor, label, n_q=5)
    assert res["n_dates"] == D
    assert np.isfinite(res["q5_q1_mean"])


def test_too_few_stocks_produces_no_rows():
    factor, label = make_panels(signal=True)
    tiny = factor.iloc[:, :10]
    res = quantile_returns(tiny, label.iloc[:, :10], n_q=5)
    assert res["n_dates"] == 0  # fewer than n_q*10 stocks


def test_quantile_spread_series_length():
    factor, label = make_panels(signal=True)
    res = quantile_returns(factor, label, n_q=5)
    assert len(res["q5_q1_series"]) == D
