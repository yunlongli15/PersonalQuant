# -*- coding: utf-8 -*-
"""LLM news analysis (tier 2 — enabled only when an API key is present).

The system is fully functional WITHOUT this tier (rule-based factors).
LLMNewsAnalyzer detects DEEPSEEK_API_KEY; when absent it reports
enabled=False and the pipeline runs RULE_BASED_ONLY (never a failure).
"""

from .analyzer import LLMNewsAnalyzer  # noqa: F401
from .prompts import PROMPT_VERSION  # noqa: F401
