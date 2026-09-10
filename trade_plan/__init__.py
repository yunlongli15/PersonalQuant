# -*- coding: utf-8 -*-
"""Trade plan engine (STEP 7E).

Answers, for a given capital and risk profile (spec §10-§16):

    给定本金、频率、风险偏好与约束，具体该以什么价格、买多少股、
    在哪里止盈/止损？

Layers (kept separate on purpose — spec §55):

    signal      pipeline/signals.py        (frozen S3, which names)
    forecast    pipeline/forecast.py       (expected return / interval)
    allocation  portfolio/                 (STEP 6, unchanged)
    execution   trade_plan/plan.py         (entry/target/stop/lots/costs)

The optimizer is NOT re-tuned here: the allocation method and constraints
come from the STEP 6 study selection (config/portfolio_v1.yaml +
experiments/portfolio/selection.json). This package adds the execution
layer the spec asks for: entry ranges, targets, stops, lot rounding and
the resulting cash/estimated fees, plus the reason attached to every
SELL (spec §14).
"""
