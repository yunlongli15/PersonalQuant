# -*- coding: utf-8 -*-
"""§3：forward_predictions 的字段契约。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

from paper_live.alerts import check_alerts
from paper_live.engine import run_day
from paper_live.store import ForwardStore

REQUIRED = ["prediction_date", "signal_date", "symbol", "predicted_return",
            "rank", "target_weight", "model_version", "feature_version",
            "strategy_version", "data_snapshot_id"]


def _predictions(cfg, provider, date="2026-09-30", force=True):
    store = ForwardStore(Path(cfg["paper_live"]["paths"]["root"]),
                         cfg["paper_live"]["forward_start_date"])
    run_day(pd.Timestamp(date), cfg, store, provider, force_rebalance=force,
            alerts_fn=check_alerts)
    return store.read_frame("predictions", pd.Timestamp(date))


def test_prediction_table_has_the_contracted_columns(pl_cfg, fake_provider):
    df = _predictions(pl_cfg, fake_provider)
    for col in REQUIRED:
        assert col in df.columns, col


def test_rank_is_one_based_and_dense(pl_cfg, fake_provider):
    df = _predictions(pl_cfg, fake_provider)
    r = df["rank"].sort_values().to_numpy()
    assert r.min() == 1
    assert r.max() == len(df)
    assert list(r) == list(range(1, len(df) + 1))


def test_predicted_return_is_finite(pl_cfg, fake_provider):
    df = _predictions(pl_cfg, fake_provider)
    assert df["predicted_return"].notna().all()
    assert df["predicted_return"].abs().max() < 1e6


def test_target_weight_marks_exactly_top_k_on_rebalance(pl_cfg, fake_provider):
    """调仓日：恰好 top_k 只被赋正权重，其余显式为 0（不是 NaN——
    "目标是不持有"本身是有意义的信息）。"""
    df = _predictions(pl_cfg, fake_provider, force=True)
    k = pl_cfg["paper_live"]["portfolio"]["top_k"]
    assert (df["target_weight"] > 0).sum() == k
    assert (df["target_weight"] == 0).sum() == len(df) - k
    assert df["target_weight"].notna().all()


def test_target_weight_is_absent_on_monitoring_days(pl_cfg, fake_provider):
    df2 = _predictions(pl_cfg, fake_provider, date="2026-10-15", force=False)
    assert df2["target_weight"].isna().all()


def test_versions_are_stamped_on_every_row(pl_cfg, fake_provider):
    df = _predictions(pl_cfg, fake_provider)
    s = pl_cfg["paper_live"]
    assert (df["strategy_version"] == s["strategy_version"]).all()
    assert (df["model_version"] == "s3").all()
    assert (df["feature_version"] == "alpha158").all()
    assert df["data_snapshot_id"].notna().all()
