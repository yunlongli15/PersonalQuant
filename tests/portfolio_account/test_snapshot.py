# -*- coding: utf-8 -*-
"""§39：每日快照与净值序列（含"部分产品未录入"的前向填充）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from wealth import engine, repository as repo


def test_snapshot_upsert_is_idempotent_per_day(conn, make_product):
    pid = make_product()
    repo.upsert_snapshot(conn, "2026-09-01", pid, units=100.0, nav=10.0,
                         market_value=1000.0)
    repo.upsert_snapshot(conn, "2026-09-01", pid, units=100.0, nav=11.0,
                         market_value=1100.0)
    rows = repo.list_snapshots(conn, product_id=pid)
    assert len(rows) == 1
    assert float(rows[0]["market_value"]) == pytest.approx(1100.0)


def test_value_series_sums_products_per_day(conn, make_product):
    a = make_product("A", "stock", "600519.SH")
    b = make_product("B", "stock", "000001.SZ")
    repo.upsert_snapshot(conn, "2026-09-01", a, market_value=1000.0)
    repo.upsert_snapshot(conn, "2026-09-01", b, market_value=500.0)
    s = engine.value_series(conn)
    assert float(s["value"].iloc[-1]) == pytest.approx(1500.0)


def test_missing_product_carries_forward_not_dropped(conn, make_product):
    """某个产品某天没录入 ≠ 它消失了（曾经因此显示假亏 14.9 万）。"""
    a = make_product("A", "stock", "600519.SH")
    b = make_product("B", "stock", "000001.SZ")
    repo.upsert_snapshot(conn, "2026-09-01", a, market_value=1000.0)
    repo.upsert_snapshot(conn, "2026-09-01", b, market_value=500.0)
    repo.upsert_snapshot(conn, "2026-09-02", a, market_value=1100.0)
    s = engine.value_series(conn)
    assert float(s["value"].iloc[-1]) == pytest.approx(1600.0)   # 不是 1100


def test_performance_reports_empty_before_any_snapshot(conn):
    assert engine.performance(conn).get("empty") is True


def test_performance_gives_a_curve_after_snapshots(conn, make_product):
    pid = make_product()
    repo.upsert_snapshot(conn, "2026-09-01", pid, market_value=1000.0)
    repo.upsert_snapshot(conn, "2026-09-02", pid, market_value=1010.0)
    perf = engine.performance(conn)
    assert not perf.get("empty")
    assert perf["curve"] is not None
    assert "twr" in perf


def test_snapshot_cash_flow_is_recorded(conn, make_product):
    pid = make_product(ptype="cash", ticker=None)
    repo.upsert_snapshot(conn, "2026-09-01", pid, market_value=1000.0,
                         cash_flow=1000.0)
    s = engine.value_series(conn)
    assert float(s["flow"].iloc[-1]) == pytest.approx(1000.0)
