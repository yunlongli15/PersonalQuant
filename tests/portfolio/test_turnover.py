# -*- coding: utf-8 -*-
"""Turnover (spec §24): the single fixed definition T = 0.5 * Σ|w_new -
w_old| — over candidates PLUS held names being fully sold. The
turnover-aware optimizer must reduce turnover vs MVO given the same
inputs."""

import numpy as np
import pandas as pd

from portfolio.allocator import allocate


def test_turnover_definition_exact(world, alloc_input):
    prev = pd.Series({"S00": 0.30, "S01": 0.25, "S02": 0.20,
                      "S03": 0.10, "S04": 0.05})
    r = allocate(alloc_input("equal_weight", prev=prev))
    w = r.weights
    # candidates are S00..S11; held names not in candidates (none here)
    t_expected = 0.5 * (w - prev.reindex(w.index).fillna(0.0)).abs().sum()
    assert abs(r.extras["turnover_total"] - t_expected) < 1e-9


def test_turnover_counts_dropped_holdings(world, alloc_input):
    # a held name OUTSIDE the candidate set is fully sold: its |Δw| = w_old
    prev = pd.Series({"X99": 0.30})
    r = allocate(alloc_input("equal_weight", prev=prev))
    w = r.weights
    cand_part = 0.5 * w.abs().sum()          # prev = 0 for all candidates
    held_out = 0.5 * 0.30                    # X99 fully sold
    assert abs(r.extras["turnover_total"] - (cand_part + held_out)) < 1e-9


def test_per_symbol_turnover_contributions(world, alloc_input):
    prev = pd.Series({"S00": 0.5, "S01": 0.5})
    r = allocate(alloc_input("equal_weight", prev=prev))
    tfp = r.extras["turnover_from_previous"]
    assert abs(tfp["S00"] - 0.5 * abs(r.weights["S00"] - 0.5)) < 1e-9
    assert abs(tfp["S01"] - 0.5 * abs(r.weights["S01"] - 0.5)) < 1e-9


def test_turnover_aware_reduces_turnover_vs_mvo(world, alloc_input):
    # strong previous holdings concentrated in two names: turnover-aware
    # must trade strictly less than MVO (medium lambda) on the same inputs
    prev = pd.Series({"S00": 0.40, "S01": 0.40, "S02": 0.10})
    r_ta = allocate(alloc_input("turnover_aware", prev=prev))
    r_mvo = allocate(alloc_input("mvo", prev=prev,
                                params={"lambda_tier": "medium"}))
    assert r_ta.extras["turnover_total"] < \
        r_mvo.extras["turnover_total"] + 1e-9


def test_turnover_aware_matches_prev_when_penalty_dominates(world,
                                                            alloc_input):
    # previous weights must respect max_weight (0.10) for the hugging
    # comparison to be meaningful
    prev = pd.Series({"S00": 0.095, "S01": 0.095, "S02": 0.095})
    r = allocate(alloc_input("turnover_aware", prev=prev,
                             params={"lambda_risk": 2.0, "lambda_turn": 20.0,
                                     "lambda_cost": 1.0}))
    # with a large turnover penalty the optimizer hugs the previous weights
    w = r.weights
    assert abs(w["S00"] - 0.095) < 0.06
    assert abs(w["S01"] - 0.095) < 0.06
    assert abs(w["S02"] - 0.095) < 0.06
