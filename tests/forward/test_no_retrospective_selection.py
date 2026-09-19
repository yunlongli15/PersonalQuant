# -*- coding: utf-8 -*-
"""§38 / §33：forward holdout 只读，不得回头用于任何选择。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

from paper_live import config as C


def test_read_only_guard_is_on():
    assert C.FORWARD_HOLDOUT_READ_ONLY is True


def test_forward_dates_are_rejected_from_selection():
    for d in ("2026-09-18", "2026-10-01", "2027-01-04"):
        with pytest.raises(ValueError, match="forward holdout"):
            C.assert_not_used_for_selection(pd.DatetimeIndex([d]), "test")


def test_pre_forward_dates_are_allowed():
    C.assert_not_used_for_selection(
        pd.DatetimeIndex(["2018-01-01", "2023-12-29", "2026-09-17"]), "test")


def test_the_boundary_is_exactly_the_configured_start():
    start = C.spec()["forward_start_date"]
    assert start == "2026-09-18"
    C.assert_not_used_for_selection(
        pd.DatetimeIndex([pd.Timestamp(start) - pd.Timedelta(days=1)]), "b")
    with pytest.raises(ValueError):
        C.assert_not_used_for_selection(pd.DatetimeIndex([start]), "b")


def test_historical_test_is_not_forward_data():
    """2024-2025 是 HISTORICAL TEST，不是 forward —— 两者含义不同。"""
    assert C.is_historical_test("2024-06-30")
    assert not C.is_forward_date("2024-06-30")
    assert C.is_forward_date("2026-09-18")
    assert not C.is_historical_test("2026-09-18")


def test_the_two_windows_do_not_overlap():
    s = C.spec()
    lo, hi = (pd.Timestamp(x) for x in s["historical_test"])
    assert hi < pd.Timestamp(s["forward_start_date"])
    assert lo > pd.Timestamp("2023-12-31")


def test_selection_config_still_refuses_forward_dates():
    """STEP 9 的选择协议同样不得碰 forward 数据。"""
    from incremental.windows import assert_selection_window
    with pytest.raises(ValueError, match="选择窗口"):
        assert_selection_window(pd.DatetimeIndex(["2026-09-18"]), "t")


def test_forward_modules_do_not_import_selection_machinery():
    """forward 引擎不得 import 因子选择/组合优化模块。"""
    import re
    root = Path(__file__).resolve().parents[2] / "paper_live"
    banned = ("incremental.stats", "incremental.redundancy",
              "factors.selection", "portfolio.allocator")
    for f in root.glob("*.py"):
        text = f.read_text(encoding="utf-8")
        for b in banned:
            assert not re.search(rf"^\s*(from|import)\s+{re.escape(b)}",
                                 text, re.M), f"{f.name} 引用了 {b}"
