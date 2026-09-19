# -*- coding: utf-8 -*-
"""Paper Live —— 从 2026-09-18 起的 clean forward holdout（STEP 10）。

分工（不得混淆）：

    历史研究      →  DISCOVERY   （找想法）
    Validation    →  SELECTION   （选策略，只能看 2018-2023）
    Forward       →  OBSERVATION （只看，绝不回头改）

本包只做第三件事。`record_only = true`：所有写入都是 append-only，
过去的 observation 不可覆盖；发现 bug 也只能新增 revision，旧版本必须保留。

模块：
  config.py     冻结配置读取 + 哈希（drift 检测的基础）
  store.py      观测存储（append-only + revision_id）
  engine.py     单日运行：信号 → 目标组合 → T+1 执行 → 组合更新
  execution.py  手数取整、下单计划、T+1 成交结果
  metrics.py    forward 业绩 / 预测质量 / 滚动统计
  audit.py      PIT 审计 + 数据完整性
  drift.py      strategy / model / news / data 漂移
  alerts.py     告警（只报警，绝不自动交易或改参数）
"""

from .config import (freeze_hashes, load_config, verify_freeze,
                     config_sha256)
from .store import ForwardStore, WriteResult

__all__ = [
    "load_config", "freeze_hashes", "verify_freeze", "config_sha256",
    "ForwardStore", "WriteResult",
]

FORWARD_START = "2026-09-18"
HISTORICAL_TEST = ("2024-01-01", "2025-12-31")
