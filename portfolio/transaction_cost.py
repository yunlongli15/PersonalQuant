# -*- coding: utf-8 -*-
"""Transaction costs: the frozen strategy_v1 model, re-exported (spec §23).

All portfolio optimizers use the SAME TransactionCostModel as the
strategy backtests (fair comparison). The unit rates below are used by
the turnover-aware objective; the 5-yuan minimum commission is ignored in
unit rates (for a 1M portfolio every position is >= 47.5k so the minimum
never binds — documented).
"""

from __future__ import annotations

from personal_quant.strategy.costs import TransactionCostModel  # noqa: F401


def unit_buy_rate(cost: TransactionCostModel) -> float:
    """Cost per 1 CNY of buy value: commission + transfer + slippage."""
    return cost.commission_rate + cost.transfer_fee + cost.slippage


def unit_sell_rate(cost: TransactionCostModel) -> float:
    """Cost per 1 CNY of sell value: commission + stamp + transfer + slip."""
    return (cost.commission_rate + cost.stamp_duty + cost.transfer_fee
            + cost.slippage)


def round_trip_rate(cost: TransactionCostModel) -> float:
    return unit_buy_rate(cost) + unit_sell_rate(cost)
