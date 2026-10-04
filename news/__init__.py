# -*- coding: utf-8 -*-
"""STEP 5 news / announcement factor system.

Layering (RAW -> CANONICAL -> DERIVED):
- news/providers/  fetch from official exchanges first (SSE/SZSE), CNINFO
  fallback, AkShare wrappers — business code never touches requests
- canonical news_documents (DuckDB): deduplicated, symbol-mapped,
  timestamped documents
- derived news_events (rule/LLM extraction, PIT availability times)
- derived news_factors (per signal-date factor panels, evaluated by the
  STEP 4 factor engine — news factors live in FACTOR_REGISTRY)

PIT rule: a news item with publication time p is usable for a signal at
date T close iff available_at <= T close, where available_at = p when p is
on a trading day with time <= 15:00 (Asia/Shanghai), else the next
trading day 09:30. Date-only publications are conservatively available
the NEXT trading day (docs/步骤5-新闻时点规则.md).
"""

from . import schema  # noqa: F401
