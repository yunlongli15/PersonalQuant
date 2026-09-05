# -*- coding: utf-8 -*-
"""Provider interfaces.

Providers never talk to DuckDB directly; they produce plain
DataFrames / records that the storage layer persists. The financial
document pipeline is layered as:

    DocumentProvider -> DocumentExtractor -> Normalized Record -> Storage
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class FetchedPdf:
    """Result of a (successful) on-demand PDF fetch, fully validated."""

    url: str
    http_status: int
    file_size: int
    sha256: str
    content: bytes
    retrieval_timestamp: datetime = field(default_factory=lambda: datetime.now())
    local_path: Optional[str] = None  # set only when LEVEL-3 cache is used

    @classmethod
    def from_bytes(cls, url: str, http_status: int, content: bytes, **kw) -> "FetchedPdf":
        return cls(
            url=url,
            http_status=http_status,
            file_size=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            content=content,
            **kw,
        )


@dataclass
class ReportMetadata:
    """Metadata row for a single financial report document."""

    document_id: str
    symbol: str                      # canonical DIGITS.EXCHANGE
    exchange: str
    fiscal_year: int
    report_type: str                 # annual | semi_annual | quarterly ...
    document_role: str               # annual_report | annual_summary | ...
    title: Optional[str]
    announcement_date: Optional[str]  # YYYY-MM-DD
    announcement_date_source: Optional[str]
    source: str                      # sse | cninfo
    source_url: Optional[str]
    status: str
    sha256: Optional[str] = None
    file_size: Optional[int] = None
