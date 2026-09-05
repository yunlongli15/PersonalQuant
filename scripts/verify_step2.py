# -*- coding: utf-8 -*-
"""STEP 2 acceptance verification.

    python scripts/verify_step2.py [--offline]

Runs all acceptance checks and prints PASS / FAIL per item plus a summary.
Exit code 0 only when every check passes.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from personal_quant import config, db
from personal_quant.errors import NotAvailableAtTimeError, NotAvailableError

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()
    if args.offline:
        import os

        os.environ["PQ_MODE"] = "offline"
        config.MODE = "offline"

    print("=" * 64)
    print("STEP 2 verification: local A-share data infrastructure")
    print("=" * 64)

    # --- DuckDB + schema ---
    conn = db.connect()
    tables = {
        r[0] for r in conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()
    }
    required = {
        "securities", "trading_calendar", "daily_bars", "daily_valuation",
        "company_lifecycle", "industry_membership", "corporate_actions",
        "report_documents", "financial_metrics", "extraction_audit",
        "source_registry",
    }
    missing = required - tables
    check("DuckDB database + schema", not missing,
          f"missing: {sorted(missing)}" if missing else str(config.DUCKDB_PATH))

    def count(t):
        return conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]

    # --- data tables ---
    n_sec = count("securities")
    check("securities master", n_sec > 5000, f"{n_sec} rows")
    check("trading calendar", count("trading_calendar") > 4000,
          f"{count('trading_calendar')} days")
    n_bars = count("daily_bars")
    check("daily bars", n_bars > 10_000_000, f"{n_bars:,} rows")
    check("daily valuation", count("daily_valuation") > 3000,
          f"{count('daily_valuation')} rows")
    check("company lifecycle", count("company_lifecycle") > 2000,
          f"{count('company_lifecycle')} rows")
    check("industry membership", count("industry_membership") > 3000,
          f"{count('industry_membership')} rows")
    check("corporate actions", count("corporate_actions") > 3000,
          f"{count('corporate_actions')} rows")
    n_docs = count("report_documents")
    check("report_documents", n_docs > 60000, f"{n_docs:,} rows")
    check("SSE metadata imported", n_docs > 60000
          and conn.execute(
              "SELECT COUNT(*) FROM report_documents WHERE source='cninfo'"
          ).fetchone()[0] > 30000,
          "cninfo URLs present")

    # --- symbol normalization ---
    from personal_quant.symbols import normalize_symbol

    try:
        ok = (normalize_symbol("SH600519") == "600519.SH"
              and normalize_symbol("000001") == "000001.SZ"
              and normalize_symbol("430017") == "430017.BJ")
        check("symbol normalization", ok)
    except Exception as e:
        check("symbol normalization", False, str(e))

    # --- duplicate checks ---
    dup_bars = conn.execute(
        "SELECT COUNT(*) FROM (SELECT symbol, trade_date FROM daily_bars "
        "GROUP BY 1,2 HAVING COUNT(*)>1)"
    ).fetchone()[0]
    dup_docs = conn.execute(
        "SELECT COUNT(*) FROM (SELECT symbol, fiscal_year, document_role "
        "FROM report_documents GROUP BY 1,2,3 HAVING COUNT(*)>1)"
    ).fetchone()[0]
    check("duplicate checks (bars + reports)", dup_bars == 0 and dup_docs == 0,
          f"bars={dup_bars}, reports={dup_docs}")

    # --- PIT checks ---
    pit_bad = conn.execute(
        "SELECT COUNT(*) FROM financial_metrics f "
        "LEFT JOIN report_documents d ON f.source_document_id=d.document_id "
        "WHERE d.announcement_date IS NOT NULL "
        "AND f.announcement_date != d.announcement_date"
    ).fetchone()[0]
    future = conn.execute(
        "SELECT COUNT(*) FROM financial_metrics WHERE fiscal_period > announcement_date"
    ).fetchone()[0]
    check("PIT checks (metric-document consistency)", pit_bad == 0 and future == 0,
          f"mismatch={pit_bad}, future={future}")

    # --- source registry ---
    check("source registry", count("source_registry") >= 8,
          f"{count('source_registry')} sources")

    # --- financial query API ---
    try:
        from personal_quant.financial.query import get_financial_metric

        r = get_financial_metric("600519.SH", "revenue", "2024-06-01", online=False)
        ok_q = (r["value"] is not None and r["fiscal_year"] == 2023
                and r["source_sha256"])
        check("financial query API (PIT)", ok_q,
              f"revenue FY{r['fiscal_year']} = {r['value']:,.0f} CNY")
    except Exception as e:
        check("financial query API (PIT)", False, f"{type(e).__name__}: {e}")

    # --- on-demand PDF extraction (offline-safe: from cached PDF bytes) ---
    try:
        from personal_quant.financial.extractor import FinancialDocumentExtractor

        cached = sorted(config.PDF_CACHE_DIR.glob("*.pdf"))
        if not cached:
            check("on-demand PDF extraction", False, "no cached PDF")
        else:
            ext = FinancialDocumentExtractor(cached[0].read_bytes())
            res = ext.extract_all(2023)
            n_ok = sum(1 for v in res.values() if v.status == "VALID")
            check("on-demand PDF extraction", n_ok >= 8,
                  f"{n_ok} metrics from cached PDF")
    except Exception as e:
        check("on-demand PDF extraction", False, f"{type(e).__name__}: {e}")

    # --- financial sanity checks ---
    try:
        fm = conn.execute(
            "SELECT metric_name, metric_value FROM financial_metrics "
            "WHERE symbol='600519.SH' AND fiscal_year=2023"
        ).fetch_df()
        vals = dict(zip(fm["metric_name"], fm["metric_value"]))
        net_margin_ok = abs(vals["net_margin"] - vals["net_profit"] / vals["revenue"]) < 0.02
        dta_ok = abs(vals["debt_to_asset"] - vals["total_liabilities"] / vals["total_assets"]) < 0.02
        check("financial sanity checks", net_margin_ok and dta_ok,
              f"net_margin={vals['net_margin']:.4f}, debt_to_asset={vals['debt_to_asset']:.4f}")
    except Exception as e:
        check("financial sanity checks", False, f"{type(e).__name__}: {e}")

    # --- audit trail ---
    n_audit = count("extraction_audit")
    check("extraction audit trail", n_audit >= 50, f"{n_audit} rows")

    # --- Qlib cross-check (quick local subset) ---
    try:
        from personal_quant.providers.qlib_baseline import load_bars

        ref = load_bars(["SH600519", "SZ000001", "SH600036"],
                        "2020-01-01", "2020-12-31").reset_index()
        for c in ["close", "vwap"]:
            ref[c] = ref[c] / ref["factor"]
        syms = ["600519.SH", "000001.SZ", "600036.SH"]
        got = conn.execute(
            "SELECT symbol, trade_date, close FROM daily_bars "
            "WHERE trade_date BETWEEN '2020-01-01' AND '2020-12-31' "
            "AND symbol IN (SELECT unnest(?::VARCHAR[]))",
            [syms],
        ).fetch_df()
        got["qlib_symbol"] = got["symbol"].str.split(".").str[::-1].str.join("")
        m = ref.merge(got[["qlib_symbol", "trade_date", "close"]],
                      on=["qlib_symbol", "trade_date"], suffixes=("_ref", "_got"))
        maxdiff = (m["close_ref"] - m["close_got"]).abs().max()
        check("Qlib cross-check", len(m) > 700 and maxdiff < 1e-6,
              f"{len(m)} rows, max |diff|={maxdiff:.2e}")
    except Exception as e:
        check("Qlib cross-check", False, f"{type(e).__name__}: {e}")

    # --- summary ---
    n_pass = sum(1 for _, ok, _ in RESULTS if ok)
    n_fail = len(RESULTS) - n_pass
    print("-" * 64)
    print(f"SUMMARY: {n_pass} PASS / {n_fail} FAIL")
    print("OVERALL: PASS" if n_fail == 0 else "OVERALL: FAIL")
    for name, ok, detail in RESULTS:
        if not ok:
            print(f"  FAILED: {name} -- {detail}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
