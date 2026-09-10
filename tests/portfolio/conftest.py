# -*- coding: utf-8 -*-
"""Shared synthetic fixtures for tests/portfolio/.

All tests are DB-free: prices/returns are synthetic wide panels, and the
DuckDB layer is never touched (portfolio research may run while the
financial fetcher holds the DuckDB lock).
"""

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from portfolio.constraints import PortfolioConstraints
from personal_quant.strategy.costs import TransactionCostModel

N = 12          # 12 stocks, 6 industries -> sector cap 0.20 feasible
T = 80


@pytest.fixture
def world():
    np.random.seed(42)
    dates = pd.date_range("2023-01-02", periods=T, freq="B")
    rets = pd.DataFrame(np.random.randn(T, N) * 0.02, index=dates,
                        columns=[f"S{i:02d}" for i in range(N)])
    close = (1 + rets).cumprod()
    preds = pd.Series(np.linspace(0.04, 0.01, N), index=close.columns)
    inds = pd.Series([f"G{i % 6}" for i in range(N)], index=close.columns)
    cons = PortfolioConstraints(max_weight=0.10, sector_cap=0.20,
                                invest_target=0.95, cash_buffer=0.05)
    return SimpleNamespace(dates=dates, close=close, preds=preds, inds=inds,
                           cons=cons, cost=TransactionCostModel())


@pytest.fixture
def alloc_input(world):
    """Factory: build an AllocationInput for a method over the world."""
    from portfolio.allocator import AllocationInput
    from portfolio.covariance import estimate_covariance

    cov = estimate_covariance(world.close, world.close.columns,
                              world.dates[-1], window=60, method="sample")

    def _make(method="gmv", params=None, prev=None, cons=None,
              close=None, preds=None, end_date=None):
        c = close if close is not None else world.close
        p = preds if preds is not None else world.preds
        ed = pd.Timestamp(end_date) if end_date is not None else c.index[-1]
        cv = cov if close is None and end_date is None else \
            estimate_covariance(c, c.columns, ed, window=60, method="sample")
        cand = pd.DataFrame({
            "prediction": p, "vol": cv.vols.reindex(p.index),
            "industry": world.inds.reindex(p.index), "liq_cap": np.nan,
        })
        return AllocationInput(
            date=ed, candidates=cand, cov=cv,
            prev_weights=(prev if prev is not None
                          else pd.Series(dtype=float)),
            constraints=cons if cons is not None else world.cons,
            cost_model=world.cost, method=method,
            params=params if params is not None else {},
        )

    return _make
