# -*- coding: utf-8 -*-
"""账本：append-only 事件流 + 现金核算 + 对账恒等式。

**账本是真相，state.json 只是指针。** 任何"修正"都必须是一条新事件，
绝不回头改旧行。

现金恒等式（每次运行结束都要成立）：

    cash = initial_capital
         - Σ 买入成交金额 - Σ 全部费用
         + Σ 卖出成交金额

事件类型（spec §25）
--------------------
    EXPERIMENT_CREATED  ORDER_CREATED  ORDER_FILLED  ORDER_NO_FILL
    ORDER_CANCELLED    POSITION_OPENED  POSITION_CLOSED
    CASH_RESERVE       CASH_RELEASE     FEE           RUN_SUMMARY
"""

from __future__ import annotations

from typing import Dict, List

import pandas as pd


class ReconciliationError(RuntimeError):
    """对账不通过。**绝不自动改账** —— 停下来让人核对。"""


def cash_from_ledger(events: List[dict], initial_capital: float) -> float:
    """从账本重算现金（真相）。"""
    cash = float(initial_capital)
    for e in events:
        t = e.get("type")
        if t == "ORDER_FILLED":
            cash -= float(e.get("value") or 0.0) + float(e.get("fee") or 0.0)
        elif t == "POSITION_CLOSED":
            cash += float(e.get("value") or 0.0) - float(e.get("fee") or 0.0)
    return cash


def fees_from_ledger(events: List[dict]) -> float:
    return float(sum(float(e.get("fee") or 0.0) for e in events
                     if e.get("type") in ("ORDER_FILLED", "POSITION_CLOSED")))


def check_invariants(state: dict, prices: Dict[str, float]) -> Dict[str, float]:
    """结构性恒等式：非负、不重复计量、组合价值自洽。"""
    cash = float(state["cash"])
    reserved = float(state.get("reserved_cash") or 0.0)
    avail = cash - reserved
    pos_value = 0.0
    for sym, p in (state.get("positions") or {}).items():
        if p.get("status") not in ("OPEN", "PENDING_EXIT"):
            continue
        shares = int(p.get("entry_shares", 0))
        if shares < 0:
            raise ReconciliationError(f"{sym} 持仓股数为负：{shares}")
        px = prices.get(sym, p.get("last_price"))
        if px is None or not pd.notna(px):
            px = p.get("entry_price", 0.0)
        pos_value += shares * float(px or 0.0)
    if cash < -1e-6:
        raise ReconciliationError(f"cash 为负：{cash:,.2f}")
    if reserved < -1e-6:
        raise ReconciliationError(f"reserved_cash 为负：{reserved:,.2f}")
    if avail < -1e-6:
        raise ReconciliationError(
            f"available_cash 为负：{avail:,.2f}（cash {cash:,.2f} - "
            f"reserved {reserved:,.2f}）—— 买单预留超过了账上现金")
    total = cash + pos_value
    return {"cash": cash, "reserved_cash": reserved,
            "available_cash": avail, "position_value": pos_value,
            "portfolio_value": total}


def reconcile(state: dict, events: List[dict],
              prices: Dict[str, float]) -> Dict[str, float]:
    """完整对账：结构恒等式 + 账本重算的现金必须等于 state 记的现金。"""
    totals = check_invariants(state, prices)
    expected = cash_from_ledger(events, state["initial_capital"])
    actual = float(state["cash"])
    if abs(expected - actual) > 0.01:
        raise ReconciliationError(
            f"账本重算现金 {expected:,.2f} ≠ state 记的 {actual:,.2f}"
            f"（差 {expected - actual:+,.2f}）。**不自动改账** —— "
            f"请人工核对 experiments/*/ledger.jsonl 与 state.json。")
    totals["cash_from_ledger"] = expected
    totals["fees_total"] = fees_from_ledger(events)
    return totals
