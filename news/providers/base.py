# -*- coding: utf-8 -*-
"""BaseNewsProvider + polite-fetch machinery + provider registry.

Polite-fetch policy (project rules): single connection, random delay
1-3s between requests, per-request timeout, up to MAX_RETRIES with
exponential backoff, honest User-Agent, raw responses cached under
data/raw/news/<source>/. Blocked sources raise SourceBlockedError and are
recorded (never bypassed via proxies/WAF tricks).
"""

from __future__ import annotations

import random
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

import pandas as pd
import requests

from personal_quant import PROJECT_ROOT, config

from ..schema import NewsDocument

RAW_NEWS = PROJECT_ROOT / "data" / "raw" / "news"
PROVIDERS: dict = {}


class SourceBlockedError(RuntimeError):
    """The source is rate-limiting / blocking this IP. Record and switch."""


class BaseNewsProvider(ABC):
    """Uniform provider interface.

    Subclasses implement fetch methods returning lists of NewsDocument.
    The base class provides polite HTTP + raw caching + the registry.
    """

    name: str = "base"
    official: bool = False
    exchanges: tuple = ()          # ('SH',) / ('SZ',) / ('SH','SZ')

    def __init__(self, use_cache: bool = True, min_delay: float = 1.0,
                 max_delay: float = 3.0):
        self.use_cache = use_cache
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._last_request: float = 0.0

    # -- polite HTTP -----------------------------------------------------
    def _sleep_politely(self) -> None:
        time.sleep(random.uniform(self.min_delay, self.max_delay))

    def _throttle(self) -> None:
        # guarantee at least min_delay between consecutive requests
        wait = self.min_delay - (time.time() - self._last_request)
        if wait > 0:
            time.sleep(wait)

    def get(self, url: str, params=None, headers=None, timeout: int = 60,
            retries: int = 3) -> requests.Response:
        """Polite GET with retry/backoff; SourceBlockedError on 403/429."""
        merged = {"User-Agent": config.USER_AGENT, **({} or {})}
        if headers:
            merged.update(headers)
        last_err: Optional[Exception] = None
        for attempt in range(1, retries + 1):
            self._throttle()
            try:
                resp = requests.get(url, params=params, headers=merged,
                                    timeout=timeout)
                self._last_request = time.time()
                if resp.status_code in (403, 429):
                    raise SourceBlockedError(
                        f"{self.name} blocked (HTTP {resp.status_code})")
                if resp.status_code != 200:
                    raise requests.HTTPError(f"HTTP {resp.status_code}")
                return resp
            except SourceBlockedError:
                raise
            except (requests.RequestException, requests.HTTPError) as e:
                last_err = e
                if attempt < retries:
                    time.sleep(2 ** attempt)
        raise RuntimeError(f"{self.name} GET failed after {retries} "
                           f"attempts: {last_err}")

    def post(self, url: str, json=None, data=None, headers=None,
             timeout: int = 60, retries: int = 3) -> requests.Response:
        merged = {"User-Agent": config.USER_AGENT}
        if headers:
            merged.update(headers)
        last_err: Optional[Exception] = None
        for attempt in range(1, retries + 1):
            self._throttle()
            try:
                resp = requests.post(url, json=json, data=data,
                                     headers=merged, timeout=timeout)
                self._last_request = time.time()
                if resp.status_code in (403, 429):
                    raise SourceBlockedError(
                        f"{self.name} blocked (HTTP {resp.status_code})")
                if resp.status_code != 200:
                    raise requests.HTTPError(f"HTTP {resp.status_code}")
                return resp
            except SourceBlockedError:
                raise
            except (requests.RequestException, requests.HTTPError) as e:
                last_err = e
                if attempt < retries:
                    time.sleep(2 ** attempt)
        raise RuntimeError(f"{self.name} POST failed after {retries} "
                           f"attempts: {last_err}")

    # -- raw cache -------------------------------------------------------
    def cache_path(self, key: str) -> Path:
        p = RAW_NEWS / self.name / f"{key}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def save_cache(self, key: str, payload) -> Path:
        import json

        p = self.cache_path(key)
        p.write_text(json.dumps(payload, ensure_ascii=False, default=str),
                     encoding="utf-8")
        return p

    def load_cache(self, key: str):
        import json

        p = self.cache_path(key)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None

    # -- interface -------------------------------------------------------
    @abstractmethod
    def fetch_announcements(self, start: str, end: str,
                            symbol: Optional[str] = None) -> List[NewsDocument]:
        """Announcements in [start, end]; per-stock when symbol is given."""

    def fetch_news(self, symbol: str, start: str, end: str,
                   limit: int = 20) -> List[NewsDocument]:
        """General company news (providers that support it)."""
        return []

    def audit(self) -> dict:
        """Provider audit row (docs/step5_news_sources.md)."""
        return {
            "provider": self.name,
            "official": self.official,
            "exchanges": ",".join(self.exchanges),
            "availability": "unknown",
            "historical_depth": "unknown",
            "timestamp_quality": "unknown",
            "stock_mapping_quality": "unknown",
            "rate_limit": "unknown",
            "reliability": "unknown",
            "duplicate_rate": "unknown",
            "content_quality": "unknown",
        }


def register(cls) -> type:
    PROVIDERS[cls.name] = cls
    return cls
