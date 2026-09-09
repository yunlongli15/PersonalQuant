# -*- coding: utf-8 -*-
"""Valuation + turnover factors built on PIT annual-report data.

Per-share metrics (eps = 基本每股收益, bps = 归属于上市公司股东的每股净资产)
are extracted from the annual report's key-accounting-data section; total
shares = net_assets / bps. Price is the RAW close at the signal date.

PE with negative EPS is kept (a negative PE is itself informative); the
evaluator's rank normalization handles it naturally — negative PE values
are never silently dropped (see docs/step4_financial_factor_pit.md).
Banks/insurers have no cost_of_revenue (gross_margin MISSING) but do
disclose eps/bps, so the valuation factors are available for them.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import FactorData
from .fundamental import pit_metric_panel, shares_panel
from .registry import register


def _close_at(data: FactorData, dates) -> pd.DataFrame:
    return data.close_raw.reindex(pd.DatetimeIndex(dates))


def _eps_bps(data: FactorData, dates):
    eps, fy = pit_metric_panel(data, "eps", dates)
    bps, fy2 = pit_metric_panel(data, "bps", dates)
    return eps, bps


@register(dict(
    factor_name="pe", category="valuation",
    formula="close / eps_latest_annual (eps=基本每股收益; negative EPS kept)",
    source="financial", required_fields=["close", "eps"],
    pit=True, direction="negative",
    description="price-to-earnings on the latest PIT annual report",
    version="1.0", status="candidate",
))
def pe(data: FactorData, dates=None):
    eps, _ = _eps_bps(data, dates)
    px = _close_at(data, dates)
    return px / eps.where(eps != 0)


@register(dict(
    factor_name="pb", category="valuation",
    formula="close / bps_latest_annual (bps=披露每股净资产, "
            "fallback net_assets/(net_profit/eps), same report)",
    source="financial", required_fields=["close", "bps", "net_assets",
                                          "net_profit", "eps"],
    pit=True, direction="negative",
    description="price-to-book on the latest PIT annual report",
    version="1.0", status="candidate",
))
def pb(data: FactorData, dates=None):
    from .fundamental import bps_panel

    bps = bps_panel(data, dates)
    px = _close_at(data, dates)
    return px / bps.where(bps > 0)


@register(dict(
    factor_name="ps", category="valuation",
    formula="close*shares/revenue_latest_annual; shares=net_assets/bps",
    source="financial", required_fields=["close", "revenue", "net_assets",
                                          "bps"],
    pit=True, direction="negative",
    description="price-to-sales on the latest PIT annual report",
    version="1.0", status="candidate",
))
def ps(data: FactorData, dates=None):
    shares = shares_panel(data, dates)
    rev, _ = pit_metric_panel(data, "revenue", dates)
    px = _close_at(data, dates)
    mcap = px * shares
    return mcap / rev.where(rev > 0)


@register(dict(
    factor_name="earnings_yield", category="valuation",
    formula="eps_latest_annual / close",
    source="financial", required_fields=["close", "eps"],
    pit=True, direction="positive",
    description="inverse of PE (EPS/price) on the latest PIT annual report",
    version="1.0", status="candidate",
))
def earnings_yield(data: FactorData, dates=None):
    eps, _ = _eps_bps(data, dates)
    px = _close_at(data, dates)
    return eps / px.where(px > 0)


# --- turnover (shares from the latest annual report; coverage = financial
#     universe — the full-market turnover source (eastmoney) is WAF-blocked,
#     documented in docs/step4_market_data_quality.md) -----------------------

@register(dict(
    factor_name="turnover_20", category="liquidity",
    formula="MA(volume_shares,20)/shares_latest_annual",
    source="financial+market", required_fields=["volume", "market_scale",
                                                 "net_assets", "bps"],
    pit=True, direction="negative",
    description="20-day average share turnover; shares from the latest PIT "
                "annual report (financial-universe coverage only)",
    version="1.0", status="candidate",
))
def turnover_20(data: FactorData, dates=None):
    vol20 = data.volume_shares.rolling(20).mean()
    shares = shares_panel(data, dates if dates is not None
                          else data.calendar)
    vol = vol20.reindex(shares.index) if dates is not None else vol20
    return vol / shares.where(shares > 0)


@register(dict(
    factor_name="turnover_60", category="liquidity",
    formula="MA(volume_shares,60)/shares_latest_annual",
    source="financial+market", required_fields=["volume", "market_scale",
                                                 "net_assets", "bps"],
    pit=True, direction="negative",
    description="60-day average share turnover; shares from the latest PIT "
                "annual report (financial-universe coverage only)",
    version="1.0", status="candidate",
))
def turnover_60(data: FactorData, dates=None):
    vol60 = data.volume_shares.rolling(60).mean()
    shares = shares_panel(data, dates if dates is not None
                          else data.calendar)
    vol = vol60.reindex(shares.index) if dates is not None else vol60
    return vol / shares.where(shares > 0)
