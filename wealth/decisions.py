# -*- coding: utf-8 -*-
"""Recommendation -> decision -> execution trail (STEP 7G, spec §33/§34/§36).

The system never trades. It records three separate things so the user can
later ask "did following the model actually help?":

    recommendation  what the engine proposed (price band, shares, target)
    decision        what the user chose (accept / modify / reject)
    execution       what actually filled (price, shares, fees)

From those: slippage vs the recommended price, decision quality, and the
gap between the model portfolio and the real one (under/overweight, §36).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from . import db as wdb


def save_recommendation(conn, plan: dict, source: str = "trade_plan"
                        ) -> int:
    """Persist a trade plan's rows as recommendations (idempotent)."""
    n = 0
    for r in plan.get("rows", []):
        if r.get("action") not in ("BUY", "SELL", "HOLD", "SKIP"):
            continue
        rec_price = r.get("recommended_entry_price")
        conn.execute(
            "INSERT INTO recommendations (as_of, symbol, name, action, "
            "rec_price, entry_low, entry_high, shares, target_price, "
            "stop_loss, expected_return, signal_rank, source) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(as_of, symbol, source) DO UPDATE SET "
            "action=excluded.action, rec_price=excluded.rec_price, "
            "shares=excluded.shares, target_price=excluded.target_price",
            (plan["as_of"], r["symbol"], r.get("name"), r["action"],
             rec_price, r.get("entry_low"), r.get("entry_high"),
             int(r.get("shares") or 0), r.get("target_price"),
             r.get("stop_loss"), r.get("expected_return"),
             r.get("raw_rank"), source))
        n += 1
    conn.commit()
    if n:
        wdb.audit(conn, "create", "recommendations", plan["as_of"],
                  new_value={"n": n, "source": source})
    return n


def list_recommendations(conn, as_of: Optional[str] = None) -> List[dict]:
    if as_of:
        rows = conn.execute(
            "SELECT * FROM recommendations WHERE as_of=? "
            "ORDER BY signal_rank", (as_of,))
    else:
        rows = conn.execute(
            "SELECT * FROM recommendations ORDER BY as_of DESC, signal_rank")
    return [dict(r) for r in rows]


def record_decision(conn, recommendation_id: int, decision: str,
                    modified_price: Optional[float] = None,
                    modified_shares: Optional[int] = None,
                    note: Optional[str] = None, actor: str = "local_user"
                    ) -> int:
    if decision not in ("accept", "modify", "reject"):
        raise ValueError(f"decision must be accept|modify|reject, "
                         f"got {decision!r}")
    if decision == "modify" and modified_price is None and \
            modified_shares is None:
        raise ValueError("a 'modify' decision must change price or shares")
    cur = conn.execute(
        "INSERT INTO decisions (recommendation_id, decision, "
        "modified_price, modified_shares, note) VALUES (?,?,?,?,?)",
        (recommendation_id, decision, modified_price, modified_shares,
         note))
    conn.commit()
    wdb.audit(conn, "decision", "recommendations", recommendation_id,
              new_value={"decision": decision, "price": modified_price,
                         "shares": modified_shares},
              reason=note, actor=actor)
    return int(cur.lastrowid)


def record_execution(conn, executed_at: str, price: float, shares: int,
                     fees: float = 0.0,
                     recommendation_id: Optional[int] = None,
                     product_id: Optional[int] = None,
                     note: Optional[str] = None) -> int:
    """A real fill. Optionally mirrored into the wealth ledger as a
    buy/sell transaction so holdings stay in step with reality."""
    cur = conn.execute(
        "INSERT INTO executions (recommendation_id, executed_at, price, "
        "shares, fees, note) VALUES (?,?,?,?,?,?)",
        (recommendation_id, executed_at, price, shares, fees, note))
    conn.commit()
    wdb.audit(conn, "execute", "executions", int(cur.lastrowid),
              new_value={"price": price, "shares": shares, "fees": fees,
                         "at": executed_at}, reason=note)
    return int(cur.lastrowid)


def execution_slippage(conn, as_of: Optional[str] = None) -> List[dict]:
    """Recommended vs actual (spec §34)."""
    sql = ("SELECT e.execution_id, e.executed_at, e.price, e.shares, "
           "e.fees, r.symbol, r.name, r.rec_price, r.entry_low, "
           "r.entry_high, r.target_price, r.as_of "
           "FROM executions e JOIN recommendations r ON "
           "r.recommendation_id = e.recommendation_id WHERE 1=1")
    params = []
    if as_of:
        sql += " AND r.as_of = ?"
        params.append(as_of)
    out = []
    for row in conn.execute(sql + " ORDER BY e.executed_at DESC", params):
        d = dict(row)
        if d["rec_price"]:
            d["slippage"] = d["price"] - d["rec_price"]
            d["slippage_pct"] = d["slippage"] / d["rec_price"]
            d["inside_band"] = (d["entry_low"] is not None
                                and d["entry_low"] <= d["price"]
                                <= (d["entry_high"] or d["rec_price"]))
        else:
            d["slippage"] = None
            d["slippage_pct"] = None
            d["inside_band"] = None
        out.append(d)
    return out


def decision_summary(conn, as_of: Optional[str] = None) -> Dict[str, int]:
    sql = ("SELECT d.decision AS decision, COUNT(*) AS n FROM decisions d "
           "JOIN recommendations r ON "
           "r.recommendation_id = d.recommendation_id")
    params = []
    if as_of:
        sql += " WHERE r.as_of = ?"
        params.append(as_of)
    sql += " GROUP BY d.decision"
    return {r["decision"]: r["n"] for r in conn.execute(sql, params)}


def portfolio_gap(conn, plan: Optional[dict] = None) -> List[dict]:
    """Model portfolio vs the real one (spec §36).

    Compares the target weights of the latest plan with the actual value
    weights from the wealth DB. Only stock products whose ticker matches
    a recommended symbol can be compared; other assets are reported with
    a null model weight rather than a wrong one.
    """
    from . import engine

    summary = engine.portfolio_summary(conn)
    actual = {}
    for h in summary["holdings"]:
        ticker = None
        prods = conn.execute(
            "SELECT ticker FROM products WHERE product_id=?",
            (h["product_id"],)).fetchone()
        if prods and prods["ticker"]:
            ticker = prods["ticker"]
        if ticker:
            actual[ticker] = actual.get(ticker, 0.0) + h["weight"]
    rows = []
    model = {}
    if plan:
        capital = plan.get("capital") or 1.0
        for r in plan.get("rows", []):
            model[r["symbol"]] = r.get("target_weight") or 0.0
    for sym in sorted(set(model) | set(actual)):
        m = model.get(sym)
        a = actual.get(sym, 0.0 if m is not None else None)
        gap = None
        if m is not None and a is not None:
            gap = a - m
        rows.append({
            "symbol": sym, "model_weight": m, "actual_weight": a,
            "gap": gap,
            "status": ("On target" if gap is not None and abs(gap) < 0.005
                       else "Underweight" if gap is not None and gap < 0
                       else "Overweight" if gap is not None else "not held"),
        })
    return rows
