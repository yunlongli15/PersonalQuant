# -*- coding: utf-8 -*-
"""Factor engine base: FactorData container + canonical-layer loading.

Strictness rules (tested in tests/factors/):
- technical factors use only data <= the signal date (rolling/shift on
  per-stock rows, never future rows);
- financial factors honor PIT: a report is usable iff signal_date >
  availability_date (= announcement_date; see docs/point_in_time.md);
- cross-stock comparability of volume/amount comes from the calibrated
  scale table (docs/step4_market_data_quality.md); when no calibration
  exists the raw columns are used with scale=1 and the fact is recorded.

Loading reads parquet via pyarrow (multi-process safe; DuckDB stays free
for other processes such as the financial fetcher).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

from personal_quant import PROJECT_ROOT, config

DERIVED = PROJECT_ROOT / "data" / "derived" / "factors"
SCALE_PATH = config.PARQUET_SUBDIRS["market"] / "market_scale.parquet"
FINANCIAL_SNAPSHOT = DERIVED / "financial_metrics.parquet"
CALENDAR_CACHE = DERIVED / "calendar.parquet"
TURNOVER_CACHE = DERIVED / "em_turnover.parquet"
INDUSTRY_CACHE = DERIVED / "industries.parquet"

_lock = threading.Lock()
_data_cache: Dict[tuple, "FactorData"] = {}


# ---------------------------------------------------------------------------
# Small loaders (parquet caches, DuckDB fallback)
# ---------------------------------------------------------------------------

def load_calendar() -> pd.DatetimeIndex:
    """Official trading calendar (cached to parquet by factor_prepare)."""
    if CALENDAR_CACHE.exists():
        days = pd.read_parquet(CALENDAR_CACHE)["trade_date"]
        return pd.DatetimeIndex(pd.to_datetime(days))
    from personal_quant import db

    days = db.connect().execute(
        "SELECT trade_date FROM trading_calendar WHERE is_open ORDER BY trade_date"
    ).fetch_df()
    return pd.DatetimeIndex(days["trade_date"])


def cached_rebalance_dates(start, end, frequency="monthly",
                           rule="last_trading_day"):
    """Rebalance calendar from the cached trading calendar (DB-free, so
    research scripts can run while the financial fetcher holds the DuckDB
    lock). Same semantics as strategy.rebalance.rebalance_dates."""
    cal = load_calendar()
    days = cal[(cal >= pd.Timestamp(start)) & (cal <= pd.Timestamp(end))]
    if len(days) == 0:
        return []
    offset = pd.tseries.frequencies.to_offset(
        {"monthly": "ME", "weekly": "W-FRI"}[frequency])
    groups = days.to_series().groupby(days.to_period(offset))
    if rule == "last_trading_day":
        out = [g.iloc[-1] for _, g in groups]
    elif rule == "first_trading_day":
        out = [g.iloc[0] for _, g in groups]
    else:
        raise ValueError(f"unsupported rule {rule}")
    return [pd.Timestamp(t) for t in out]


def load_scale() -> pd.DataFrame:
    """Per-stock volume/amount calibration (repair pipeline output)."""
    if SCALE_PATH.exists():
        return pd.read_parquet(SCALE_PATH)
    return pd.DataFrame(columns=["symbol", "scale_volume", "scale_amount"])


def load_financial() -> pd.DataFrame:
    """PIT financial metrics (snapshot; refreshed by the financial fetcher)."""
    cols = ["symbol", "fiscal_year", "fiscal_period", "availability_date",
            "availability_date_unknown", "metric_name", "metric_value"]
    if FINANCIAL_SNAPSHOT.exists():
        return pd.read_parquet(FINANCIAL_SNAPSHOT, columns=cols)
    from personal_quant import db

    return db.connect().execute(
        f"SELECT {', '.join(cols)} FROM financial_metrics"
    ).fetch_df()


def load_industries() -> pd.Series:
    """symbol -> industry_name (CSRC, current classification)."""
    if INDUSTRY_CACHE.exists():
        df = pd.read_parquet(INDUSTRY_CACHE)
        return df.set_index("symbol")["industry_name"]
    from personal_quant import db

    df = db.connect().execute(
        "SELECT symbol, industry_name FROM industry_membership "
        "WHERE classification='csrc' AND industry_name IS NOT NULL"
    ).fetch_df()
    return df.groupby("symbol")["industry_name"].last()


# ---------------------------------------------------------------------------
# FactorData
# ---------------------------------------------------------------------------

@dataclass
class FactorData:
    """Everything a factor computation may read, aligned to the calendar.

    Wide panels are indexed by the official trading calendar and have one
    column per symbol; a NaN marks a day the stock did not trade.
    """

    calendar: pd.DatetimeIndex
    bars: pd.DataFrame                      # long: symbol, trade_date, OHLCV+factor
    adj_close: pd.DataFrame                 # close * factor (adjusted)
    close_raw: pd.DataFrame                 # raw close (execution price)
    volume_raw: pd.DataFrame                # source units (per-stock scale)
    volume_shares: pd.DataFrame             # calibrated shares
    amount_cny: pd.DataFrame                # calibrated CNY amount
    scale: pd.DataFrame                     # calibration table (raw)
    financial: pd.DataFrame                 # PIT metrics long table
    industries: pd.Series                   # symbol -> industry
    turnover: Optional[pd.DataFrame] = None # EM turnover (wide; may be absent)
    start: Optional[pd.Timestamp] = None
    end: Optional[pd.Timestamp] = None
    scale_available: bool = True

    def slice(self, start, end) -> "FactorData":
        cal = self.calendar[(self.calendar >= start) & (self.calendar <= end)]
        w = {f: self._slice_wide(getattr(self, f), start, end)
             for f in ("adj_close", "close_raw", "volume_raw",
                       "volume_shares", "amount_cny")}
        w["turnover"] = self._slice_wide(self.turnover, start, end) \
            if self.turnover is not None else None
        return FactorData(
            calendar=cal, bars=self.bars, financial=self.financial,
            industries=self.industries, scale=self.scale,
            start=start, end=end, scale_available=self.scale_available, **w,
        )

    @staticmethod
    def _slice_wide(df, start, end):
        if df is None:
            return None
        return df[(df.index >= start) & (df.index <= end)]


def load_factor_data(
    start, end,
    symbols: Optional[list] = None,
    use_cache: bool = True,
) -> FactorData:
    """Load canonical bars (+calibration) into a FactorData for [start, end].

    History is padded 370 calendar days to the left so factors with a
    120-trading-day lookback have warm-up data; rows before `start` are
    trimmed afterwards (NaN warm-up values are expected at the head).
    """
    import pyarrow.parquet as pq

    start, end = pd.Timestamp(start), pd.Timestamp(end)
    key = (str(start.date()), str(end.date()), tuple(sorted(symbols)) if symbols else ())
    with _lock:
        if use_cache and key in _data_cache:
            return _data_cache[key]

        lo = start - pd.Timedelta(days=370)
        tbl = pq.read_table(
            str(config.PARQUET_SUBDIRS["daily"]),
            columns=["symbol", "trade_date", "open", "high", "low", "close",
                     "volume", "amount", "vwap", "factor"],
            filters=[("trade_date", ">=", lo.to_pydatetime()),
                     ("trade_date", "<=", end.to_pydatetime())],
        )
        bars = tbl.to_pandas()
        bars["trade_date"] = pd.to_datetime(bars["trade_date"])
        if symbols:
            bars = bars[bars["symbol"].isin(symbols)]

        calendar = load_calendar()
        cal = calendar[(calendar >= lo) & (calendar <= end)]

        scale = load_scale()
        scale_available = len(scale) > 0
        if not scale_available:
            scale = pd.DataFrame(columns=["symbol", "scale_volume", "scale_amount"])
        sv = scale.set_index("symbol")["scale_volume"].reindex(
            bars["symbol"].unique()).fillna(1.0)
        sa = scale.set_index("symbol")["scale_amount"] \
            if "scale_amount" in scale.columns else pd.Series(dtype=float)

        bars["adj_close"] = bars["close"] * bars["factor"]
        bars["volume_shares"] = bars["volume"] * bars["symbol"].map(sv)
        sa_map = sa.reindex(bars["symbol"].unique()) if len(sa) else \
            pd.Series(np.nan, index=bars["symbol"].unique())
        bars["amount_cny"] = np.where(
            bars["symbol"].map(sa_map).notna().to_numpy(),
            bars["amount"] * bars["symbol"].map(sa_map).to_numpy(),
            bars["volume_shares"] * bars["close"],
        )

        def wide(col, dtype=np.float64):
            w = bars.pivot_table(index="trade_date", columns="symbol",
                                 values=col, aggfunc="last")
            return w.reindex(cal).astype(dtype)

        data = FactorData(
            calendar=cal,
            bars=bars,
            adj_close=wide("adj_close"),
            close_raw=wide("close"),
            volume_raw=wide("volume", np.float64),
            volume_shares=wide("volume_shares", np.float64),
            amount_cny=wide("amount_cny", np.float64),
            scale=scale,
            financial=load_financial(),
            industries=load_industries(),
            start=start,
            end=end,
            scale_available=scale_available,
        )
        if TURNOVER_CACHE.exists():
            turn = pd.read_parquet(TURNOVER_CACHE,
                                   filters=[("trade_date", ">=", lo),
                                            ("trade_date", "<=", end)])
            data.turnover = turn.pivot_table(
                index="trade_date", columns="symbol", values="turnover_pct"
            ).reindex(cal)
        data = data.slice(start, end)
        _data_cache[key] = data
        return data


# ---------------------------------------------------------------------------
# Spec interface: compute_factor(data, as_of_date) -> symbol/date/factor_value
# ---------------------------------------------------------------------------

def compute_factor_at(data: FactorData, name: str, date) -> pd.Series:
    """Factor value at one date as a (symbol -> factor_value) series."""
    from .registry import FACTORS

    fn = FACTORS[name]
    panel = fn(data, dates=[pd.Timestamp(date)])
    if panel is None or panel.empty:
        return pd.Series(dtype=float)
    s = panel.iloc[-1].dropna()
    s.name = name
    return s
