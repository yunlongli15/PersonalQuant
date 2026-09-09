# -*- coding: utf-8 -*-
"""LLM result cache (keyed by document_hash + prompt_version + model).

Never re-pay for the same document twice. The cache lives under
data/derived/news/llm_cache/ as one JSON file per key (small, resumable,
git-ignored with the rest of data/).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from personal_quant import PROJECT_ROOT

CACHE_DIR = PROJECT_ROOT / "data" / "derived" / "news" / "llm_cache"


def cache_key(document_hash: str, prompt_version: str, model: str) -> str:
    return f"{document_hash}_{prompt_version}_{model}"


def get(document_hash: str, prompt_version: str, model: str) -> Optional[dict]:
    p = CACHE_DIR / f"{cache_key(document_hash, prompt_version, model)}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def put(document_hash: str, prompt_version: str, model: str,
        result: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p = CACHE_DIR / f"{cache_key(document_hash, prompt_version, model)}.json"
    p.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")


def stats() -> dict:
    if not CACHE_DIR.exists():
        return {"entries": 0}
    return {"entries": len(list(CACHE_DIR.glob("*.json")))}
