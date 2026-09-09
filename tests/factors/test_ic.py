# -*- coding: utf-8 -*-
"""IC / RankIC computation properties."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from factors.evaluator import ic_series, _summarize

N, D = 200, 24
IDX = pd.date_range("2020-01-31", periods=D, freq="ME")
SYMS = [f"{i:06d}.SH" for i in range(N)]
rng = np.random.default_rng(11)


def make(label_signal: bool, noise_scale: float = 0.1):
    factor = pd.DataFrame(index=IDX, columns=SYMS, dtype=float)
    label = pd.DataFrame(index=IDX, columns=SYMS, dtype=float)
    for i in range(D):
        alpha = np.linspace(-0.03, 0.03, N)
        rng.shuffle(alpha)
        factor.iloc[i] = alpha + rng.normal(0, noise_scale, N)
        label.iloc[i] = (alpha + rng.normal(0, 0.001, N)) if label_signal \
            else rng.normal(0, 0.02, N)
    return factor, label


def test_perfectly_ordered_factor_ic_near_one():
    f, l = make(label_signal=True, noise_scale=0.0)
    ic = ic_series(f, l, min_stocks=30)
    s = _summarize(ic, "rank_ic")
    assert s["mean"] == pytest.approx(1.0, abs=0.02)
    assert s["icir"] > 20
    assert s["positive_ratio"] == 1.0


def test_random_factor_ic_near_zero():
    f, l = make(label_signal=False)
    f = pd.DataFrame(rng.normal(0, 1, (D, N)), index=IDX, columns=SYMS)
    ic = ic_series(f, l, min_stocks=30)
    s = _summarize(ic, "ic")
    assert abs(s["mean"]) < 0.05
    assert s["n"] == D


def test_min_stocks_filter():
    f, l = make(label_signal=True)
    f.iloc[0, 30:] = np.nan  # only 30 valid -> exactly at threshold
    ic = ic_series(f, l, min_stocks=30)
    assert ic["n"].iloc[0] == 30


def test_rank_ic_robust_to_monotone_transform():
    f, l = make(label_signal=True, noise_scale=0.3)
    g = np.exp(f) * 3  # monotone transform
    a = ic_series(f, l)
    b = ic_series(g, l)
    assert np.allclose(a["rank_ic"], b["rank_ic"], atol=1e-12)


def test_constant_label_skipped():
    f, l = make(label_signal=True)
    l.iloc[3] = 0.05  # zero std -> skipped
    ic = ic_series(f, l)
    assert pd.Timestamp("2020-04-30") not in set(ic["date"])
