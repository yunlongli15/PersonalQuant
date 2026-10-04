# -*- coding: utf-8 -*-
"""Ingest Qlib baseline data (LOCAL) into the canonical layer.

- trading calendar  <- qlib_data/calendars/day.txt
- securities master base <- qlib_data/instruments/all.txt (availability windows)
- daily bars        <- qlib_data/features/*.bin via qlib D.features,
                       written to data/parquet/daily/bars_<year>.parquet
                       and exposed in DuckDB as the daily_bars view.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import List

import pandas as pd

from .. import config, db
from ..providers.qlib_baseline import load_bars, load_calendar, load_instruments
from ..storage.parquet import register_source


def ingest_calendar() -> pd.DataFrame:
    cal = load_calendar()
    # One transaction: an empty trading_calendar means "no trading day at all"
    # to the whole system, so the clear-and-refill must not be interruptible.
    with db.transaction() as conn:
        conn.execute("DELETE FROM trading_calendar")
        conn.execute("INSERT INTO trading_calendar SELECT * FROM cal")
    register_source(
        source_name="qlib_chenditc",
        data_type="trading_calendar",
        url="https://github.com/chenditc/investment_data/releases/tag/2026-09-04",
        version="2026-09-04",
        file="qlib_data/calendars/day.txt",
        parser_version="1.0",
    )
    return cal


def ingest_daily_bars(
    years: range | None = None,
    chunk_years: int = 3,
    verbose: bool = True,
) -> List[Path]:
    """Import all instruments' daily bars, chunked by year, into parquet."""
    inst = load_instruments()
    qlib_symbols = inst["qlib_symbol"].tolist()
    if years is None:
        years = range(2000, 2026 + 1)

    written = []
    conn = db.connect()
    for start_year in range(years.start, years.stop, chunk_years):
        end_year = min(start_year + chunk_years - 1, years.stop - 1)
        t0 = time.time()
        df = load_bars(
            qlib_symbols,
            start_time=f"{start_year}-01-01",
            end_time=f"{end_year}-12-31",
        )
        if df.empty:
            continue
        df = df.reset_index()
        df["symbol"] = df["qlib_symbol"].map(_to_canonical)
        # The source dataset stores Yahoo-adjusted prices ($close etc. are
        # adjusted; raw = value / factor, see docs/数据来源与口径.md). The
        # canonical layer stores RAW prices plus the factor so downstream
        # research can adjust in either direction.
        price_cols = ["open", "high", "low", "close", "vwap"]
        f = df["factor"]
        for c in price_cols:
            df[c] = df[c] / f
        df = df[["symbol", "trade_date"] + price_cols
                + ["volume", "amount", "factor"]]
        df["source"] = "qlib_chenditc"
        df = df[df["symbol"].notna()]
        for year in range(start_year, end_year + 1):
            sub = df[df["trade_date"].dt.year == year]
            if sub.empty:
                continue
            p = config.PARQUET_SUBDIRS["daily"] / f"bars_{year}.parquet"
            sub.to_parquet(p, index=False)
            written.append(p)
        if verbose:
            print(
                f"[bars] {start_year}-{end_year}: {len(df)} rows in "
                f"{time.time() - t0:.1f}s"
            )
    db.refresh_daily_bars_view()
    register_source(
        source_name="qlib_chenditc",
        data_type="daily_bars",
        url="https://github.com/chenditc/investment_data/releases/tag/2026-09-04",
        version="2026-09-04",
        file="qlib_data/features/*.bin -> data/parquet/daily/*.parquet",
        parser_version="1.0",
    )
    return written


def _to_canonical(qlib_symbol: str):
    from ..symbols import normalize_symbol

    try:
        return normalize_symbol(qlib_symbol)
    except Exception:
        return None
