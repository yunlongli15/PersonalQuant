# -*- coding: utf-8 -*-
"""News/announcement ingestion (official exchanges first).

    python scripts/news/update_news.py --dry-run
    python scripts/news/update_news.py                    # incremental
    python scripts/news/update_news.py --backfill-sse --start 2018-01-01
    python scripts/news/update_news.py --backfill-szse --max-stocks 800

- incremental: fetch each trading day after the last successful date
- backfill-sse: whole-market per-day queries (the SSE bulletin API
  ignores per-stock filters; locally filtered by SECURITY_CODE)
- backfill-szse: per-stock queries (cap-ranked from daily_valuation),
  resumable via the raw cache
- polite: single connection, random 1-3s delay, retry/backoff, raw JSON
  cache under data/raw/news/<source>/; a blocked source raises
  SOURCE_BLOCKED and the run records it (never bypasses)
"""

import argparse
import json
import random
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

from news.providers import CNINFOProvider, SSEProvider, SZSEProvider
from news.storage import ensure_tables, upsert_documents

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = PROJECT_ROOT / "data" / "derived" / "news" / "update_state.json"


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    return {"last_successful_date": None, "sources_blocked": []}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                          encoding="utf-8")


def trading_days_between(start, end) -> list:
    cal = pd.read_parquet(PROJECT_ROOT / "data" / "derived" / "factors"
                          / "calendar.parquet")["trade_date"]
    cal = pd.DatetimeIndex(pd.to_datetime(cal))
    return [d.date() for d in cal if pd.Timestamp(start).date() <= d.date()
            <= pd.Timestamp(end).date()]


def sz_stock_priority(max_stocks: int) -> list:
    from personal_quant import db

    conn = db.connect()
    df = conn.execute(
        "SELECT symbol FROM daily_valuation WHERE trade_date = "
        "(SELECT MAX(trade_date) FROM daily_valuation) "
        "AND symbol IN (SELECT symbol FROM securities WHERE exchange='SZ') "
        "ORDER BY total_market_cap DESC LIMIT ?", [max_stocks]
    ).fetch_df()
    return df["symbol"].tolist()


def fetch_day(sse: SSEProvider, szse: SZSEProvider, d, state,
              which=("sse", "szse")) -> tuple:
    """Fetch one trading day from the selected official exchanges."""
    s = d.strftime("%Y-%m-%d")
    docs = []
    blocked = state.setdefault("sources_blocked", [])
    for prov, name in ((sse, "sse"), (szse, "szse")):
        if name not in which or name in blocked:
            continue
        try:
            docs += prov.fetch_announcements(s, s)
        except Exception as e:
            print(f"[update] {name} failed for {s}: {type(e).__name__}: "
                  f"{str(e)[:100]}", flush=True)
            blocked.append(name)
            save_state(state)
    return docs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    ap.add_argument("--backfill-sse", action="store_true")
    ap.add_argument("--backfill-szse", action="store_true")
    ap.add_argument("--repair-truncated", action="store_true",
                    help="re-fetch SSE days whose first-pass caches show "
                         "total > 100 (the old broken pagination truncated "
                         "them at 100 rows/day)")
    ap.add_argument("--max-stocks", type=int, default=0,
                    help="SZ backfill cap (0 = all)")
    args = ap.parse_args()

    state = load_state()
    sse = SSEProvider()
    szse = SZSEProvider()
    ensure_tables()

    if args.dry_run:
        print("=== DRY RUN: provider reachability ===")
        # ONE settled trading day (not a recent window — the official
        # indexes lag a few days, so fresh windows are legitimately empty)
        probe = (pd.Timestamp.now().normalize()
                 - pd.Timedelta(days=8)).strftime("%Y-%m-%d")
        for prov in (sse, szse):
            try:
                docs = prov.fetch_announcements(probe, probe)
                print(f"  {prov.name}: reachable, sample {len(docs)} docs "
                      f"({probe})")
            except Exception as e:
                print(f"  {prov.name}: BLOCKED/FAILED — "
                      f"{type(e).__name__}: {str(e)[:80]}")
        from news.storage import document_count

        print(f"  stored documents: {document_count()}")
        print("  last successful date:", state["last_successful_date"])
        print("  (no fetch persisted)")
        return 0

    end = pd.Timestamp(args.end or datetime.now().date())
    # the official bulletin indexes lag ~5 days: cap backfills below the
    # unsettled tail (incremental mode picks those days up later)
    settled_end = min(end, pd.Timestamp.now().normalize()
                      - pd.Timedelta(days=7))
    if settled_end < pd.Timestamp(args.start or "2018-01-01"):
        settled_end = end
    if args.backfill_sse:
        start = pd.Timestamp(args.start or "2018-01-01")
        days = trading_days_between(start, settled_end)
        print(f"[backfill-sse] {len(days)} trading days "
              f"{days[0]}..{days[-1]} (tail after "
              f"{settled_end.date()} left to incremental)")
        for i, d in enumerate(days):
            # SZSE per-day pagination is too heavy (30/page); SZ coverage
            # comes from the per-stock backfill mode instead
            docs = fetch_day(sse, szse, d, state, which=("sse",))
            if docs:
                stats = upsert_documents(docs)
                print(f"[backfill-sse] {d}: {stats['inserted']} new, "
                      f"{stats['duplicates']} dup", flush=True)
            state["last_successful_date"] = str(d)
            if (i + 1) % 100 == 0:
                save_state(state)
                print(f"[backfill-sse] progress {i+1}/{len(days)}", flush=True)
        save_state(state)
        return 0

    if args.repair_truncated:
        # find days whose first-pass cache (pageSize=100) reported >100
        # announcements and re-fetch them with the fixed pagination
        import glob

        sse_cache = Path("data/raw/news/sse")
        truncated = []
        for f in sorted(sse_cache.glob("bulletin_*_*_p1.json")):
            if "_sz" in f.name:  # already a fixed-size cache
                continue
            payload = json.loads(f.read_text(encoding="utf-8"))
            if (payload.get("total") or 0) > 100:
                d = f.name.replace("bulletin_", "").replace("_p1.json", "")
                truncated.append(d)
        print(f"[repair-truncated] {len(truncated)} days with >100 "
              f"announcements (old pagination truncated them)")
        for d in truncated:
            lo, hi = d.split("_")[0], d.split("_")[1]
            docs = sse.fetch_announcements(lo, hi)
            if docs:
                stats = upsert_documents(docs)
                print(f"[repair] {lo}: {stats['inserted']} new, "
                      f"{stats['duplicates']} dup", flush=True)
        state["last_successful_date"] = str(end.date())
        save_state(state)
        return 0

    if args.backfill_szse:
        stocks = sz_stock_priority(args.max_stocks or 50000)
        print(f"[backfill-szse] {len(stocks)} stocks (cap-ranked)")
        start_s, end_s = (args.start or "2018-01-01"), str(end.date())
        done = new = 0
        for i, sym in enumerate(stocks):
            try:
                docs = szse.fetch_announcements(start_s, end_s, symbol=sym)
                stats = upsert_documents(docs)
                new += stats["inserted"]
            except Exception as e:
                print(f"[backfill-szse] {sym} failed: "
                      f"{type(e).__name__}: {str(e)[:80]}", flush=True)
                time.sleep(random.uniform(1.0, 3.0))
            done += 1
            if done % 25 == 0:
                print(f"[backfill-szse] {done}/{len(stocks)}, "
                      f"{new} new docs", flush=True)
        state["last_successful_date"] = str(end.date())
        save_state(state)
        print(f"[backfill-szse] done: {done} stocks, {new} new docs")
        return 0

    # ---- incremental: every trading day after the last successful date ---
    last = state["last_successful_date"]
    start = pd.Timestamp(args.start or last or "2026-09-05")
    days = trading_days_between(start, end)
    print(f"[incremental] {len(days)} days from {start.date()}")
    for d in days:
        docs = fetch_day(sse, szse, d, state)
        if docs:
            stats = upsert_documents(docs)
            print(f"[incremental] {d}: {stats['inserted']} new", flush=True)
        # only advance past a settled day: an empty fresh day may just be
        # the source index lagging — retried on the next run
        if docs or (datetime.now().date() - d).days >= 7:
            state["last_successful_date"] = str(d)
            save_state(state)
        else:
            print(f"[incremental] {d}: 0 docs (index may lag) — "
                  f"will retry next run", flush=True)
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
