# -*- coding: utf-8 -*-
"""Daily LLM budget control (news_llm_daily_budget in config/news_v1.yaml).

Budget state is a tiny JSON file under data/derived/news/; when the daily
call/token budget is exhausted the analyzer reports
mode=RULE_BASED_ONLY — the pipeline degrades gracefully, never fails.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from personal_quant import PROJECT_ROOT

STATE_PATH = PROJECT_ROOT / "data" / "derived" / "news" / "llm_budget.json"


def _today() -> str:
    return time.strftime("%Y-%m-%d")


def _load() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    return {}


def _save(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False),
                          encoding="utf-8")


class Budget:
    def __init__(self, max_calls: int = 0, max_tokens: int = 0):
        self.max_calls = max_calls
        self.max_tokens = max_tokens
        state = _load()
        if state.get("day") != _today():
            state = {"day": _today(), "calls": 0, "tokens": 0}
            _save(state)
        self.state = state

    @property
    def calls_used(self) -> int:
        return int(self.state.get("calls", 0))

    @property
    def tokens_used(self) -> int:
        return int(self.state.get("tokens", 0))

    def available(self, estimated_tokens: int = 500) -> bool:
        if self.max_calls and self.calls_used >= self.max_calls:
            return False
        if self.max_tokens and self.tokens_used + estimated_tokens > \
                self.max_tokens:
            return False
        return True

    def record(self, tokens: int = 0) -> None:
        self.state["calls"] = self.calls_used + 1
        self.state["tokens"] = self.tokens_used + int(tokens)
        _save(self.state)

    def summary(self) -> dict:
        return {"day": self.state.get("day"), "calls": self.calls_used,
                "tokens": self.tokens_used, "max_calls": self.max_calls,
                "max_tokens": self.max_tokens}
