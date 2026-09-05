# -*- coding: utf-8 -*-
"""One-shot data bootstrap for STEP 2.

    python scripts/bootstrap_data.py [--offline] [--skip-bars] [--skip-online]

Steps:
  1. initialize DuckDB + schema       (local)
  2. trading calendar                 (local, Qlib baseline)
  3. daily bars -> Parquet            (local, ~5 min, skippable)
  4. securities master                (online: SSE/SZSE/BSE + snapshot)
  5. daily valuation snapshot         (online: Tencent rank)
  6. industry membership              (online: official CSRC lists)
  7. corporate actions                (online: EastMoney datacenter)
  8. SSE report metadata + lifecycle  (local, sse-reports-archive)
  9. financial tables                 (schema, already initialized)
 10. data quality checks              (local)
 11. data catalog                     (reports/step2_data_catalog.md)

OFFLINE_MODE (--offline or PQ_MODE=offline) skips the online steps and only
uses cached data. Historical research/backtests must prefer OFFLINE_MODE.
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from personal_quant import config, db


def step(name, fn):
    print(f"\n[{name}] ...")
    try:
        out = fn()
        print(f"[{name}] OK")
        return out
    except Exception as e:
        print(f"[{name}] FAILED: {type(e).__name__}: {e}")
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="skip all online steps (cached data only)")
    ap.add_argument("--skip-bars", action="store_true",
                    help="skip the daily bars import (long)")
    ap.add_argument("--skip-online", action="store_true",
                    help="skip online market data (securities/valuation/...)")
    args = ap.parse_args()
    if args.offline:
        os.environ["PQ_MODE"] = "offline"
        config.MODE = "offline"

    # 1. schema
    conn = db.connect()
    print("[1/11] DuckDB schema ready at", config.DUCKDB_PATH)

    # 2. calendar
    from personal_quant.ingest.qlib_baseline import ingest_calendar

    cal = step("2/11 trading calendar", ingest_calendar)
    if cal is not None:
        print(f"       {len(cal)} trading days")

    # 3. bars
    if not args.skip_bars:
        from personal_quant.ingest.qlib_baseline import ingest_daily_bars

        def _bars():
            files = ingest_daily_bars()
            n = conn.execute("SELECT COUNT(*) FROM daily_bars").fetchone()[0]
            print(f"       {n} rows in {len(files)} parquet files")
            return files

        step("3/11 daily bars", _bars)
    else:
        print("[3/11 daily bars] skipped (--skip-bars)")

    if not args.offline and not args.skip_online:
        from personal_quant.ingest.market_online import (
            ingest_corporate_actions,
            ingest_industry,
            ingest_securities,
            ingest_valuation,
        )

        sec = step("4/11 securities", ingest_securities)
        if sec is not None:
            print(f"       {len(sec)} securities")
        val = step("5/11 valuation snapshot", ingest_valuation)
        if val is not None:
            print(f"       {len(val)} rows @ {val['trade_date'].iloc[0]}")
        ind = step("6/11 industry", ingest_industry)
        if ind is not None:
            print(f"       {len(ind)} memberships")
        act = step("7/11 corporate actions", ingest_corporate_actions)
        if act is not None:
            print(f"       {len(act)} actions")
    else:
        print("[4-7/11 online market data] skipped (offline / --skip-online)")

    # 8. SSE reports
    from personal_quant.ingest.sse_reports import ingest_lifecycle, ingest_sse_reports

    docs = step("8/11 SSE report metadata", ingest_sse_reports)
    if docs is not None:
        print(f"       {len(docs)} report documents")
    step("8/11 company lifecycle", ingest_lifecycle)

    # 9. financial tables are part of the schema (financial_metrics,
    # extraction_audit already exist); nothing to import at bootstrap time.
    print("[9/11 financial tables] schema ready (populated on demand)")

    # 10. quality checks
    from personal_quant.quality.checks import run_all_checks

    def _quality():
        df = run_all_checks()
        ok = int(df["passed"].sum())
        for _, r in df.iterrows():
            print(f"       [{'PASS' if r['passed'] else 'FAIL'}] {r['check']}")
        print(f"       {ok}/{len(df)} checks passed")
        return df

    q = step("10/11 data quality checks", _quality)
    if q is not None and (q["passed"] == False).any():  # noqa: E712
        print("WARNING: some quality checks failed - see details above")

    # 11. catalog
    def _catalog():
        from personal_quant.storage.parquet import table_summary
        import datetime as dt

        summary = table_summary()
        lines = [
            "# STEP 2 data catalog",
            "",
            f"generated: {dt.datetime.now():%Y-%m-%d %H:%M}",
            "",
            "## Tables (DuckDB)",
            "",
            "| table | rows |",
            "| --- | --- |",
        ]
        for _, r in summary.iterrows():
            lines.append(f"| {r['table']} | {int(r['rows']):,} |")
        lines += [
            "",
            "## Parquet files",
            "",
            "| path | size |",
            "| --- | --- |",
        ]
        for p in sorted(config.PARQUET_DIR.rglob("*.parquet")):
            lines.append(
                f"| {p.relative_to(config.PARQUET_DIR)} | "
                f"{p.stat().st_size / 1e6:.1f} MB |"
            )
        report = Path(__file__).resolve().parents[1] / "reports" / "step2_data_catalog.md"
        report.write_text("\n".join(lines), encoding="utf-8")
        print(f"       written {report}")
        return summary

    step("11/11 data catalog", _catalog)
    print("\nbootstrap done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
