# -*- coding: utf-8 -*-
"""STEP 7 acceptance checks (spec §51/§56).

    PYTHONIOENCODING=utf-8 python scripts/verify_step7.py

Verifies that the personal wealth + GUI layer is present, correct and
STILL SEPARATE from the research system (wealth records must never leak
into backtests), that the loop's artifacts exist, and that STEP 1-6 kept
passing. Prints PASS/FAIL per item and a summary.
"""

import json
import subprocess
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PROJECT_ROOT = Path(__file__).resolve().parents[1]

checks = []


def check(name, ok, detail=""):
    checks.append({"name": name, "ok": bool(ok), "detail": str(detail)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}"
          + (f" — {detail}" if detail and not ok else ""))


def main() -> int:
    # --- 7A: wealth database --------------------------------------------
    sys.path.insert(0, str(PROJECT_ROOT))
    from wealth import db as wdb

    conn = wdb.connect()
    names = set(wdb.table_names(conn))
    needed = {"platforms", "accounts", "products", "transactions",
              "daily_snapshots", "positions", "income_records",
              "benchmark_records", "wealth_categories", "audit_log",
              "recommendations", "decisions", "executions",
              "cash_flows", "fees", "dividends", "v_latest_values"}
    missing = needed - names
    check("wealth db schema", not missing, f"missing {sorted(missing)}")
    check("wealth db is sqlite (local)",
          str(wdb.WEALTH_DB).endswith(".db") and
          isinstance(conn, sqlite3.Connection))

    # --- separation from research ---------------------------------------
    research_duckdb = PROJECT_ROOT / "data" / "duckdb" / \
        "personal_quant.duckdb"
    wealth_src = "\n".join(
        p.read_text(encoding="utf-8") for p in
        (PROJECT_ROOT / "wealth").glob("*.py"))
    check("wealth layer never touches research duckdb",
          "personal_quant.duckdb" not in wealth_src
          and "import duckdb" not in wealth_src)

    # --- 7B: engine sanity on the live db (read-only checks) ------------
    from wealth import engine, service

    check("engine: P&L excludes external flows",
          engine.investment_pnl(100.0, 110.0, 10.0) == 0.0)
    check("engine: TWR exists", callable(engine.twr))
    s = service.latest_summary(conn)
    check("wealth summary computable", "net_worth" in s,
          f"net_worth={s.get('net_worth')}")

    # --- 7C/7D/7E artifacts ---------------------------------------------
    from pipeline import freshness

    status = {f.domain: f.status for f in freshness.data_status()}
    check("data status computable", len(status) >= 7, str(status))

    from pipeline.signals import load_signals, signals_state

    sig = load_signals()
    check("signal snapshot", not sig.empty,
          f"{len(sig)} rows @ {signals_state().get('as_of')}")

    from pipeline.forecast import load_forecasts, forecast_state

    fc = load_forecasts()
    check("forecast snapshot", not fc.empty and
          set(fc["horizon"].unique()) >= {1, 5, 20},
          f"{len(fc)} rows, horizons "
          f"{sorted(fc['horizon'].unique()) if not fc.empty else []}")
    check("forecast is versioned",
          bool(forecast_state().get("model", {}).get("name")))

    from trade_plan.plan import load_plan

    plan = load_plan()
    ok_plan = bool(plan and plan.get("rows"))
    check("trade plan artifacts",
          ok_plan and (PROJECT_ROOT / "data" / "quant" / "trade_plans").exists())
    if ok_plan:
        rows = plan["rows"]
        lots_ok = all(r["shares"] % 100 == 0 for r in rows)
        band_ok = all(r["entry_low"] <= r["recommended_entry_price"]
                      <= r["entry_high"] for r in rows)
        stop_ok = all((r.get("stop_loss") or 0) <
                      r["recommended_entry_price"] for r in rows)
        cash_ok = plan["remaining_cash"] >= 0
        check("plan: 100-share lots", lots_ok)
        check("plan: entry band around price", band_ok)
        check("plan: stop below entry", stop_ok)
        check("plan: cash never negative", cash_ok,
              f"residual {plan['remaining_cash']}")

    # --- 7F: GUI -----------------------------------------------------------
    from fastapi.testclient import TestClient

    from webapp.app import app as webapp

    client = TestClient(webapp)
    pages = ["/", "/wealth/overview", "/wealth/daily-update",
             "/quant/signals", "/quant/forecasts", "/quant/trade-plan",
             "/quant/research", "/data/status", "/settings"]
    codes = {p: client.get(p).status_code for p in pages}
    check("gui pages render", all(c == 200 for c in codes.values()),
          str({k: v for k, v in codes.items() if v != 200}))
    import re

    all_html = "".join(client.get(p).text for p in pages)
    remote = re.findall(r'(?:src|href)="(https?://[^"]+)"', all_html)
    check("gui is offline (no remote assets)", not remote, str(remote[:3]))
    check("gui health endpoint",
          client.get("/api/health").json().get("status") == "ok")

    # --- 7G: loop + decisions --------------------------------------------
    loop = PROJECT_ROOT / "data" / "quant" / "loop_report.json"
    loop_ok = False
    if loop.exists():
        rep = json.loads(loop.read_text(encoding="utf-8"))
        loop_ok = all(s["ok"] for s in rep.get("steps", []))
    check("closed loop ran clean", loop_ok, str(loop))

    from wealth import decisions as dec

    recs = dec.list_recommendations(conn)
    check("recommendations recorded", len(recs) > 0, f"{len(recs)} rows")

    # --- no auto-trading anywhere ---------------------------------------
    app_src = (PROJECT_ROOT / "webapp" / "app.py").read_text(encoding="utf-8")
    plan_src = (PROJECT_ROOT / "trade_plan" / "plan.py").read_text(
        encoding="utf-8")
    forbidden = ("place_order", "broker_api", "easytrader", "ths_trader",
                 "submit_order", "requests.post(")
    hatch = [f for f in forbidden if f in app_src + plan_src]
    check("no auto-trading code paths", not hatch, str(hatch))

    # --- LLM never decides trades ----------------------------------------
    llm_files = list((PROJECT_ROOT / "news" / "llm").glob("*.py"))
    llm_src = "\n".join(p.read_text(encoding="utf-8") for p in llm_files)
    check("LLM layer produces research only",
          "BUY" not in llm_src and "SELL" not in llm_src)

    # --- STEP 1-6 regression ---------------------------------------------
    prev = {"1": 21, "2": 19, "3": 19, "4": 21, "5": 22, "6": 25}
    for step, expected in prev.items():
        r = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts"
                                 / f"verify_step{step}.py")],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True,
            timeout=1800)
        out = r.stdout
        passed = f"{expected} PASS" in out and "0 FAIL" in out
        check(f"verify_step{step} still passes", passed,
              out.strip().splitlines()[-1] if out.strip() else "no output")

    # --- STEP 7 test suite ------------------------------------------------
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/wealth", "tests/pipeline",
         "tests/trade_plan", "tests/webapp", "-q"],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=1800)
    check("step7 tests pass", r.returncode == 0,
          (r.stdout + r.stderr).strip().splitlines()[-1]
          if (r.stdout + r.stderr).strip() else "")

    n_pass = sum(1 for c in checks if c["ok"])
    print(f"\nSUMMARY: {n_pass} PASS / {len(checks) - n_pass} FAIL / "
          f"OVERALL: {'PASS' if n_pass == len(checks) else 'FAIL'}")
    return 0 if n_pass == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
