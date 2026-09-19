# -*- coding: utf-8 -*-
"""§16：资金加权收益 XIRR（个人账户有追加/提款时必须看它）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from wealth import engine


def test_xirr_of_a_one_year_double():
    r = engine.xirr(["2025-01-01", "2026-01-01"], [-1000.0, 1100.0])
    assert r == pytest.approx(0.10, abs=1e-4)


def test_xirr_of_a_half_year_double_is_annualized():
    """半年赚 10% ≈ 年化 21%（不是 10%）。"""
    r = engine.xirr(["2025-01-01", "2025-07-02"], [-1000.0, 1100.0])
    assert r is not None and r > 0.15


def test_xirr_handles_intermediate_flows():
    r = engine.xirr(["2025-01-01", "2025-07-01", "2026-01-01"],
                    [-1000.0, -500.0, 1700.0])
    assert r is not None and -0.99 < r < 5.0


def test_xirr_returns_none_without_a_sign_change():
    """全是流出（或全是流入）时 XIRR 无定义 —— 返回 None，不是编一个数。"""
    assert engine.xirr(["2025-01-01", "2026-01-01"],
                       [-1000.0, -200.0]) is None
    assert engine.xirr(["2025-01-01", "2026-01-01"],
                       [1000.0, 200.0]) is None


def test_xirr_needs_two_points():
    assert engine.xirr(["2025-01-01"], [-1000.0]) is None
    assert engine.xirr([], []) is None


def test_xirr_of_a_loss_is_negative():
    r = engine.xirr(["2025-01-01", "2026-01-01"], [-1000.0, 800.0])
    assert r is not None and r < 0


def test_xirr_is_reproducible():
    args = (["2025-01-01", "2025-06-01", "2026-01-01"],
            [-1000.0, -500.0, 1800.0])
    assert engine.xirr(*args) == engine.xirr(*args)
