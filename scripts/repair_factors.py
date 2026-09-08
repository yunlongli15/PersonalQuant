# -*- coding: utf-8 -*-
"""One-off canonical-layer repair: spurious adjustment-factor jumps.

The Yahoo-sourced baseline contains ~48 factor discontinuities where the
factor jumps >2x while the raw close barely moves (bad corporate-action
records) — these inject fake +/-100..400% adjusted-return days into features
and labels. This script detects them and carries the previous factor forward,
rewrites the daily parquet files, and registers the repair in
source_registry. Raw prices are never touched.

    python scripts/repair_factors.py [--dry-run]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from personal_quant import config, db
from personal_quant.storage.parquet import register_source


def find_spurious(conn) -> pd.DataFrame:
    return conn.execute(
        """
        WITH px AS (
          SELECT symbol, trade_date, close, factor,
                 LAG(close) OVER (PARTITION BY symbol ORDER BY trade_date) prev_close,
                 LAG(factor) OVER (PARTITION BY symbol ORDER BY trade_date) prev_factor
          FROM daily_bars WHERE trade_date >= '2000-01-01'
        )
        SELECT symbol, trade_date, prev_factor
        FROM px
        WHERE prev_factor > 0 AND factor/prev_factor > 2.0
          AND prev_close > 0 AND abs(close/prev_close - 1) < 0.15
        """
    ).fetch_df()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conn = db.connect()
    bad = find_spurious(conn)
    print(f"spurious factor jumps: {len(bad)} across {bad['symbol'].nunique()} symbols")
    if args.dry_run:
        print(bad.to_string(index=False))
        return 0

    # per-event repair: the spurious factor usually persists for a run of days,
    # so replace the whole bad segment (until the factor returns to ~the
    # previous level or the series ends) with the pre-jump factor
    events = [
        (r["symbol"], pd.Timestamp(r["trade_date"]), float(r["prev_factor"]))
        for _, r in bad.iterrows()
    ]
    daily_dir = config.PARQUET_SUBDIRS["daily"]
    n_fixed = 0
    for f in sorted(daily_dir.glob("*.parquet")):
        df = pd.read_parquet(f)
        if df.empty:
            continue
        df = df.sort_values(["symbol", "trade_date"])
        fixed_here = 0
        for sym, d, prev_fac in events:
            mask = (df["symbol"] == sym) & (df["trade_date"] >= d)
            if not mask.any():
                continue
            seg = df[mask]
            # end of the bad run: first day where factor returns near the
            # pre-jump level (within 50%), else the end of the file
            stop = seg[seg["factor"] <= prev_fac * 1.5]
            if not stop.empty:
                seg = seg[seg["trade_date"] < stop["trade_date"].iloc[0]]
            if seg.empty:
                continue
            df.loc[seg.index, "factor"] = prev_fac
            fixed_here += len(seg)
        if fixed_here:
            df.to_parquet(f, index=False)
            n_fixed += fixed_here
            print(f"  {f.name}: fixed {fixed_here} rows")
    db.refresh_daily_bars_view()
    register_source(
        source_name="factor_repair_v1",
        data_type="daily_bars.factor",
        url="local repair script scripts/repair_factors.py",
        version="1.0",
        file="data/parquet/daily/*.parquet",
        parser_version="1.0",
    )
    # verify
    remaining = find_spurious(db.connect())
    print(f"fixed {n_fixed} rows; remaining spurious jumps: {len(remaining)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
