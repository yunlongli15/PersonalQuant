# -*- coding: utf-8 -*-
"""Risk contributions (spec §41): marginal risk = (Σw)_i / σ_p,
component risk = w_i·(Σw)_i with Σ = σ_p², shares sum to 1."""

import numpy as np

from portfolio.risk_model import (component_risk, marginal_risk,
                                  portfolio_vol, risk_shares)


def test_component_risk_sums_to_variance(world, alloc_input):
    from portfolio.allocator import allocate

    r = allocate(alloc_input("gmv"))
    cov = alloc_input("gmv").cov
    c = component_risk(cov, r.weights)
    pv = portfolio_vol(cov, r.weights)
    assert abs(c.sum() - pv ** 2) < 1e-9


def test_risk_shares_sum_to_one(world, alloc_input):
    from portfolio.allocator import allocate

    r = allocate(alloc_input("mvo"))
    cov = alloc_input("mvo").cov
    shares = risk_shares(cov, r.weights)
    assert abs(shares.sum() - 1.0) < 1e-9
    # individual shares may be slightly negative in correlated portfolios
    # (a stock can act as a hedge) — but never wildly so
    assert (shares.abs() <= 1.0).all()


def test_marginal_risk_formula(world, alloc_input):
    from portfolio.allocator import allocate

    r = allocate(alloc_input("risk_parity"))
    cov = alloc_input("risk_parity").cov
    w = r.weights.reindex(cov.cov.columns).fillna(0.0)
    m = marginal_risk(cov, w)
    expected = (cov.cov.to_numpy() @ w.to_numpy()) / portfolio_vol(cov, w)
    assert np.allclose(m.to_numpy(), expected)


def test_risk_parity_equalizes_contribution(world, alloc_input):
    from portfolio.allocator import allocate

    r = allocate(alloc_input("risk_parity"))
    cov = alloc_input("risk_parity").cov
    shares = risk_shares(cov, r.weights)
    # contributions should be close to 1/K (SLSQP numeric tolerance)
    assert np.max(np.abs(shares.to_numpy() - 1.0 / len(shares))) < 0.05
