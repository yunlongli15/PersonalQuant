# -*- coding: utf-8 -*-
"""Position sizing: equal weights, cash buffer, A-share 100-share lots."""

import math

import pytest
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG = yaml.safe_load(
    (PROJECT_ROOT / "config" / "strategy_v1.yaml").read_text(encoding="utf-8")
)

LOT = CONFIG["execution"]["lot_size"]
TOP_K = CONFIG["portfolio"]["top_k"]
BUFFER = CONFIG["portfolio"]["cash_buffer"]


def test_target_weights_sum():
    w = (1.0 - BUFFER) / TOP_K
    assert TOP_K * w + BUFFER == pytest.approx(1.0)
    assert w == pytest.approx(0.0475, abs=1e-4)


def test_lot_rounding_down():
    """237 theoretical shares -> 200 actual (round down to 100s)."""
    def lots_for(value, price):
        return math.floor(value / price / LOT) * LOT

    assert lots_for(237 * 10.0, 10.0) == 200
    assert lots_for(99 * 10.0, 10.0) == 0     # below one lot -> no buy
    assert lots_for(100 * 10.0, 10.0) == 100


def test_cash_buffer_config_values():
    assert BUFFER in (0.0, 0.05, 0.10)


def test_weight_config_is_equal_weight():
    assert CONFIG["portfolio"]["weighting"] == "equal_weight"
    assert TOP_K == 20
