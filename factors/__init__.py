# -*- coding: utf-8 -*-
"""STEP 4 factor research engine.

Layers:
- base.py        FactorData container + canonical-layer loading
- registry.py    factor metadata + compute-function registry
- technical.py   market factors (momentum/reversal/volatility/liquidity/…)
- fundamental.py PIT financial-metric join engine
- valuation.py   PE/PB/PS/earnings-yield/turnover factors
- quality.py     ROE/ROA/margins/leverage/cash-flow factors
- growth.py      revenue/net-profit growth factors
- normalization  cross-sectional rank/zscore/winsorized_zscore + missing fill
- evaluator.py   IC/decay/quantiles/long-short/stability/correlation
- selection.py   coverage/ICIR/stability/correlation de-duplication
- mining.py      shallow expression search (train/valid/test separation)
- reports.py     per-factor reports + leaderboard + dashboard data
"""

from . import base, fundamental, growth, normalization, quality, registry
from . import news_factors, technical, valuation  # noqa: F401  (registration)
