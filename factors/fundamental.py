# -*- coding: utf-8 -*-
"""PIT financial-metric join engine (STEP 4).

Turns the canonical financial_metrics table (strict PIT, see
docs/point_in_time.md) into factor panels: at each signal date a stock
carries the LATEST annual-report value whose availability_date < signal
date (the announcement day itself is excluded — the data becomes usable
the next trading day). Values are forward-filled step functions that only
move on announcement days; financial factors therefore have zero look-ahead
by construction.

The panels are computed on demand from the financial snapshot
(data/derived/factors/financial_metrics.parquet, refreshed by
scripts/fetch_financial_universe.py) — the factor engine never triggers
downloads itself; the lazy pipeline does that offline from research runs.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from .base import FactorData

_STRICT_SQL_MASK = ["availability_date_unknown", "availability_date"]


def _metric_rows(data: FactorData, metric: str) -> pd.DataFrame:
    fin = data.financial
    if fin is None or fin.empty:
        return pd.DataFrame(columns=["symbol", "availability_date",
                                     "fiscal_year", "metric_value"])
    sub = fin[fin["metric_name"] == metric]
    sub = sub[sub["availability_date"].notna()]
    sub = sub[~sub["availability_date_unknown"].fillna(False)]
    sub = sub.copy()
    sub["availability_date"] = pd.to_datetime(sub["availability_date"])
    sub = sub.sort_values(["symbol", "availability_date", "fiscal_year"],
                          kind="stable")
    # one row per (symbol, availability_date): latest extraction version
    return sub.drop_duplicates(subset=["symbol", "availability_date"],
                               keep="last")


def pit_metric_panel(
    data: FactorData, metric: str, dates,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Return (value_panel, fiscal_year_panel) indexed by dates x symbols.

    value = latest annual-report value usable at the date (strict PIT);
    fiscal_year = which report period supplied the value.
    """
    sub = _metric_rows(data, metric)
    out = pd.DataFrame(index=pd.DatetimeIndex(dates),
                       columns=sub["symbol"].unique(), dtype=float)
    fy = pd.DataFrame(index=pd.DatetimeIndex(dates),
                      columns=sub["symbol"].unique(), dtype=float)
    if sub.empty:
        return out, fy
    for d in pd.DatetimeIndex(dates):
        avail = sub[sub["availability_date"] < d]  # strict: > availability_date
        if avail.empty:
            continue
        latest = avail.groupby("symbol").last()
        out.loc[d, latest.index] = latest["metric_value"].values
        fy.loc[d, latest.index] = latest["fiscal_year"].values
    return out, fy


def pit_metric_series(data: FactorData, metric: str, date) -> pd.Series:
    panel, _ = pit_metric_panel(data, metric, [pd.Timestamp(date)])
    if panel.empty:
        return pd.Series(dtype=float)
    s = panel.iloc[-1].dropna()
    s.name = metric
    return s


def bps_panel(data: FactorData, dates) -> pd.DataFrame:
    """Book value per share: the disclosed 每股净资产 when present, else
    calculated as net_assets / (net_profit / eps) — three figures from the
    SAME annual report (many reports put 每股净资产 outside the key
    accounting-data table, so the reported value is often absent while the
    three components are all reported). Loss-making stocks work (both
    signs cancel); eps=0 or net_profit missing -> NaN."""
    bps, _ = pit_metric_panel(data, "bps", dates)
    na, _ = pit_metric_panel(data, "net_assets", dates)
    np_, _ = pit_metric_panel(data, "net_profit", dates)
    eps, _ = pit_metric_panel(data, "eps", dates)
    shares = np_ / eps.where(eps != 0)
    calc = na / shares.where(shares > 0)
    return bps.where(bps.notna(), calc).replace([np.inf, -np.inf], np.nan)


def shares_panel(data: FactorData, dates) -> pd.DataFrame:
    """Total shares outstanding from the latest annual report
    (net_assets / book-value-per-share)."""
    na, _ = pit_metric_panel(data, "net_assets", dates)
    bps = bps_panel(data, dates)
    shares = na / bps.where(bps > 0)
    return shares.replace([np.inf, -np.inf], np.nan)


def financial_coverage(data: FactorData, metric: str, dates,
                       universe: Optional[dict] = None) -> float:
    """Fraction of universe-date cells covered by a PIT metric panel."""
    panel, _ = pit_metric_panel(data, metric, dates)
    if panel.empty:
        return 0.0
    if universe:
        mask = pd.DataFrame(False, index=panel.index, columns=panel.columns)
        for d, syms in universe.items():
            if d in panel.index:
                mask.loc[d, mask.columns.intersection(syms)] = True
        panel = panel.where(mask)
    n = panel.notna().sum().sum()
    denom = (mask.sum().sum() if universe else panel.size)
    return float(n / denom) if denom else 0.0
