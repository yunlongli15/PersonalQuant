# -*- coding: utf-8 -*-
"""Daily update service (STEP 7B): what happens when the user types in
today's numbers.

Spec §6: the user should only have to enter today's amount (and any cash
flow). Everything else — income, 万份收益, units, positions — is derived,
and derived values are labelled with how they were obtained
(exact / estimated) rather than presented as facts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from . import engine
from . import repository as repo


@dataclass
class UpdateEntry:
    product_id: int
    market_value: float
    units: Optional[float] = None
    nav: Optional[float] = None
    cash_flow: float = 0.0
    note: Optional[str] = None
    #: 平台 App 上显示的“今日收益”（元）。用户直接抄下来即可；系统会与
    #: 自己推导的收益对账，差异超过容忍度就提示（不覆盖用户填的数）。
    reported_income: Optional[float] = None


@dataclass
class UpdateResult:
    snap_date: str
    updated: List[dict] = field(default_factory=list)
    income_records: List[dict] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def _previous_snapshot(conn, product_id: int, before: str) -> Optional[dict]:
    rows = repo.list_snapshots(conn, product_id=product_id, end=before)
    rows = [r for r in rows if r["snap_date"] < before]
    return rows[-1] if rows else None


def _flows_on(conn, product_id: int, day: str) -> float:
    txns = repo.list_transactions(conn, product_id=product_id,
                                  start=day, end=day)
    return engine.net_external_flow(txns)


def _flow_units_on(conn, product_id: int, day: str,
                   nav: Optional[float]) -> float:
    """Signed units moved by today's EXTERNAL flows (from the ledger).

    Units are the right unit of account for 万份收益, but they must come
    from actual deposits/withdrawals — not from the units delta, which
    also contains reinvested income (that is the yield we are measuring).
    """
    from .models import EXTERNAL_FLOW_TYPES

    txns = [t for t in repo.list_transactions(conn, product_id=product_id,
                                              start=day, end=day)
            if t["txn_type"] in EXTERNAL_FLOW_TYPES]
    if not txns:
        return 0.0
    total = 0.0
    for t in txns:
        cf = float(t.get("cash_flow") or 0.0)
        if t.get("units"):
            total += float(t["units"])
        elif nav and nav > 0:
            total += cf / nav
        else:
            total += cf                     # NAV = 1 convention
    return total


def record_daily_update(conn, snap_date: str,
                        entries: Sequence[UpdateEntry],
                        max_stale_days: int = 7) -> UpdateResult:
    """Upsert one day of snapshots and derive the income records.

    For 货币型 products (cash / money_fund) an income_records row is
    written using the flow-aware effective-units rule (spec §8.3): the
    day's P&L is never diluted by a same-day deposit, and when the flow
    timing is unknown the record is marked `estimated`.
    """
    res = UpdateResult(snap_date=snap_date)
    from datetime import date as _d

    import pandas as pd

    for e in entries:
        product = repo.get_product(conn, e.product_id)
        prev = _previous_snapshot(conn, e.product_id, snap_date)
        if prev is None and e.cash_flow == 0.0 and \
                _flows_on(conn, e.product_id, snap_date) == 0.0:
            # first ever entry: treat today's value as a contribution
            res.warnings.append(
                f"{product['name']}：首次录入，金额 {e.market_value:,.2f} 元"
                f"已作为「初始投入」记账（这样收益从 0 开始算，不会把本金"
                f"当成收益）")
            repo.create_transaction(
                conn, snap_date, e.product_id, "deposit",
                amount=float(e.market_value),
                cash_flow=float(e.market_value),
                note="auto: opening balance", source="system")
        if prev is not None:
            gap = (pd.Timestamp(snap_date)
                   - pd.Timestamp(prev["snap_date"])).days
            if gap > max_stale_days:
                res.warnings.append(
                    f"{product['name']}：距上次录入（{prev['snap_date']}）"
                    f"已有 {gap} 天，中间空档不做插值（不猜数据）")

        units = e.units
        nav = e.nav
        if units is None:
            if nav and nav > 0:
                units = e.market_value / nav
            else:
                units = e.market_value      # NAV = 1 convention (money mkt)
        if nav is None and units:
            nav = e.market_value / units if units else None

        # the ledger is the source of truth for external flows: a deposit
        # recorded as a transaction must show up in the snapshot's
        # cash_flow, otherwise the P&L計算 counts it as investment gain
        ledger_flow = _flows_on(conn, e.product_id, snap_date)
        if ledger_flow and e.cash_flow and \
                abs(ledger_flow - e.cash_flow) > 1e-9:
            res.warnings.append(
                f"{product['name']}：填写的资金流 {e.cash_flow:.2f} 与台账"
                f"（{ledger_flow:.2f}）不一致 —— 以台账为准")
        cash_flow = ledger_flow if ledger_flow else e.cash_flow

        repo.upsert_snapshot(conn, snap_date, e.product_id, units=units,
                             nav=nav, market_value=e.market_value,
                             cash_flow=cash_flow, note=e.note,
                             source="manual")
        res.updated.append({"product_id": e.product_id, "units": units,
                            "nav": nav, "market_value": e.market_value,
                            "cash_flow": cash_flow})

        if product["product_type"] in ("cash", "money_fund") and prev:
            flow_units = _flow_units_on(conn, e.product_id, snap_date, nav)
            day = engine.money_market_day(
                beginning_units=float(prev["units"]),
                ending_units=float(units or 0.0),
                beginning_value=float(prev["market_value"]),
                ending_value=float(e.market_value),
                flows=[(flow_units, None)] if flow_units else [],
                external_net_flow=cash_flow)
            repo.upsert_income(
                conn, snap_date, e.product_id,
                beginning_units=day.beginning_units,
                ending_units=day.ending_units,
                beginning_value=float(prev["market_value"]),
                ending_value=float(e.market_value),
                cash_flow=cash_flow, daily_income=day.daily_income,
                income_per_10000=day.income_per_10000,
                annualized_yield=day.annualized_yield,
                calculation_method=day.calculation_method,
                source="system")
            res.income_records.append({"product_id": e.product_id,
                                       **day.as_record()})
            derived = day.daily_income
        else:
            derived = (float(e.market_value)
                       - float(prev["market_value"]) - cash_flow
                       if prev is not None else None)

        # 用户从平台 App 抄下来的“今日收益”：照原样入库（calculation
        # _method='reported'，来源是用户而不是系统），并与系统推导值对账。
        # 对不上时只提示，不覆盖——平台口径可能有费用/分红/确认日差异，
        # 谁对谁错要人看，不能由程序替用户决定。
        if e.reported_income is not None:
            reps = (float(prev["units"]) if prev else 0.0)
            if not reps and units:
                reps = float(units)
            per_10000 = (e.reported_income / reps * 10000.0) if reps else 0.0
            repo.upsert_income(
                conn, snap_date, e.product_id,
                beginning_units=float(prev["units"]) if prev else 0.0,
                ending_units=float(units or 0.0),
                beginning_value=float(prev["market_value"]) if prev else 0.0,
                ending_value=float(e.market_value),
                cash_flow=cash_flow, daily_income=float(e.reported_income),
                income_per_10000=per_10000,
                annualized_yield=(per_10000 / 10000.0 * 365.0
                                  if per_10000 else None),
                calculation_method="reported", source="user")
            res.income_records.append({
                "product_id": e.product_id, "daily_income":
                float(e.reported_income),
                "calculation_method": "reported"})
            if derived is not None:
                diff = float(e.reported_income) - derived
                tol = max(0.05, abs(derived) * 0.2)
                if abs(diff) > tol:
                    res.warnings.append(
                        f"{product['name']}：你填的今日收益 "
                        f"{e.reported_income:.2f} 与系统按金额变动推导的 "
                        f"{derived:.2f} 相差 {diff:+.2f} 元 —— 已按你填的"
                        f"数字记录；若差额来自费用/分红，建议在"
                        f"「交易流水」补一笔")
    return res


def snapshot_from_amount(conn, snap_date: str, product_id: int,
                         amount: float, cash_flow: float = 0.0,
                         **kw) -> UpdateResult:
    """The one-line case: 'today this product is worth X'."""
    return record_daily_update(
        conn, snap_date,
        [UpdateEntry(product_id=product_id, market_value=amount,
                     cash_flow=cash_flow, **kw)])


def latest_summary(conn, as_of: Optional[str] = None) -> dict:
    """Everything the dashboard needs, in one call (spec §26/§47)."""
    perf = engine.performance(conn, end=as_of)
    summary = engine.portfolio_summary(conn, as_of=as_of)
    out = {"as_of": summary.get("as_of"), **summary}
    if not perf.get("empty"):
        curve = perf["curve"]
        out["net_worth"] = perf["net_worth"]
        out["total_pnl"] = perf["total_pnl"]
        out["twr"] = perf["twr"]
        out["mwr_xirr"] = perf["mwr_xirr"]
        out["external_net_flow"] = perf["external_net_flow"]
        out["daily_return"] = perf.get("daily_return")
        if len(curve) >= 2:
            out["day_pnl"] = float(curve["pnl"].iloc[-1])
        out["curve"] = curve
        # period P&L (month / year to date)
        c = curve.set_index("snap_date")
        if len(c):
            last = c.index[-1]
            month_start = last.replace(day=1)
            year_start = last.replace(month=1, day=1)
            out["month_pnl"] = float(c.loc[c.index >= month_start,
                                           "pnl"].sum())
            out["year_pnl"] = float(c.loc[c.index >= year_start, "pnl"].sum())
    else:
        out.update({"net_worth": 0.0, "total_pnl": 0.0, "twr": None,
                    "mwr_xirr": None, "day_pnl": 0.0, "month_pnl": 0.0,
                    "year_pnl": 0.0})
    return out


def decompose_period(conn, start: str, end: str) -> dict:
    """Net-worth change decomposition for a period (spec §27)."""
    vs = engine.value_series(conn, start, end)
    txns = [t for t in repo.list_transactions(conn, start=start, end=end)]
    begin = engine._value_before(conn, str(vs["snap_date"].iloc[0].date())) \
        if not vs.empty else 0.0
    if vs.empty:
        begin = engine._value_before(conn, end)
    end_value = float(vs["value"].iloc[-1]) if not vs.empty \
        else engine._value_before(conn, end)
    d = engine.decompose_change(begin, end_value, txns)
    return {"start": start, "end": end, "begin_value": begin,
            "end_value": end_value, **d.__dict__}
