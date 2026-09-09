# -*- coding: utf-8 -*-
"""Shared market-scale calibration math (used by the full calibration run
and by the interim cache builder).

Per-stock constant-scale model: canonical volume/amount carry a per-stock
multiplicative scale (Yahoo adjustment artifacts; within-stock CV ~0.11,
cross-stock spread ~230x — see docs/step4_market_data_quality.md). The
repair estimates scale_volume = median(ground_truth_shares / canonical)
over the overlap window; canonical files are never modified.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .. import config

REPAIR_VERSION = "1.0"


def load_canonical(start: str) -> pd.DataFrame:
    """Canonical bars from parquet (pyarrow; DuckDB stays free)."""
    import pyarrow.parquet as pq

    tbl = pq.read_table(
        str(config.PARQUET_SUBDIRS["daily"]),
        columns=["symbol", "trade_date", "close", "volume", "amount"],
        filters=[("trade_date", ">=", pd.Timestamp(start).to_pydatetime())],
    )
    df = tbl.to_pandas()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def calibrate_one(canon: pd.DataFrame, symbol: str, payload: dict) -> dict:
    """Median gt/canonical ratios over the overlap window + stability CV.

    payload: {"source": "eastmoney"|"tencent", "rows": [{
        trade_date, volume_lot, amount, turnover_pct}]}
    Returns a scale-table row (or None when unusable).
    """
    rows = pd.DataFrame(payload["rows"])
    if rows.empty:
        return None
    rows["trade_date"] = pd.to_datetime(rows["trade_date"])
    sub = canon[canon["symbol"] == symbol]
    if sub.empty:
        return None
    m = sub.merge(rows, on="trade_date", how="inner")
    m = m[(m["volume"] > 0) & (m["volume_lot"] > 0)]
    if len(m) < 10:
        return None
    gt_shares = m["volume_lot"] * 100.0
    r_v = (gt_shares / m["volume"]).replace([np.inf, -np.inf], np.nan).dropna()
    if r_v.empty:
        return None
    scale_volume = float(np.median(r_v))
    out = {
        "symbol": symbol,
        "source": payload["source"],
        "n_overlap": int(len(r_v)),
        "window_start": str(m["trade_date"].min().date()),
        "window_end": str(m["trade_date"].max().date()),
        "ratio_median": float(np.median(r_v)),
        "ratio_cv": float(r_v.std() / r_v.mean()) if r_v.mean() > 0 else np.nan,
        "scale_volume": scale_volume,
        "scale_amount": None,
        "amount_implied_check": None,
    }
    if payload["source"] == "eastmoney" and m["amount"].notna().any():
        both = m[(m["amount"] > 0) & (m["amount_y"] > 0)]
        if len(both) >= 10:
            r_a = (both["amount_y"] / both["amount"]).replace(
                [np.inf, -np.inf], np.nan).dropna()
            if not r_a.empty:
                out["scale_amount"] = float(np.median(r_a))
                implied = both["volume"] * scale_volume * both["close"]
                out["amount_implied_check"] = float(
                    (implied / both["amount_y"] - 1.0).abs().median())
    return out


def finalize_table(results: list) -> pd.DataFrame:
    """Attach the repair metadata columns required by the audit trail."""
    out = pd.DataFrame(results)
    out["repair_version"] = REPAIR_VERSION
    out["method"] = "median_gt_canonical_ratio"
    out["reason"] = (
        "Yahoo-source per-stock volume/amount scaling artifact "
        "(see docs/step4_market_data_quality.md)"
    )
    return out
