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


# ---------------------------------------------------------------------------
# SSE 公告类型回归（2026-10-05）
#
# 修之前请求里写死 reportType2="DQBG"（定期报告），于是**只有**年报/半年报/
# 季报进了库 —— 实测 2026-09-29：带 DQBG 返回 0 条，不带返回 814 条。
# 后果是沪市（约半个市场）的质押/减持/诉讼/立案/冻结等公告全部缺失，
# 全库负向事件里沪市只占 1 条，news_risk_20d 对沪市股票恒为 0。
#
# 这里不联网：拦下 BaseNewsProvider.get，直接检查发出去的参数。
# ---------------------------------------------------------------------------

def _captured_params(monkeypatch, payload=None):
    """拦截 SSE 的 HTTP 调用，把 params 抓下来。"""
    seen = {}

    class _Resp:
        def json(self):
            return payload or {"pageHelp": {"data": [], "total": 0}}

    def fake_get(self, url, params=None, headers=None, **kw):
        seen.update(params or {})
        return _Resp()

    monkeypatch.setattr(BaseNewsProvider, "get", fake_get)
    monkeypatch.setattr(BaseNewsProvider, "load_cache", lambda self, k: None)
    monkeypatch.setattr(BaseNewsProvider, "save_cache", lambda self, k, p: None)
    return seen


def test_sse_does_not_restrict_to_periodic_reports(monkeypatch):
    """必须不能是 DQBG —— 那是把 99% 的公告挡在门外的那个值。"""
    params = _captured_params(monkeypatch)
    SSEProvider().fetch_announcements("2026-09-29", "2026-09-29")
    assert params.get("reportType2") != "DQBG", (
        "reportType2 又被限制成定期报告了 —— 普通公告会一条都进不来")
    assert params.get("reportType2") == "ALL"


def test_sse_still_sends_the_other_required_params(monkeypatch):
    params = _captured_params(monkeypatch)
    SSEProvider().fetch_announcements("2026-09-29", "2026-09-29")
    assert params.get("reportType") == "ALL"
    assert params.get("securityType"), "不传 securityType 会返回 0 条"
    assert params.get("beginDate") == "2026-09-29"
    # 分页：pageNo 被 API 忽略，必须走 beginPage/endPage
    assert params.get("pageHelp.beginPage") == "1"
    assert params.get("pageHelp.endPage") == "1"


def test_sse_cache_key_is_versioned(monkeypatch):
    """缓存键必须带版本号 —— 否则改了参数还会读回旧参数下的缓存，
    修复会“看起来生效”却一条新数据都没有（2026-10-05 踩过）。"""
    keys = []
    monkeypatch.setattr(BaseNewsProvider, "load_cache",
                        lambda self, k: keys.append(k) or None)
    monkeypatch.setattr(BaseNewsProvider, "save_cache",
                        lambda self, k, p: None)

    class _Resp:
        def json(self):
            return {"pageHelp": {"data": [], "total": 0}}
    monkeypatch.setattr(BaseNewsProvider, "get",
                        lambda self, *a, **kw: _Resp())

    SSEProvider().fetch_announcements("2026-09-29", "2026-09-29")
    assert keys, "应当查询过缓存"
    assert all("_v2_" in k for k in keys), f"缓存键没带版本：{keys}"
