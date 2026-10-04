# -*- coding: utf-8 -*-
"""DuckDB connection management and canonical schema DDL.

Layering: Parquet files under data/parquet/<domain>/ are the canonical
storage; DuckDB materializes the small/medium tables natively and exposes
the large daily_bars table as a view over the parquet files.

All large data files are git-ignored (data/).
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import duckdb

from . import config

_conn: Optional[duckdb.DuckDBPyConnection] = None
_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE SEQUENCE IF NOT EXISTS seq_extraction_audit;

CREATE TABLE IF NOT EXISTS securities (
    symbol            VARCHAR PRIMARY KEY,
    exchange          VARCHAR,
    name              VARCHAR,
    list_date         DATE,
    delist_date       DATE,
    is_active         BOOLEAN,
    is_st             BOOLEAN,
    first_seen_year   INTEGER,
    last_seen_year    INTEGER,
    source            VARCHAR
);

CREATE TABLE IF NOT EXISTS trading_calendar (
    exchange   VARCHAR,
    trade_date DATE,
    is_open    BOOLEAN,
    PRIMARY KEY (exchange, trade_date)
);

CREATE TABLE IF NOT EXISTS daily_valuation (
    symbol             VARCHAR,
    trade_date         DATE,
    pe                 DOUBLE,
    pb                 DOUBLE,
    ps                 DOUBLE,
    total_market_cap   DOUBLE,
    float_market_cap   DOUBLE,
    turnover           DOUBLE,
    source             VARCHAR,
    PRIMARY KEY (symbol, trade_date)
);

CREATE TABLE IF NOT EXISTS company_lifecycle (
    symbol         VARCHAR,
    effective_date DATE,
    end_date       DATE,
    status         VARCHAR,
    reason         VARCHAR,
    source         VARCHAR
);
CREATE INDEX IF NOT EXISTS idx_lifecycle_symbol ON company_lifecycle(symbol);

CREATE TABLE IF NOT EXISTS industry_membership (
    symbol         VARCHAR,
    industry_code  VARCHAR,
    industry_name  VARCHAR,
    classification VARCHAR,
    effective_date DATE,
    end_date       DATE,
    source         VARCHAR
);
CREATE INDEX IF NOT EXISTS idx_industry_symbol ON industry_membership(symbol);

CREATE TABLE IF NOT EXISTS corporate_actions (
    symbol       VARCHAR,
    action_date  DATE,
    ex_date      DATE,
    action_type  VARCHAR,
    dividend     DOUBLE,
    split_ratio  DOUBLE,
    rights_ratio DOUBLE,
    source       VARCHAR
);
CREATE INDEX IF NOT EXISTS idx_actions_symbol ON corporate_actions(symbol);

CREATE TABLE IF NOT EXISTS report_documents (
    document_id                 VARCHAR PRIMARY KEY,
    symbol                      VARCHAR,
    exchange                    VARCHAR,
    fiscal_year                 INTEGER,
    report_type                 VARCHAR,
    document_role               VARCHAR,
    title                       VARCHAR,
    announcement_date           DATE,
    announcement_date_source    VARCHAR,
    availability_date           DATE,
    availability_date_unknown   BOOLEAN,
    source                      VARCHAR,
    source_url                  VARCHAR,
    local_path                  VARCHAR,
    status                      VARCHAR,
    sha256                      VARCHAR,
    file_size                   BIGINT,
    retrieval_timestamp         TIMESTAMP,
    first_seen                  TIMESTAMP,
    last_seen                   TIMESTAMP,
    extraction_status           VARCHAR
);
CREATE INDEX IF NOT EXISTS idx_reports_symbol_year
    ON report_documents(symbol, fiscal_year);

CREATE TABLE IF NOT EXISTS financial_metrics (
    symbol                     VARCHAR,
    fiscal_period              DATE,
    fiscal_year                INTEGER,
    report_type                VARCHAR,
    announcement_date          DATE,
    availability_date          DATE,
    availability_date_unknown  BOOLEAN,
    metric_name                VARCHAR,
    metric_value               DOUBLE,
    unit                       VARCHAR,
    source_document_id         VARCHAR,
    source_url                 VARCHAR,
    source_sha256              VARCHAR,
    extraction_method          VARCHAR,
    extraction_version         VARCHAR,
    extracted_at               TIMESTAMP,
    raw_value                  VARCHAR,
    validation_status          VARCHAR,
    PRIMARY KEY (symbol, fiscal_period, report_type, metric_name, extraction_method)
);

CREATE TABLE IF NOT EXISTS extraction_audit (
    id                  UBIGINT PRIMARY KEY,
    extracted_at        TIMESTAMP,
    symbol              VARCHAR,
    fiscal_year         INTEGER,
    metric_name         VARCHAR,
    source_document_id  VARCHAR,
    source_url          VARCHAR,
    source_sha256       VARCHAR,
    page                INTEGER,
    section             VARCHAR,
    raw_value           VARCHAR,
    normalized_value    DOUBLE,
    unit                VARCHAR,
    extraction_method   VARCHAR,
    extraction_version  VARCHAR,
    validation_status   VARCHAR,
    validation_note     VARCHAR
);

CREATE TABLE IF NOT EXISTS source_registry (
    source_name     VARCHAR,
    data_type       VARCHAR,
    url             VARCHAR,
    retrieval_time  TIMESTAMP,
    version         VARCHAR,
    file            VARCHAR,
    sha256          VARCHAR,
    parser_version  VARCHAR
);
"""


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Return the process-wide DuckDB connection (auto-creates schema)."""
    global _conn
    with _lock:
        if _conn is None:
            config.ensure_dirs()
            _conn = duckdb.connect(str(config.DUCKDB_PATH))
            _conn.execute(SCHEMA_SQL)
            _register_daily_bars_view(_conn)
        return _conn


def _register_daily_bars_view(conn: duckdb.DuckDBPyConnection) -> None:
    """daily_bars lives as parquet files (partitioned by year); expose a view."""
    import glob

    pattern = str(config.PARQUET_SUBDIRS["daily"] / "*.parquet").replace("\\", "/")
    files = sorted(glob.glob(pattern))
    if files:
        src = f"read_parquet({[f.replace(chr(92), '/') for f in files]})"
        conn.execute(f"""
            CREATE OR REPLACE VIEW daily_bars AS
            SELECT * FROM {src};
        """)
    else:
        conn.execute("""
            CREATE OR REPLACE VIEW daily_bars AS
            SELECT * FROM (VALUES (
                'X'::VARCHAR, DATE '1970-01-01', 0.0::DOUBLE, 0.0::DOUBLE,
                0.0::DOUBLE, 0.0::DOUBLE, 0.0::DOUBLE, 0.0::DOUBLE,
                0.0::DOUBLE, 0.0::DOUBLE, 'X'::VARCHAR))
            t(symbol, trade_date, open, high, low, close, volume, amount,
              vwap, factor, source)
            WHERE 1 = 0;
        """)


def refresh_daily_bars_view() -> None:
    """Re-create the daily_bars view (call after writing new parquet files)."""
    conn = connect()
    with _lock:
        _register_daily_bars_view(conn)


@contextmanager
def transaction():
    """Run a group of statements as one atomic unit.

    The DuckDB Python client **autocommits every statement**, so a
    "clear the table, then refill it" pair is two separate commits: a crash in
    between leaves the table EMPTY, and an empty table is indistinguishable
    from "genuinely no rows" downstream (see
    reports/事故-20261004-新闻事件索引.md). Use this for any
    multi-statement write that is only valid as a whole:

        with db.transaction() as conn:
            conn.execute("DELETE FROM t")
            conn.execute("INSERT INTO t SELECT * FROM df")

    COMMIT happens only after the block finishes; anything raised inside —
    KeyboardInterrupt included — rolls the whole group back and re-raises.
    """
    conn = connect()
    conn.execute("BEGIN")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def close() -> None:
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
            _conn = None


def query(sql: str, params: Optional[list] = None) -> list:
    """Run a query and return rows as a list of dicts."""
    conn = connect()
    if params is None:
        cur = conn.execute(sql)
    else:
        cur = conn.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def table_count(table: str) -> int:
    return connect().execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
