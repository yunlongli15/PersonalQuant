# -*- coding: utf-8 -*-
"""Outlier handling: winsorization and the no-silent-drop rule for
negative PE / extreme ratios."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from factors.normalization import normalize_panel


def test_extreme_outlier_does_not_dominate_winsorized_zscore():
    p = pd.DataFrame({"x": [1, 2, 3, 4, 5, 1e9], "y": [2, 3, 4, 5, 6, 7]},
                     index=pd.date_range("2020-01-01", periods=6))
    w = normalize_panel(p, "winsorized_zscore", winsor_sigma=3.0)
    # with clipping, the z-scores are bounded and the outlier is pulled in
    assert w["x"].abs().max() <= 3.0 + 1e-9
    assert w["y"].abs().max() <= 3.0 + 1e-9


def test_winsorization_keeps_ordering_within_row():
    p = pd.DataFrame({"x": [5, -1e12, 3], "y": [2, 0, 1]},
                     index=pd.date_range("2020-01-01", periods=3))
    w = normalize_panel(p, "winsorized_zscore")
    for _, row in w.iterrows():
        assert list(row.values) == sorted(row.values, reverse=False) or \
            list(row.values) == sorted(row.values, reverse=True)


def test_negative_values_are_not_dropped_by_normalization():
    # negative PE is meaningful (loss-making); normalization keeps the cell
    p = pd.DataFrame({"x": [-30.0, 5.0, 10.0], "y": [1.0, 2.0, 3.0],
                      "z": [4.0, 5.0, 6.0]},
                     index=pd.date_range("2020-01-01", periods=3))
    r = normalize_panel(p, "rank")
    assert r.iloc[0, 0] == pytest.approx(1 / 3)  # lowest rank, but present
    z = normalize_panel(p, "winsorized_zscore")
    assert np.isfinite(z.iloc[0, 0])


def test_winsor_sigma_respected():
    p = pd.DataFrame({"x": [1, 2, 3, 4, 50], "y": [1, 1, 1, 1, 1]},
                     index=pd.date_range("2020-01-01", periods=5))
    w = normalize_panel(p, "winsorized_zscore", winsor_sigma=1.0)
    assert w["x"].abs().max() <= 1.0 + 1e-9


def test_nan_cells_survive_normalization():
    p = pd.DataFrame({"x": [1.0, np.nan, 3.0], "y": [2.0, 4.0, np.nan]},
                     index=pd.date_range("2020-01-01", periods=3))
    # rank keeps NaN cells untouched
    r = normalize_panel(p, "rank")
    assert r.isna().sum().sum() == 2
    assert r.iloc[0, 0] == pytest.approx(0.5)   # 1 vs 2 -> lowest of two
    assert r.iloc[0, 1] == pytest.approx(1.0)
    assert r.iloc[1, 1] == pytest.approx(1.0)   # only valid value in row
    assert r.iloc[2, 0] == pytest.approx(1.0)
    # zscore/winsorized: rows with <2 valid values cannot be scaled ->
    # those rows become NaN, valid rows keep finite values
    for method in ("zscore", "winsorized_zscore"):
        out = normalize_panel(p, method)
        assert np.isfinite(out.iloc[0]).all()  # two valid values -> scaled
        assert out.iloc[1].isna().all()
        assert out.iloc[2].isna().all()
        # original NaN positions never become numbers
        assert np.isnan(out.iloc[1, 0]) and np.isnan(out.iloc[2, 1])
