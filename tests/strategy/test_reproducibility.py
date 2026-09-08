# -*- coding: utf-8 -*-
"""Reproducibility: same seed + same data => identical model outputs."""

import numpy as np
import pandas as pd

from personal_quant.strategy.model import AlphaModel

PARAMS = {
    "learning_rate": 0.05,
    "num_leaves": 15,
    "n_estimators": 30,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 1,
    "num_threads": 2,
}


def _data():
    rng = np.random.RandomState(7)
    X = pd.DataFrame(rng.randn(2000, 20), columns=[f"f{i}" for i in range(20)])
    y = pd.Series(X["f0"] * 0.5 - X["f1"] * 0.3 + rng.randn(2000) * 0.1)
    return X, y


def test_same_seed_same_predictions():
    X, y = _data()
    m1 = AlphaModel(dict(PARAMS), seed=42)
    m1.fit(X.iloc[:1500], y.iloc[:1500])
    m2 = AlphaModel(dict(PARAMS), seed=42)
    m2.fit(X.iloc[:1500], y.iloc[:1500])
    p1, p2 = m1.predict(X.iloc[1500:]), m2.predict(X.iloc[1500:])
    assert np.array_equal(p1, p2), "identical seed+data must give identical predictions"


def test_different_seed_may_differ():
    X, y = _data()
    m1 = AlphaModel(dict(PARAMS), seed=1)
    m1.fit(X.iloc[:1500], y.iloc[:1500])
    m2 = AlphaModel(dict(PARAMS), seed=2)
    m2.fit(X.iloc[:1500], y.iloc[:1500])
    # different seeds typically differ; this asserts the seed is actually used
    # (not required to differ, but with these params it will)
    p1, p2 = m1.predict(X.iloc[1500:]), m2.predict(X.iloc[1500:])
    assert not np.array_equal(p1, p2)


def test_manifest_fields_defined():
    """The experiment manifest must carry the reproducibility fields."""
    import yaml
    from pathlib import Path

    cfg = yaml.safe_load(
        (Path(__file__).resolve().parents[2] / "config" / "strategy_v1.yaml")
        .read_text(encoding="utf-8")
    )
    assert cfg["model"]["seed"] is not None
    assert cfg["experiment"]["dir"]
    assert cfg["strategy"]["version"]
