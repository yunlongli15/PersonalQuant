# -*- coding: utf-8 -*-
"""LLMNewsAnalyzer: DeepSeek-backed structured news analysis.

- enabled only when DEEPSEEK_API_KEY is set (auto-detect; otherwise the
  whole news pipeline runs RULE_BASED_ONLY — never a failure)
- input: only tier-1 documents (major announcements, earnings, M&A,
  contracts, regulatory, shareholder/management change, large financing,
  high-novelty news) — routine news never reaches the LLM
- output: STRICT JSON with bounded fields (sentiment/importance/novelty/
  financial_impact/risk/confidence); unparseable JSON => EXTRACTION_FAILED
  (never guessed)
- every call records prompt_version/model/temperature/document_hash and
  goes through the cache + daily budget
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import List, Optional

from ..budget import Budget
from ..schema import EVENT_TYPES, NewsDocument, NewsEvent, hash_text
from . import cache
from .prompts import PROMPT_VERSION, SYSTEM_PROMPT, USER_TEMPLATE

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


class LLMNewsAnalyzer:
    def __init__(self, model: Optional[str] = None, temperature: float = 0.0,
                 max_tokens: int = 400, budget: Optional[Budget] = None,
                 timeout: int = 60):
        self.api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        self.base_url = os.environ.get("DEEPSEEK_BASE_URL",
                                       DEFAULT_BASE_URL).strip()
        self.model = model or os.environ.get("DEEPSEEK_MODEL",
                                             DEFAULT_MODEL)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.budget = budget or Budget()
        self.timeout = timeout
        self.enabled = bool(self.api_key)
        self.calls = 0
        self.cache_hits = 0
        self.failures = 0
        self.tokens_in = 0
        self.tokens_out = 0

    # -- public ----------------------------------------------------------
    def analyze(self, doc: NewsDocument) -> NewsEvent:
        """LLM event for one document; falls back to the rule result when
        the LLM tier is disabled/unavailable (method records the tier)."""
        rule_ev = _rule_event(doc)
        if not self.enabled:
            return rule_ev
        result = self._call_cached(doc)
        if result is None:
            return rule_ev
        rule_ev.sentiment = result.get("sentiment")
        rule_ev.importance = result.get("importance")
        rule_ev.novelty = result.get("novelty")
        rule_ev.financial_impact = result.get("financial_impact")
        rule_ev.risk = result.get("risk")
        rule_ev.confidence = result.get("confidence")
        if result.get("event_type") in EVENT_TYPES:
            rule_ev.event_type = result["event_type"]
        rule_ev.extraction_method = "llm"
        rule_ev.extraction_model = self.model
        rule_ev.extraction_version = PROMPT_VERSION
        return rule_ev

    def should_analyze(self, doc: NewsDocument) -> bool:
        """Tier-1 filter: only materially relevant documents reach the
        LLM (routine announcements never do)."""
        from ..events import classify_title

        et, _, importance, _ = classify_title(doc.title)
        if et in ("other", "guidance"):
            return False
        return importance >= 0.5

    # -- internals --------------------------------------------------------
    def _call_cached(self, doc: NewsDocument) -> Optional[dict]:
        key = hash_text(doc.title, doc.symbol or "", "llmv1")
        cached = cache.get(key, PROMPT_VERSION, self.model)
        if cached is not None:
            self.cache_hits += 1
            return cached.get("result") if cached.get("ok") else None
        if not self.budget.available(self.max_tokens * 2):
            return None
        try:
            result, usage = self._call_api(doc.title, doc.symbol or "")
        except Exception:
            self.failures += 1
            return None
        self.calls += 1
        self.budget.record(usage.get("total_tokens", 0))
        self.tokens_in += usage.get("prompt_tokens", 0)
        self.tokens_out += usage.get("completion_tokens", 0)
        ok = result is not None
        cache.put(key, PROMPT_VERSION, self.model,
                  {"ok": ok, "result": result, "usage": usage,
                   "model": self.model, "temperature": self.temperature})
        return result if ok else None

    def _call_api(self, title: str, symbol: str):
        import requests

        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",
                 "content": USER_TEMPLATE.format(title=title[:2000],
                                                 symbol=symbol)},
            ],
        }
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        body = resp.json()
        usage = body.get("usage", {}) or {}
        content = body["choices"][0]["message"]["content"]
        return _parse_json(content), usage


def _rule_event(doc: NewsDocument) -> NewsEvent:
    from ..events import classify_title
    from ..pit import document_availability

    et, direction, importance, confidence = classify_title(doc.title)
    avail, unknown = document_availability(doc)
    return NewsEvent(
        event_id=hash_text(doc.document_id, et)[:24],
        document_id=doc.document_id,
        symbol=doc.symbol,
        event_type=et,
        publication_time=doc.published_at,
        availability_time=avail,
        availability_unknown=unknown,
        direction=direction,
        importance=importance,
        confidence=confidence,
        extraction_method="rule",
        extraction_version="1.0",
    )


def _parse_json(text: str) -> Optional[dict]:
    """Strict JSON extraction; anything unparseable -> None (never guess)."""
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return None
    bounds = {"sentiment": (-1.0, 1.0), "importance": (0.0, 1.0),
              "novelty": (0.0, 1.0), "financial_impact": (-1.0, 1.0),
              "risk": (0.0, 1.0), "confidence": (0.0, 1.0)}
    out = {}
    for k, (lo, hi) in bounds.items():
        if k not in data or not isinstance(data[k], (int, float)):
            return None
        v = float(data[k])
        if not (lo <= v <= hi):
            return None
        out[k] = v
    if data.get("event_type") not in EVENT_TYPES:
        return None
    out["event_type"] = data["event_type"]
    return out
