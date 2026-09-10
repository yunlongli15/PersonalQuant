# -*- coding: utf-8 -*-
"""Reproducibility: identical inputs -> identical covariance, identical
weights for every method (deterministic SLSQP with fixed warm starts).
The engine-level anchor run (equal_weight reproducing strategy_v1_news at
drift 0.0000) covers the full-pipeline reproducibility."""

import numpy as np
import pytest

from portfolio.allocator import allocate
from portfolio.covariance import estimate_covariance

METHODS = ["equal_weight", "score_weight", "inverse_vol", "gmv", "mvo",
           "risk_parity", "turnover_aware"]


def test_covariance_deterministic(world):
    c1 = estimate_covariance(world.close, world.close.columns,
                             world.dates[-1], 60, "sample")
    c2 = estimate_covariance(world.close, world.close.columns,
                             world.dates[-1], 60, "sample")
    assert c1.cov.equals(c2.cov)
    c3 = estimate_covariance(world.close, world.close.columns,
                             world.dates[-1], 60, "ewma", halflife=30)
    c4 = estimate_covariance(world.close, world.close.columns,
                             world.dates[-1], 60, "ewma", halflife=30)
    assert c3.cov.equals(c4.cov)


@pytest.mark.parametrize("method", METHODS)
def test_weights_deterministic(method, alloc_input, world):
    prev = world.preds.iloc[:3].rename({})
    prev = prev * 0.9 / prev.sum() * 0.3
    r1 = allocate(alloc_input(method, prev=prev))
    r2 = allocate(alloc_input(method, prev=prev))
    assert r1.weights.equals(r2.weights)
    assert r1.optimizer_status == r2.optimizer_status
    assert r1.fallback_reason == r2.fallback_reason
    assert np.allclose(r1.extras["portfolio_vol"],
                       r2.extras["portfolio_vol"])
