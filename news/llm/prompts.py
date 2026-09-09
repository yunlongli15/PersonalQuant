# -*- coding: utf-8 -*-
"""LLM prompt templates (versioned; no secrets live here).

PROMPT_VERSION must be bumped whenever the prompt changes — the LLM cache
is keyed on (document_hash, prompt_version, model).
"""

PROMPT_VERSION = "1.0"

SYSTEM_PROMPT = (
    "你是 A 股公司公告分析器。只输出 JSON，不要输出任何其他文本。"
    "分析给定公告标题（可能没有正文），判断其对股价的潜在影响。"
    "严格遵守字段取值范围。"
)

USER_TEMPLATE = (
    "公告标题：{title}\n"
    "公司：{symbol}\n\n"
    '输出 JSON（只能包含以下字段）：\n'
    '{{\n'
    '  "event_type": "从 earnings, earnings_forecast, earnings_revision, '
    'dividend, share_buyback, shareholder_change, management_change, '
    'major_contract, m_and_a, financing, refinancing, asset_sale, '
    'asset_purchase, lawsuit, regulatory, penalty, investigation, pledge, '
    'unpledge, bankruptcy, production_change, product_launch, '
    'capacity_expansion, guidance, government_policy, other 中选择",\n'
    '  "sentiment": -1.0 到 1.0,\n'
    '  "importance": 0.0 到 1.0,\n'
    '  "novelty": 0.0 到 1.0,\n'
    '  "financial_impact": -1.0 到 1.0,\n'
    '  "risk": 0.0 到 1.0,\n'
    '  "confidence": 0.0 到 1.0\n'
    '}}\n'
    "只输出 JSON。"
)
