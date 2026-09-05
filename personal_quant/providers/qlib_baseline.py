# -*- coding: utf-8 -*-
"""Qlib baseline data provider.

Reads the local Qlib dataset (qlib_data/, from chenditc/investment_data via
the official README recommendation) and emits plain DataFrames:

- trading calendar (from calendars/day.txt)
- instrument list with data availability ranges (from instruments/all.txt)
- daily bars via qlib D.features (open/high/low/close/volume/amount/vwap)

Pure local reads — no network involved.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import pandas as pd

from .. import config

QLIB_DATA_DIR = config.PROJECT_ROOT / "qlib_data"
CALENDAR_FILE = QLIB_DATA_DIR / "calendars" / "day.txt"
INSTRUMENTS_FILE = QLIB_DATA_DIR / "instruments" / "all.txt"

BAR_FIELDS = ["$open", "$high", "$low", "$close", "$volume", "$amount", "$vwap",
              "$factor"]
BAR_COLUMNS = ["open", "high", "low", "close", "volume", "amount", "vwap",
               "factor"]


def load_calendar() -> pd.DataFrame:
    """Return DataFrame(exchange, trade_date) with is_open=True for all rows."""
    dates = pd.read_csv(
        CALENDAR_FILE, header=None, names=["trade_date"], dtype=str
    )["trade_date"].tolist()
    return pd.DataFrame(
        {"exchange": "CN", "trade_date": pd.to_datetime(dates), "is_open": True}
    )


def load_instruments() -> pd.DataFrame:
    """Return DataFrame(symbol, start_date, end_date) from instruments/all.txt.

    start_date/end_date are the data availability window in the Qlib dataset,
    NOT list/delist dates.
    """
    df = pd.read_csv(
        INSTRUMENTS_FILE,
        sep=r"\s+",
        header=None,
        names=["qlib_symbol", "start_date", "end_date"],
        dtype=str,
    )
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"] = pd.to_datetime(df["end_date"])
    return df


def load_bars(
    instruments: List[str],
    start_time: str,
    end_time: str,
    freq: str = "day",
    n_jobs: int = 20,
) -> pd.DataFrame:
    """Load daily bars for `instruments` (Qlib spelling, e.g. SH600519).

    Returns a MultiIndex(qlib_symbol, datetime) DataFrame with columns
    open/high/low/close/volume/amount/vwap. Raises on qlib errors.
    """
    import qlib
    from qlib.constant import REG_CN
    from qlib.data import D

    if not getattr(qlib, "_initialized", False):
        try:
            qlib.init(
                provider_uri=str(QLIB_DATA_DIR), region=REG_CN, n_jobs=n_jobs
            )
        except TypeError:
            # older signatures don't accept n_jobs
            qlib.init(provider_uri=str(QLIB_DATA_DIR), region=REG_CN)
    df = D.features(
        instruments,
        BAR_FIELDS,
        start_time=start_time,
        end_time=end_time,
        freq=freq,
    )
    if df is None or df.empty:
        return pd.DataFrame(columns=["symbol", "trade_date"] + BAR_COLUMNS)
    df = df.rename(
        columns={f"${c}": c for c in BAR_COLUMNS}
    )
    df.index = df.index.set_names(["qlib_symbol", "trade_date"])
    return df


def load_bars_chunked(
    start_year: int, end_year: int, chunk_years: int = 3
) -> "list[Tuple[str, str]]":
    """Yield (start_time, end_time) calendar windows for chunked import."""
    for y in range(start_year, end_year + 1, chunk_years):
        end = min(y + chunk_years - 1, end_year)
        yield f"{y}-01-01", f"{end}-12-31"
