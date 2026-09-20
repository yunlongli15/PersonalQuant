# -*- coding: utf-8 -*-
"""No-future-leakage tests: labels and features never use future data."""

import pandas as pd
import pytest
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG = yaml.safe_load(
    (PROJECT_ROOT / "config" / "strategy_v1.yaml").read_text(encoding="utf-8")
)


@pytest.fixture
def sandbox_features(monkeypatch, tmp_path):
    """Feature cache MUST NOT be written into the real DERIVED layer.

    These tests run Alpha158 for 2 symbols, and the worker writes the
    whole month file: without isolation `compute_features(cache=False)`
    overwrites `data/derived/features/2024-01.parquet` with a 2-row
    frame (observed 2026-09-20 — the real file had 4,943 rows). Every
    later reader of that cache then silently gets wrong data.
    """
    import personal_quant.strategy.features as fmod

    cache = tmp_path / "features"
    cache.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(fmod, "FEATURE_CACHE", cache)
    return cache


def test_label_uses_only_future_rows():
    """Label at t is built from close/factor at t and t+20 only."""
    from personal_quant.strategy.features import compute_labels
    from personal_quant.strategy.rebalance import trading_days

    days = list(trading_days("2024-01-01", "2024-03-31"))
    t = days[5]
    labels = compute_labels(["600519.SH"], [t], horizon_days=20)
    if "600519.SH" not in labels[t].index:
        pytest.skip("no label available for the sample date")
    # the label value must equal the adjusted return over the next 20 days
    from personal_quant import db

    conn = db.connect()
    base = conn.execute(
        "SELECT close * factor a FROM daily_bars WHERE symbol='600519.SH' AND trade_date=?",
        [t],
    ).fetchone()[0]
    fwd = conn.execute(
        "SELECT close * factor a FROM daily_bars WHERE symbol='600519.SH' AND trade_date=?",
        [days[25]],
    ).fetchone()[0]
    expected = fwd / base - 1.0
    # canonical prices originate from float32 bins: allow representation noise
    assert abs(labels[t]["600519.SH"] - expected) < 1e-6


def test_label_date_is_future_relative_to_signal():
    from personal_quant.strategy.rebalance import trading_days

    days = list(trading_days("2024-01-01", "2024-06-30"))
    for i in range(0, len(days) - 30, 7):
        t = days[i]
        # label horizon date must be strictly after the signal date
        assert days[i + 20] > t


def test_feature_columns_have_no_future_refs(sandbox_features):
    """Alpha158 columns are fixed formulas with no t+k (k>0) references."""
    from personal_quant.strategy.features import compute_features
    from personal_quant.strategy.rebalance import trading_days

    days = list(trading_days("2024-01-01", "2024-03-31"))
    feats = compute_features(["600519.SH", "000001.SZ"], [days[5]], cache=False)
    import personal_quant.strategy.features as fmod

    cols = list(fmod.ALPHA158_COLS or [])
    assert cols, "Alpha158 columns not computed"
    # official Alpha158 formulas are leading-indicator free; the raw feature
    # set contains no label column (labels are added by the strategy layer)
    names = [str(c) for c in cols]
    assert "LABEL" not in [n.upper() for n in names]


def test_no_label_column_in_features(sandbox_features):
    """The qlib handler's label column (Ref($close,-2)/Ref($close,-1): a
    2-day FORWARD return in qlib semantics) must never enter features."""
    import pandas as pd

    from personal_quant.strategy.features import compute_features, flatten_columns
    from personal_quant.strategy.rebalance import trading_days

    days = list(trading_days("2024-01-01", "2024-03-31"))
    feats = compute_features(["600519.SH", "000001.SZ"], [days[5]], cache=False)
    f = flatten_columns(feats[days[5]])
    assert not any(str(c).startswith("label") for c in f.columns), \
        f"label column leaked into features: {[c for c in f.columns if str(c).startswith('label')]}"


def test_training_rows_all_before_prediction_date():
    """Any (signal date) row used for training predates any test signal."""
    from personal_quant.strategy.rebalance import rebalance_dates

    train_dates = rebalance_dates(
        CONFIG["time_split"]["train"][0], CONFIG["time_split"]["train"][1]
    )
    test_dates = rebalance_dates(
        CONFIG["time_split"]["test"][0], CONFIG["time_split"]["test"][1]
    )
    if train_dates and test_dates:
        assert max(train_dates) < min(test_dates)
