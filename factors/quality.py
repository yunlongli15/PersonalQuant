# -*- coding: utf-8 -*-
"""Quality + cash-flow factors from PIT annual-report metrics.

roe: the report's disclosed value (加权平均净资产收益率); when the report
does not disclose it, the calculated net_profit/net_assets (year-end,
first-order approximation) is used — the split between reported and
calculated coverage is recorded in the factor report (never silently).
gross_margin is MISSING for banks/insurers (no cost_of_revenue in their
income statements — the extractor returns EXTRACTION_FAILED, we never
invent values).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import FactorData
from .fundamental import pit_metric_panel
from .registry import register


def _pit(data, metric, dates):
    panel, _ = pit_metric_panel(data, metric, dates)
    return panel


@register(dict(
    factor_name="roe", category="quality",
    formula="disclosed ROE, fallback net_profit/net_assets (year-end)",
    source="financial", required_fields=["roe", "net_profit", "net_assets"],
    pit=True, direction="positive",
    description="return on equity, latest PIT annual report",
    version="1.0", status="candidate",
))
def roe(data: FactorData, dates=None):
    reported = _pit(data, "roe", dates)
    np_ = _pit(data, "net_profit", dates)
    na = _pit(data, "net_assets", dates)
    calc = np_ / na.where(na.abs() > 0)
    return reported.where(reported.notna(), calc)


def roe_source_split(data: FactorData, dates):
    """Fraction of roe coverage that comes from the disclosed value."""
    reported = _pit(data, "roe", dates)
    calc_part = _pit(data, "net_profit", dates).where(reported.isna())
    tot = reported.notna().sum().sum()
    denom = tot + calc_part.notna().sum().sum()
    return float(tot / denom) if denom else np.nan


@register(dict(
    factor_name="roa", category="quality",
    formula="net_profit/total_assets (derived, stored)",
    source="financial", required_fields=["net_profit", "total_assets"],
    pit=True, direction="positive",
    description="return on assets, latest PIT annual report",
    version="1.0", status="candidate",
))
def roa(data: FactorData, dates=None):
    return _pit(data, "roa", dates)


@register(dict(
    factor_name="gross_margin", category="quality",
    formula="(revenue-cost_of_revenue)/revenue",
    source="financial", required_fields=["revenue", "cost_of_revenue"],
    pit=True, direction="positive",
    description="gross margin, latest PIT annual report (MISSING for "
                "banks/insurers: no cost_of_revenue)",
    version="1.0", status="candidate",
))
def gross_margin(data: FactorData, dates=None):
    return _pit(data, "gross_margin", dates)


@register(dict(
    factor_name="net_margin", category="quality",
    formula="net_profit/revenue",
    source="financial", required_fields=["net_profit", "revenue"],
    pit=True, direction="positive",
    description="net margin, latest PIT annual report",
    version="1.0", status="candidate",
))
def net_margin(data: FactorData, dates=None):
    return _pit(data, "net_margin", dates)


@register(dict(
    factor_name="debt_to_asset", category="quality",
    formula="total_liabilities/total_assets",
    source="financial", required_fields=["total_liabilities", "total_assets"],
    pit=True, direction="negative",
    description="leverage, latest PIT annual report (banks structurally "
                "~0.9 — handled as real data, not an error)",
    version="1.0", status="candidate",
))
def debt_to_asset(data: FactorData, dates=None):
    return _pit(data, "debt_to_asset", dates)


@register(dict(
    factor_name="operating_cash_flow", category="cash_flow",
    formula="operating cash flow (absolute, latest PIT annual report)",
    source="financial", required_fields=["operating_cash_flow"],
    pit=True, direction="neutral",
    description="operating cash flow level (a size proxy; the ratio forms "
                "below are the comparable cash-flow factors)",
    version="1.0", status="candidate",
))
def operating_cash_flow(data: FactorData, dates=None):
    return _pit(data, "operating_cash_flow", dates)


@register(dict(
    factor_name="ocf_to_assets", category="cash_flow",
    formula="operating_cash_flow/total_assets",
    source="financial", required_fields=["operating_cash_flow",
                                          "total_assets"],
    pit=True, direction="positive",
    description="cash-flow yield on assets, latest PIT annual report",
    version="1.0", status="candidate",
))
def ocf_to_assets(data: FactorData, dates=None):
    ocf = _pit(data, "operating_cash_flow", dates)
    ta = _pit(data, "total_assets", dates)
    return ocf / ta.where(ta.abs() > 0)


@register(dict(
    factor_name="ocf_to_net_profit", category="cash_flow",
    formula="operating_cash_flow/net_profit",
    source="financial", required_fields=["operating_cash_flow",
                                          "net_profit"],
    pit=True, direction="positive",
    description="earnings quality (cash coverage of profit), latest PIT "
                "annual report; undefined when |net_profit| is tiny",
    version="1.0", status="candidate",
))
def ocf_to_net_profit(data: FactorData, dates=None):
    ocf = _pit(data, "operating_cash_flow", dates)
    np_ = _pit(data, "net_profit", dates)
    # tiny denominators make the ratio meaningless — treat as missing
    np_safe = np_.where(np_.abs() > 1e-8)
    return ocf / np_safe
