# -*- coding: utf-8 -*-
"""News provider layer.

Business code talks ONLY to providers (never issues direct HTTP calls to
a news site); a source failure means swapping the provider, not rewriting
the system. Priority: official exchanges (SSE/SZSE) > CNINFO > AkShare
wrappers > other public sources. Fetching is always polite: single
connection, random 1-3s delay, timeout, retry with exponential backoff,
local cache. A blocked source is recorded as SOURCE_BLOCKED and the next
legal source is used — no proxy pools, no WAF bypass, no high concurrency.
"""

from . import akshare_news  # noqa: F401  (registers akshare)
from .base import BaseNewsProvider, PROVIDERS, SourceBlockedError
from .cninfo import CNINFOProvider
from .sse import SSEProvider
from .szse import SZSEProvider

__all__ = ["BaseNewsProvider", "PROVIDERS", "SourceBlockedError",
           "SSEProvider", "SZSEProvider", "CNINFOProvider"]
