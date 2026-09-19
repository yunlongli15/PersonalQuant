# -*- coding: utf-8 -*-
"""Wealth calculation engine (STEP 7B).

The one rule everything follows (spec §7):

    Investment P&L = Ending Value - Beginning Value - Net External Flow

External flows are ONLY deposit / withdrawal / transfer_in / transfer_out.
Buy / sell / subscribe / redeem are INTERNAL: they move money between the
cash and the holdings of the same product and must never change P&L.
Getting this wrong is the classic personal-accounting bug the spec calls
out, so the ledger enforces it (wealth/repository.create_transaction) and
every function here takes the external flow explicitly.

Money-market products (spec §8) additionally report 万份收益
(income_per_10000) with intraday-flow-aware effective units, so a
same-day deposit does not fabricate a yield drop (spec §8.3).

Returns (spec §28): simple, time-weighted (TWR, flow-adjusted) and
money-weighted (XIRR). Annualized 万份收益 uses the standard
income_per_10000 / 10000 * 365 convention.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd

DAYS_PER_YEAR = 365.0
TRADING_DAYS = 252.0


# ---------------------------------------------------------------------------
# 1. P&L
# ---------------------------------------------------------------------------

def investment_pnl(beginning_value: float, ending_value: float,
                   external_net_flow: float) -> float:
    """Spec §7. `external_net_flow` is signed (deposit +, withdrawal -)."""
    return ending_value - beginning_value - external_net_flow


def net_external_flow(txns: Sequence[dict]) -> float:
    """Signed external flow of a ledger slice (non-external rows -> 0)."""
    from .models import EXTERNAL_FLOW_TYPES

    return float(sum(t.get("cash_flow", 0.0) or 0.0 for t in txns
                     if t.get("txn_type") in EXTERNAL_FLOW_TYPES))


# ---------------------------------------------------------------------------
# 2. money-market products: 万份收益 (spec §8)
# ---------------------------------------------------------------------------

@dataclass
class MoneyMarketDay:
    beginning_units: float
    ending_units: float
    effective_units: float
    daily_income: float
    income_per_10000: float
    annualized_yield: Optional[float]
    calculation_method: str          # exact | estimated
    cash_flow: float = 0.0

    def as_record(self) -> dict:
        return {
            "beginning_units": self.beginning_units,
            "ending_units": self.ending_units,
            "daily_income": self.daily_income,
            "income_per_10000": self.income_per_10000,
            "annualized_yield": self.annualized_yield,
            "calculation_method": self.calculation_method,
            "cash_flow": self.cash_flow,
        }


def effective_units(beginning_units: float,
                    flows: Sequence[Tuple[float, Optional[float]]]
                    ) -> Tuple[float, bool]:
    """Units actually exposed to today's income.

    `flows` = [(units_signed, day_fraction)] where day_fraction is the
    fraction of the day remaining after the flow (0 = at close, 1 = at
    open). When the timing is unknown the caller passes None and the
    convention is 0.5 (half a day), flagged as estimated — the alternative
    (using ending units) is what fabricates the yield drop in spec §8.3.

    Returns (effective_units, timing_known).
    """
    total = float(beginning_units)
    known = True
    for units, frac in flows:
        if frac is None:
            frac = 0.5
            known = False
        total += float(units) * float(frac)
    return total, known


def money_market_day(
    beginning_units: float,
    ending_units: float,
    beginning_value: float,
    ending_value: float,
    flows: Sequence[Tuple[float, Optional[float]]] = (),
    external_net_flow: float = 0.0,
) -> MoneyMarketDay:
    """One day of a 货币基金/现金管理 product.

    daily_income is the P&L of the day (value change net of external
    flows); income_per_10000 scales it to 10,000 units of average exposure.
    """
    income = investment_pnl(beginning_value, ending_value,
                            external_net_flow)
    eff, known = effective_units(beginning_units, flows)
    if eff <= 0:
        return MoneyMarketDay(beginning_units, ending_units, eff, income,
                              0.0, None,
                              "exact" if known else "estimated",
                              external_net_flow)
    per_10000 = income / eff * 10000.0
    annualized = per_10000 / 10000.0 * DAYS_PER_YEAR
    return MoneyMarketDay(beginning_units, ending_units, eff, income,
                          per_10000, annualized,
                          "exact" if known else "estimated",
                          external_net_flow)


def seven_day_annualized(per_10000_series: Sequence[float]) -> Optional[float]:
    """7-day annualized yield from the last (up to) 7 万份收益 values."""
    vals = [v for v in per_10000_series if v is not None]
    if not vals:
        return None
    last = vals[-7:]
    avg = sum(last) / len(last)
    return avg / 10000.0 * DAYS_PER_YEAR


# ---------------------------------------------------------------------------
# 3. holdings from the ledger (nav-based products: funds, stocks)
# ---------------------------------------------------------------------------

@dataclass
class Holding:
    product_id: int
    units: float = 0.0
    avg_cost: float = 0.0            # per unit, dividends not subtracted
    realized_pnl: float = 0.0
    fees_paid: float = 0.0
    dividends: float = 0.0
    invested: float = 0.0            # 累计投入本金（外部流入）

    def market_value(self, nav: float) -> float:
        return self.units * nav if nav else 0.0

    def unrealized_pnl(self, nav: float) -> float:
        return self.market_value(nav) - self.units * self.avg_cost


def holdings_from_ledger(txns: Sequence[dict]) -> Holding:
    """Average-cost bookkeeping over one product's transactions.

    Rules (documented, tested):
      buy / subscribe      : units += u; cost += amount + fee
      sell / redeem        : units -= u; realized += (price*u - fee) - avg_cost*u
      dividend             : realized P&L (cash received, units unchanged)
      fee                  : fees_paid += fee (realized P&L reduced)
      all fees are also tracked separately and never double-counted
    """
    h = Holding(product_id=int(txns[0]["product_id"]) if txns else 0)
    for t in sorted(txns, key=lambda r: (r["txn_date"], r["txn_id"] or 0)):
        ttype = t["txn_type"]
        units = float(t.get("units") or 0.0)
        amount = float(t.get("amount") or 0.0)
        fee = float(t.get("fee") or 0.0)
        price = t.get("price")
        h.fees_paid += fee
        if ttype in ("buy", "subscribe"):
            px = float(price) if price else (amount / units if units else 0.0)
            h.units += units
            h.invested += amount + fee
            # weighted average cost including fees paid on entry
            total_cost = h.avg_cost * (h.units - units) + amount + fee
            h.avg_cost = total_cost / h.units if h.units > 0 else 0.0
            if px is None:                      # pragma: no cover
                continue
        elif ttype in ("sell", "redeem"):
            px = float(price) if price else (amount / units if units else 0.0)
            h.units -= units
            h.realized_pnl += (amount - fee) - h.avg_cost * units
            h.invested -= h.avg_cost * units
            if h.units <= 1e-12:
                h.units = 0.0
        elif ttype == "dividend":
            h.dividends += amount
            h.realized_pnl += amount
        elif ttype == "fee":
            h.realized_pnl -= fee if fee else amount
        elif ttype == "split":
            # 拆股/送股：units 存的是**比例**（2.0 = 2 拆 1，股数翻倍、价格减半）。
            # 总成本不变，所以均价按比例缩小；不需要额外现金，也不产生损益。
            # 比例非法（<=0）时忽略并保持原状，绝不把持仓算成 0 或负数。
            if units > 0:
                h.units *= units
                h.avg_cost /= units
    return h


# ---------------------------------------------------------------------------
# 4. returns: TWR / XIRR (spec §28)
# ---------------------------------------------------------------------------

def _npv(rate: float, t_days: Sequence[float], amounts: Sequence[float]
         ) -> float:
    return sum(a / (1.0 + rate) ** (t / DAYS_PER_YEAR)
               for t, a in zip(t_days, amounts))


def xirr(dates: Sequence, amounts: Sequence[float],
         guess: float = 0.1) -> Optional[float]:
    """Money-weighted return (XIRR) by bisection on the NPV.

    `amounts` follow the cash-flow convention: investments are negative,
    final value (and withdrawals) positive. Returns None when there is no
    sign change (undefined) — never a made-up number.
    """
    if len(dates) != len(amounts) or len(dates) < 2:
        return None
    amts = [float(a) for a in amounts]
    if not (any(a > 0 for a in amts) and any(a < 0 for a in amts)):
        return None
    d0 = pd.Timestamp(min(dates))
    t_days = [float((pd.Timestamp(d) - d0).days) for d in dates]
    if all(t == 0 for t in t_days):
        return None

    lo, hi = -0.9999, 10.0
    f_lo, f_hi = _npv(lo, t_days, amts), _npv(hi, t_days, amts)
    if f_lo * f_hi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2.0
        f_mid = _npv(mid, t_days, amts)
        if abs(f_mid) < 1e-10:
            return mid
        if f_lo * f_mid <= 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2.0


def twr_period_return(begin_value: float, end_value: float,
                      flow: float, flow_at_end: bool = True
                      ) -> Optional[float]:
    """Single-period time-weighted return, flow-aware.

    Flows are assumed to arrive at the END of the day by default (the
    conservative convention for a personal ledger that records end-of-day
    balances): the day's return is measured on the capital that was
    invested for the day.

        r = (end - flow - begin) / begin
    """
    if begin_value is None or begin_value <= 0:
        return None
    base = begin_value
    end = end_value - (flow if flow_at_end else 0.0)
    return (end - base) / base


def twr(series: Sequence[dict]) -> Optional[float]:
    """Chain-linked TWR from [{date, value, flow}].

    Valuation dates with no prior value are skipped (the first point is
    the base, not a return). Returns the cumulative return over the
    window, or None when there is not enough information.
    """
    if len(series) < 2:
        return None
    cum = 1.0
    n = 0
    for prev, cur in zip(series[:-1], series[1:]):
        r = twr_period_return(prev["value"], cur["value"],
                              float(cur.get("flow") or 0.0))
        if r is None:
            continue
        cum *= (1.0 + r)
        n += 1
    if n == 0:
        return None
    return cum - 1.0


def annualize(cumulative_return: float, days: float) -> Optional[float]:
    if days <= 0 or cumulative_return <= -1.0:
        return None
    return (1.0 + cumulative_return) ** (DAYS_PER_YEAR / days) - 1.0


# ---------------------------------------------------------------------------
# 5. net-worth change decomposition (spec §27)
# ---------------------------------------------------------------------------

@dataclass
class ChangeDecomposition:
    external_contributions: float = 0.0
    withdrawals: float = 0.0
    investment_pnl: float = 0.0
    dividends: float = 0.0
    fees: float = 0.0
    net_change: float = 0.0
    reconciliation_error: float = 0.0

    def as_row(self) -> List[Tuple[str, float]]:
        return [("External Contributions", self.external_contributions),
                ("Investment P&L", self.investment_pnl),
                ("Dividends", self.dividends),
                ("Fees", -self.fees),
                ("Withdrawals", -self.withdrawals),
                ("Net Change", self.net_change)]


def decompose_change(begin_value: float, end_value: float,
                     txns: Sequence[dict]) -> ChangeDecomposition:
    """Split the change in total value into its drivers (spec §27).

    Investment P&L is the residual after external flows, so the parts
    always reconcile with the total change:
        net_change = contributions - withdrawals + pnl
        pnl        = investment_pnl + dividends - fees
    (dividends and fees are shown separately but live inside the residual
    investment result; they are NOT added on top of it).
    """
    contrib = sum(float(t.get("cash_flow") or 0.0) for t in txns
                  if t["txn_type"] in ("deposit", "transfer_in"))
    withdraw = sum(-float(t.get("cash_flow") or 0.0) for t in txns
                   if t["txn_type"] in ("withdrawal", "transfer_out"))
    divs = sum(float(t.get("amount") or 0.0) for t in txns
               if t["txn_type"] == "dividend")
    fees = sum(float(t.get("fee") or 0.0) for t in txns)
    net_change = end_value - begin_value
    pnl_total = investment_pnl(begin_value, end_value, contrib - withdraw)
    d = ChangeDecomposition(
        external_contributions=contrib, withdrawals=withdraw,
        investment_pnl=pnl_total - divs + fees,
        dividends=divs, fees=fees, net_change=net_change)
    d.reconciliation_error = (
        d.external_contributions - d.withdrawals + d.investment_pnl
        + d.dividends - d.fees - d.net_change)
    return d


# ---------------------------------------------------------------------------
# 6. portfolio views over the wealth DB
# ---------------------------------------------------------------------------

def value_series(conn, start: Optional[str] = None,
                 end: Optional[str] = None) -> pd.DataFrame:
    """Daily total market value + external flow.

    Carry-forward rule: the user rarely updates every product on the same
    day (they add a fund on Tuesday, another on Wednesday), and a product
    that was not touched still holds its previous value. So the series is
    built per product and forward-filled before summing — otherwise the
    day after a partial update looks like those products vanished, which
    shows up as a fake crash in net worth and a fake loss in P&L.
    """
    sql = ("SELECT snap_date, product_id, market_value, cash_flow "
           "FROM daily_snapshots WHERE 1=1")
    params: List = []
    if start:
        sql += " AND snap_date >= ?"
        params.append(start)
    if end:
        sql += " AND snap_date <= ?"
        params.append(end)
    df = pd.DataFrame([dict(r) for r in conn.execute(sql, params)])
    if df.empty:
        return df
    df["snap_date"] = pd.to_datetime(df["snap_date"])
    wide = df.pivot_table(index="snap_date", columns="product_id",
                          values="market_value", aggfunc="last")
    wide = wide.sort_index().ffill()          # 未录入的产品沿用上次的值
    flow = df.groupby("snap_date")["cash_flow"].sum()
    out = pd.DataFrame({"value": wide.sum(axis=1)})
    out["flow"] = flow.reindex(out.index).fillna(0.0)
    return out.reset_index()


def _value_before(conn, date_str: str) -> float:
    """Total market value of the last snapshot strictly before `date_str`
    (0.0 when the window starts at account inception)."""
    row = conn.execute(
        "SELECT SUM(market_value) AS v FROM daily_snapshots WHERE "
        "snap_date = (SELECT MAX(snap_date) FROM daily_snapshots "
        "WHERE snap_date < ?)", (date_str,)).fetchone()
    return float(row["v"]) if row and row["v"] is not None else 0.0


def performance(conn, start: Optional[str] = None,
                end: Optional[str] = None) -> dict:
    """Net worth curve, cumulative investment P&L, and return set.

    P&L convention: each day's investment P&L is Δvalue − external flow,
    with the first day measured from the value carried into the window
    (`_value_before`, 0 for an account that starts inside the window).
    This is what makes `total_pnl` a real investment result rather than a
    capital counter (spec §7).
    """
    vs = value_series(conn, start, end)
    if vs.empty:
        return {"empty": True}
    vs = vs.sort_values("snap_date").reset_index(drop=True)
    base_value = _value_before(conn, str(vs["snap_date"].iloc[0].date()))
    # Investment P&L per day: Δvalue - external flow of that day.
    vs["delta"] = vs["value"].diff().fillna(vs["value"].iloc[0] - base_value)
    vs["flow"] = vs["flow"].fillna(0.0)
    vs["pnl"] = vs["delta"] - vs["flow"]
    vs["cum_pnl"] = vs["pnl"].cumsum()
    vs["invested"] = vs["flow"].cumsum()
    series = [{"date": r.snap_date, "value": r.value, "flow": r.flow}
              for r in vs.itertuples()]
    tw = twr(series)
    days = (vs["snap_date"].iloc[-1] - vs["snap_date"].iloc[0]).days
    mwr = xirr(
        list(vs["snap_date"]) + [vs["snap_date"].iloc[-1]],
        [-f for f in vs["flow"]] + [float(vs["value"].iloc[-1])])
    daily = vs["value"].pct_change()
    out = {
        "empty": False,
        "curve": vs,
        "net_worth": float(vs["value"].iloc[-1]),
        "net_worth_start": float(vs["value"].iloc[0]),
        "base_value": base_value,
        "total_pnl": float(vs["cum_pnl"].iloc[-1]),
        "external_net_flow": float(vs["flow"].sum()),
        "twr": tw,
        "mwr_xirr": mwr,
        "annualized_twr": annualize(tw, days) if tw is not None else None,
        "days": int(days),
    }
    out["daily_return"] = _daily_return_with_flows(vs)
    out["daily_returns"] = vs.set_index("snap_date")["pnl"] / \
        vs.set_index("snap_date")["value"].shift(1)
    return out


def _daily_return_with_flows(vs: pd.DataFrame) -> Optional[float]:
    """Latest daily time-weighted return (flow-adjusted, spec §28)."""
    if len(vs) < 2:
        return None
    last = vs.iloc[-1]
    prev = vs.iloc[-2]
    return twr_period_return(float(prev["value"]), float(last["value"]),
                             float(last["flow"]))


def portfolio_summary(conn, as_of: Optional[str] = None) -> dict:
    """Totals + realized/unrealized/income/fees + allocations (spec §29).

    Holdings come from the `positions` table (written by the update
    engine); values from the latest daily_snapshots up to `as_of`.
    """
    from . import repository as repo

    products = {p["product_id"]: p for p in
                repo.list_products(conn, include_inactive=True)}
    platforms = {p["platform_id"]: p for p in repo.list_platforms(conn)}
    accounts = {a["account_id"]: a for a in repo.list_accounts(conn)}
    txns = repo.list_transactions(conn)
    if as_of:
        txns = [t for t in txns if t["txn_date"] <= as_of]

    # latest snapshot per product (<= as_of)
    if as_of:
        snap_rows = repo.list_snapshots(conn, end=as_of)
    else:
        snap_rows = repo.list_snapshots(conn)
    latest: Dict[int, dict] = {}
    for s in snap_rows:
        latest[s["product_id"]] = s          # list is date-ascending

    total = 0.0
    by_category: Dict[str, float] = {}
    by_platform: Dict[str, float] = {}
    by_product: Dict[str, float] = {}
    holdings = []
    for pid, s in latest.items():
        p = products.get(pid)
        if not p:
            continue
        mv = float(s["market_value"] or 0.0)
        total += mv
        ptype = p["product_type"]
        cat = _category_of(ptype)
        by_category[cat] = by_category.get(cat, 0.0) + mv
        plat = platforms.get(accounts.get(p["account_id"], {})
                             .get("platform_id"), {}).get("name", "?")
        by_platform[plat] = by_platform.get(plat, 0.0) + mv
        by_product[p["name"]] = by_product.get(p["name"], 0.0) + mv
        h = holdings_from_ledger([t for t in txns if t["product_id"] == pid])
        nav = s["nav"]
        holdings.append({
            "product_id": pid, "name": p["name"],
            "product_type": ptype, "platform": plat,
            "units": float(s["units"] or 0.0), "nav": nav,
            "market_value": mv,
            "avg_cost": h.avg_cost,
            "unrealized_pnl": (mv - h.units * h.avg_cost) if nav else None,
            "realized_pnl": h.realized_pnl,
            "dividends": h.dividends, "fees": h.fees_paid,
            "weight": (mv / total) if total else 0.0,
        })

    fees_total = sum(float(t.get("fee") or 0.0) for t in txns)
    divs_total = sum(float(t.get("amount") or 0.0) for t in txns
                     if t["txn_type"] == "dividend")
    contrib = sum(float(t.get("cash_flow") or 0.0) for t in txns
                  if t["txn_type"] in ("deposit", "transfer_in"))
    withdraw = sum(-float(t.get("cash_flow") or 0.0) for t in txns
                   if t["txn_type"] in ("withdrawal", "transfer_out"))
    realized = sum(holdings_from_ledger(
        [t for t in txns if t["product_id"] == pid]).realized_pnl
        for pid in latest)
    unrealized = sum((h["unrealized_pnl"] or 0.0) for h in holdings)
    return {
        "as_of": (max((s["snap_date"] for s in latest.values()),
                      default=None)),
        "total_value": total,
        "invested_capital": contrib - withdraw,
        "realized_pnl": realized,
        "unrealized_pnl": unrealized,
        "income": divs_total,
        "fees": fees_total,
        "holdings": sorted(holdings, key=lambda h: -h["market_value"]),
        "by_category": by_category,
        "by_platform": by_platform,
        "by_product": by_product,
    }


def _category_of(product_type: str) -> str:
    if product_type in ("cash", "money_fund"):
        return "Cash"
    if product_type in ("bond_fund",):
        return "Bond Funds"
    if product_type in ("index_fund", "qdii"):
        return "Index Funds"
    if product_type in ("stock", "etf"):
        return "Stocks"
    if product_type == "gold":
        return "Gold"
    return "Other"


def positions_at(conn, product_id: int, as_of: str) -> Holding:
    """Ledger-derived holding of one product up to `as_of`."""
    from . import repository as repo

    txns = repo.list_transactions(conn, product_id=product_id, end=as_of)
    return holdings_from_ledger(txns)


def write_positions(conn, as_of: str, navs: Dict[int, float]) -> int:
    """Materialise the `positions` table for one date (spec §29)."""
    from . import repository as repo

    rows = []
    for p in repo.list_products(conn, include_inactive=True):
        pid = p["product_id"]
        h = positions_at(conn, pid, as_of)
        nav = navs.get(pid)
        mv = h.units * nav if nav else 0.0
        if h.units == 0 and mv == 0:
            continue
        rows.append({
            "product_id": pid, "units": h.units, "avg_cost": h.avg_cost,
            "market_value": mv, "realized_pnl": h.realized_pnl,
            "unrealized_pnl": (mv - h.units * h.avg_cost) if nav else 0.0,
        })
    return repo.replace_positions(conn, as_of, rows)


# ---------------------------------------------------------------------------
# 12. cash & reconciliation (STEP 11, spec §14 / §52)
# ---------------------------------------------------------------------------

def cash_balance(conn, account_id: Optional[int] = None) -> dict:
    """现金余额的两种口径 —— 都给出，差值本身就是对账信号。

    recorded : 现金类产品（cash / money_market）的最新市值。
               这是用户实际记录下来的"账户里有多少钱"。
    implied  : 由**流水**推导的现金净额：
               外部净流入 − 买入/申购 + 卖出/赎回 + 分红 − 独立费用。
               如果用户从不记录现金类产品，这个值才是唯一可用的现金口径。

    两者不一致不代表谁错了：券商账户的现金本来就不在产品表里。
    """
    from .models import MONEY_MARKET_TYPES

    where, params = "", []
    if account_id is not None:
        where = " AND a.account_id = ?"
        params = [account_id]

    rows = conn.execute(
        f"""SELECT p.product_type, p.product_id,
                   COALESCE(s.market_value, 0) AS market_value
            FROM products p
            JOIN accounts a ON a.account_id = p.account_id
            LEFT JOIN daily_snapshots s
                   ON s.product_id = p.product_id
                  AND s.snap_date = (SELECT MAX(s2.snap_date)
                                     FROM daily_snapshots s2
                                     WHERE s2.product_id = p.product_id)
            WHERE p.status = 'active'{where}""", params).fetchall()
    recorded = sum(float(r["market_value"] or 0.0) for r in rows
                   if r["product_type"] in MONEY_MARKET_TYPES)

    txn_sql = """SELECT t.txn_type, t.amount, t.fee, t.cash_flow
                 FROM transactions t
                 JOIN products p ON p.product_id = t.product_id
                 JOIN accounts a ON a.account_id = p.account_id
                 WHERE 1=1"""
    if account_id is not None:
        txn_sql += " AND a.account_id = ?"
    inflow = outflow = 0.0
    for r in conn.execute(txn_sql, params).fetchall():
        t = r["txn_type"]
        amt = float(r["amount"] or 0.0)
        fee = float(r["fee"] or 0.0)
        if t in ("deposit", "transfer_in"):
            inflow += amt
        elif t in ("withdrawal", "transfer_out"):
            outflow += amt
        elif t in ("buy", "subscribe"):
            outflow += amt + fee
        elif t in ("sell", "redeem"):
            inflow += amt - fee
        elif t == "dividend":
            inflow += amt
        elif t == "fee":
            outflow += fee if fee else amt
    return {
        "recorded": float(recorded),
        "implied": float(inflow - outflow),
        "external_inflow": float(inflow),
        "external_outflow": float(outflow),
    }


def reconcile(conn, tolerance: float = 1.0) -> dict:
    """对账（spec §52）：各类资产 + 现金 = 总资产，误差在容差内。

    同时对每个**由流水重建**的持仓做一次一致性检查：
    账本推导出的股数 与 positions 表里写的 是否一致（§53）。
    """
    summary = portfolio_summary(conn)
    by_cat = summary.get("by_category", {})
    total = float(summary.get("total_value") or 0.0)
    parts = {k: float(v or 0.0) for k, v in by_cat.items()}
    parts_total = sum(parts.values())
    diff = total - parts_total
    return {
        "as_of": summary.get("as_of"),
        "total_value": total,
        "by_category": parts,
        "sum_of_parts": parts_total,
        "difference": diff,
        "tolerance": float(tolerance),
        "ok": abs(diff) <= float(tolerance),
    }


def position_consistency(conn, as_of: Optional[str] = None,
                         tol: float = 1e-6) -> List[dict]:
    """positions 表 vs 由 transactions 重建的持仓（spec §53）。

    持仓的唯一真相是流水；positions 只是物化缓存。任何不一致都要报出来，
    并标明是"手工 override"还是"真的算错了"。
    """
    stored = {}
    for r in conn.execute(
            "SELECT product_id, units, source FROM positions "
            "WHERE as_of = (SELECT MAX(as_of) FROM positions)").fetchall():
        stored[int(r["product_id"])] = (float(r["units"] or 0.0),
                                        r["source"] or "system")
    out = []
    for p in conn.execute("SELECT product_id, name FROM products").fetchall():
        pid = int(p["product_id"])
        txns = [dict(r) for r in conn.execute(
            "SELECT * FROM transactions WHERE product_id = ?", (pid,))]
        derived = holdings_from_ledger(txns).units
        if not txns:
            continue
        s_units, src = stored.get(pid, (None, "missing"))
        if s_units is None:
            out.append({"product_id": pid, "name": p["name"],
                        "derived_units": derived, "stored_units": None,
                        "delta": None, "status": "not_materialised",
                        "source": src})
            continue
        delta = s_units - derived
        ok = abs(delta) <= tol
        out.append({
            "product_id": pid, "name": p["name"],
            "derived_units": derived, "stored_units": s_units,
            "delta": delta,
            "status": "ok" if ok else
                      ("manual_override" if src == "manual" else "MISMATCH"),
            "source": src,
        })
    return out


def value_positions(conn, prices: Optional[Dict[str, float]] = None,
                    account_id: Optional[int] = None) -> dict:
    """由**流水**重建持仓并按给定价格估值（STEP 11）。

    与 `portfolio_summary` 的区别：
      - portfolio_summary 读的是 `daily_snapshots`（用户每天报的金额），
        适合"货币基金/理财"这类用户只报余额的产品；
      - 本函数读的是 `transactions`（账本真相），适合**券商持仓**这类
        有明确买卖记录的标的。导入历史成交后还没有任何快照时，
        只有这个口径能算出市值。

    prices: {symbol: 最新价}。缺价的标的按 avg_cost 计价并在 missing_price
    里列出 —— **不猜价格，也不静默当成 0**。
    """
    from .models import MONEY_MARKET_TYPES

    prices = prices or {}
    where, params = "", []
    if account_id is not None:
        where = " AND p.account_id = ?"
        params = [account_id]

    rows = conn.execute(
        f"""SELECT p.product_id, p.name, p.ticker, p.product_type,
                   p.account_id, a.name AS account
            FROM products p JOIN accounts a ON a.account_id = p.account_id
            WHERE p.status = 'active'{where}""", params).fetchall()

    holdings, missing, by_class = [], [], {}
    invested_total = realized_total = unrealized_total = 0.0
    market_total = 0.0
    for r in rows:
        pid = int(r["product_id"])
        txns = [dict(x) for x in conn.execute(
            "SELECT * FROM transactions WHERE product_id = ? ORDER BY "
            "txn_date, txn_id", (pid,))]
        if not txns:
            continue
        h = holdings_from_ledger(txns)
        if abs(h.units) < 1e-12 and abs(h.realized_pnl) < 1e-9:
            continue
        sym = r["ticker"]
        px = prices.get(sym) if sym else None
        if px is None:
            px = h.avg_cost
            if sym and r["product_type"] not in MONEY_MARKET_TYPES:
                missing.append(sym)
        mv = h.units * float(px or 0.0)
        unreal = mv - h.units * h.avg_cost
        holdings.append({
            "product_id": pid, "account": r["account"], "symbol": sym,
            "name": r["name"], "asset_class": r["product_type"],
            "units": h.units, "avg_cost": h.avg_cost, "price": float(px or 0.0),
            "market_value": mv, "unrealized_pnl": unreal,
            "realized_pnl": h.realized_pnl, "dividends": h.dividends,
            "fees_paid": h.fees_paid,
        })
        market_total += mv
        invested_total += h.invested
        realized_total += h.realized_pnl
        unrealized_total += unreal
        by_class[r["product_type"]] = by_class.get(r["product_type"], 0.0) + mv

    cash = cash_balance(conn, account_id)
    return {
        "holdings": holdings,
        "market_value": market_total,
        "cash_recorded": cash["recorded"],
        "cash_implied": cash["implied"],
        "total_value_recorded": market_total + cash["recorded"],
        "invested": invested_total,
        "realized_pnl": realized_total,
        "unrealized_pnl": unrealized_total,
        "by_asset_class": by_class,
        "missing_price": missing,
        "n_positions": len(holdings),
    }
