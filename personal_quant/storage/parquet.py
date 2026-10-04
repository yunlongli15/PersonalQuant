# -*- coding: utf-8 -*-
"""Storage layer: canonical Parquet writers + DuckDB table loaders.

Canonical = the unified schema under data/parquet/<domain>/. DuckDB holds
small/medium tables natively and daily_bars as a view over parquet.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from .. import config, db


def write_parquet(df: pd.DataFrame, domain: str, name: str) -> Path:
    """Write a DataFrame into data/parquet/<domain>/<name>.parquet."""
    config.ensure_dirs()
    p = config.PARQUET_SUBDIRS[domain] / f"{name}.parquet"
    df.to_parquet(p, index=False)
    return p


def write_table(df: pd.DataFrame, table: str, mode: str = "replace") -> None:
    """Insert/replace a DataFrame into the corresponding DuckDB table.

    "replace" clears the table first, so the two statements must commit
    together — otherwise a crash in between empties it (see db.transaction).
    An empty df still means "nothing to write", not "clear the table".
    """
    if df is None or df.empty:
        return
    if mode != "replace":
        db.connect().execute(f"INSERT INTO {table} SELECT * FROM df")
        return
    with db.transaction() as conn:
        conn.execute(f"DELETE FROM {table}")
        conn.execute(f"INSERT INTO {table} SELECT * FROM df")


def register_source(
    source_name: str,
    data_type: str,
    url: str,
    file: Optional[str] = None,
    sha256: Optional[str] = None,
    version: Optional[str] = None,
    parser_version: str = "1.0",
    retrieval_time: Optional[datetime] = None,
) -> None:
    """Append a row to the source_registry table."""
    conn = db.connect()
    conn.execute(
        "INSERT INTO source_registry VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            source_name,
            data_type,
            url,
            retrieval_time or datetime.now(),
            version,
            file,
            sha256,
            parser_version,
        ],
    )


def upsert_financial_metric(record: dict) -> None:
    """Insert one PIT financial metric row (upsert by natural key)."""
    conn = db.connect()
    cols = [
        "symbol", "fiscal_period", "fiscal_year", "report_type",
        "announcement_date", "availability_date", "availability_date_unknown",
        "metric_name", "metric_value", "unit", "source_document_id",
        "source_url", "source_sha256", "extraction_method",
        "extraction_version", "extracted_at", "raw_value", "validation_status",
    ]
    values = [record.get(c) for c in cols]
    placeholders = ", ".join(["?"] * len(cols))
    conn.execute(
        f"INSERT OR REPLACE INTO financial_metrics ({', '.join(cols)}) "
        f"VALUES ({placeholders})",
        values,
    )


def insert_audit_row(record: dict) -> int:
    """Append one extraction-audit row; returns its id.

    The sequence can fall behind the table's max id (e.g. after a killed
    run) — on a duplicate-key collision the id falls back to MAX(id)+1 and
    the sequence is re-aligned.
    """
    conn = db.connect()
    row_id = conn.execute(
        "SELECT nextval('seq_extraction_audit')"
    ).fetchone()[0]
    taken = conn.execute(
        "SELECT COUNT(*) FROM extraction_audit WHERE id=?", [row_id]
    ).fetchone()[0]
    if taken:
        row_id = conn.execute(
            "SELECT COALESCE(MAX(id), 0) + 1 FROM extraction_audit"
        ).fetchone()[0]
    try:
        conn.execute(
            "SELECT setval('seq_extraction_audit', "
            "(SELECT COALESCE(MAX(id), 0) FROM extraction_audit))"
        )
    except Exception:
        pass  # sequence re-alignment is best-effort; the fallback covers it
    conn.execute(
        "INSERT INTO extraction_audit VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
        "?, ?, ?, ?, ?, ?, ?)",
        [
            row_id,
            record.get("extracted_at", datetime.now()),
            record.get("symbol"),
            record.get("fiscal_year"),
            record.get("metric_name"),
            record.get("source_document_id"),
            record.get("source_url"),
            record.get("source_sha256"),
            record.get("page"),
            record.get("section"),
            record.get("raw_value"),
            record.get("normalized_value"),
            record.get("unit"),
            record.get("extraction_method"),
            record.get("extraction_version"),
            record.get("validation_status"),
            record.get("validation_note"),
        ],
    )
    return row_id


def update_report_extraction_status(document_id: str, status: str) -> None:
    conn = db.connect()
    conn.execute(
        "UPDATE report_documents SET extraction_status=? WHERE document_id=?",
        [status, document_id],
    )


def table_summary() -> pd.DataFrame:
    """Row counts of all canonical tables (for the data catalog)."""
    conn = db.connect()
    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='main' ORDER BY table_name"
    ).fetchall()
    rows = []
    for (t,) in tables:
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        rows.append({"table": t, "rows": n})
    return pd.DataFrame(rows)
