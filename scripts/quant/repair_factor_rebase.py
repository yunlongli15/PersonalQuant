# -*- coding: utf-8 -*-
"""Repair a source-side factor REBASE (opposite direction to
scripts/repair_factors.py).

Symptom found after the 2026-09-12 snapshot refresh: for 7 symbols the
adjustment factor of the *earlier* history was rescaled by a constant
(2x-6x) while the raw close stayed continuous, so the ADJUSTED series
jumped at the 2026-01-05 boundary. Evidence that the newer segment is the
correct one: the post-jump factor equals the value in the previous
snapshot (qlib_data_old), while the pre-jump value does not.

Repair: for each detected jump, rescale every row STRICTLY BEFORE the
jump by r = factor_after / factor_before. A uniform rescale of the
earlier segment preserves all returns inside it and makes the series
continuous across the boundary; it reproduces the previous snapshot's
adjusted series exactly (verified for the 7 symbols).

    python scripts/quant/repair_factor_rebase.py --dry-run
    python scripts/quant/repair_factor_rebase.py
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

from personal_quant import config, db
from personal_quant.storage.parquet import register_source


def find_rebases(conn) -> pd.DataFrame:
    return conn.execute(
        """
        WITH px AS (
          SELECT symbol, trade_date, close, factor,
                 LAG(close) OVER (PARTITION BY symbol ORDER BY trade_date)
                     AS prev_close,
                 LAG(factor) OVER (PARTITION BY symbol ORDER BY trade_date)
                     AS prev_factor
          FROM daily_bars WHERE trade_date >= '2000-01-01'
        )
        SELECT symbol, trade_date, prev_factor, factor,
               factor / prev_factor AS r
        FROM px
        WHERE prev_factor > 0 AND factor / prev_factor > 2.0
          AND prev_close > 0 AND abs(close / prev_close - 1) < 0.15
        """
    ).fetch_df()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conn = db.connect()
    events = find_rebases(conn)
    print(f"factor rebases: {len(events)} across "
          f"{events['symbol'].nunique()} symbols")
    if events.empty:
        return 0
    print(events.to_string(index=False))
    if args.dry_run:
        return 0

    daily_dir = config.PARQUET_SUBDIRS["daily"]
    total = 0
    for f in sorted(daily_dir.glob("*.parquet")):
        df = pd.read_parquet(f)
        if df.empty:
            continue
        fixed = 0
        for _, e in events.iterrows():
            sym, d, r = e["symbol"], pd.Timestamp(e["trade_date"]), \
                float(e["r"])
            mask = (df["symbol"] == sym) & (df["trade_date"] < d)
            if not mask.any():
                continue
            df.loc[mask, "factor"] = df.loc[mask, "factor"] * r
            fixed += int(mask.sum())
        if fixed:
            df.to_parquet(f, index=False)
            total += fixed
            print(f"  {f.name}: rescaled {fixed} rows")

    db.refresh_daily_bars_view()
    register_source(
        source_name="factor_rebase_repair_v1",
        data_type="daily_bars.factor",
        url="local repair scripts/quant/repair_factor_rebase.py",
        version="1.0",
        file="data/parquet/daily/*.parquet",
        parser_version="1.0",
    )
    remaining = find_rebases(db.connect())
    print(f"rescaled {total} rows; remaining rebases: {len(remaining)}")
    return 0 if remaining.empty else 1


if __name__ == "__main__":
    sys.exit(main())
