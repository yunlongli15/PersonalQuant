# -*- coding: utf-8 -*-
"""Optimizer methods when a candidate lacks enough history for the
covariance (regression: dimension mismatch between weights (K) and the
covariance (K-m) — fixed by _cov_aligned with the frozen proportional
under-invest rule: dropped names stay in cash)."""

import numpy as np
import pandas as pd
import pytest

from portfolio.allocator import AllocationFailure, allocate
from portfolio.constraints import PortfolioConstraints
from portfolio.covariance import estimate_covariance
from personal_quant.strategy.costs import TransactionCostModel

N, T = 12, 80


@pytest.fixture
def sparse_world():
    np.random.seed(1)
    dates = pd.date_range("2023-01-02", periods=T, freq="B")
    rets = pd.DataFrame(np.random.randn(T, N) * 0.02, index=dates,
                        columns=[f"S{i}" for i in range(N)])
    close = (1 + rets).cumprod()
    close.loc[close.index[:-5], "S11"] = np.nan   # sparse -> excluded
    preds = pd.Series(np.linspace(0.04, 0.01, N), index=close.columns)
    inds = pd.Series([f"G{i % 6}" for i in range(N)], index=close.columns)
    cons = PortfolioConstraints(max_weight=0.10, sector_cap=0.20,
                                invest_target=0.95, cash_buffer=0.05)
    cost = TransactionCostModel()

    def make(method="gmv", params=None):
        cov = estimate_covariance(close, close.columns, close.index[-1], 60)
        cand = pd.DataFrame({"prediction": preds,
                             "vol": cov.vols.reindex(preds.index),
                             "industry": inds, "liq_cap": np.nan})
        from portfolio.allocator import AllocationInput
        return AllocationInput(
            date=close.index[-1], candidates=cand, cov=cov,
            prev_weights=pd.Series(dtype=float), constraints=cons,
            cost_model=cost, method=method, params=params or {})

    return make


@pytest.mark.parametrize("method,params", [
    ("gmv", {}), ("mvo", {"lambda_tier": "medium"}),
    ("risk_parity", {}), ("turnover_aware", {})])
def test_sparse_candidate_excluded_not_crash(method, params, sparse_world):
    r = allocate(sparse_world(method, params))
    assert r.optimizer_status == "optimal"
    assert "S11" not in r.weights.index        # no covariance -> stays cash
    # frozen proportional rule: target scaled by the surviving fraction
    assert abs(r.weights.sum() - 0.95 * 11 / 12) < 1e-6
    assert r.weights.max() <= 0.10 + 1e-6


def test_all_sparse_falls_back(sparse_world):
    inp = sparse_world("gmv")
    from portfolio.allocator import _cov_aligned

    inp.cov.cov = inp.cov.cov.iloc[0:0, 0:0]     # empty covariance
    with pytest.raises(AllocationFailure):
        _cov_aligned(inp)
    # through allocate(): the chain falls back to direct methods, which
    # do not need the covariance
    r = allocate(inp)
    assert r.optimizer_status.startswith("fallback_")
    assert abs(r.weights.sum() - 0.95) < 1e-6


def test_direct_methods_keep_full_candidate_set(sparse_world):
    for method in ("equal_weight", "score_weight", "inverse_vol"):
        r = allocate(sparse_world(method))
        assert len(r.weights) == N               # direct methods use all K
        assert abs(r.weights.sum() - 0.95) < 1e-6
