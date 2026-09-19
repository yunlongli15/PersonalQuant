# -*- coding: utf-8 -*-
"""§14 / §41：回撤与业绩事实。短样本不年化、不算 Sharpe。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from paper_live import metrics as pm


def _nav(vals, start="2026-01-01"):
    idx = pd.bdate_range(start, periods=len(vals))
    return pd.Series(vals, index=idx, dtype=float)


def test_drawdown_is_zero_on_a_monotone_rise():
    assert (pm.drawdown(_nav([1, 2, 3, 4])) == 0).all()


def test_drawdown_is_measured_from_the_running_peak():
    nav = _nav([1.0, 2.0, 1.0, 1.5, 0.5])
    dd = pm.drawdown(nav)
    assert dd.min() == pytest.approx(0.5 / 2.0 - 1.0)
    assert dd.iloc[-1] == pytest.approx(0.5 / 2.0 - 1.0)


def test_performance_reports_only_facts():
    perf = pm.performance(_nav(np.linspace(1.0, 1.2, 30)))
    for k in ("cumulative_return", "max_drawdown", "volatility",
              "positive_day_ratio", "n_days"):
        assert k in perf
    assert perf["cumulative_return"] == pytest.approx(0.2)


def test_short_samples_are_not_annualized():
    perf = pm.performance(_nav(np.linspace(1.0, 1.1, 30)))
    assert np.isnan(perf["annualized_return"])
    assert np.isnan(perf["sharpe"])
    assert "不年化" in perf["note"]


def test_long_enough_samples_do_get_annualized():
    perf = pm.performance(_nav(np.linspace(1.0, 1.2, 120)))
    assert np.isfinite(perf["annualized_return"])
    assert np.isfinite(perf["sharpe"])


def test_active_return_is_strategy_minus_benchmark():
    nav = _nav(np.linspace(1.0, 1.2, 30))
    bench = _nav(np.linspace(1.0, 1.05, 30))
    perf = pm.performance(nav, {"CSI300": bench})
    assert perf["CSI300_cumulative"] == pytest.approx(0.05, abs=1e-6)
    assert perf["CSI300_active"] == pytest.approx(0.15, abs=1e-6)


def test_distribution_shift_reports_a_z_score():
    rng = np.random.default_rng(0)
    hist = pd.Series(rng.normal(0.02, 0.01, 500))
    same = pd.Series(rng.normal(0.02, 0.01, 30))
    far = pd.Series(rng.normal(0.10, 0.01, 30))
    assert abs(pm.distribution_shift(same, hist)["shift_z"]) < 3
    assert abs(pm.distribution_shift(far, hist)["shift_z"]) > 3
