# -*- coding: utf-8 -*-
"""Transaction cost model (fully configurable; no claim of real broker fees)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TransactionCostModel:
    commission_rate: float = 0.00025   # 买卖双向
    min_commission: float = 5.0        # 最低佣金（元）
    stamp_duty: float = 0.0005         # 印花税（仅卖出）
    transfer_fee: float = 0.00001      # 过户费（双向）
    slippage: float = 0.0005           # 滑点（单边，按成交额）

    @classmethod
    def from_config(cls, cfg: dict) -> "TransactionCostModel":
        c = cfg["transaction_costs"]
        return cls(
            commission_rate=c["commission_rate"],
            min_commission=c["min_commission"],
            stamp_duty=c["stamp_duty"],
            transfer_fee=c["transfer_fee"],
            slippage=c["slippage"],
        )

    def buy_cost(self, value: float) -> float:
        return self._cost(value, is_sell=False)

    def sell_cost(self, value: float) -> float:
        return self._cost(value, is_sell=True)

    def _cost(self, value: float, is_sell: bool) -> float:
        commission = max(self.min_commission, value * self.commission_rate)
        stamp = value * self.stamp_duty if is_sell else 0.0
        transfer = value * self.transfer_fee
        slip = value * self.slippage
        return commission + stamp + transfer + slip
