# -*- coding: utf-8 -*-
"""Board detection + trading-permission requirements.

A recommendation the user cannot act on is a bad recommendation, so every
plan row carries its board and whether the account currently satisfies
the board's eligibility rule.

A-share board eligibility (开通门槛，券商统一执行):

    科创板 STAR     688xxx.SH   50万元日均资产 + 24个月交易经验
    创业板 ChiNext  300xxx/301xxx.SZ  10万元日均资产 + 24个月交易经验
    北交所 BSE      4xxxxx/8xxxxx/920xxx  50万元 + 24个月
    主板 Main       600/601/603/605.SH, 000/001/002/003.SZ  无门槛
    基金/ETF        5xxxxx.SH, 15xxxx/16xxxx.SZ  无门槛

The 资产 threshold is the account's average daily assets over the
preceding 20 trading days; the 交易经验 requirement means a first-time
investor cannot pass regardless of cash, so it is tracked separately and
conservatively defaults to unknown (not automatically satisfied).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

STAR, CHINEXT, BSE, MAIN, FUND, UNKNOWN = (
    "STAR", "CHINEXT", "BSE", "MAIN", "FUND", "UNKNOWN")

BOARD_NAMES = {STAR: "科创板", CHINEXT: "创业板", BSE: "北交所",
               MAIN: "主板", FUND: "基金/ETF", UNKNOWN: "未知"}

#: 各板块的开通门槛（人民币元，20 个交易日日均资产）
BOARD_CAPITAL_REQUIREMENT = {
    STAR: 500_000.0,
    CHINEXT: 100_000.0,
    BSE: 500_000.0,
    MAIN: 0.0,
    FUND: 0.0,
    UNKNOWN: 0.0,
}

#: 交易经验要求（月）
BOARD_EXPERIENCE_MONTHS = {STAR: 24, CHINEXT: 24, BSE: 24,
                           MAIN: 0, FUND: 0, UNKNOWN: 0}


def board_of(symbol: str) -> str:
    """Classify a canonical symbol (600519.SH form)."""
    if not symbol or "." not in symbol:
        return UNKNOWN
    code, _, exch = symbol.partition(".")
    if exch == "SH":
        if code.startswith("688"):
            return STAR
        if code.startswith(("600", "601", "603", "605")):
            return MAIN
        if code.startswith("51") or code.startswith("56") or \
                code.startswith("58"):
            return FUND          # 上交所 ETF
        return UNKNOWN
    if exch == "SZ":
        if code.startswith(("300", "301")):
            return CHINEXT
        if code.startswith(("000", "001", "002", "003")):
            return MAIN
        if code.startswith(("15", "16", "18")):
            return FUND          # 深交所 ETF/LOF
        return UNKNOWN
    if exch == "BJ":
        return BSE
    return UNKNOWN


@dataclass
class Eligibility:
    board: str
    board_name: str
    capital_required: float
    experience_months: int
    capital_ok: bool
    experience_ok: Optional[bool]     # None = 账户交易经验未知
    can_buy: bool                     # 门槛是否全部满足
    reason: str                       # 不可购买的原因（可购买时为空）

    @property
    def restricted(self) -> bool:
        return not self.can_buy


def eligibility(symbol: str, account_capital: float,
                account_experience_months: Optional[int] = None
                ) -> Eligibility:
    """Whether the account can currently trade this board.

    `account_capital` compares against the board's 20-day average asset
    requirement. When the account's trading experience is unknown the
    result is a *warning*, not a block: the user may well have opened the
    board already — we flag what we cannot verify rather than silently
    assuming either way (documented in the user guide).
    """
    b = board_of(symbol)
    need = BOARD_CAPITAL_REQUIREMENT.get(b, 0.0)
    months = BOARD_EXPERIENCE_MONTHS.get(b, 0)
    capital_ok = account_capital >= need
    if account_experience_months is None:
        experience_ok = None
    else:
        experience_ok = account_experience_months >= months
    can_buy = capital_ok and (experience_ok is not False)
    reasons = []
    if not capital_ok:
        reasons.append(f"需{need/10000:.0f}万元日均资产（当前 "
                       f"{account_capital/10000:.1f}万元）")
    elif need and account_capital < need * 1.2:
        # within 20% of the threshold: the rule uses the 20-day AVERAGE
        # daily assets, which we cannot verify from a single balance
        reasons.append(f"门槛{need/10000:.0f}万元，当前 "
                       f"{account_capital/10000:.1f}万元仅临界达标"
                       f"（按20日均资产认定，请在券商核实）")
    if experience_ok is False:
        reasons.append(f"需{months}个月交易经验")
    if can_buy and months and experience_ok is None:
        reasons.append(f"需{months}个月交易经验（未核实，请在券商确认）")
    return Eligibility(board=b, board_name=BOARD_NAMES[b],
                       capital_required=need, experience_months=months,
                       capital_ok=capital_ok, experience_ok=experience_ok,
                       can_buy=can_buy, reason="；".join(reasons))
