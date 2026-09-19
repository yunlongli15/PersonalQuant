# -*- coding: utf-8 -*-
"""§15：P&L 恒等式与变动分解。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from wealth import engine


def test_pnl_identity():
    assert engine.investment_pnl(1000.0, 1150.0, 100.0) == pytest.approx(50.0)


def test_pnl_is_negative_when_value_falls():
    assert engine.investment_pnl(1000.0, 900.0, 0.0) == pytest.approx(-100.0)


def test_decompose_change_splits_sources():
    d = engine.decompose_change(
        begin_value=10000.0, end_value=12500.0,
        txns=[{"txn_type": "deposit", "amount": 2000.0, "cash_flow": 2000.0},
              {"txn_type": "withdrawal", "amount": 500.0,
               "cash_flow": -500.0},
              {"txn_type": "dividend", "amount": 100.0},
              {"txn_type": "fee", "fee": 20.0}])
    assert d.external_contributions == pytest.approx(2000.0)
    assert d.withdrawals == pytest.approx(500.0)
    assert d.dividends == pytest.approx(100.0)
    assert d.net_change == pytest.approx(2500.0)


def test_decomposition_absorbs_the_unexplained_part_into_pnl():
    """存入 500 但总资产没变 → 投资端亏了 500（残差法，不是对账失败）。"""
    d = engine.decompose_change(
        begin_value=1000.0, end_value=1000.0,
        txns=[{"txn_type": "deposit", "amount": 500.0, "cash_flow": 500.0}])
    assert d.external_contributions == pytest.approx(500.0)
    assert d.investment_pnl == pytest.approx(-500.0)


def test_decomposition_parts_always_sum_to_the_change():
    """分解是恒等式：各部分之和必然等于总变动（残差被 pnl 吸收）。"""
    d = engine.decompose_change(
        begin_value=1000.0, end_value=1300.0,
        txns=[{"txn_type": "deposit", "amount": 200.0, "cash_flow": 200.0},
              {"txn_type": "dividend", "amount": 30.0},
              {"txn_type": "fee", "fee": 10.0}])
    total = (d.external_contributions - d.withdrawals + d.investment_pnl
             + d.dividends - d.fees)
    assert total == pytest.approx(d.net_change)
    assert d.reconciliation_error == pytest.approx(0.0)


def test_rows_are_serialisable():
    d = engine.decompose_change(1000.0, 1100.0, [])
    rows = d.as_row()
    assert isinstance(rows, list) and rows
    assert all(isinstance(k, str) for k, _ in rows)
