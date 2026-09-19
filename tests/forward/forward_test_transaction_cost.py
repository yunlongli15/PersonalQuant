# -*- coding: utf-8 -*-
"""§8 / 唯一费率口径：paper live 必须复用 strategy_v1 的成本模型。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from paper_live.config import load_config
from personal_quant.strategy.costs import TransactionCostModel


def test_paper_live_reuses_the_frozen_cost_model():
    cfg = load_config()
    pl = TransactionCostModel.from_config(
        {"transaction_costs": cfg["paper_live"]["transaction_costs"]})
    prod = TransactionCostModel.from_config(load_config()["paper_live"])
    # 与 strategy_v1 完全同参：禁止第二套费率
    assert pl == prod
    v1 = TransactionCostModel(commission_rate=0.00025, min_commission=5.0,
                              stamp_duty=0.0005, transfer_fee=0.00001,
                              slippage=0.0005)
    assert pl == v1


def test_buy_and_sell_costs_differ_by_stamp_duty():
    cm = TransactionCostModel()
    v = 100_000.0
    assert cm.sell_cost(v) > cm.buy_cost(v)
    assert cm.sell_cost(v) - cm.buy_cost(v) == pytest.approx(v * 0.0005)


def test_minimum_commission_applies_to_small_trades():
    cm = TransactionCostModel()
    small = 1_000.0
    assert cm.buy_cost(small) >= 5.0
    assert cm.sell_cost(small) >= 5.0


def test_cost_is_monotone_in_value():
    cm = TransactionCostModel()
    assert cm.buy_cost(200_000) > cm.buy_cost(100_000)
