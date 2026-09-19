# -*- coding: utf-8 -*-
"""§10：真实 A 股手数。理论股数 ≠ 实际股数，残差现金必须显式记录。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from paper_live.execution import LOT, build_orders, round_lots


def test_round_down_to_whole_lots():
    assert round_lots(150) == 100
    assert round_lots(199.9) == 100
    assert round_lots(200) == 200
    assert round_lots(99) == 0


def test_negative_shares_round_toward_zero():
    assert round_lots(-150) == -100
    assert round_lots(-99) == 0


def test_nan_and_none_safe():
    assert round_lots(float("nan")) == 0
    assert round_lots(None) == 0


def test_never_rounds_up():
    for x in (100, 250, 999, 1001):
        assert round_lots(x) <= x


def test_theoretical_vs_rounded_is_recorded():
    from personal_quant.strategy.costs import TransactionCostModel
    cm = TransactionCostModel(commission_rate=0.00025, min_commission=5.0,
                              stamp_duty=0.0005, transfer_fee=0.00001,
                              slippage=0.0005)
    tw = {"A.SH": 0.5}
    preds = __import__("pandas").Series({"A.SH": 1.0})
    orders = build_orders(tw, preds, {"A.SH": "甲"}, {"A.SH": 33.33},
                          {}, 100_000.0, 100_000.0, cm)
    o = orders[0]
    assert o.target_value == pytest.approx(50_000.0)
    assert o.theoretical_shares == pytest.approx(50_000 / 33.33)
    assert o.estimated_shares == 1500          # 100 股整数倍且向下取整
    assert o.estimated_shares % LOT == 0
    assert o.estimated_trade_value == pytest.approx(1500 * 33.33)
    # 因取整而没投出去的钱
    residual = o.target_value - o.estimated_trade_value
    assert residual > 0


def test_below_one_lot_is_no_trade():
    from personal_quant.strategy.costs import TransactionCostModel
    cm = TransactionCostModel()
    orders = build_orders({"A.SH": 0.001}, __import__("pandas").Series(
        {"A.SH": 1.0}), {"A.SH": "甲"}, {"A.SH": 100.0}, {}, 100_000.0,
        100_000.0, cm)
    assert orders[0].estimated_shares == 0
    assert orders[0].action == "NO_TRADE"


def test_sell_all_clears_the_position_exactly():
    """清仓必须是精确的：持仓本来就是整手，卖出不该留残股。"""
    from personal_quant.strategy.costs import TransactionCostModel
    cm = TransactionCostModel()
    orders = build_orders({}, __import__("pandas").Series(dtype=float),
                          {"A.SH": "甲"}, {"A.SH": 12.5},
                          {"A.SH": {"shares": 800, "price": 10.0}},
                          100_000.0, 100_000.0, cm)
    assert orders[0].estimated_shares == -800
    assert orders[0].action == "SELL"
