# -*- coding: utf-8 -*-
"""Model evaluation: IC series, quantile analysis, stability."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .model import compute_ic


def ic_summary(ic_df: pd.DataFrame, period: str) -> dict:
    """IC mean/std/ICIR/positive-ratio for a period."""
    if ic_df.empty:
        return {"period": period, "n_months": 0}
    ic = ic_df["ic"]
    ric = ic_df["rank_ic"]
    return {
        "period": period,
        "n_months": int(len(ic_df)),
        "ic_mean": float(ic.mean()),
        "ic_std": float(ic.std(ddof=1)) if len(ic) > 1 else float("nan"),
        "icir": float(ic.mean() / ic.std(ddof=1)) if len(ic) > 1 and ic.std(ddof=1) > 0 else float("nan"),
        "ic_positive_ratio": float((ic > 0).mean()),
        "rank_ic_mean": float(ric.mean()),
        "rank_icir": float(ric.mean() / ric.std(ddof=1)) if len(ric) > 1 and ric.std(ddof=1) > 0 else float("nan"),
        "rank_ic_positive_ratio": float((ric > 0).mean()),
    }


def quantile_analysis(predictions: pd.DataFrame, n_quantiles: int = 5) -> pd.DataFrame:
    """Per-month quantile future returns (Q1 worst .. Q5 best by prediction).

    Returns one row per month per quantile with the mean realized label.
    """
    rows = []
    for date, g in predictions.groupby("date"):
        if len(g) < n_quantiles * 5:
            continue
        g = g.dropna(subset=["label"])
        if len(g) < n_quantiles * 5:
            continue
        g["q"] = pd.qcut(g["prediction"], n_quantiles, labels=False)
        for q in range(n_quantiles):
            sub = g[g["q"] == q]
            rows.append(
                {
                    "date": date,
                    "quantile": q + 1,
                    "n": len(sub),
                    "mean_return": float(sub["label"].mean()),
                    "mean_prediction": float(sub["prediction"].mean()),
                }
            )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def quantile_summary(qa: pd.DataFrame) -> pd.DataFrame:
    """Average future return per quantile across months."""
    if qa.empty:
        return pd.DataFrame()
    return qa.groupby("quantile")[["mean_return", "n"]].agg(
        mean_return=("mean_return", "mean"), n=("n", "sum")
    ).reset_index()


def top_bottom_spread(qa: pd.DataFrame) -> dict:
    """Mean monthly spread between Q5 and Q1 realized returns."""
    if qa.empty:
        return {}
    piv = qa.pivot(index="date", columns="quantile", values="mean_return")
    if piv.empty or 5 not in piv.columns or 1 not in piv.columns:
        return {}
    spread = piv[5] - piv[1]
    return {
        "spread_mean": float(spread.mean()),
        "spread_positive_ratio": float((spread > 0).mean()),
        "n_months": int(len(spread)),
    }
