# -*- coding: utf-8 -*-
"""Application Service Layer（STEP 11, spec §5 / §48）。

**这是 GUI 与量化核心之间唯一的接触面。**
Streamlit 页面只允许调用这里，不允许自己 import pandas 算收益、
更不允许碰因子/回测/组合优化/PIT。

分层：

    app/ (Streamlit 页面)          只做展示 / 输入 / 查询
        ↓ 只调用
    services/                      视图模型 + 编排
        ↓ 复用
    wealth/  trade_plan/  pipeline/  factors/  portfolio/  paper_live/
                                    （既有引擎，本阶段不重写）

复用说明（见 docs/步骤11-既有资产系统审计.md §3.3）：
`webapp/services.py` 已经是同一职责的服务层，本包**直接复用它**，
只补齐缺口（风险、因子、健康、账本估值），不重写一遍。
"""

from . import (backtest_service, factor_service, health_service,
               market_service, news_service, performance_service,
               portfolio_service, recommendation_service, risk_service,
               strategy_service)

__all__ = [
    "backtest_service", "factor_service", "health_service",
    "market_service", "news_service", "performance_service",
    "portfolio_service", "recommendation_service", "risk_service",
    "strategy_service",
]
