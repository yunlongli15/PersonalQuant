# -*- coding: utf-8 -*-
"""Technical / market factors (strictly backward-looking).

Every factor here is a per-stock rolling/shift operation over the stock's
own trading rows — data <= the signal date only. The no-future-data
property is enforced by construction and tested by perturbing future rows
(tests/factors/test_no_future_data.py).

Conventions:
- returns are computed on ADJUSTED close (close * factor);
- volume/amount RATIOS cancel the per-stock source scaling and use raw
  columns; LEVELS (amount_*) use the calibrated columns (amount_cny);
- NaN rows are suspension days (the stock has no bar that day).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import FactorData
from .registry import register


def _out(panel: pd.DataFrame, dates) -> pd.DataFrame:
    if dates is None:
        return panel
    return panel.reindex(pd.DatetimeIndex(dates))


# --- momentum ---------------------------------------------------------------

@register(dict(
    factor_name="momentum_20", category="momentum",
    formula="adj_close[t]/adj_close[t-20]-1",
    source="market", required_fields=["close", "factor"],
    pit=True, direction="positive",
    description="20-trading-day momentum on adjusted close",
    version="1.0", status="candidate",
))
def momentum_20(data: FactorData, dates=None):
    return _out(data.adj_close / data.adj_close.shift(20) - 1.0, dates)


@register(dict(
    factor_name="momentum_60", category="momentum",
    formula="adj_close[t]/adj_close[t-60]-1",
    source="market", required_fields=["close", "factor"],
    pit=True, direction="positive",
    description="60-trading-day momentum on adjusted close",
    version="1.0", status="candidate",
))
def momentum_60(data: FactorData, dates=None):
    return _out(data.adj_close / data.adj_close.shift(60) - 1.0, dates)


@register(dict(
    factor_name="momentum_120", category="momentum",
    formula="adj_close[t]/adj_close[t-120]-1",
    source="market", required_fields=["close", "factor"],
    pit=True, direction="positive",
    description="120-trading-day momentum on adjusted close",
    version="1.0", status="candidate",
))
def momentum_120(data: FactorData, dates=None):
    return _out(data.adj_close / data.adj_close.shift(120) - 1.0, dates)


# --- reversal ---------------------------------------------------------------

@register(dict(
    factor_name="reversal_5", category="reversal",
    formula="-(adj_close[t]/adj_close[t-5]-1)",
    source="market", required_fields=["close", "factor"],
    pit=True, direction="positive",
    description="negative 5-trading-day return (short-term reversal)",
    version="1.0", status="candidate",
))
def reversal_5(data: FactorData, dates=None):
    return _out(-(data.adj_close / data.adj_close.shift(5) - 1.0), dates)


@register(dict(
    factor_name="reversal_20", category="reversal",
    formula="-(adj_close[t]/adj_close[t-20]-1)",
    source="market", required_fields=["close", "factor"],
    pit=True, direction="positive",
    description="negative 20-trading-day return (short-term reversal)",
    version="1.0", status="candidate",
))
def reversal_20(data: FactorData, dates=None):
    return _out(-(data.adj_close / data.adj_close.shift(20) - 1.0), dates)


# --- volatility -------------------------------------------------------------

@register(dict(
    factor_name="volatility_20", category="volatility",
    formula="std(ret_daily, 20)",
    source="market", required_fields=["close", "factor"],
    pit=True, direction="negative",
    description="20-day daily-return volatility",
    version="1.0", status="candidate",
))
def volatility_20(data: FactorData, dates=None):
    return _out(data.adj_close.pct_change(fill_method=None).rolling(20).std(),
                dates)


@register(dict(
    factor_name="volatility_60", category="volatility",
    formula="std(ret_daily, 60)",
    source="market", required_fields=["close", "factor"],
    pit=True, direction="negative",
    description="60-day daily-return volatility",
    version="1.0", status="candidate",
))
def volatility_60(data: FactorData, dates=None):
    return _out(data.adj_close.pct_change(fill_method=None).rolling(60).std(),
                dates)


@register(dict(
    factor_name="downside_volatility_60", category="volatility",
    formula="sqrt(mean(min(ret,0)^2, 60))",
    source="market", required_fields=["close", "factor"],
    pit=True, direction="negative",
    description="60-day downside semideviation",
    version="1.0", status="candidate",
))
def downside_volatility_60(data: FactorData, dates=None):
    r = data.adj_close.pct_change(fill_method=None)
    neg = r.where(r < 0, 0.0)
    return _out((neg ** 2).rolling(60).mean() ** 0.5, dates)


# --- price position ---------------------------------------------------------

@register(dict(
    factor_name="price_vs_ma20", category="price_position",
    formula="adj_close/MA(adj_close,20)-1",
    source="market", required_fields=["close", "factor"],
    pit=True, direction="positive",
    description="close relative to its 20-day moving average",
    version="1.0", status="candidate",
))
def price_vs_ma20(data: FactorData, dates=None):
    return _out(data.adj_close / data.adj_close.rolling(20).mean() - 1.0, dates)


@register(dict(
    factor_name="price_vs_ma60", category="price_position",
    formula="adj_close/MA(adj_close,60)-1",
    source="market", required_fields=["close", "factor"],
    pit=True, direction="positive",
    description="close relative to its 60-day moving average",
    version="1.0", status="candidate",
))
def price_vs_ma60(data: FactorData, dates=None):
    return _out(data.adj_close / data.adj_close.rolling(60).mean() - 1.0, dates)


@register(dict(
    factor_name="price_vs_ma120", category="price_position",
    formula="adj_close/MA(adj_close,120)-1",
    source="market", required_fields=["close", "factor"],
    pit=True, direction="positive",
    description="close relative to its 120-day moving average",
    version="1.0", status="candidate",
))
def price_vs_ma120(data: FactorData, dates=None):
    return _out(data.adj_close / data.adj_close.rolling(120).mean() - 1.0, dates)


# --- volume ----------------------------------------------------------------

@register(dict(
    factor_name="volume_ratio_5_20", category="volume",
    formula="MA(volume,5)/MA(volume,20)",
    source="market", required_fields=["volume"],
    pit=True, direction="neutral",
    description="5-day vs 20-day average volume (activity acceleration)",
    version="1.0", status="candidate",
))
def volume_ratio_5_20(data: FactorData, dates=None):
    return _out(data.volume_raw.rolling(5).mean()
                / data.volume_raw.rolling(20).mean(), dates)


@register(dict(
    factor_name="volume_ratio_20_60", category="volume",
    formula="MA(volume,20)/MA(volume,60)",
    source="market", required_fields=["volume"],
    pit=True, direction="neutral",
    description="20-day vs 60-day average volume (activity acceleration)",
    version="1.0", status="candidate",
))
def volume_ratio_20_60(data: FactorData, dates=None):
    return _out(data.volume_raw.rolling(20).mean()
                / data.volume_raw.rolling(60).mean(), dates)


# --- liquidity (calibrated CNY amount; see step4_market_data_quality.md) -----

def _log_amount(data: FactorData, window: int):
    amt = data.amount_cny.rolling(window).mean()
    with np.errstate(divide="ignore"):
        out = np.log(amt)
    return out.replace([np.inf, -np.inf], np.nan)


@register(dict(
    factor_name="amount_20", category="liquidity",
    formula="log(MA(amount_cny,20))",
    source="market", required_fields=["amount", "close", "volume",
                                       "market_scale"],
    pit=True, direction="neutral",
    description="log 20-day average calibrated turnover value (CNY)",
    version="1.0", status="candidate",
))
def amount_20(data: FactorData, dates=None):
    return _out(_log_amount(data, 20), dates)


@register(dict(
    factor_name="amount_60", category="liquidity",
    formula="log(MA(amount_cny,60))",
    source="market", required_fields=["amount", "close", "volume",
                                       "market_scale"],
    pit=True, direction="neutral",
    description="log 60-day average calibrated turnover value (CNY)",
    version="1.0", status="candidate",
))
def amount_60(data: FactorData, dates=None):
    return _out(_log_amount(data, 60), dates)
