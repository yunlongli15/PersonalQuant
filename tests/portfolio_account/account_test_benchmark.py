# -*- coding: utf-8 -*-
"""§17：基准 —— 真实账户 vs 策略模拟必须分开标注。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from wealth import repository as repo


def test_benchmarks_are_stored_and_read_back(conn):
    repo.upsert_benchmark(conn, "2026-09-01", "CSI300", 4500.0)
    rows = repo.list_benchmarks(conn, benchmark="CSI300")
    assert len(rows) == 1
    assert float(rows[0]["close"]) == pytest.approx(4500.0)


def test_benchmark_upsert_is_idempotent(conn):
    repo.upsert_benchmark(conn, "2026-09-01", "CSI300", 4500.0)
    repo.upsert_benchmark(conn, "2026-09-01", "CSI300", 4550.0)
    rows = repo.list_benchmarks(conn, benchmark="CSI300")
    assert len(rows) == 1
    assert float(rows[0]["close"]) == pytest.approx(4550.0)


def test_custom_benchmarks_are_allowed(conn):
    repo.upsert_benchmark(conn, "2026-09-01", "custom:我的组合", 1.0)
    assert repo.list_benchmarks(conn, benchmark="custom:我的组合")


def test_unknown_benchmark_name_is_rejected(conn):
    with pytest.raises(Exception):
        repo.upsert_benchmark(conn, "2026-09-01", "随便什么", 1.0)


def test_strategy_vs_actual_are_separate_namespaces():
    """§17：真实账户表现与策略模拟表现不能混为一谈。

    策略结果住在 experiments/，账户数据住在 wealth.db —— 物理隔离。
    """
    from pathlib import Path as P

    from wealth.db import WEALTH_DB
    assert "wealth" in str(WEALTH_DB)
    assert "experiments" not in str(WEALTH_DB)
