# -*- coding: utf-8 -*-
"""Factor correlation matrix + redundancy clustering."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from factors.evaluator import cluster_correlated, pairwise_correlation

N, D = 100, 24
IDX = pd.date_range("2020-01-31", periods=D, freq="ME")
SYMS = [f"{i:06d}.SH" for i in range(N)]
rng = np.random.default_rng(2)

base = pd.DataFrame(rng.normal(0, 1, (D, N)), index=IDX, columns=SYMS)


def test_identical_panels_corr_one():
    c = pairwise_correlation({"a": base, "b": base.copy()},
                             method="spearman")
    assert c.loc["a", "b"] == pytest.approx(1.0, abs=0.05)


def test_opposite_panels_corr_minus_one():
    c = pairwise_correlation({"a": base, "b": -base}, method="spearman")
    assert c.loc["a", "b"] == pytest.approx(-1.0, abs=0.05)


def test_matrix_is_symmetric_with_unit_diagonal():
    panels = {"a": base, "b": base.shift(1).fillna(0), "c": base * 2 + 1}
    c = pairwise_correlation(panels)
    assert np.allclose(c.values, c.values.T, equal_nan=True)
    assert np.allclose(np.diag(c.values), 1.0)


def test_clustering_merges_above_threshold():
    corr = pd.DataFrame({
        "a": [1.0, 0.9, 0.1, 0.1],
        "b": [0.9, 1.0, 0.05, 0.05],
        "c": [0.1, 0.05, 1.0, 0.85],
        "d": [0.1, 0.05, 0.85, 1.0],
    }, index=["a", "b", "c", "d"])
    clusters = cluster_correlated(corr, threshold=0.8)
    assert sorted(map(sorted, clusters)) == [["a", "b"], ["c", "d"]]


def test_clustering_no_merge_below_threshold():
    corr = pd.DataFrame({
        "a": [1.0, 0.5], "b": [0.5, 1.0],
    }, index=["a", "b"])
    clusters = cluster_correlated(corr, threshold=0.8)
    assert sorted(map(sorted, clusters)) == [["a"], ["b"]]
