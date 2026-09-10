# -*- coding: utf-8 -*-
"""Constraint enforcement: water-fill + finalize_weights (spec §16/§17)."""

import numpy as np
import pandas as pd
import pytest

from portfolio.constraints import PortfolioConstraints
from portfolio.optimizer import (AllocationFailure, _waterfill,
                                 finalize_weights)


def test_waterfill_up_and_down():
    caps = np.array([0.2, 0.2, 0.2])
    up = _waterfill(np.array([0.1, 0.1, 0.1]), caps, 0.45)
    assert abs(up.sum() - 0.45) < 1e-9
    assert (up <= caps + 1e-12).all()
    down = _waterfill(np.array([0.3, 0.3, 0.3]), caps, 0.45)
    assert abs(down.sum() - 0.45) < 1e-9
    assert (down <= caps + 1e-12).all()


def test_waterfill_saturates_when_infeasible():
    caps = np.array([0.1, 0.1])
    w = _waterfill(np.array([0.5, 0.5]), caps, 0.95)
    assert abs(w.sum() - 0.2) < 1e-9   # saturated at the caps, caller detects


def test_finalize_respects_max_weight_and_sum(world):
    raw = pd.Series(np.full(12, 0.2), index=world.close.columns)
    w = finalize_weights(raw, world.cons)
    assert abs(w.sum() - world.cons.invest_target) < 1e-6
    assert w.max() <= world.cons.max_weight + 1e-6


def test_finalize_sector_cap_exact(world):
    # 6 industries: raw weights concentrate everything into G0's two names
    raw = pd.Series(1.0, index=world.close.columns)
    raw.loc[world.inds == "G0"] = 10.0
    w = finalize_weights(raw, world.cons, world.inds)
    assert abs(w.sum() - world.cons.invest_target) < 1e-6
    for g in world.inds.unique():
        assert w.groupby(world.inds).sum()[g] <= \
            world.cons.sector_cap + 1e-6


def test_finalize_infeasible_raises(world):
    cons = PortfolioConstraints(max_weight=0.10, sector_cap=0.10,
                                invest_target=0.95)
    raw = pd.Series(1.0, index=world.close.columns)
    with pytest.raises(AllocationFailure):
        finalize_weights(raw, cons, world.inds)


def test_finalize_liquidity_cap(world):
    liq = pd.Series(0.10, index=world.close.columns)
    liq.loc[world.inds == "G0"] = 0.08        # binds for G0's two names
    raw = pd.Series(1.0, index=world.close.columns)
    w = finalize_weights(raw, world.cons, world.inds, liq)
    assert abs(w.sum() - world.cons.invest_target) < 1e-6
    assert w.loc[world.inds == "G0"].max() <= 0.08 + 1e-6
    assert w.max() <= 0.10 + 1e-6


def test_finalize_liquidity_infeasible_raises(world):
    liq = pd.Series(0.02, index=world.close.columns)   # 12 x 0.02 = 0.24 < 0.95
    raw = pd.Series(1.0, index=world.close.columns)
    with pytest.raises(AllocationFailure):
        finalize_weights(raw, world.cons, world.inds, liq)
