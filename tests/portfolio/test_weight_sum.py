# -*- coding: utf-8 -*-
"""Every allocation method returns weights that sum to invest_target
(spec §42: sum(weights) = invest_target ± tolerance)."""

import pytest

from portfolio.allocator import allocate

METHODS = ["equal_weight", "score_weight", "inverse_vol", "gmv", "mvo",
           "risk_parity", "turnover_aware"]


@pytest.mark.parametrize("method", METHODS)
def test_weights_sum_to_invest_target(method, alloc_input):
    r = allocate(alloc_input(method))
    assert abs(r.weights.sum() - 0.95) < 1e-6
    assert (r.weights > 0).all()


@pytest.mark.parametrize("method", METHODS)
def test_scaled_target_small_candidate_set(method, alloc_input, world):
    # scarce candidates: the engine scales the effective target to
    # n * invest_target/top_k (frozen under-invest semantics)
    from portfolio.backtest import effective_target

    eff = effective_target(2, 20, 0.95)
    assert abs(eff - 0.095) < 1e-9
    inp = alloc_input(method)
    from dataclasses import replace

    cons = replace(inp.constraints, invest_target=eff, cash_buffer=1.0 - eff)
    inp.constraints = cons
    inp.candidates = inp.candidates.iloc[:2]
    # the engine computes the covariance on the candidate set only
    from portfolio.covariance import estimate_covariance

    inp.cov = estimate_covariance(world.close, inp.candidates.index,
                                  world.dates[-1], 60, "sample")
    inp.candidates["vol"] = inp.cov.vols.reindex(inp.candidates.index)
    r = allocate(inp)
    assert abs(r.weights.sum() - eff) < 1e-6
    # per-pick weight for equal weight stays invest_target/top_k
    if method == "equal_weight":
        assert abs(r.weights.iloc[0] - 0.0475) < 1e-9


def test_effective_target_bounds():
    from portfolio.backtest import effective_target

    assert effective_target(20, 20, 0.95) == 0.95
    assert effective_target(30, 20, 0.95) == 0.95   # capped by target
    assert effective_target(0, 20, 0.95) == 0.0
    assert effective_target(5, 0, 0.95) == 0.0
