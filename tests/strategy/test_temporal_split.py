# -*- coding: utf-8 -*-
"""Temporal split tests: train < valid < test, strictly time-forward."""

import pytest
import yaml

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "strategy_v1.yaml"


def load_config():
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def test_split_ordering():
    cfg = load_config()
    ts = cfg["time_split"]
    assert ts["train"][1] < ts["valid"][0], "train must end before validation starts"
    assert ts["valid"][1] < ts["test"][0], "validation must end before test starts"
    assert ts["test"][1] < ts["paper_live_start"], "test must end before paper live"


def test_no_overlap():
    cfg = load_config()
    ts = cfg["time_split"]
    import pandas as pd

    train = pd.date_range(*ts["train"])
    valid = pd.date_range(*ts["valid"])
    test = pd.date_range(*ts["test"])
    assert not train.intersection(valid).size
    assert not valid.intersection(test).size


def test_training_frequency_supported():
    cfg = load_config()
    assert cfg["model"]["training_frequency"] in ("quarterly", "monthly", "yearly")


def test_no_random_split_indicator():
    cfg = load_config()
    # the config must not carry any random-split option
    assert "random" not in str(cfg["time_split"]).lower()
