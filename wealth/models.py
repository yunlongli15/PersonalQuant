# -*- coding: utf-8 -*-
"""Wealth domain vocabulary: platform/product/transaction/cash-flow types.

Enum values are stored as TEXT in SQLite (readable, greppable, stable
across refactors). Adding a value is a schema-compatible change; removing
one requires a migration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

# --- platform kinds (spec §5.1) --------------------------------------------
PLATFORM_KINDS = ("fund_platform", "bank", "broker", "cash", "other")

# --- product types (spec §5.2) ---------------------------------------------
PRODUCT_TYPES = ("cash", "money_fund", "bond_fund", "index_fund", "qdii",
                 "stock", "etf", "gold", "other")

#: 货币型：按“万份收益”口径（spec §8）；其余按 units x NAV 口径（spec §9）
MONEY_MARKET_TYPES = ("cash", "money_fund")

# --- transaction types ------------------------------------------------------
#: 外部资金流（影响 Investment P&L 的扣减项，spec §7）
EXTERNAL_FLOW_TYPES = ("deposit", "withdrawal", "transfer_in",
                       "transfer_out")
#: 组合内部变化（不影响 Investment P&L）
INTERNAL_FLOW_TYPES = ("buy", "sell", "subscribe", "redeem", "dividend",
                       "fee", "adjustment", "split")
TXN_TYPES = EXTERNAL_FLOW_TYPES + INTERNAL_FLOW_TYPES

#: 收益记录的计算口径（spec §8.2）
#: exact     — derived from begin/end values with known flow timing
#: estimated — derived, but the intraday flow timing was unknown
#: reported  — typed in by the user from the platform's own 今日收益
#: manual    — entered/adjusted by hand with no derivation
CALCULATION_METHODS = ("exact", "estimated", "reported", "manual")

BENCHMARKS = ("CSI300", "SSE_COMPOSITE", "SP500", "NASDAQ")


@dataclass
class Platform:
    platform_id: Optional[int] = None
    name: str = ""
    kind: str = "other"            # PLATFORM_KINDS
    note: Optional[str] = None
    status: str = "active"
    created_at: Optional[str] = None


@dataclass
class Account:
    account_id: Optional[int] = None
    platform_id: int = 0
    name: str = ""
    currency: str = "CNY"
    note: Optional[str] = None
    status: str = "active"
    created_at: Optional[str] = None


@dataclass
class Product:
    product_id: Optional[int] = None
    account_id: int = 0
    name: str = ""
    product_type: str = "other"    # PRODUCT_TYPES
    ticker: Optional[str] = None   # 股票/ETF 代码（600519.SH 口径）
    currency: str = "CNY"
    market: Optional[str] = None   # SH / SZ / FUND / ...
    unit: str = "CNY"
    status: str = "active"
    created_at: Optional[str] = None

    @property
    def is_money_market(self) -> bool:
        return self.product_type in MONEY_MARKET_TYPES


@dataclass
class Transaction:
    txn_id: Optional[int] = None
    txn_date: str = ""             # ISO date
    product_id: int = 0
    txn_type: str = "buy"          # TXN_TYPES
    units: float = 0.0             # 份额/股数（现金类为金额）
    price: Optional[float] = None  # 净值/成交价
    amount: float = 0.0            # 成交金额（正数）
    fee: float = 0.0
    cash_flow: float = 0.0         # 外部现金流符号：转入 +，转出 -
    note: Optional[str] = None
    source: str = "manual"         # manual | import | system
    created_at: Optional[str] = None


@dataclass
class DailySnapshot:
    snapshot_id: Optional[int] = None
    snap_date: str = ""
    product_id: int = 0
    units: float = 0.0             # 收盘份额/股数
    nav: Optional[float] = None     # 单位净值（股票为收盘价）
    market_value: float = 0.0      # 收盘市值/金额
    cash_flow: float = 0.0         # 当日外部净流入
    note: Optional[str] = None
    source: str = "manual"
    created_at: Optional[str] = None


@dataclass
class IncomeRecord:
    """货币型产品的“万份收益”记录（spec §8.1）。"""
    income_id: Optional[int] = None
    income_date: str = ""
    product_id: int = 0
    beginning_units: float = 0.0
    ending_units: float = 0.0
    beginning_value: float = 0.0
    ending_value: float = 0.0
    cash_flow: float = 0.0
    daily_income: float = 0.0
    income_per_10000: float = 0.0
    annualized_yield: Optional[float] = None
    calculation_method: str = "exact"    # CALCULATION_METHODS
    source: str = "system"


@dataclass
class BenchmarkRecord:
    benchmark_id: Optional[int] = None
    record_date: str = ""
    benchmark: str = "CSI300"
    close: float = 0.0
    source: str = "canonical"


@dataclass
class AuditEntry:
    audit_id: Optional[int] = None
    timestamp: Optional[str] = None
    action: str = ""               # create | update | delete | manual_adjust
    actor: str = "local_user"
    object_type: str = ""
    object_id: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    reason: Optional[str] = None
