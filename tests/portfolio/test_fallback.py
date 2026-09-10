# -*- coding: utf-8 -*-
"""Fallback chain (spec §44): method -> inverse_vol -> equal_weight, with
optimizer_status + fallback_reason recorded; never garbage weights."""

import numpy as np
import pandas as pd
import pytest

from portfolio.allocator import AllocationFailure, allocate
from portfolio.constraints import PortfolioConstraints


def test_nan_covariance_falls_back_to_inverse_vol(world, alloc_input):
    inp = alloc_input("gmv")
    inp.cov.cov.iloc[0, 0] = np.nan
    r = allocate(inp)
    assert r.optimizer_status == "fallback_inverse_vol"
    assert "gmv" in r.fallback_reason
    assert abs(r.weights.sum() - 0.95) < 1e-6
    assert r.weights.max() <= 0.10 + 1e-6


def test_mvo_infeasible_falls_back_chain(world, alloc_input):
    # sector cap 0.10 x 6 industries = 0.60 < 0.95: mvo and inverse_vol are
    # infeasible; the chain lands on equal_weight (the frozen baseline,
    # which does not enforce sector caps) and records the reason
    cons = PortfolioConstraints(max_weight=0.10, sector_cap=0.10,
                                invest_target=0.95)
    r = allocate(alloc_input("mvo", cons=cons))
    assert r.optimizer_status == "fallback_equal_weight"
    assert "mvo" in r.fallback_reason
    assert "inverse_vol" in r.fallback_reason
    assert abs(r.weights.sum() - 0.95) < 1e-6


def test_everything_infeasible_raises_with_chain(world, alloc_input):
    # per-stock cap 0.02 x 12 = 0.24 < 0.95: even equal_weight is
    # infeasible -> AllocationFailure with the whole chain recorded
    cons = PortfolioConstraints(max_weight=0.02, sector_cap=0.20,
                                invest_target=0.95)
    with pytest.raises(AllocationFailure) as ei:
        allocate(alloc_input("gmv", cons=cons))
    msg = str(ei.value)
    assert "gmv" in msg and "inverse_vol" in msg and "equal_weight" in msg


def test_all_nan_vol_still_yields_equal_weight(world, alloc_input):
    inp = alloc_input("inverse_vol")
    inp.candidates["vol"] = np.nan
    r = allocate(inp)
    assert abs(r.weights.sum() - 0.95) < 1e-6
    assert np.allclose(r.weights.to_numpy(), 0.95 / 12)


def test_slsqp_garbage_detected(world, alloc_input):
    # poison the optimizer objective through a degenerate covariance:
    # zero variance for every stock -> objective NaN territory
    inp = alloc_input("gmv")
    inp.cov.cov.iloc[:, :] = 0.0
    r = allocate(inp)
    # either an optimal solve on the degenerate matrix or a fallback —
    # but the weights must always be valid
    assert abs(r.weights.sum() - 0.95) < 1e-6
    assert r.weights.max() <= 0.10 + 1e-6
    assert r.optimizer_status in ("optimal", "fallback_inverse_vol",
                                  "fallback_equal_weight")
    assert r.fallback_reason is None or isinstance(r.fallback_reason, str)
