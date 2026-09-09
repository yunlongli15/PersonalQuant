# -*- coding: utf-8 -*-
"""STEP 4 financial-universe PIT factor pipeline: lazy + incremental.

For every (symbol, fiscal_year) in the financial universe, the needed
annual-report metrics are queried from the LEVEL-2 cache
(financial_metrics). When missing, the STEP 2 lazy pipeline runs:
report metadata -> on-demand PDF fetch (single connection, polite) ->
extraction -> validation -> financial_metrics + extraction_audit.
Already-extracted reports are never re-downloaded (except a one-time
re-extraction of pre-1.1 reports to backfill the per-share metrics eps/bps
added by STEP 4).

The financial universe = top-N A-shares by current total market cap
(valuation snapshot). This is a documented large-cap sample, not the full
universe: results on it carry a survivorship/large-cap caveat recorded in
reports/step4_financial_factor_coverage.md. Fiscal years 2017-2025:
FY2017 covers signals from 2018, FY2024 covers 2025 signals, FY2025 covers
2026 paper-live signals.

Resumable: re-running continues from the current financial_metrics state.
The financial snapshot for the factor engine
(data/derived/factors/financial_metrics.parquet) is refreshed every
checkpoint so research runs see incremental coverage.

    python scripts/fetch_financial_universe.py [--top-n 300] [--max-reports N]
"""

import argparse
import random
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from personal_quant import db
from personal_quant.errors import NotAvailableError
from personal_quant.financial.query import extract_and_store
from personal_quant.providers.sse_reports import SSEReportsProvider
from personal_quant.storage.parquet import register_source

from factors.base import DERIVED

FISCAL_YEARS = list(range(2017, 2026))  # FY2017..FY2025
# metrics a complete extraction must carry (per-share eps/bps are the STEP 4
# additions; the pre-1.1 demo extractions lack them and get one re-extraction)
CORE_METRICS = {"revenue", "net_profit", "total_assets", "total_liabilities",
                "net_assets", "operating_cash_flow", "roe", "eps", "bps"}
MAX_ATTEMPTS = 3  # cap re-extraction attempts per report


def load_financial_anchor(top_n: int) -> list:
    """Top-N SH/SZ symbols by current total market cap."""
    conn = db.connect()
    df = conn.execute(
        "SELECT symbol FROM daily_valuation WHERE trade_date = "
        "(SELECT MAX(trade_date) FROM daily_valuation) "
        "AND symbol IN (SELECT symbol FROM securities WHERE exchange IN ('SH','SZ')) "
        "ORDER BY total_market_cap DESC LIMIT ?", [top_n]
    ).fetch_df()
    return df["symbol"].tolist()


def refresh_snapshot() -> None:
    conn = db.connect()
    df = conn.execute(
        "SELECT symbol, fiscal_year, fiscal_period, availability_date, "
        "availability_date_unknown, metric_name, metric_value "
        "FROM financial_metrics"
    ).fetch_df()
    DERIVED.mkdir(parents=True, exist_ok=True)
    df.to_parquet(DERIVED / "financial_metrics.parquet", index=False)


def is_complete(conn, document_id: str) -> bool:
    """True when the report carries the full core metric set — or when it
    has already been extracted >= MAX_ATTEMPTS times (some reports
    legitimately cannot yield eps/bps; retrying forever would waste a PDF
    fetch per run). Attempts are counted by one representative metric's
    audit rows (one per extraction) — not by total audit rows (~14 per
    extraction)."""
    n = conn.execute(
        "SELECT COUNT(DISTINCT metric_name) FROM financial_metrics "
        "WHERE source_document_id=? AND metric_name IN "
        "(SELECT unnest(?::VARCHAR[]))",
        [document_id, sorted(CORE_METRICS)],
    ).fetchone()[0]
    if n >= len(CORE_METRICS):
        return True
    attempts = conn.execute(
        "SELECT COUNT(*) FROM extraction_audit "
        "WHERE source_document_id=? AND metric_name='revenue'",
        [document_id],
    ).fetchone()[0]
    return attempts >= MAX_ATTEMPTS


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-n", type=int, default=300)
    ap.add_argument("--max-reports", type=int, default=0,
                    help="stop after N successful extractions (0 = no limit)")
    ap.add_argument("--no-sleep", action="store_true")
    args = ap.parse_args()

    provider = SSEReportsProvider()
    conn = db.connect()
    symbols = load_financial_anchor(args.top_n)
    print(f"financial universe: {len(symbols)} symbols "
          f"({symbols[0]} .. {symbols[-1]}), fiscal years "
          f"{FISCAL_YEARS[0]}-{FISCAL_YEARS[-1]}", flush=True)

    t0 = time.time()
    ok = skipped = failed = re_extracted = 0
    fail_streak = 0
    done_years = set()
    for i, symbol in enumerate(symbols):
        for fy in FISCAL_YEARS:
            try:
                meta = provider.get_report_metadata(symbol, fy, "annual_report")
            except Exception:
                meta = None
            if meta is None or not meta.get("source_url"):
                skipped += 1
                continue
            doc_id = meta["document_id"]
            if is_complete(conn, doc_id):
                skipped += 1
                continue
            ann = meta.get("announcement_date")
            if not ann:
                # strict PIT: unknown announcement date -> unusable for
                # factor research; do not download
                skipped += 1
                continue
            try:
                extract_and_store(symbol, fy, cache=False, provider=provider)
                ok += 1
                fail_streak = 0
                if not is_complete(db.connect(), doc_id):
                    re_extracted += 1
            except Exception as e:
                failed += 1
                fail_streak += 1
                if fail_streak <= 10 or failed % 50 == 0:
                    print(f"[fetch] {symbol} FY{fy} failed: "
                          f"{type(e).__name__}: {e}", flush=True)
                if fail_streak >= 50:
                    print("[fetch] 50 consecutive failures — source may be "
                          "blocked; stopping. Re-run to resume.", flush=True)
                    break
            if not args.no_sleep:
                time.sleep(random.uniform(1.0, 3.0))
            if ok and ok % 50 == 0:
                rate = ok / max(time.time() - t0, 1)
                done_years.add(fy)
                print(f"[fetch] {ok} extracted, {skipped} skipped, "
                      f"{failed} failed ({rate:.3f}/s, "
                      f"eta {(args.max_reports - ok) / rate / 60 if args.max_reports else 0:.0f}min)",
                      flush=True)
                refresh_snapshot()
            if args.max_reports and ok >= args.max_reports:
                print(f"[fetch] reached --max-reports {args.max_reports}")
                refresh_snapshot()
                return 0
        if fail_streak >= 50:
            break

    refresh_snapshot()
    el = time.time() - t0
    print(f"\n===== fetch summary =====\n"
          f"extracted: {ok}, skipped (cached/no-metadata/no-date): {skipped}, "
          f"failed: {failed}, re-extracted-for-eps/bps: {re_extracted}\n"
          f"elapsed: {el/60:.1f} min", flush=True)

    try:
        register_source(
            source_name="financial_universe_fetch_v1",
            data_type="financial_metrics (top-N market-cap universe)",
            url="local script scripts/fetch_financial_universe.py "
                "(CNINFO on-demand PDFs)",
            version="1.0",
            file=str(DERIVED / "financial_metrics.parquet"),
            parser_version="1.0",
        )
    except Exception as e:
        print(f"WARNING: source_registry write failed: {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
