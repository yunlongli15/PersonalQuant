# -*- coding: utf-8 -*-
"""Transaction cost model math."""

import pytest

from personal_quant.strategy.costs import TransactionCostModel


@pytest.fixture
def model():
    return TransactionCostModel(
        commission_rate=0.00025, min_commission=5.0, stamp_duty=0.0005,
        transfer_fee=0.00001, slippage=0.0005,
    )


def test_buy_cost_components(model):
    value = 100_000.0
    c = model.buy_cost(value)
    expected = value * 0.00025 + value * 0.00001 + value * 0.0005  # no stamp
    assert c == pytest.approx(expected, abs=1e-6)


def test_sell_cost_includes_stamp(model):
    value = 100_000.0
    c = model.sell_cost(value)
    expected = (value * 0.00025 + value * 0.0005 + value * 0.00001
                + value * 0.0005)
    assert c == pytest.approx(expected, abs=1e-6)


def test_min_commission_binds(model):
    small = model.buy_cost(1000.0)
    # commission alone would be 0.25 -> min 5 applies
    assert small >= 5.0 + 1000 * 0.00001 + 1000 * 0.0005


def test_config_loaded():
    import yaml
    from pathlib import Path

    cfg = yaml.safe_load(
        (Path(__file__).resolve().parents[2] / "config" / "strategy_v1.yaml")
        .read_text(encoding="utf-8")
    )
    m = TransactionCostModel.from_config(cfg)
    assert m.commission_rate == 0.00025
    assert m.stamp_duty == 0.0005
    assert m.min_commission == 5.0
    assert m.slippage == 0.0005
