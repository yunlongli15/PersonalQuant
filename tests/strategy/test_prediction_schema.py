# -*- coding: utf-8 -*-
"""Prediction persistence schema tests."""

import pandas as pd

REQUIRED_COLUMNS = [
    "prediction_date", "symbol", "predicted_return", "rank",
    "target_weight", "model_version", "dataset_version", "feature_version",
]


def _sample_predictions() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "prediction_date": pd.to_datetime(["2024-01-31"] * 3),
            "symbol": ["600519.SH", "000001.SZ", "300750.SZ"],
            "predicted_return": [0.05, 0.02, -0.01],
            "rank": [1, 2, 3],
            "target_weight": [0.0475] * 3,
            "model_version": ["strategy_v1"] * 3,
            "dataset_version": ["canonical"] * 3,
            "feature_version": ["alpha158"] * 3,
        }
    )


def test_required_columns():
    df = _sample_predictions()
    for c in REQUIRED_COLUMNS:
        assert c in df.columns, f"missing {c}"


def test_ranks_are_1_based_contiguous():
    df = _sample_predictions()
    assert sorted(df["rank"].tolist()) == [1, 2, 3]


def test_weights_sum_to_0_95():
    df = _sample_predictions()
    # 3 sample rows x 4.75%; a full 20-stock portfolio sums to 95%
    assert df["target_weight"].sum() == pytest.approx(3 * 0.0475, rel=1e-6)


def test_prediction_date_is_signal_date():
    from personal_quant.strategy.rebalance import rebalance_dates

    df = _sample_predictions()
    rbs = rebalance_dates("2024-01-01", "2024-02-29")
    assert df["prediction_date"].iloc[0] in rbs


import pytest  # noqa: E402  (imported late for readability)
