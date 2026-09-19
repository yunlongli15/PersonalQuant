# -*- coding: utf-8 -*-
"""Incremental IC factor selection protocol V2 (STEP 9).

回答的问题不是"这个因子单独强不强"，而是：

    把 F 加进已有模型后，模型对未来横截面收益的预测信息**是否真的增加**？

即 mean(IC1 − IC0)，而不是 mean(IC1)。

包结构：
  windows.py       时间窗口边界（2018-2023 可选，2024-2025 禁用）
  engine.py        walk-forward 折、M0/M1 配对训练与预测、DeltaIC、预测影响
  stats.py         block bootstrap、Evidence Score、候选门槛
  redundancy.py    冗余诊断（**原始因子秩相关**为主，残差只作辅助）
  holdout.py       forward holdout 登记与只读监控

纪律：本包只接受 2018-2023 作为选择窗口，超出即抛错
（tests/factors/test_no_test_usage.py 覆盖）。
"""

from .windows import (HISTORICAL_TEST, SELECTION_END, SELECTION_START,
                      assert_not_historical_test, assert_selection_window)

__all__ = [
    "HISTORICAL_TEST", "SELECTION_START", "SELECTION_END",
    "assert_selection_window", "assert_not_historical_test",
]
