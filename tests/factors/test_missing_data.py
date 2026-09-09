# -*- coding: utf-8 -*-
"""Missing-value handling: drop / cross_median / sector_median.

The chosen method must be a real, visible policy — never a silent fill.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from factors.normalization import fill_missing

IDX = pd.date_range("2020-01-31", periods=2, freq="ME")
PANEL = pd.DataFrame(
    {"a": [1.0, np.nan], "b": [2.0, 4.0], "c": [np.nan, 6.0],
     "d": [9.0, 8.0], "e": [5.0, 10.0]},
    index=IDX,
)
IND = pd.Series({"a": "bank", "b": "bank", "c": "tech", "d": "tech",
                 "e": "tech"})


def test_drop_leaves_nan():
    out = fill_missing(PANEL, "drop")
    assert out.isna().sum().sum() == PANEL.isna().sum().sum()


def test_cross_median_fills_row_median():
    out = fill_missing(PANEL, "cross_median")
    assert not out.isna().any().any()
    # row 0: values 1,2,9,5 -> median 3.5 fills 'c'
    assert out.loc[IDX[0], "c"] == pytest.approx(3.5)


def test_sector_median_prefers_sector():
    out = fill_missing(PANEL, "sector_median", IND)
    # row 0: 'c' is tech -> tech median of {9,5} = 7 (sector, not row median)
    assert out.loc[IDX[0], "c"] == pytest.approx(7.0)
    # row 0: 'a' has a value already -> unchanged
    assert out.loc[IDX[0], "a"] == 1.0


def test_sector_median_falls_back_to_row_median_when_sector_empty():
    panel = PANEL.copy()
    # 'c' sector has only NaN values in row 0 -> sector median unavailable
    panel.loc[IDX[0], ["d", "e"]] = np.nan
    out = fill_missing(panel, "sector_median", IND)
    assert np.isfinite(out.loc[IDX[0], "c"])  # fell back to row median


def test_unknown_industries_fall_back_to_row_median():
    ind = IND.copy()
    ind["c"] = None
    out = fill_missing(PANEL, "sector_median", ind)
    assert np.isfinite(out.loc[IDX[0], "c"])


def test_unknown_method_raises():
    with pytest.raises(ValueError):
        fill_missing(PANEL, "magic")
