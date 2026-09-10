# -*- coding: utf-8 -*-
"""End-to-end closed loop (STEP 7G, spec §1/§55).

    market data -> factors -> news -> signal -> forecast -> allocation
    -> trade plan -> wealth ledger -> performance -> back to research

This script demonstrates and verifies the loop with the REAL engines and
whatever data is present locally (no network unless --refresh says so):

    python scripts/quant/run_full_loop.py --demo-wealth
    python scripts/quant/run_full_loop.py --refresh          # includes net jobs

With --demo-wealth it also books a small illustrative portfolio into the
wealth database (a demo product + today's amount) so the wealth side of
the loop has data; the demo rows are tagged source='demo' and can be
removed with --clean-demo.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEMO_TAG = "demo"


def step(name: str, fn) -> dict:
    t0 = datetime.now()
    try:
        detail = fn()
        ok = True
    except Exception as e:                                   # noqa: BLE001
        detail, ok = f"{type(e).__name__}: {e}", False
    took = (datetime.now() - t0).total_seconds()
    mark = "OK  " if ok else "FAIL"
    print(f"[{mark}] {name:<22} {took:6.1f}s  "
          + (str(detail)[:110] if detail is not None else ""))
    return {"step": name, "ok": ok, "detail": str(detail)[:400],
            "seconds": round(took, 1)}


def _demo_wealth(capital: float = 100_000.0) -> str:
    """Book a demo fund product + today's amount (tagged, removable)."""
    from wealth import db as wdb
    from wealth import repository as repo
    from wealth import service

    conn = wdb.connect()
    plat = [p for p in repo.list_platforms(conn) if p["name"] == "天天盈"]
    if not plat:
        raise RuntimeError("run scripts/wealth/init_wealth_db.py first")
    acct = repo.list_accounts(conn, plat[0]["platform_id"])[0]["account_id"]
    products = [p for p in repo.list_products(conn, include_inactive=True)
                if p["account_id"] == acct and p["name"] == "演示债券基金"]
    if products:
        pid = products[0]["product_id"]
    else:
        pid = repo.create_product(conn, acct, "演示债券基金", "bond_fund",
                                  note=f"{DEMO_TAG}: created by "
                                       f"run_full_loop --demo-wealth")
    conn.execute("UPDATE products SET status='active' WHERE product_id=?",
                 (pid,))
    conn.execute("UPDATE products SET note=? WHERE product_id=?",
                 (f"{DEMO_TAG}: created by run_full_loop --demo-wealth", pid))
    conn.commit()
    today = datetime.now().date().isoformat()
    # a little growth so the P&L curve is not flat
    rows = repo.list_snapshots(conn, product_id=pid)
    last = rows[-1]["market_value"] if rows else capital
    value = round(float(last) * 1.0004 + 15.0, 2)
    res = service.snapshot_from_amount(conn, today, pid, value)
    return (f"demo product {pid}: {today} = {value:.2f} "
            f"(warnings: {len(res.warnings)})")


def _clean_demo() -> str:
    from wealth import db as wdb
    from wealth import repository as repo

    conn = wdb.connect()
    removed = 0
    for p in repo.list_products(conn, include_inactive=True):
        if p["name"] == "演示债券基金" or (p["note"] or "").startswith(DEMO_TAG):
            conn.execute("DELETE FROM daily_snapshots WHERE product_id=?",
                         (p["product_id"],))
            conn.execute("DELETE FROM income_records WHERE product_id=?",
                         (p["product_id"],))
            conn.execute("DELETE FROM transactions WHERE product_id=?",
                         (p["product_id"],))
            conn.execute("DELETE FROM positions WHERE product_id=?",
                         (p["product_id"],))
            conn.execute("DELETE FROM products WHERE product_id=?",
                         (p["product_id"],))
            removed += 1
    conn.commit()
    if removed:
        wdb.audit(conn, "delete", "products", "demo",
                  reason="run_full_loop --clean-demo")
    return f"removed {removed} demo product(s)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true",
                    help="also run the network refresh jobs")
    ap.add_argument("--demo-wealth", action="store_true")
    ap.add_argument("--clean-demo", action="store_true")
    ap.add_argument("--capital", type=float, default=500_000.0)
    ap.add_argument("--top-k", type=int, default=20)
    args = ap.parse_args()

    if args.clean_demo:
        print(_clean_demo())
        return 0

    results = []
    print("===== PersonalQuant closed loop =====")
    from pipeline import freshness, jobs, refresh

    if args.refresh:
        results.append(step("refresh_all", lambda: refresh.run_all(
            conn=None, continue_on_error=True)))
    else:
        results.append(step("data_freshness", lambda: [
            f"{f.domain}={f.status}" for f in freshness.data_status()]))

    results.append(step("factors (cached)", lambda: {
        "labels": str((PROJECT_ROOT / "data" / "derived" / "factors"
                       / "labels.parquet").exists()),
        "financial": str((PROJECT_ROOT / "data" / "derived" / "factors"
                          / "financial_metrics.parquet").exists())}))

    def signals():
        from pipeline.signals import load_signals, signals_state

        df = load_signals()
        st = signals_state()
        if df.empty:
            return "no snapshot — run scripts/quant/refresh_all.py"
        return f"{len(df)} symbols @ {st.get('as_of')} ({st.get('model_version')})"

    results.append(step("signal", signals))

    def forecasts():
        from pipeline.forecast import load_forecasts, forecast_state

        df = load_forecasts()
        if df.empty:
            return "no forecasts"
        st = forecast_state()
        return (f"{df['symbol'].nunique()} symbols x "
                f"{df['horizon'].nunique()} horizons @ {st.get('as_of')}")

    results.append(step("forecast", forecasts))

    def plan():
        from trade_plan.plan import build_trade_plan, load_plan, save_plan

        p = load_plan()
        if not p:
            p = build_trade_plan(capital=args.capital, top_k=args.top_k)
            save_plan(p)
        return (f"{p['n_positions']} positions, invested "
                f"{p['total_buy_value']:,.0f}, fees "
                f"{p['estimated_fees']:,.0f}, net exp "
                f"{p['expected_net_return_pct']*100:.2f}%")

    results.append(step("trade_plan", plan))

    if args.demo_wealth:
        results.append(step("wealth (demo entry)",
                            lambda: _demo_wealth()))

    def wealth():
        from wealth import db as wdb
        from wealth import service

        s = service.latest_summary(wdb.connect())
        return (f"net worth {s['net_worth']:,.2f}, total P&L "
                f"{s['total_pnl']:,.2f}, TWR {s['twr']}")

    results.append(step("wealth summary", wealth))

    def decisions():
        from wealth import db as wdb
        from wealth import decisions as dec
        from trade_plan.plan import load_plan

        p = load_plan()
        if not p:
            return "no plan"
        n = dec.save_recommendation(wdb.connect(), p)
        return f"{n} recommendations recorded for user decision"

    results.append(step("recommendations", decisions))

    def gap():
        from wealth import db as wdb
        from wealth import decisions as dec
        from trade_plan.plan import load_plan

        rows = dec.portfolio_gap(wdb.connect(), load_plan())
        under = sum(1 for r in rows if r["status"] == "Underweight")
        return f"{len(rows)} symbols compared, {under} underweight"

    results.append(step("model vs actual", gap))

    out = PROJECT_ROOT / "data" / "quant" / "loop_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"ran_at": datetime.now().isoformat(
        timespec="seconds"), "steps": results}, indent=2,
        ensure_ascii=False), encoding="utf-8")
    ok = all(r["ok"] for r in results)
    print(f"\nloop: {sum(1 for r in results if r['ok'])}/{len(results)} "
          f"steps OK -> {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
