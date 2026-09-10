# -*- coding: utf-8 -*-
"""Portfolio method registry (STEP 6 spec §29).

方法名是实验与报告的单一事实来源；CLI 与 verify_step6 都从这里读。
"""

from __future__ import annotations

ALLOCATION_METHODS = [
    "equal_weight",
    "score_weight",
    "inverse_vol",
    "gmv",
    "mvo",
    "risk_parity",
    "turnover_aware",
]

PORTFOLIO_REGISTRY = {
    "equal_weight": {
        "label": "P0 Equal Weight",
        "description": "等权（strategy_v1 基线分配，spec §7）",
        "defaults": {},
    },
    "score_weight": {
        "label": "P1 Score Weight",
        "description": "权重 ∝ 预测分变换（rank/raw_positive/softmax），"
                       "max_weight 上限（spec §8）",
        "defaults": {"variant": "rank"},
    },
    "inverse_vol": {
        "label": "P2 Inverse Volatility",
        "description": "权重 ∝ 1/σ（20D/60D 波动，只用 signal_date 之前数据，"
                       "spec §9）",
        "defaults": {},
    },
    "gmv": {
        "label": "P3 Global Minimum Variance",
        "description": "min w'Σw，s.t. Σw=invest_target, w>=0, w<=max_weight, "
                       "行业上限, cash 缓冲（spec §10）",
        "defaults": {},
    },
    "mvo": {
        "label": "P4 Mean-Variance",
        "description": "max μ̄'w - λ·w'Σ̄w（归一化效用；λ 三档 small/medium/"
                       "large，spec §11）",
        "defaults": {"lambda_tier": "medium"},
    },
    "risk_parity": {
        "label": "P5 Risk Parity",
        "description": "等风险贡献（long-only、无杠杆、cash 缓冲，spec §12）",
        "defaults": {},
    },
    "turnover_aware": {
        "label": "P6 Turnover-Aware",
        "description": "max μ̄'w - λrisk·w'Σ̄w - λturn·T - λcost·rate·T，"
                       "T=0.5Σ|w_new-w_old|（spec §13/§24）",
        "defaults": {"lambda_risk": 2.0, "lambda_turn": 0.5,
                     "lambda_cost": 1.0},
    },
}
