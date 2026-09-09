# -*- coding: utf-8 -*-
"""Cross-sectional normalization + missing handling.

Methods: raw (no transform), rank (cross-sectional percentile), zscore,
winsorized_zscore (clip at mean +/- winsor_sigma*std, then zscore).
Missing handling: drop (only rows where the factor exists), cross_median
(cross-sectional median fill), sector_median (CSRC-industry median fill;
the industry is the current CSRC classification — industry changes are
rare, limitation recorded). The chosen method is ALWAYS recorded in the
result metadata — never a silent fill.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

METHODS = ("raw", "rank", "zscore", "winsorized_zscore")


def normalize_panel(panel: pd.DataFrame, method: str,
                    winsor_sigma: float = 3.0) -> pd.DataFrame:
    """Normalize each row (date) cross-sectionally."""
    if method == "raw":
        return panel.copy()
    if method == "rank":
        return panel.rank(axis=1, pct=True, method="average")
    if method == "zscore":
        mu = panel.mean(axis=1)
        sd = panel.std(axis=1)
        return panel.sub(mu, axis=0).div(sd.replace(0, np.nan), axis=0)
    if method == "winsorized_zscore":
        mu = panel.mean(axis=1)
        sd = panel.std(axis=1)
        lo, hi = mu - winsor_sigma * sd, mu + winsor_sigma * sd
        clipped = panel.clip(lower=lo, upper=hi, axis=0)
        cmu = clipped.mean(axis=1)
        csd = clipped.std(axis=1)
        return clipped.sub(cmu, axis=0).div(csd.replace(0, np.nan), axis=0)
    raise ValueError(f"unknown normalization method {method!r}; one of {METHODS}")


def fill_missing(panel: pd.DataFrame, method: str,
                 industries: Optional[pd.Series] = None) -> pd.DataFrame:
    """Fill NaN cells per the configured policy. Returns a new frame.

    - drop: no fill (NaNs stay; the evaluator drops them per cell)
    - cross_median: fill each row's median
    - sector_median: fill each row's per-industry median; cells whose
      industry is unknown fall back to the row median
    """
    if method == "drop":
        return panel.copy()
    if method == "cross_median":
        return panel.apply(lambda row: row.fillna(row.median()), axis=1)
    if method == "sector_median":
        cols = panel.columns
        ind = industries.reindex(cols) if industries is not None else None
        if ind is None:
            return panel.apply(lambda row: row.fillna(row.median()), axis=1)
        out = panel.copy()
        for sec in ind.dropna().unique():
            sec_cols = ind[ind == sec].index
            for dt, row in panel.iterrows():
                vals = row[sec_cols].dropna()
                if vals.empty:
                    continue
                out.loc[dt, sec_cols] = row[sec_cols].fillna(vals.median())
        # remaining NaN (no industry peers / no value at all in the sector)
        return out.apply(lambda row: row.fillna(row.median()), axis=1)
    raise ValueError(f"unknown missing method {method!r}")
