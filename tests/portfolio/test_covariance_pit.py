# -*- coding: utf-8 -*-
"""Covariance PIT (STEP 6 spec §28): an estimate at T uses only bars <= T,
and is invariant to whatever happens after T."""

import numpy as np
import pandas as pd

from portfolio.covariance import (build_returns, estimate_covariance,
                                  is_stable)


def test_estimate_invariant_to_future_data(world):
    d = world.dates[60]
    full = world.close                 # includes rows after d
    trunc = world.close.loc[:d]
    c1 = estimate_covariance(full, full.columns, d, 40, "sample")
    c2 = estimate_covariance(trunc, trunc.columns, d, 40, "sample")
    assert c1.cov.equals(c2.cov)


def test_poisoned_future_does_not_leak(world):
    d = world.dates[60]
    clean = estimate_covariance(world.close, world.close.columns, d, 40)
    poisoned = world.close.copy()
    poisoned.loc[poisoned.index > d, :] *= 1000.0
    c = estimate_covariance(poisoned, poisoned.columns, d, 40)
    assert np.allclose(c.cov.to_numpy(), clean.cov.to_numpy())


def test_window_bound(world):
    d = world.dates[79]
    ret = build_returns(world.close, world.close.columns, d, 20)
    assert len(ret) <= 20
    assert ret.index.max() <= d


def test_sparse_symbol_excluded(world):
    # S00 gets only 5 non-NaN returns in the window -> excluded
    close = world.close.copy()
    close.loc[close.index[:-5], "S00"] = np.nan
    cov = estimate_covariance(close, close.columns, close.index[-1], 60)
    assert "S00" in cov.excluded
    assert "S00" not in cov.cov.columns


def test_diagnostics_psd_and_symmetric(world):
    cov = estimate_covariance(world.close, world.close.columns,
                              world.dates[-1], 60)
    d = cov.diagnostics
    assert d["symmetric_err"] < 1e-8
    assert d["min_eigenvalue"] >= -1e-8
    assert d["min_diag"] > 0
    assert d["n_nan"] == 0
    assert is_stable(d)
    assert (cov.vols > 0).all()


def test_ewma_psd(world):
    cov = estimate_covariance(world.close, world.close.columns,
                              world.dates[-1], 60, "ewma", halflife=30)
    assert cov.method_used == "ewma"
    d = cov.diagnostics
    assert d["min_eigenvalue"] >= -1e-8


def test_repair_on_unstable_matrix():
    # a degenerate two-stock panel (perfect correlation, one near-zero
    # variance stock) forces the repair chain; never a silent pass-through
    n = 40
    idx = pd.date_range("2023-01-02", periods=n, freq="B")
    r = pd.DataFrame({"A": np.random.randn(n) * 0.02,
                      "B": 0.0}, index=idx)
    close = (1 + r).cumprod()
    cov = estimate_covariance(close, ["A", "B"], idx[-1], 40, "sample")
    # B has zero variance: either repaired or excluded, never an unstable
    # matrix returned as usable
    if "B" in cov.cov.columns:
        assert cov.repaired or is_stable(cov.diagnostics)
    assert cov.reason is None or "unstable" in cov.reason
