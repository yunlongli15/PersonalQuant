# -*- coding: utf-8 -*-
"""Provider layer: registry, abstraction, raw cache, blocking signal."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json

import pytest

from news.providers import (CNINFOProvider, PROVIDERS, SSEProvider,
                            SZSEProvider, SourceBlockedError)
from news.providers.base import BaseNewsProvider


def test_registry_contains_all_providers():
    assert {"sse", "szse", "cninfo", "akshare"} <= set(PROVIDERS)
    assert PROVIDERS["sse"] is SSEProvider
    assert PROVIDERS["szse"] is SZSEProvider
    assert PROVIDERS["cninfo"] is CNINFOProvider


def test_official_priority_metadata():
    assert SSEProvider().official and SSEProvider().exchanges == ("SH",)
    assert SZSEProvider().official and SZSEProvider().exchanges == ("SZ",)
    assert not CNINFOProvider().official


def test_unified_interface():
    for cls in (SSEProvider, SZSEProvider, CNINFOProvider):
        p = cls.__new__(cls)
        assert hasattr(p, "fetch_announcements")
        assert hasattr(p, "fetch_news")
        assert hasattr(p, "audit")


def test_raw_cache_roundtrip(tmp_path, monkeypatch):
    import news.providers.base as base

    class Concrete(base.BaseNewsProvider):
        name = "testprov"

        def fetch_announcements(self, start, end, symbol=None):
            return []

    monkeypatch.setattr(base, "RAW_NEWS", tmp_path)
    p = Concrete()
    p.save_cache("k1", {"a": 1})
    assert p.load_cache("k1") == {"a": 1}
    assert p.load_cache("missing") is None


def test_source_blocked_is_distinct_error():
    err = SourceBlockedError("sse blocked (HTTP 403)")
    assert isinstance(err, RuntimeError)
    assert "blocked" in str(err)


def test_business_code_never_imports_requests_directly():
    # the news package must route everything through BaseNewsProvider.get/
    # post; guard against accidental direct requests usage creeping in
    import inspect

    from news import providers  # noqa: F401

    src = Path(providers.__file__).parent
    offenders = []
    for f in src.glob("*.py"):
        text = f.read_text(encoding="utf-8")
        if "requests.get" in text or "requests.post" in text:
            offenders.append(f.name)
    assert offenders == ["base.py"], \
        f"direct requests calls outside base: {offenders}"
