# -*- coding: utf-8 -*-
"""Ingest SSE annual-report metadata into canonical report_documents.

Source: sse-reports-archive (metadata-only). PDF bytes are NEVER bulk
downloaded; only metadata/URL/coverage/lifecycle is imported.
"""

from __future__ import annotations

import pandas as pd

from .. import db
from ..providers.sse_reports import SSEReportsProvider
from ..storage.parquet import register_source, write_parquet, write_table


def ingest_sse_reports(provider: SSEReportsProvider | None = None) -> pd.DataFrame:
    provider = provider or SSEReportsProvider()
    docs = provider.build_report_documents()

    conn = db.connect()
    conn.execute("DELETE FROM report_documents")
    conn.execute("INSERT INTO report_documents SELECT * FROM docs")
    write_parquet(docs, "reports", "report_documents")

    register_source(
        source_name="sse_reports_archive",
        data_type="report_metadata",
        url="https://github.com/yunlongli15/sse-reports-archive",
        version="master@2026-08-16",
        file="sse_reports/data/reports.db + market_metadata.csv",
        parser_version="1.0",
    )
    return docs


def ingest_lifecycle(provider: SSEReportsProvider | None = None) -> pd.DataFrame:
    provider = provider or SSEReportsProvider()
    lc = provider.load_lifecycle()
    conn = db.connect()
    conn.execute("DELETE FROM company_lifecycle")
    conn.execute("INSERT INTO company_lifecycle SELECT * FROM lc")
    return lc
