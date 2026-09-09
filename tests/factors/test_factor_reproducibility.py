# -*- coding: utf-8 -*-
"""Reproducibility: same inputs -> byte-identical outputs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from factors.base import FactorData
from factors.evaluator import evaluate_factor
from factors.mining import AlphaMiner
from factors.normalization import fill_missing, normalize_panel

IDX = pd.date_range("2020-01-31", periods=24, freq="ME")
SYMS = [f"{i:06d}.SH" for i in range(80)]


def make_frame(seed=7):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(rng.normal(0, 1, (24, 80)), index=IDX, columns=SYMS)


class Data:
    industries = pd.Series(dtype=object)
    financial = pd.DataFrame()


def test_normalization_deterministic():
    a = normalize_panel(make_frame(), "winsorized_zscore")
    b = normalize_panel(make_frame(), "winsorized_zscore")
    pd.testing.assert_frame_equal(a, b)


def test_fill_deterministic():
    f = make_frame()
    f.iloc[3, 5] = np.nan
    pd.testing.assert_frame_equal(
        fill_missing(f, "cross_median"), fill_missing(f, "cross_median"))


def test_evaluate_factor_deterministic():
    labels = {20: make_frame(3)}
    cfg = {"labels": {"horizons": [20], "primary_horizon": 20},
           "normalization": {"methods": ["rank", "winsorized_zscore"]},
           "missing": {"method": "sector_median"},
           "evaluation": {"min_stocks_per_date": 30}}
    f = make_frame(4)

    def compute(data, dates):
        return f

    a = evaluate_factor(Data(), "x", list(IDX), labels, config=cfg,
                        compute=compute)
    b = evaluate_factor(Data(), "x", list(IDX), labels, config=cfg,
                        compute=compute)
    # the JSON-serialized form must be identical
    import json

    assert json.dumps(a, sort_keys=True, default=str) == \
        json.dumps(b, sort_keys=True, default=str)


def test_mining_generation_deterministic_with_seed():
    atoms = {f"a{i}": make_frame(i) for i in range(6)}
    miner1 = AlphaMiner(
        {"mining": {"depth_max": 3, "max_candidates_per_generation": 1000,
                    "beam_size": 20, "score": {}}},
        atoms, pd.DatetimeIndex(IDX), {20: make_frame(9)}, seed=42)
    miner2 = AlphaMiner(
        {"mining": {"depth_max": 3, "max_candidates_per_generation": 1000,
                    "beam_size": 20, "score": {}}},
        atoms, pd.DatetimeIndex(IDX), {20: make_frame(9)}, seed=42)
    g1 = [e.render() for e in miner1.generate_depth3(
        [miner1.generate_depth2(list(atoms))[0]], list(atoms))]
    g2 = [e.render() for e in miner2.generate_depth3(
        [miner2.generate_depth2(list(atoms))[0]], list(atoms))]
    assert g1 == g2
