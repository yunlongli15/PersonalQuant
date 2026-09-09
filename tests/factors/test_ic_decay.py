# -*- coding: utf-8 -*-
"""IC decay: per-horizon IC on the right forward returns."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from factors.evaluator import evaluate_factor, ic_series

HORIZONS = [1, 5, 10, 20, 40, 60]
N, D = 150, 36
IDX = pd.date_range("2020-01-31", periods=D, freq="ME")
SYMS = [f"{i:06d}.SH" for i in range(N)]


class Data:
    industries = pd.Series(dtype=object)
    financial = pd.DataFrame()


def make_labels_and_factor(signal_horizon: int):
    """Labels + a factor that carries the SAME signal draw (so the factor
    correlates ~1 with horizon `signal_horizon` and ~0 with the rest)."""
    rng = np.random.default_rng(5)
    labels = {h: pd.DataFrame(rng.normal(0, 0.02, (D, N)),
                              index=IDX, columns=SYMS) for h in HORIZONS}
    f = pd.DataFrame(index=IDX, columns=SYMS, dtype=float)
    for i in range(D):
        alpha = np.linspace(-0.03, 0.03, N)
        rng.shuffle(alpha)
        labels[signal_horizon].iloc[i] = alpha
        f.iloc[i] = alpha
    return labels, f


def test_ic_only_high_at_the_signal_horizon():
    labels, f = make_labels_and_factor(signal_horizon=20)
    ic_by_horizon = {}
    for h in HORIZONS:
        ic = ic_series(f, labels[h], min_stocks=30)
        ic_by_horizon[h] = ic["rank_ic"].mean()
    assert abs(ic_by_horizon[20]) > 0.9
    for h in HORIZONS:
        if h != 20:
            assert abs(ic_by_horizon[h]) < 0.15, \
                f"h={h} IC {ic_by_horizon[h]:.3f} should be ~0"


def test_evaluate_factor_produces_all_horizons():
    labels, f = make_labels_and_factor(signal_horizon=20)
    cfg = {"labels": {"horizons": HORIZONS, "primary_horizon": 20},
           "normalization": {"methods": ["rank"]},
           "missing": {"method": "drop"},
           "evaluation": {"min_stocks_per_date": 30}}
    ev = evaluate_factor(Data(), "test_factor", list(IDX), labels,
                         config=cfg, compute=lambda data, dates: f)
    res = ev["normalizations"]["rank"]["horizons"]
    assert set(res) == {str(h) for h in HORIZONS}
    # decay: IC(20) clearly above the neighbouring horizons
    ic20 = res["20"]["rank_ic"]["mean"]
    ic1 = res["1"]["rank_ic"]["mean"]
    assert abs(ic20) > abs(ic1)
