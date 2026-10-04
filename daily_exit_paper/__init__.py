# -*- coding: utf-8 -*-
"""daily_exit_paper_v1 —— 与 monthly paper_live 完全独立的 forward 实验。

    strategy_v2 / S3 信号
        → 每日推荐（Top-K，空缺席位等权）
        → T+1 限价入场（entry_high）
        → OPEN
        → target / stop / time-stop
        → CLOSED
        → 现金回流 → 下一轮

隔离（spec §2）：本包**不 import paper_live**。order / position / cash /
lifecycle 全部自己管理；与外部共享的只有纯函数（成本模型、入场区间与
target/stop 公式、交易日历）。

研究用途，永不自动下单。
"""

from __future__ import annotations

__all__ = ["config", "store", "state", "execution", "ledger", "decisions",
           "preflight", "engine", "report"]
