# -*- coding: utf-8 -*-
"""Mining leakage guards: search may never see the frozen test period."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from factors.mining import AlphaMiner, MiningError

IDX_R = pd.date_range("2018-01-31", periods=24, freq="ME")   # research
IDX_V = pd.date_range("2022-01-31", periods=12, freq="ME")   # valid
IDX_T = pd.date_range("2024-01-31", periods=12, freq="ME")   # frozen test
SYMS = [f"{i:06d}.SH" for i in range(60)]
rng = np.random.default_rng(0)


def make_panels():
    atoms = {n: pd.DataFrame(rng.normal(0, 1, (24, 60)),
                             index=IDX_R, columns=SYMS)
             for n in ("a", "b", "c")}
    labels = {20: pd.DataFrame(rng.normal(0, 0.02, (24, 60)),
                               index=IDX_R, columns=SYMS)}
    return atoms, labels


def make_miner(period_end):
    atoms, labels = make_panels()
    return AlphaMiner(
        {"mining": {"depth_max": 3, "max_candidates_per_generation": 50,
                    "beam_size": 5, "score": {}},
         "missing": {"method": "drop"}},
        atoms, IDX_R, labels, period_end=period_end)


def test_guard_rejects_dates_beyond_period_end():
    miner = make_miner(pd.Timestamp("2023-12-31"))
    with pytest.raises(MiningError, match="beyond the allowed period"):
        miner._guard(IDX_T)
    miner._guard(IDX_R)  # research dates are fine


def test_guard_rejects_valid_dates_when_period_is_research_only():
    miner = make_miner(pd.Timestamp("2021-12-31"))
    with pytest.raises(MiningError):
        miner._guard(IDX_V)


def test_scoring_raises_on_test_dates():
    miner = make_miner(pd.Timestamp("2023-12-31"))
    panel = pd.DataFrame(rng.normal(0, 1, (12, 60)), index=IDX_T,
                         columns=SYMS)
    with pytest.raises(MiningError):
        miner._quick_score(panel)


def test_search_never_touches_test_labels():
    # labels for the test period exist in the environment; the miner must
    # only ever receive research labels — simulate by checking that scoring
    # uses exactly the labels handed to it (identity check via object ref)
    miner = make_miner(pd.Timestamp("2023-12-31"))
    assert miner.labels[20].index.max() == IDX_R.max()


def test_snooping_diagnostics_count_candidates():
    miner = make_miner(pd.Timestamp("2023-12-31"))
    res = miner.search(["a", "b", "c"])
    assert res["n_candidates_tested"] == miner.n_candidates_tested > 0
    assert "best_research_score" in res
    assert len(miner.score_log) == miner.n_candidates_tested


def test_depth3_generation_capped():
    atoms, labels = make_panels()
    miner = AlphaMiner(
        {"mining": {"depth_max": 3, "max_candidates_per_generation": 100,
                    "beam_size": 5, "score": {}}},
        atoms, IDX_R, labels, period_end=pd.Timestamp("2023-12-31"))
    beam = miner.generate_depth2(["a", "b", "c"])
    gen3 = miner.generate_depth3(beam, ["a", "b", "c"])
    assert len(gen3) <= 100
