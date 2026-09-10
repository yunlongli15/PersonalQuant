# -*- coding: utf-8 -*-
"""Sector exposure cap (spec §16): single industry <= 20% hard cap for
P1-P6; P0 (frozen equal-weight baseline) is exempt and must match the
frozen allocation exactly."""

import numpy as np
import pandas as pd
import pytest

from portfolio.allocator import AllocationFailure, allocate
from portfolio.constraints import PortfolioConstraints

METHODS = ["score_weight", "inverse_vol", "gmv", "mvo", "risk_parity",
           "turnover_aware"]


@pytest.mark.parametrize("method", METHODS)
def test_sector_cap_enforced(method, alloc_input, world):
    r = allocate(alloc_input(method))
    for g in world.inds.unique():
        assert r.weights.groupby(world.inds).sum()[g] <= 0.20 + 1e-6


def test_equal_weight_bypasses_sector_cap(world, alloc_input):
    # P0 = frozen baseline: pure equal weight, no sector redistribution
    inp = alloc_input("equal_weight")
    r = allocate(inp)
    w = r.weights
    assert np.allclose(w.to_numpy(), 0.95 / 12)


def test_equal_weight_with_heavy_concentration_stays_equal(world,
                                                           alloc_input):
    # even when predictions concentrate in one industry, P0 keeps 1/K
    preds = world.preds.copy()
    preds.loc[world.inds == "G0"] = 0.9
    inp = alloc_input("equal_weight", preds=preds)
    r = allocate(inp)
    assert np.allclose(r.weights.to_numpy(), 0.95 / 12)


def test_infeasible_sector_cap_falls_back_to_baseline(world, alloc_input):
    # sector cap 0.10 x 6 industries = 0.60 < 0.95: the optimizer methods
    # are infeasible; the chain lands on the frozen equal-weight baseline
    # (which does not enforce sector caps) and records the reason — never
    # garbage weights
    cons = PortfolioConstraints(max_weight=0.10, sector_cap=0.10,
                                invest_target=0.95)
    r = allocate(alloc_input("gmv", cons=cons))
    assert r.optimizer_status == "fallback_equal_weight"
    assert "gmv" in r.fallback_reason
    assert abs(r.weights.sum() - 0.95) < 1e-6
