# -*- coding: utf-8 -*-
"""NewsDocument / NewsEvent schemas + validation.

All datetimes are timezone-AWARE Asia/Shanghai (never naive, never UTC —
docs/步骤5-新闻时点规则.md). event_time (what happened) is kept separate from
publication_time/availability_time (when the market could know); factor
research uses publication/availability times ONLY.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Optional

import pandas as pd

MARKET_TZ = "Asia/Shanghai"
CLOSE_TIME = pd.Timestamp("15:00").time()   # A-share continuous close
OPEN_TIME = pd.Timestamp("09:30").time()

EVENT_TYPES = {
    "earnings", "earnings_forecast", "earnings_revision", "dividend",
    "share_buyback", "shareholder_change", "management_change",
    "major_contract", "m_and_a", "financing", "refinancing", "asset_sale",
    "asset_purchase", "lawsuit", "regulatory", "penalty", "investigation",
    "pledge", "unpledge", "bankruptcy", "production_change",
    "product_launch", "capacity_expansion", "guidance", "government_policy",
    "other",
}

DOCUMENT_TYPES = {"announcement", "news", "research_report", "policy_news"}


def _now_tz():
    return pd.Timestamp.now(tz=MARKET_TZ)


@dataclass
class NewsDocument:
    """Canonical news/announcement document.

    symbol: canonical code (None for market-wide news). published_at is
    tz-aware Asia/Shanghai; when only a date is known the time is 00:00:00
    and `time_known=False` (conservative PIT: next trading day).
    """
    document_id: str
    source: str                    # sse | szse | cninfo | akshare | ...
    source_url: str
    title: str
    symbol: Optional[str] = None
    content: Optional[str] = None
    published_at: Optional[pd.Timestamp] = None
    updated_at: Optional[pd.Timestamp] = None
    fetched_at: Optional[pd.Timestamp] = None
    language: str = "zh"
    document_type: str = "announcement"
    time_known: bool = True
    raw_hash: str = ""
    content_hash: str = ""
    status: str = "new"            # new | blocked | failed | stale
    org_id: Optional[str] = None

    def __post_init__(self):
        if self.document_type not in DOCUMENT_TYPES:
            raise ValueError(f"bad document_type {self.document_type!r}")
        if self.symbol is not None and not (len(self.symbol) == 9
                                            and self.symbol[6] == "."):
            raise ValueError(f"symbol must be canonical (600519.SH), "
                             f"got {self.symbol!r}")
        for attr in ("published_at", "updated_at", "fetched_at"):
            v = getattr(self, attr)
            if v is not None and not isinstance(v, pd.Timestamp):
                setattr(self, attr, pd.Timestamp(v))
            v = getattr(self, attr)
            if v is not None and v.tzinfo is None:
                setattr(self, attr, v.tz_localize(MARKET_TZ))
        if self.fetched_at is None:
            self.fetched_at = _now_tz()
        if not self.raw_hash:
            self.raw_hash = hash_text(self.title, str(self.published_at),
                                      self.source)
        if not self.content_hash:
            self.content_hash = hash_text(self.title, self.symbol or "")

    def to_dict(self) -> dict:
        out = asdict(self)
        for k in ("published_at", "updated_at", "fetched_at"):
            v = out[k]
            out[k] = str(v) if v is not None else None
        return out


@dataclass
class NewsEvent:
    """One classified event extracted from a NewsDocument.

    event_time: when the event happened (often unknown); research uses
    publication/availability time only.
    """
    event_id: str
    document_id: str
    symbol: Optional[str]
    event_type: str
    publication_time: Optional[pd.Timestamp] = None
    availability_time: Optional[pd.Timestamp] = None
    availability_unknown: bool = False
    event_time: Optional[pd.Timestamp] = None
    direction: Optional[str] = None        # positive | negative | neutral | None
    importance: Optional[float] = None     # [0,1]
    sentiment: Optional[float] = None      # [-1,1]
    confidence: Optional[float] = None     # [0,1]
    novelty: Optional[float] = None        # [0,1]
    financial_impact: Optional[float] = None  # [-1,1] (LLM tier)
    risk: Optional[float] = None           # [0,1]
    extraction_method: str = "rule"
    extraction_model: Optional[str] = None
    extraction_version: str = "1.0"

    def __post_init__(self):
        if self.event_type not in EVENT_TYPES:
            raise ValueError(f"bad event_type {self.event_type!r}")
        if self.direction not in (None, "positive", "negative", "neutral"):
            raise ValueError(f"bad direction {self.direction!r}")
        for attr, lo, hi in (("importance", 0.0, 1.0), ("sentiment", -1.0, 1.0),
                             ("confidence", 0.0, 1.0), ("novelty", 0.0, 1.0),
                             ("financial_impact", -1.0, 1.0),
                             ("risk", 0.0, 1.0)):
            v = getattr(self, attr)
            if v is not None and not (lo <= v <= hi):
                raise ValueError(f"{attr}={v} outside [{lo},{hi}]")
        for attr in ("publication_time", "availability_time", "event_time"):
            v = getattr(self, attr)
            if v is not None and not isinstance(v, pd.Timestamp):
                setattr(self, attr, pd.Timestamp(v))
            v = getattr(self, attr)
            if v is not None and v.tzinfo is None:
                setattr(self, attr, v.tz_localize(MARKET_TZ))

    def to_dict(self) -> dict:
        out = asdict(self)
        for k in ("publication_time", "availability_time", "event_time"):
            v = out[k]
            out[k] = str(v) if v is not None else None
        return out


def hash_text(*parts: str) -> str:
    """Stable sha256 over normalized text parts (dedup keys)."""
    norm = "\x1f".join(
        (p or "").strip().lower().replace(" ", "").replace("　", "")
        for p in parts)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def make_document_id(source: str, raw_hash: str) -> str:
    return f"{source}-{raw_hash[:24]}"
