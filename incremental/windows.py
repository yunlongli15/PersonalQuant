# -*- coding: utf-8 -*-
"""时间窗口边界：唯一口径，防止 2024-2025 / forward holdout 混进选择路径。

单独成模块是为了避免 `incremental/__init__` 与 engine/holdout 的循环导入。
"""

from __future__ import annotations

import pandas as pd

SELECTION_START = "2018-01-01"
SELECTION_END = "2023-12-31"
HISTORICAL_TEST = ("2024-01-01", "2025-12-31")


def assert_selection_window(dates, context: str = "") -> None:
    """拒绝任何落在 2018-2023 之外的日期。

    2024-2025 是 HISTORICAL TEST（STEP 6 终评、step8、step9 已看过多次），
    不得进入任何选择路径：不选因子、不调参、不排因子、不选阈值。
    """
    lo, hi = pd.Timestamp(SELECTION_START), pd.Timestamp(SELECTION_END)
    bad = [d for d in pd.DatetimeIndex(dates) if d < lo or d > hi]
    if len(bad):
        raise ValueError(
            f"{context}: {len(bad)} 个日期超出选择窗口 "
            f"{SELECTION_START}..{SELECTION_END}（2024-2025 是 HISTORICAL "
            f"TEST，禁止用于选择）：{[str(d.date()) for d in bad[:5]]}")


def assert_not_historical_test(dates, context: str = "") -> None:
    lo, hi = pd.Timestamp(HISTORICAL_TEST[0]), pd.Timestamp(HISTORICAL_TEST[1])
    bad = [d for d in pd.DatetimeIndex(dates) if lo <= d <= hi]
    if len(bad):
        raise ValueError(
            f"{context}: {len(bad)} 个日期落在 HISTORICAL TEST "
            f"{HISTORICAL_TEST[0]}..{HISTORICAL_TEST[1]}（已被观察多次，"
            f"禁止用于选择）：{[str(d.date()) for d in bad[:5]]}")
