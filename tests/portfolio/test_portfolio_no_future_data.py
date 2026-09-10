# -*- coding: utf-8 -*-
"""No future data (spec §28): allocation at T is invariant to what
happens after T. Poisoning the future must not move a single weight."""

import numpy as np
import pytest

from portfolio.allocator import allocate

METHODS = ["equal_weight", "score_weight", "inverse_vol", "gmv", "mvo",
           "risk_parity", "turnover_aware"]


@pytest.mark.parametrize("method", METHODS)
def test_allocation_invariant_to_future_poisoning(method, alloc_input,
                                                  world):
    d = world.dates[60]
    clean_close = world.close.loc[:d]
    inp = alloc_input(method, close=clean_close, end_date=d)

    poisoned = world.close.copy()
    # absurd future prices (x1000) after T must not change anything
    poisoned.loc[poisoned.index > d, :] *= 1000.0
    inp2 = alloc_input(method, close=poisoned, end_date=d)

    r1 = allocate(inp)
    r2 = allocate(inp2)
    assert np.allclose(r1.weights.reindex(r2.weights.index).to_numpy(),
                       r2.weights.to_numpy())


def test_vol_uses_only_past(world):
    from portfolio.covariance import estimate_covariance

    d = world.dates[60]
    clean = estimate_covariance(world.close.loc[:d], world.close.columns,
                                d, 40)
    poisoned = world.close.copy()
    poisoned.loc[poisoned.index > d, :] *= 1000.0
    c = estimate_covariance(poisoned, poisoned.columns, d, 40)
    assert np.allclose(c.vols.to_numpy(), clean.vols.to_numpy())
    # a later date uses a different window -> different vols
    later = estimate_covariance(world.close, world.close.columns,
                                world.dates[79], 40)
    assert not np.allclose(later.vols.to_numpy(), clean.vols.to_numpy())
