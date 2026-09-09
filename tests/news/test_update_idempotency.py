# -*- coding: utf-8 -*-
"""Ingestion idempotency: re-fetching the same day must not duplicate
documents (dedup + source_count)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from news.schema import NewsDocument
from news.storage import ensure_tables, upsert_documents


@pytest.fixture(scope="module")
def storage():
    import duckdb

    from personal_quant import config, db

    if not config.DUCKDB_PATH.exists():
        pytest.skip("no canonical DB")
    try:
        ensure_tables()
        db.connect().execute("SELECT 1 FROM news_documents").fetchone()
    except duckdb.IOException:
        pytest.skip("DuckDB locked by the backfill — rerun the suite after")
    yield
    db.connect().execute("DELETE FROM news_documents "
                         "WHERE document_id LIKE 'test-%'")


def make_doc(seed="a"):
    return NewsDocument(document_id=f"test-{seed}", source="sse",
                        source_url="u", title=f"公告 {seed}",
                        symbol="600519.SH",
                        published_at="2025-01-02 10:00")


def test_first_insert_new(storage):
    stats = upsert_documents([make_doc("a")])
    assert stats["inserted"] == 1
    assert stats["duplicates"] == 0


def test_second_insert_is_duplicate_with_source_count(storage):
    stats = upsert_documents([make_doc("a")])
    assert stats["inserted"] == 0 and stats["duplicates"] == 1
    from personal_quant import db

    n = db.connect().execute(
        "SELECT source_count FROM news_documents "
        "WHERE document_id='test-a'").fetchone()[0]
    assert n == 2


def test_distinct_documents_not_deduplicated(storage):
    stats = upsert_documents([make_doc("b")])
    assert stats["inserted"] == 1
    from personal_quant import db

    n = db.connect().execute(
        "SELECT COUNT(*) FROM news_documents "
        "WHERE document_id LIKE 'test-%'").fetchone()[0]
    assert n == 2
