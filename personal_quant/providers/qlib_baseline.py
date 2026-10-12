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

#: Same-session overlay (scripts/quant/update_daily_overlay.py): the current
#: trading day's bars, bridged onto the canonical scale because the upstream
#: snapshot is always one session behind. Every reader of the daily layer
#: must include it, or that reader silently ranks on T-1 — which is the exact
#: bug this layer exists to remove. Kept here rather than in
#: `strategy/qlib_provider.py` because `factors/` is forbidden from importing
#: strategy modules, and both need the same merge.
OVERLAY_DIR = config.PARQUET_DIR / "overlay"
OVERLAY_BARS = OVERLAY_DIR / "daily_overlay.parquet"
OVERLAY_CALENDAR = OVERLAY_DIR / "calendar_extra.parquet"
OVERLAY_COLUMNS = ["symbol", "trade_date", "open", "high", "low", "close",
                   "volume", "amount", "vwap", "factor", "source"]


def load_overlay(start_time=None, end_time=None) -> pd.DataFrame:
    """The overlay slice in the canonical schema (empty when absent)."""
    import pyarrow.parquet as pq

    if not OVERLAY_BARS.exists():
        return pd.DataFrame(columns=OVERLAY_COLUMNS)
    filters = []
    if start_time is not None:
        filters.append(("trade_date", ">=",
                        pd.Timestamp(start_time).to_pydatetime()))
    if end_time is not None:
        filters.append(("trade_date", "<=",
                        pd.Timestamp(end_time).to_pydatetime()))
    try:
        df = pq.read_table(str(OVERLAY_BARS), filters=filters or None) \
            .to_pandas()
    except Exception:                                          # noqa: BLE001
        return pd.DataFrame(columns=OVERLAY_COLUMNS)
    if not df.empty:
        df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def overlay_dates() -> List[pd.Timestamp]:
    """Sessions the overlay contributes to the trading calendar."""
    if not OVERLAY_CALENDAR.exists():
        return []
    try:
        df = pd.read_parquet(OVERLAY_CALENDAR, columns=["trade_date"])
    except Exception:                                          # noqa: BLE001
        return []
    return sorted(pd.to_datetime(df["trade_date"]).tolist())


def read_daily_bars(start_time=None, end_time=None, columns=None,
                    directory=None) -> pd.DataFrame:
    """Canonical daily bars **with the overlay merged in**.

    `keep="last"` lets the overlay win on the only collision that can occur —
    the overlay re-stating a session the snapshot also carries (which
    `scripts/quant/update_daily_overlay.py --reconcile-only` then retires).
    """
    import pyarrow.parquet as pq

    filters = []
    if start_time is not None:
        filters.append(("trade_date", ">=",
                        pd.Timestamp(start_time).to_pydatetime()))
    if end_time is not None:
        filters.append(("trade_date", "<=",
                        pd.Timestamp(end_time).to_pydatetime()))
    tbl = pq.read_table(str(directory or config.PARQUET_SUBDIRS["daily"]),
                        columns=columns, filters=filters or None)
    bars = tbl.to_pandas()
    if "trade_date" in bars.columns:
        bars["trade_date"] = pd.to_datetime(bars["trade_date"])

    ov = load_overlay(start_time, end_time)
    if not ov.empty:
        want = [c for c in (columns or OVERLAY_COLUMNS)
                if c in bars.columns or c in ov.columns]
        for c in want:
            if c not in bars.columns:
                bars[c] = pd.NA
        bars = pd.concat([bars[want], ov.reindex(columns=want)],
                         ignore_index=True)
        bars = bars.drop_duplicates(subset=["symbol", "trade_date"],
                                    keep="last")
    return bars


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
