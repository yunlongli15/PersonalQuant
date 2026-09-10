# -*- coding: utf-8 -*-
"""Portfolio constraints (STEP 6 spec §16/§17/§20).

Defaults: max_weight 10%, sector cap 20%, cash buffer 5% (stock target
95%), 100-share lots, long-only, no leverage. Every deviation from these
defaults must be recorded in the run manifest — 禁止为"收益更好"反复调
这些参数（研究期选择 → validation 确认 → test 单次）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PortfolioConstraints:
    max_weight: float = 0.10          # 单只上限（spec §17 默认 10%）
    min_weight: float = 0.0           # 不设下限（可归零）
    sector_cap: float = 0.20          # 单一行业上限（spec §16 硬上限）
    invest_target: float = 0.95       # 股票总权重 = 1 - cash_buffer
    cash_buffer: float = 0.05         # 现金缓冲（spec §20）
    lot_size: int = 100               # A 股 100 股整数手
    liquidity_frac: Optional[float] = None   # None=关；仓位市值 <= frac×20日均额
    tol: float = 1e-6

    @classmethod
    def from_dict(cls, cfg: dict) -> "PortfolioConstraints":
        c = dict(cfg)
        return cls(
            max_weight=float(c.get("max_weight", 0.10)),
            min_weight=float(c.get("min_weight", 0.0)),
            sector_cap=float(c.get("sector_cap", 0.20)),
            cash_buffer=float(c.get("cash_buffer", 0.05)),
            invest_target=float(c.get("invest_target",
                                      1.0 - c.get("cash_buffer", 0.05))),
            lot_size=int(c.get("lot_size", 100)),
            liquidity_frac=(None if c.get("liquidity_frac") is None
                            else float(c["liquidity_frac"])),
            tol=float(c.get("tol", 1e-6)),
        )

    def to_dict(self) -> dict:
        return {
            "max_weight": self.max_weight,
            "min_weight": self.min_weight,
            "sector_cap": self.sector_cap,
            "cash_buffer": self.cash_buffer,
            "invest_target": self.invest_target,
            "lot_size": self.lot_size,
            "liquidity_frac": self.liquidity_frac,
            "tol": self.tol,
        }
