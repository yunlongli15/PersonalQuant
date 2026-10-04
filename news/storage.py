# -*- coding: utf-8 -*-
"""News storage: canonical news_documents (DuckDB) + derived news_events /
news_coverage (parquet snapshots consumed by the factor engine).

Canonical documents are deduplicated by document_id; a duplicate insert
bumps source_count (the same event seen through several sources counts
once). Derived events/factors never mix with canonical documents.
"""

from __future__ import annotations

from typing import List, Optional

import pandas as pd

from personal_quant import PROJECT_ROOT, db

from .schema import NewsDocument, NewsEvent

DERIVED_NEWS = PROJECT_ROOT / "data" / "derived" / "news"
EVENTS_SNAPSHOT = DERIVED_NEWS / "news_events.parquet"
COVERAGE_SNAPSHOT = DERIVED_NEWS / "news_coverage.parquet"

DOCUMENT_COLS = [
    "document_id", "symbol", "source", "source_url", "title",
    "published_at", "updated_at", "fetched_at", "language",
    "document_type", "time_known", "raw_hash", "content_hash", "status",
    "org_id", "source_count",
]

EVENT_COLS = [
    "event_id", "document_id", "symbol", "event_type", "publication_time",
    "availability_time", "availability_unknown", "event_time", "direction",
    "importance", "sentiment", "confidence", "novelty", "financial_impact",
    "risk", "extraction_method", "extraction_model", "extraction_version",
]


def ensure_tables() -> None:
    conn = db.connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS news_documents (
            document_id    VARCHAR PRIMARY KEY,
            symbol         VARCHAR,
            source         VARCHAR,
            source_url     VARCHAR,
            title          VARCHAR,
            published_at   TIMESTAMP,
            updated_at     TIMESTAMP,
            fetched_at     TIMESTAMP,
            language       VARCHAR,
            document_type  VARCHAR,
            time_known     BOOLEAN,
            raw_hash       VARCHAR,
            content_hash   VARCHAR,
            status         VARCHAR,
            org_id         VARCHAR,
            source_count   INTEGER DEFAULT 1
        );
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_news_symbol
            ON news_documents(symbol);
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_news_pub
            ON news_documents(published_at);
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS news_events (
            event_id            VARCHAR PRIMARY KEY,
            document_id         VARCHAR,
            symbol              VARCHAR,
            event_type          VARCHAR,
            publication_time    TIMESTAMP,
            availability_time   TIMESTAMP,
            availability_unknown BOOLEAN,
            event_time          TIMESTAMP,
            direction           VARCHAR,
            importance          DOUBLE,
            sentiment           DOUBLE,
            confidence          DOUBLE,
            novelty             DOUBLE,
            financial_impact    DOUBLE,
            risk                DOUBLE,
            extraction_method   VARCHAR,
            extraction_model    VARCHAR,
            extraction_version  VARCHAR
        );
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_news_events_symbol
            ON news_events(symbol);
    """)


def upsert_documents(docs: List[NewsDocument]) -> dict:
    """Insert documents; duplicates bump source_count. Returns stats."""
    ensure_tables()
    conn = db.connect()
    inserted = 0
    dup = 0
    for d in docs:
        row = [d.document_id, d.symbol, d.source, d.source_url, d.title,
               d.published_at, d.updated_at, d.fetched_at, d.language,
               d.document_type, d.time_known, d.raw_hash, d.content_hash,
               d.status, d.org_id, 1]
        existing = conn.execute(
            "SELECT 1 FROM news_documents WHERE document_id=?", [d.document_id]
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE news_documents SET source_count = source_count + 1, "
                "updated_at = COALESCE(updated_at, ?) WHERE document_id=?",
                [d.fetched_at, d.document_id])
            dup += 1
        else:
            conn.execute(
                f"INSERT INTO news_documents ({', '.join(DOCUMENT_COLS)}) "
                f"VALUES ({', '.join(['?'] * len(DOCUMENT_COLS))})", row)
            inserted += 1
    return {"inserted": inserted, "duplicates": dup}


def replace_events(events: List[NewsEvent]) -> int:
    """整表重建：先清空 news_events，再把新事件全部插回去。

    **必须在一个事务里做**（db.transaction）：这两步以前是两条各自自动
    提交的语句，中途崩溃（Ctrl-C、进程被杀、DuckDB 报错）会留下**空表**
    —— 而空的 news_events 在下游是**看不出来的**：计数类新闻因子 0 是
    "真的没有事件"的合法取值（docs/步骤5-新闻时点规则.md），于是信号会
    静默退化，没有任何一层会报警。

    另：本函数只保证"要么全换、要么不动"，不负责修复 DuckDB 自身的
    索引不一致（2026-10-04 遇到过 `DELETE` 因二级索引失配而失败，
    恢复办法见 reports/事故-20261004-新闻事件索引.md）。
    """
    ensure_tables()
    # 行数据先在 Python 侧拼好，把事务窗口压到最小
    rows = [[getattr(e, c) for c in EVENT_COLS] for e in events]
    with db.transaction() as conn:
        conn.execute("DELETE FROM news_events")
        if rows:
            conn.executemany(
                f"INSERT INTO news_events ({', '.join(EVENT_COLS)}) "
                f"VALUES ({', '.join(['?'] * len(EVENT_COLS))})", rows)
    return len(rows)


def export_events_snapshot(events: List[NewsEvent]) -> Path:
    DERIVED_NEWS.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([e.to_dict() for e in events])
    df.to_parquet(EVENTS_SNAPSHOT, index=False)
    return EVENTS_SNAPSHOT


def write_coverage(coverage: pd.DataFrame) -> Path:
    """coverage: symbol, start_date (dataset window per fetched symbol)."""
    DERIVED_NEWS.mkdir(parents=True, exist_ok=True)
    coverage.to_parquet(COVERAGE_SNAPSHOT, index=False)
    return COVERAGE_SNAPSHOT


def load_events_snapshot() -> pd.DataFrame:
    if not EVENTS_SNAPSHOT.exists():
        return pd.DataFrame(columns=EVENT_COLS)
    return pd.read_parquet(EVENTS_SNAPSHOT)


def load_coverage() -> pd.DataFrame:
    if not COVERAGE_SNAPSHOT.exists():
        return pd.DataFrame(columns=["symbol", "start_date"])
    return pd.read_parquet(COVERAGE_SNAPSHOT)


def document_count() -> int:
    try:
        return db.connect().execute(
            "SELECT COUNT(*) FROM news_documents").fetchone()[0]
    except Exception:
        return 0
