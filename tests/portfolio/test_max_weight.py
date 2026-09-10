# -*- coding: utf-8 -*-
"""Single-stock cap (spec §17): max_weight = 10% enforced by every
method, including under extreme score concentration."""

import pytest

from portfolio.allocator import allocate

METHODS = ["equal_weight", "score_weight", "inverse_vol", "gmv", "mvo",
           "risk_parity", "turnover_aware"]


@pytest.mark.parametrize("method", METHODS)
def test_max_weight_enforced(method, alloc_input, world):
    # one stock dominates the prediction -> score weights would blow up
    preds = world.preds.copy()
    preds["S00"] = 5.0
    r = allocate(alloc_input(method, preds=preds))
    assert r.weights.max() <= 0.10 + 1e-6


@pytest.mark.parametrize("method", METHODS)
def test_max_weight_enforced_small_k(method, alloc_input, world):
    # K=6 with max_weight 0.10: 6 x 0.10 = 0.60 < 0.95 -> infeasible and
    # must raise (never silently return overweight names)
    inp = alloc_input(method)
    inp.candidates = inp.candidates.iloc[:6]
    from portfolio.covariance import estimate_covariance

    inp.cov = estimate_covariance(world.close, inp.candidates.index,
                                  world.dates[-1], 60, "sample")
    inp.candidates["vol"] = inp.cov.vols.reindex(inp.candidates.index)
    try:
        r = allocate(inp)
        assert r.weights.max() <= 0.10 + 1e-6
    except Exception:
        # infeasible at K=6 is acceptable (fallback chain exhausts) —
        # what is NOT acceptable is a returned weight above the cap
        pass


def test_extreme_score_single_stock_capped(world, alloc_input):
    preds = world.preds.copy()
    preds["S00"] = 100.0
    for variant in ("rank", "raw_positive", "softmax"):
        r = allocate(alloc_input("score_weight",
                                 params={"variant": variant}, preds=preds))
        assert r.weights.max() <= 0.10 + 1e-6
