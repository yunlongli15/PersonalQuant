# -*- coding: utf-8 -*-
"""Growth factors from PIT annual-report data.

Growth is reported-year vs previous-year (the previous-year column of the
report); both values come from the SAME document, so no extra PIT step is
needed beyond the report's own availability date.
"""

from __future__ import annotations

from .base import FactorData
from .fundamental import pit_metric_panel
from .registry import register


@register(dict(
    factor_name="revenue_growth", category="growth",
    formula="revenue[t]/revenue[t-1]-1 (same report, prior-year column)",
    source="financial", required_fields=["revenue"],
    pit=True, direction="positive",
    description="annual revenue growth, latest PIT annual report",
    version="1.0", status="candidate",
))
def revenue_growth(data: FactorData, dates=None):
    panel, _ = pit_metric_panel(data, "revenue_growth", dates)
    return panel


@register(dict(
    factor_name="net_profit_growth", category="growth",
    formula="net_profit[t]/net_profit[t-1]-1 (same report, prior-year column)",
    source="financial", required_fields=["net_profit"],
    pit=True, direction="positive",
    description="annual net-profit growth, latest PIT annual report",
    version="1.0", status="candidate",
))
def net_profit_growth(data: FactorData, dates=None):
    panel, _ = pit_metric_panel(data, "net_profit_growth", dates)
    return panel
