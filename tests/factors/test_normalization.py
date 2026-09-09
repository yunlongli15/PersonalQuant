# -*- coding: utf-8 -*-
"""Cross-sectional normalization properties."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from factors.normalization import METHODS, normalize_panel

PANEL = pd.DataFrame(
    {"a": [1.0, 2.0, 3.0], "b": [2.0, 4.0, 6.0], "c": [100.0, -5.0, 9.0]},
    index=pd.date_range("2020-01-31", periods=3, freq="ME"),
)


def test_rank_is_percentile_in_unit_interval():
    r = normalize_panel(PANEL, "rank")
    assert ((r >= 0) & (r <= 1)).all().all()
    # row0: a=1 < b=2 < c=100 -> 1/3; row1: c=-5 < a=2 < b=4 -> 2/3;
    # row2: a=3 < b=6 < c=9 -> 1/3
    assert np.allclose(r["a"].values, [1 / 3, 2 / 3, 1 / 3])


def test_rank_invariant_to_monotone_transform():
    x = normalize_panel(PANEL, "rank")
    y = normalize_panel(PANEL * 100 + 7, "rank")
    pd.testing.assert_frame_equal(x, y)


def test_zscore_mean_zero_std_one():
    z = normalize_panel(PANEL, "zscore")
    assert np.allclose(z.mean(axis=1), 0, atol=1e-12)
    assert np.allclose(z.std(axis=1), 1, atol=1e-9)


def test_winsorized_zscore_clips_extremes():
    w = normalize_panel(PANEL, "winsorized_zscore", winsor_sigma=1.5)
    assert w.abs().max().max() <= 1.5 + 1e-9


def test_raw_is_identity():
    pd.testing.assert_frame_equal(normalize_panel(PANEL, "raw"), PANEL)


def test_unknown_method_raises():
    with pytest.raises(ValueError):
        normalize_panel(PANEL, "nonsense")


def test_methods_tuple():
    assert METHODS == ("raw", "rank", "zscore", "winsorized_zscore")
