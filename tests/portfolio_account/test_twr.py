# -*- coding: utf-8 -*-
"""§16：时间加权收益（剔除资金流影响）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from wealth import engine


def test_single_period_without_flow():
    r = engine.twr_period_return(1000.0, 1100.0, 0.0)
    assert r == pytest.approx(0.10)


def test_flow_at_end_is_removed():
    """期末追加 500：净值涨到 1600 里那 500 不是收益。"""
    r = engine.twr_period_return(1000.0, 1600.0, 500.0, flow_at_end=True)
    assert r == pytest.approx(0.10)


def test_flow_at_start_is_not_counted_as_gain():
    r = engine.twr_period_return(1000.0, 1000.0 + 500.0, 500.0,
                                 flow_at_end=True)
    assert r == pytest.approx(0.0)


def test_twr_chains_periods():
    series = [
        {"date": "2026-01-01", "value": 1000.0, "flow": 0.0},
        {"date": "2026-01-02", "value": 1100.0, "flow": 0.0},   # +10%
        {"date": "2026-01-03", "value": 990.0, "flow": 0.0},    # -10%
    ]
    assert engine.twr(series) == pytest.approx(1.10 * 0.90 - 1.0)


def test_twr_ignores_a_pure_deposit():
    """存钱不改 TWR —— 这是它存在的全部意义。"""
    series = [
        {"date": "2026-01-01", "value": 1000.0, "flow": 0.0},
        {"date": "2026-01-02", "value": 11000.0, "flow": 10000.0},
    ]
    assert engine.twr(series) == pytest.approx(0.0, abs=1e-9)


def test_twr_needs_at_least_two_points():
    assert engine.twr([{"date": "2026-01-01", "value": 1000.0,
                        "flow": 0.0}]) is None


def test_zero_begin_value_is_undefined_not_infinite():
    assert engine.twr_period_return(0.0, 100.0, 0.0) is None


def test_annualize_uses_calendar_days():
    a = engine.annualize(0.10, 365.0)
    assert a == pytest.approx(0.10, abs=1e-9)
    assert engine.annualize(0.10, 182.5) == pytest.approx(0.21, abs=1e-3)
