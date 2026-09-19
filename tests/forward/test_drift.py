# -*- coding: utf-8 -*-
"""§20-§23：漂移只监控，绝不自动修复。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from paper_live import drift as D
from paper_live.config import load_config


def test_strategy_drift_is_ok_on_the_frozen_config():
    r = D.strategy_drift(load_config())
    assert r["status"] == "OK"
    assert r["drift"] is False


def test_strategy_drift_detects_a_moved_hash():
    cfg = load_config()
    cfg["paper_live"] = dict(cfg["paper_live"])
    cfg["paper_live"]["freeze"] = dict(cfg["paper_live"]["freeze"])
    cfg["paper_live"]["freeze"]["feature_pack_0"] = "0" * 64
    r = D.strategy_drift(cfg)
    assert r["status"] == "DRIFT_DETECTED"
    assert "feature_pack_0" in r["mismatches"]


def test_strategy_drift_reports_unfrozen():
    cfg = load_config()
    cfg["paper_live"] = dict(cfg["paper_live"])
    cfg["paper_live"]["freeze"] = {}
    assert D.strategy_drift(cfg)["status"] == "UNFROZEN"


def test_model_drift_flags_a_shifted_distribution():
    rng = np.random.default_rng(0)
    base = pd.Series(rng.normal(0, 1, 5000))
    same = pd.Series(rng.normal(0, 1, 500))
    far = pd.Series(rng.normal(6, 1, 500))
    assert D.model_drift(same, base)["status"] == "OK"
    assert D.model_drift(far, base)["status"] == "MODEL_DRIFT_WARNING"


def test_model_drift_without_baseline_says_so():
    r = D.model_drift(pd.Series([1.0, 2.0]), None)
    assert r["status"] == "NO_BASELINE"


def test_model_drift_never_fixes_anything():
    """漂移检查的返回里不得出现任何"已调整/已重训"的动作。"""
    r = D.model_drift(pd.Series(np.linspace(0, 1, 100)),
                      pd.Series(np.linspace(0, 1, 100)))
    for k in r:
        assert "retrain" not in k and "adjust" not in k
    assert r["status"] in ("OK", "MODEL_DRIFT_WARNING", "NO_BASELINE",
                           "NO_DATA")


def test_prediction_concentration_warns_on_an_outlier():
    s = pd.Series(np.concatenate([[100.0], np.zeros(199)]))
    r = D.prediction_concentration(s, top1_z_threshold=3.0)
    assert r["status"] == "CONCENTRATION_WARNING"
    assert r["top1_z"] > 3


def test_news_drift_reports_shifted_factors():
    base = {"news_count": {"mean": 1.0, "std": 0.2}}
    assert D.news_drift({"news_count": 1.1}, base)["status"] == "OK"
    assert D.news_drift({"news_count": 5.0}, base)["status"] == \
        "NEWS_DRIFT_WARNING"


def test_news_drift_without_baseline_says_so():
    assert D.news_drift({"a": 1.0}, {})["status"] == "NO_BASELINE"


def test_data_drift_flags_a_big_change():
    base = {"n_symbols": 3000, "feature_missing_rate": 0.01}
    assert D.data_drift(dict(base), base)["status"] == "OK"
    assert D.data_drift({"n_symbols": 100, "feature_missing_rate": 0.01},
                        base)["status"] == "DATA_QUALITY_WARNING"
