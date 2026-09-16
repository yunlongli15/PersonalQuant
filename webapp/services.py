# -*- coding: utf-8 -*-
"""View models for the GUI (STEP 7F).

Every number the pages show is assembled here by calling the same
engines the CLIs use:

    wealth/     personal assets, P&L, returns, 万份收益
    pipeline/   data freshness, signals, forecasts
    trade_plan/ allocation + execution plan

Pages do no arithmetic beyond formatting. Functions are defensive: an
uninitialised system (empty wealth DB, no signal snapshot yet) yields an
`available: False` view model with a hint, never an exception in a
template.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# dashboard / wealth
# ---------------------------------------------------------------------------

def wealth_dashboard(as_of: Optional[str] = None) -> dict:
    """Everything on the home page's wealth half (spec §26/§47)."""
    from wealth import db as wdb
    from wealth import service

    try:
        conn = wdb.connect()
    except Exception as e:                                  # pragma: no cover
        return {"available": False, "reason": f"{type(e).__name__}: {e}"}
    try:
        s = service.latest_summary(conn, as_of=as_of)
    except Exception as e:
        return {"available": False, "reason": f"{type(e).__name__}: {e}"}
    curve = s.pop("curve", None)
    points = []
    if curve is not None and len(curve):
        points = [(str(d.date()), float(v))
                  for d, v in zip(curve["snap_date"], curve["value"])]
    pnl_points = []
    if curve is not None and len(curve):
        pnl_points = [(str(d.date()), float(v))
                      for d, v in zip(curve["snap_date"], curve["cum_pnl"])]
    return {
        "available": True,
        "as_of": s.get("as_of"),
        "net_worth": s.get("net_worth", 0.0),
        "day_pnl": s.get("day_pnl", 0.0),
        "month_pnl": s.get("month_pnl", 0.0),
        "year_pnl": s.get("year_pnl", 0.0),
        "total_pnl": s.get("total_pnl", 0.0),
        "twr": s.get("twr"), "mwr_xirr": s.get("mwr_xirr"),
        "invested_capital": s.get("invested_capital", 0.0),
        "realized_pnl": s.get("realized_pnl", 0.0),
        "unrealized_pnl": s.get("unrealized_pnl", 0.0),
        "income": s.get("income", 0.0), "fees": s.get("fees", 0.0),
        "by_category": s.get("by_category", {}),
        "by_platform": s.get("by_platform", {}),
        "holdings": s.get("holdings", []),
        "curve_points": points, "pnl_points": pnl_points,
    }


def wealth_breakdown(start: str, end: str) -> dict:
    """Net-worth change decomposition for a period (spec §27)."""
    from wealth import db as wdb
    from wealth import service

    conn = wdb.connect()
    d = service.decompose_period(conn, start, end)
    return {"available": True, **d}


def wealth_positions() -> List[dict]:
    from wealth import db as wdb
    from wealth import engine, repository as repo

    conn = wdb.connect()
    products = {p["product_id"]: p for p in
                repo.list_products(conn, include_inactive=True)}
    latest: Dict[int, dict] = {}
    for s in repo.list_snapshots(conn):
        latest[s["product_id"]] = s
    rows = []
    for pid, s in latest.items():
        p = products.get(pid)
        if not p:
            continue
        h = engine.positions_at(conn, pid, s["snap_date"])
        rows.append({
            "product_id": pid, "name": p["name"],
            "product_type": p["product_type"], "ticker": p["ticker"],
            "as_of": s["snap_date"], "units": s["units"], "nav": s["nav"],
            "market_value": s["market_value"],
            "avg_cost": h.avg_cost,
            "unrealized_pnl": (s["market_value"] - h.units * h.avg_cost)
            if s["units"] else 0.0,
            "realized_pnl": h.realized_pnl,
        })
    return sorted(rows, key=lambda r: -(r["market_value"] or 0))


def wealth_transactions(limit: int = 200) -> List[dict]:
    from wealth import db as wdb
    from wealth import repository as repo

    conn = wdb.connect()
    products = {p["product_id"]: p["name"] for p in
                repo.list_products(conn, include_inactive=True)}
    txns = repo.list_transactions(conn)
    for t in txns:
        t["product_name"] = products.get(t["product_id"], "?")
    return sorted(txns, key=lambda t: (t["txn_date"], t["txn_id"]),
                  reverse=True)[:limit]


def wealth_income(limit: int = 100) -> List[dict]:
    """万份收益 records (spec §8)."""
    from wealth import db as wdb
    from wealth import repository as repo

    conn = wdb.connect()
    products = {p["product_id"]: p["name"] for p in
                repo.list_products(conn, include_inactive=True)}
    rows = repo.list_income(conn)
    for r in rows:
        r["product_name"] = products.get(r["product_id"], "?")
    return sorted(rows, key=lambda r: r["income_date"], reverse=True)[:limit]


def accounts_overview() -> List[dict]:
    from wealth import db as wdb
    from wealth import repository as repo

    conn = wdb.connect()
    out = []
    for p in repo.list_platforms(conn):
        for a in repo.list_accounts(conn, p["platform_id"]):
            products = repo.list_products(conn, a["account_id"],
                                          include_inactive=True)
            total = 0.0
            for prod in products:
                snaps = repo.list_snapshots(conn,
                                            product_id=prod["product_id"])
                if snaps:
                    total += float(snaps[-1]["market_value"] or 0.0)
            out.append({"platform": p["name"], "kind": p["kind"],
                        "account": a["name"], "account_id": a["account_id"],
                        "n_products": len(products), "value": total})
    return out


# ---------------------------------------------------------------------------
# quant
# ---------------------------------------------------------------------------

def quant_signals(limit: int = 50) -> dict:
    try:
        from pipeline.signals import load_signals, signals_state

        df = load_signals()
        state = signals_state()
    except Exception as e:
        return {"available": False, "reason": f"{type(e).__name__}: {e}"}
    if df.empty:
        return {"available": False,
                "reason": "尚无信号快照 —— 请运行 "
                          "scripts/quant/refresh_all.py"}
    df = df.sort_values("raw_rank").head(limit)
    return {"available": True, "as_of": state.get("as_of"),
            "computed_at": state.get("computed_at"),
            "model_version": state.get("model_version"),
            "n_symbols": state.get("n_symbols"),
            "rows": df.to_dict("records")}


def quant_forecasts(symbols: Optional[List[str]] = None,
                    limit: int = 50) -> dict:
    try:
        from pipeline.forecast import load_forecasts, forecast_state

        df = load_forecasts()
        state = forecast_state()
    except Exception as e:
        return {"available": False, "reason": f"{type(e).__name__}: {e}"}
    if df.empty:
        return {"available": False,
                "reason": "尚无预测 —— 请运行 forecast_refresh"}
    if symbols:
        df = df[df["symbol"].isin(symbols)]
    else:
        keep = df[df["horizon"] == 20].sort_values(
            "expected_return", ascending=False).head(limit)["symbol"]
        df = df[df["symbol"].isin(keep)]
    return {"available": True, "as_of": state.get("as_of"),
            "model": state.get("model", {}),
            "rows": df.to_dict("records")}


def quant_forecast_for(symbol: str) -> dict:
    from pipeline.forecast import forecast_for_symbol, load_forecasts

    per = forecast_for_symbol(symbol)
    if per.empty:
        return {"available": False, "symbol": symbol}
    hist = price_history(symbol, days=250)
    return {"available": True, "symbol": symbol,
            "name": per["name"].iloc[0] if "name" in per.columns else None,
            "horizons": per.to_dict("records"), "history": hist}


def price_history(symbol: str, days: int = 250) -> List[tuple]:
    """Raw closes for the chart (canonical, read-only)."""
    try:
        import pyarrow.parquet as pq

        from personal_quant import config

        tbl = pq.read_table(
            str(config.PARQUET_SUBDIRS["daily"]),
            columns=["symbol", "trade_date", "close"],
            filters=[("symbol", "=", symbol)])
        df = tbl.to_pandas().sort_values("trade_date").tail(days)
        return [(str(pd.Timestamp(d).date()), float(c))
                for d, c in zip(df["trade_date"], df["close"])
                if pd.notna(c)]
    except Exception:
        return []


def trade_plan_view(capital: float = 500_000.0, top_k: int = 20,
                    rebuild: bool = False) -> dict:
    """Latest plan; rebuilt on demand from the frozen pipeline."""
    from trade_plan.plan import build_trade_plan, load_plan, save_plan

    plan = None if rebuild else load_plan()
    if not plan:
        try:
            plan = build_trade_plan(capital=capital, top_k=top_k)
            save_plan(plan)
        except Exception as e:
            return {"available": False, "reason": f"{type(e).__name__}: {e}"}
    return {"available": True, **plan}


def portfolio_view() -> dict:
    from pipeline.signals import portfolio_state

    st = portfolio_state()
    if not st:
        return {"available": False,
                "reason": "尚无组合快照"}
    return {"available": True, **st}


def research_view() -> dict:
    """Research Lab (spec §25): frozen numbers + honest status."""
    out = {"available": True, "strategies": [], "gates": {}}
    sel = PROJECT_ROOT / "experiments" / "portfolio" / "selection.json"
    if sel.exists():
        s = json.loads(sel.read_text(encoding="utf-8"))
        out["selection"] = {k: s.get(k, {}).get(f"chosen_{k[:-1]}",
                                                s.get(k, {}))
                            for k in ("stage1", "stage2", "stage3", "stage4")}
        out["protocol"] = s.get("protocol")
    gates = PROJECT_ROOT / "experiments" / "portfolio" / "strategy_v2" / \
        "gates.json"
    if gates.exists():
        g = json.loads(gates.read_text(encoding="utf-8"))
        out["gates"] = g.get("gates", {})
        out["test_metrics"] = g.get("test", {})
        out["valid_metrics"] = g.get("valid", {})
        out["research_metrics"] = g.get("research", {})
    inc = PROJECT_ROOT / "reports" / "step5_incremental_alpha_check.md"
    out["incremental_check"] = inc.exists()
    return out


def paper_live_view() -> dict:
    p = PROJECT_ROOT / "reports" / "paper_live" / \
        "latest_recommendation_v2.csv"
    if not p.exists():
        return {"available": False, "reason": "尚无模拟盘运行记录"}
    df = pd.read_csv(p)
    return {"available": True, "path": str(p.relative_to(PROJECT_ROOT)),
            "as_of": str(df["date"].iloc[0]) if len(df) else None,
            "rows": df.to_dict("records")}


# ---------------------------------------------------------------------------
# data status (spec §21)
# ---------------------------------------------------------------------------

def data_status_view(now: Optional[str] = None) -> dict:
    from pipeline import freshness
    from pipeline import jobs as jobstore

    try:
        rows = [f.as_dict() for f in freshness.data_status(now)]
        stale = [r for r in rows if r["status"] == freshness.STALE]
        missing = [r for r in rows
                   if r["status"] in (freshness.MISSING, freshness.UNKNOWN)]
        try:
            job_rows = list(jobstore.status_summary().values())
        except Exception:
            job_rows = []
        return {"available": True, "rows": rows, "stale": stale,
                "missing": missing,
                "jobs": sorted(job_rows, key=lambda j: j.get("job_name", ""))}
    except Exception as e:
        return {"available": False, "reason": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# settings
# ---------------------------------------------------------------------------

def settings_view() -> dict:
    import yaml

    from wealth import db as wdb
    from wealth import repository as repo

    strategy = yaml.safe_load((PROJECT_ROOT / "config" / "strategy_v1.yaml")
                              .read_text(encoding="utf-8"))
    portfolio = yaml.safe_load((PROJECT_ROOT / "config" / "portfolio_v1.yaml")
                               .read_text(encoding="utf-8"))
    v2 = yaml.safe_load((PROJECT_ROOT / "config" / "strategy_v2.yaml")
                        .read_text(encoding="utf-8"))
    conn = wdb.connect()
    return {
        "available": True,
        "cost_model": strategy.get("transaction_costs", {}),
        "execution": strategy.get("execution", {}),
        "portfolio": portfolio.get("portfolio", {}),
        "strategy_v2": v2.get("portfolio", {}),
        "platforms": repo.list_platforms(conn),
        "categories": repo.list_categories(conn),
        "benchmarks": repo.list_benchmarks(conn)[-20:],
    }
