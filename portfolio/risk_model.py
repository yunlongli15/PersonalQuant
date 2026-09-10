# -*- coding: utf-8 -*-
"""Risk model: per-rebalance PIT covariance + risk contributions (spec §41).

Everything is derived from the PIT covariance (portfolio/covariance.py);
no other volatility estimate is used, so risk contributions always sum to
the portfolio variance of exactly the covariance the optimizer saw.

marginal_risk_i    = (Σw)_i / σ_p          (dσ_p / dw_i)
component_risk_i   = w_i · (Σw)_i          (Σ_i = σ_p²)
risk_share_i       = component_i / σ_p²    (Σ_i = 1, 用于"每只股票风险贡献 %")
"""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np
import pandas as pd

from .covariance import CovarianceResult, build_returns, estimate_covariance


def covariance_at(data, symbols: Sequence[str], signal_date,
                  window: int = 60, method: str = "sample",
                  halflife: Optional[float] = None) -> CovarianceResult:
    """PIT covariance of `symbols` at `signal_date` (data.close_raw 宽表)."""
    return estimate_covariance(data.close_raw, symbols, signal_date,
                               window, method, halflife)


def per_symbol_vol(data, symbols: Sequence[str], signal_date,
                   window: int = 60) -> pd.Series:
    """Per-symbol realized vol over the trailing `window` trading days."""
    ret = build_returns(data.close_raw, symbols, signal_date, window)
    if ret.empty:
        return pd.Series(dtype=float)
    return ret.std(ddof=1)


def portfolio_vol(cov: CovarianceResult, weights: pd.Series) -> float:
    w = weights.reindex(cov.cov.columns).fillna(0.0)
    if len(w) == 0:
        return 0.0
    var = float(w.to_numpy() @ cov.cov.to_numpy() @ w.to_numpy())
    return float(np.sqrt(max(var, 0.0)))


def marginal_risk(cov: CovarianceResult, weights: pd.Series) -> pd.Series:
    w = weights.reindex(cov.cov.columns).fillna(0.0)
    pv = portfolio_vol(cov, w)
    if pv <= 1e-12:
        return pd.Series(0.0, index=w.index)
    m = cov.cov.to_numpy() @ w.to_numpy() / pv
    return pd.Series(m, index=w.index)


def component_risk(cov: CovarianceResult, weights: pd.Series) -> pd.Series:
    w = weights.reindex(cov.cov.columns).fillna(0.0)
    return w * pd.Series(cov.cov.to_numpy() @ w.to_numpy(), index=w.index)


def risk_shares(cov: CovarianceResult, weights: pd.Series) -> pd.Series:
    c = component_risk(cov, weights)
    tot = c.sum()
    if abs(tot) > 1e-16:
        return c / tot
    return pd.Series(0.0, index=c.index)
