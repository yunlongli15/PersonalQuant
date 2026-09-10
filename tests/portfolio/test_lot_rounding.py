# -*- coding: utf-8 -*-
"""A-share lot rounding (spec §43): target value -> 100-share lots;
execution weights are recomputed from actual shares (theoretical weights
!= execution weights is expected and recorded)."""

import math

from portfolio.backtest import lot_floor


def test_buy_rounds_down_to_lot():
    # 237 shares worth -> 200
    assert lot_floor(237 * 10.0, 10.0, 100) == 200
    assert lot_floor(199 * 10.0, 10.0, 100) == 100
    assert lot_floor(99 * 10.0, 10.0, 100) == 0


def test_exact_multiple_unchanged():
    assert lot_floor(500 * 8.0, 8.0, 100) == 500


def test_bad_price_returns_zero():
    assert lot_floor(10000, None, 100) == 0
    assert lot_floor(10000, math.nan, 100) == 0
    assert lot_floor(10000, 0.0, 100) == 0
    assert lot_floor(10000, -5.0, 100) == 0


def test_rounding_residual_goes_to_cash():
    # theoretical 237 shares at 10 CNY -> execution 200 shares: the
    # difference stays in cash (residual), never forced into the stock
    price, target_value, lot = 10.0, 2370.0, 100
    shares = lot_floor(target_value, price, lot)
    spent = shares * price
    residual = target_value - spent
    assert shares == 200
    assert residual == 370.0
    assert residual >= 0
