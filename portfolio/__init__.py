# -*- coding: utf-8 -*-
"""Portfolio optimization research package (STEP 6).

Signal 与 allocation 严格分离：本包只负责把（冻结的）alpha 排名转成
满足约束的目标权重，绝不重新训练 alpha 模型、绝不改变 alpha 排名
（raw_rank 全程保存）。

- constraints.py      组合约束（无杠杆/无做空/权重上限/行业上限/现金缓冲）
- covariance.py       PIT 协方差估计 + 稳定性 sanity gate + 修复链
- risk_model.py       每期协方差装配 + 边际/成分风险贡献
- transaction_cost.py 复用 strategy_v1 的 TransactionCostModel（公平比较）
- optimizer.py        scipy SLSQP 包装 + 权重 finalize（water-fill 强制约束）
- allocator.py        P0-P6 分配方法 + 回退链（方法→反波动→等权）
- rebalance.py        调仓日历（DB-free；monthly/quarterly）
- portfolio_metrics.py 组合级指标（含 VaR/CVaR/HHI/行业集中度/费用）
- backtest.py         组合回测引擎（T+1 执行、涨跌停 NO_TRADE、手数、成本）
- portfolio_registry.py 方法注册表
"""

from .constraints import PortfolioConstraints
from .covariance import CovarianceResult, estimate_covariance
from .allocator import AllocationFailure, AllocationInput, AllocationResult, allocate
from .portfolio_registry import ALLOCATION_METHODS, PORTFOLIO_REGISTRY

__all__ = [
    "PortfolioConstraints",
    "CovarianceResult",
    "estimate_covariance",
    "AllocationFailure",
    "AllocationInput",
    "AllocationResult",
    "allocate",
    "ALLOCATION_METHODS",
    "PORTFOLIO_REGISTRY",
]
