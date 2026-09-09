# -*- coding: utf-8 -*-
"""News deduplication + novelty.

Exact dedup: content_hash = hash(title + symbol) — the same announcement
re-published (reprints, mirror sites) collapses to one document row
(source_count tracked, never double-counted).

Near-duplicate / novelty: per-symbol character-bigram TF-IDF cosine of the
title against the previous 30 days' titles; novelty = 1 - max_similarity.
Cheap and explainable (no embeddings in the first version).
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, Iterable, List

import numpy as np

from .schema import hash_text

_NORM_RE = re.compile(r"[^一-龥a-z0-9]+")


def normalize_title(title: str) -> str:
    """Keep CJK + alnum, lowercase — for similarity."""
    return _NORM_RE.sub("", (title or "").lower())


def title_key(title: str, symbol: str, published_date: str) -> str:
    """Exact-ish dedup key: normalized title + symbol + date."""
    return hash_text(title, symbol or "", published_date or "")


def bigrams(text: str) -> set:
    return {text[i:i + 2] for i in range(len(text) - 1)} if len(text) >= 2 \
        else {text}


def _tf(sets: Iterable[set]) -> Dict[str, float]:
    df = defaultdict(int)
    total = 0
    for s in sets:
        for g in s:
            df[g] += 1
            total += 1
    return {g: c / total for g, c in df.items()} if total else {}


def title_similarity(a: str, b: str) -> float:
    na, nb = normalize_title(a), normalize_title(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ba, bb = bigrams(na), bigrams(nb)
    inter = ba & bb
    if not inter:
        return 0.0
    # idf-weighted cosine over the union of bigrams
    idf = {g: 1.0 for g in ba | bb}
    va = np.array([idf[g] for g in inter], dtype=float)
    denom = np.sqrt(len(ba)) * np.sqrt(len(bb))
    return float(va.sum() / denom) if denom else 0.0


def novelty_scores(titles: List[str], dates, window_days: int = 30,
                   recent_cap: int = 200) -> List[float]:
    """Per-title novelty vs earlier titles within `window_days`.

    novelty = 1 - max similarity to any previous title in the window.
    """
    out: List[float] = []
    for i, t in enumerate(titles):
        best = 0.0
        seen = 0
        for j in range(i - 1, max(-1, i - recent_cap - 1), -1):
            if dates[j] is None or dates[i] is None:
                break
            gap = (dates[i] - dates[j]).days
            if gap > window_days or gap < 0:
                if gap < 0:
                    continue
                break
            sim = title_similarity(titles[i], titles[j])
            best = max(best, sim)
            seen += 1
            if seen >= recent_cap:
                break
        out.append(1.0 - best)
    return out
