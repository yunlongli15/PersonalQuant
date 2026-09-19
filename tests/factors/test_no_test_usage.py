# -*- coding: utf-8 -*-
"""2024-2025 绝不允许进入选择路径（§1 / §24）。

这是本阶段最重要的一条可执行约束：不是写在文档里的君子协定，
而是会让违规代码直接报错的守卫。
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest
import yaml

from incremental.engine import build_folds
from incremental.holdout import ForwardHoldout
from incremental.windows import (HISTORICAL_TEST, SELECTION_END,
                                 SELECTION_START, assert_not_historical_test,
                                 assert_selection_window)

ROOT = Path(__file__).resolve().parents[2]
# 允许出现 2024/2025 字面量的地方：只有"守卫"本身
GUARD_FILES = {"incremental/windows.py", "incremental/holdout.py"}
SELECTION_FILES = [
    "incremental/engine.py", "incremental/stats.py",
    "incremental/redundancy.py",
    "scripts/run_incremental_factor_selection.py",
]


def _cfg():
    return yaml.safe_load(
        (ROOT / "config" / "factor_selection_v2.yaml").read_text(
            encoding="utf-8"))


def test_config_windows():
    spec = _cfg()["factor_selection_v2"]
    assert spec["selection_window"] == ["2018-01-01", "2023-12-31"]
    assert spec["forbidden_window"] == ["2024-01-01", "2025-12-31"]


def test_selection_window_guard_rejects_2024_and_2025():
    for d in ("2024-01-02", "2024-12-31", "2025-06-30", "2026-01-05"):
        with pytest.raises(ValueError, match="选择窗口"):
            assert_selection_window(pd.DatetimeIndex([d]), "test")
    assert_selection_window(pd.DatetimeIndex(["2018-01-01", "2023-12-29"]),
                            "test")


def test_historical_test_guard_rejects_the_observed_window():
    for d in ("2024-01-01", "2025-12-31"):
        with pytest.raises(ValueError, match="HISTORICAL TEST"):
            assert_not_historical_test(pd.DatetimeIndex([d]), "test")
    assert_not_historical_test(pd.DatetimeIndex(["2023-12-29"]), "test")


def test_historical_test_constant_matches_config():
    spec = _cfg()["factor_selection_v2"]
    assert list(HISTORICAL_TEST) == spec["forbidden_window"]


def test_folds_reject_a_validation_year_inside_the_test_set():
    bad = {"factor_selection_v2": {"walk_forward": {
        "drop_labels_crossing_fold_end": True,
        "folds": [{"name": "leak", "train": ["2018-01-01", "2022-12-31"],
                   "valid": ["2024-01-01", "2024-12-31"]}]}}}
    cal = pd.DatetimeIndex(pd.bdate_range("2018-01-01", "2024-12-31"))
    reb = list(pd.Series(cal, index=cal).groupby(cal.to_period("M")).last())
    with pytest.raises(ValueError, match="选择窗口"):
        build_folds(bad, cal, reb, 20)


def test_selection_modules_contain_no_2024_2025_literals():
    """静态扫描：选择路径上的模块里不得出现 2024/2025 的日期字面量。

    允许 "2026-09-18"（holdout 起点，且只出现在 config 里）。
    """
    hits = []
    for rel in SELECTION_FILES:
        assert rel not in GUARD_FILES
        text = (ROOT / rel).read_text(encoding="utf-8")
        for m in re.finditer(r"['\"]20(24|25)-\d{2}-\d{2}['\"]", text):
            hits.append(f"{rel}: {m.group(0)}")
    assert not hits, f"选择路径出现 2024/2025 字面量: {hits}"


def test_driver_only_reads_data_up_to_the_selection_end():
    """驱动脚本不得把 2024-2025 的数据读进内存。"""
    text = (ROOT / "scripts/run_incremental_factor_selection.py").read_text(
        encoding="utf-8")
    assert 'selection_window"' in text
    for m in re.finditer(r'load_factor_data\([^)]*\)', text):
        assert "2024" not in m.group(0) and "2025" not in m.group(0), \
            m.group(0)


def test_holdout_dates_cannot_be_used_for_selection():
    h = ForwardHoldout(start="2026-09-18", registry=Path("/tmp/x.json"))
    with pytest.raises(ValueError, match="forward holdout"):
        h.assert_not_selection(pd.DatetimeIndex(["2026-09-18"]), "test")
    # 窗口之前的数据不受限
    h.assert_not_selection(pd.DatetimeIndex(["2023-12-29"]), "test")


def test_holdout_start_is_after_the_last_observed_date():
    spec = _cfg()["factor_selection_v2"]
    start = pd.Timestamp(spec["forward_holdout_start"])
    assert start > pd.Timestamp("2023-12-31")
    assert spec["forward_holdout"]["mode"] == "record_only"
