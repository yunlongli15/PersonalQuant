# -*- coding: utf-8 -*-
"""Performance / risk metrics for strategy and benchmarks."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def daily_returns(nav: pd.Series) -> pd.Series:
    return nav.pct_change().dropna()


def annualized_return(nav: pd.Series) -> float:
    if len(nav) < 2:
        return float("nan")
    years = (nav.index[-1] - nav.index[0]).days / 365.25
    total = nav.iloc[-1] / nav.iloc[0] - 1.0
    if total <= -1 or years <= 0:
        return float("nan")
    return (1.0 + total) ** (1.0 / years) - 1.0


def annualized_volatility(nav: pd.Series) -> float:
    r = daily_returns(nav)
    if len(r) < 2:
        return float("nan")
    return float(r.std(ddof=1) * np.sqrt(TRADING_DAYS))


def sharpe_ratio(nav: pd.Series, rf: float = 0.02) -> float:
    r = daily_returns(nav)
    if len(r) < 2 or r.std(ddof=1) == 0:
        return float("nan")
    ann = r.mean() * TRADING_DAYS
    vol = r.std(ddof=1) * np.sqrt(TRADING_DAYS)
    return (ann - rf) / vol


def max_drawdown(nav: pd.Series) -> float:
    if nav.empty:
        return float("nan")
    peak = nav.cummax()
    dd = nav / peak - 1.0
    return float(dd.min())


def calmar_ratio(nav: pd.Series) -> float:
    ann = annualized_return(nav)
    mdd = max_drawdown(nav)
    if not mdd or np.isnan(mdd):
        return float("nan")
    return ann / abs(mdd)


def information_ratio(nav: pd.Series, bench_nav: pd.Series) -> float:
    """Annualized IR of daily excess returns vs benchmark."""
    aligned = pd.concat([nav.pct_change(), bench_nav.pct_change()],
                        axis=1, keys=["s", "b"]).dropna()
    if len(aligned) < 2:
        return float("nan")
    ex = aligned["s"] - aligned["b"]
    if ex.std(ddof=1) == 0:
        return float("nan")
    return float(ex.mean() / ex.std(ddof=1) * np.sqrt(TRADING_DAYS))


def alpha_beta(nav: pd.Series, bench_nav: pd.Series) -> tuple[float, float]:
    """Monthly-return regression vs benchmark: alpha (annualized), beta."""
    ms = nav.resample("ME").last().pct_change().dropna()
    mb = bench_nav.resample("ME").last().pct_change().dropna()
    aligned = pd.concat([ms, mb], axis=1, keys=["s", "b"]).dropna()
    if len(aligned) < 6:
        return float("nan"), float("nan")
    b, a = np.polyfit(aligned["b"], aligned["s"], 1)
    return float(a * 12), float(b)


def win_rate(nav: pd.Series) -> float:
    mr = nav.resample("ME").last().pct_change().dropna()
    if mr.empty:
        return float("nan")
    return float((mr > 0).mean())


def monthly_returns(nav: pd.Series) -> pd.Series:
    return nav.resample("ME").last().pct_change().dropna()


def yearly_returns(nav: pd.Series) -> pd.Series:
    return nav.resample("YE").last().pct_change().dropna()


def turnover_summary(turnover: pd.Series) -> dict:
    if turnover.empty:
        return {"avg": float("nan"), "total": float("nan"), "n": 0}
    return {"avg": float(turnover.mean()), "total": float(turnover.sum()),
            "n": int(len(turnover))}


def summarize(
    nav: pd.Series,
    bench_nav: Optional[pd.Series] = None,
    turnover: Optional[pd.Series] = None,
    n_trades: Optional[int] = None,
    label: str = "strategy",
) -> dict:
    out = {
        "label": label,
        "cumulative_return": float(nav.iloc[-1] / nav.iloc[0] - 1.0),
        "annualized_return": annualized_return(nav),
        "annualized_volatility": annualized_volatility(nav),
        "sharpe": sharpe_ratio(nav),
        "max_drawdown": max_drawdown(nav),
        "calmar": calmar_ratio(nav),
        "win_rate_monthly": win_rate(nav),
        "n_days": int(len(nav)),
    }
    if bench_nav is not None and not bench_nav.empty:
        out["information_ratio"] = information_ratio(nav, bench_nav)
        alpha, beta = alpha_beta(nav, bench_nav)
        out["alpha_annualized"] = alpha
        out["beta"] = beta
    if turnover is not None:
        out.update(turnover_summary(turnover))
    if n_trades is not None:
        out["n_trades"] = n_trades
    return out
