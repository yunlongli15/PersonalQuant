# -*- coding: utf-8 -*-
"""LLM cache: keyed by document_hash + prompt_version + model."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from news.llm import cache


def test_cache_key_includes_all_dimensions():
    k1 = cache.cache_key("h", "v1", "deepseek-chat")
    k2 = cache.cache_key("h", "v2", "deepseek-chat")
    k3 = cache.cache_key("h", "v1", "other-model")
    k4 = cache.cache_key("h2", "v1", "deepseek-chat")
    assert len({k1, k2, k3, k4}) == 4


def test_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path / "llm_cache")
    assert cache.get("doc1", "v1", "m") is None
    cache.put("doc1", "v1", "m", {"ok": True, "result": {"sentiment": 0.5}})
    out = cache.get("doc1", "v1", "m")
    assert out["result"]["sentiment"] == pytest.approx(0.5)
    # different prompt version misses
    assert cache.get("doc1", "v2", "m") is None


def test_corrupt_cache_file_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path / "llm_cache")
    cache.put("doc2", "v1", "m", {"ok": True})
    p = tmp_path / "llm_cache" / "doc2_v1_m.json"
    p.write_text("{corrupt", encoding="utf-8")
    assert cache.get("doc2", "v1", "m") is None


def test_stats(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path / "llm_cache")
    cache.put("a", "v1", "m", {})
    cache.put("b", "v1", "m", {})
    assert cache.stats()["entries"] == 2
