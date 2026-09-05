# -*- coding: utf-8 -*-
"""Financial query API + lazy extraction orchestration.

Layering: DocumentProvider -> DocumentExtractor -> Normalized Record ->
Storage. This module ties them together:

    get_financial_metric(symbol, metric, as_of_date)
        -> uses cached extracted metrics when available (LEVEL 2 cache),
           otherwise fetches the needed report PDF on demand (LEVEL 3 off
           by default), extracts, validates, stores, and returns the value.

The financial_metrics table is the LEVEL-2 cache: once a metric has been
extracted it is never re-downloaded.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd

from .. import config, db
from ..errors import (
    ExtractionFailedError,
    NotAvailableAtTimeError,
    NotAvailableError,
    OfflineModeError,
)
from ..providers.sse_reports import SSEReportsProvider
from ..storage.parquet import (
    insert_audit_row,
    update_report_extraction_status,
    upsert_financial_metric,
)
from ..symbols import normalize_symbol
from .extractor import EXTRACTION_VERSION, FinancialDocumentExtractor
from .metrics import derive_metrics, sanity_checks
from .pit import first_usable_date

METRIC_NAMES = {
    "revenue", "net_profit", "total_assets", "total_liabilities", "net_assets",
    "operating_cash_flow", "roe", "roa", "gross_margin", "net_margin",
    "revenue_growth", "net_profit_growth", "debt_to_asset",
}


def _usable_condition(as_of: pd.Timestamp) -> str:
    return (
        "availability_date_unknown=false AND availability_date IS NOT NULL "
        f"AND DATE '{as_of.date()}' > availability_date"
    )


def _fmt_error(status: str, symbol: str, metric: str, as_of) -> dict:
    return {
        "symbol": symbol,
        "metric": metric,
        "value": None,
        "status": status,
        "as_of_date": str(as_of.date()),
        "reason": f"{status}",
    }


def get_financial_metric(
    symbol: str,
    metric: str,
    as_of_date: Optional[str] = None,
    online: Optional[bool] = None,
) -> dict:
    """Point-in-time financial metric query with lazy extraction.

    Returns {symbol, metric, value, unit, fiscal_year, fiscal_period,
    announcement_date, availability_date, source_document_id, source_url,
    source_sha256, extraction_method, validation_status} or raises
    NotAvailableError / NotAvailableAtTimeError.
    """
    symbol = normalize_symbol(symbol)
    metric = metric.lower()
    if metric not in METRIC_NAMES:
        raise NotAvailableError(f"NOT_AVAILABLE: unknown metric {metric!r}")
    as_of = pd.Timestamp(as_of_date or pd.Timestamp.now().date())

    rows = db.query(
        "SELECT * FROM financial_metrics WHERE symbol=? AND metric_name=? "
        f"AND {_usable_condition(as_of)} "
        "ORDER BY fiscal_period DESC LIMIT 1",
        [symbol, metric],
    )
    if rows:
        r = rows[0]
        return {
            "symbol": symbol,
            "metric": metric,
            "value": r["metric_value"],
            "unit": r["unit"],
            "fiscal_year": r["fiscal_year"],
            "fiscal_period": str(r["fiscal_period"]),
            "announcement_date": str(r["announcement_date"]) if r["announcement_date"] else None,
            "availability_date": str(r["availability_date"]) if r["availability_date"] else None,
            "source_document_id": r["source_document_id"],
            "source_url": r["source_url"],
            "source_sha256": r["source_sha256"],
            "extraction_method": r["extraction_method"],
            "validation_status": r["validation_status"],
        }

    # ---- lazy extraction for the latest usable report ------------------
    if online is None:
        online = not config.is_offline()
    if online:
        _extract_latest_usable(symbol, as_of)
        rows = db.query(
            "SELECT * FROM financial_metrics WHERE symbol=? AND metric_name=? "
            f"AND {_usable_condition(as_of)} "
            "ORDER BY fiscal_period DESC LIMIT 1",
            [symbol, metric],
        )
        if rows:
            r = rows[0]
            return {
                "symbol": symbol,
                "metric": metric,
                "value": r["metric_value"],
                "unit": r["unit"],
                "fiscal_year": r["fiscal_year"],
                "fiscal_period": str(r["fiscal_period"]),
                "announcement_date": str(r["announcement_date"]) if r["announcement_date"] else None,
                "availability_date": str(r["availability_date"]) if r["availability_date"] else None,
                "source_document_id": r["source_document_id"],
                "source_url": r["source_url"],
                "source_sha256": r["source_sha256"],
                "extraction_method": r["extraction_method"],
                "validation_status": r["validation_status"],
            }

    # distinguish NOT_AVAILABLE vs NOT_AVAILABLE_AT_TIME for a clean answer:
    # reports exist but none is usable at as_of -> NOT_AVAILABLE_AT_TIME;
    # no reports with a known announcement date at all -> NOT_AVAILABLE
    cand = db.query(
        "SELECT COUNT(*) n FROM report_documents WHERE symbol=? "
        "AND document_role='annual_report' AND announcement_date IS NOT NULL",
        [symbol],
    )
    status = "NOT_AVAILABLE_AT_TIME" if cand and cand[0]["n"] > 0 else "NOT_AVAILABLE"
    if status == "NOT_AVAILABLE_AT_TIME":
        raise NotAvailableAtTimeError(
            f"{status}: no PIT-usable {metric} for {symbol} at {as_of.date()}"
        )
    raise NotAvailableError(
        f"{status}: no {metric} for {symbol} at {as_of.date()}"
    )


def _extract_latest_usable(symbol: str, as_of: pd.Timestamp) -> Optional[str]:
    """Extract the newest report usable at as_of (lazy, one PDF at most)."""
    cands = db.query(
        "SELECT * FROM report_documents WHERE symbol=? AND document_role='annual_report' "
        "AND announcement_date IS NOT NULL AND source_url IS NOT NULL "
        "AND status IN ('verified','available') ORDER BY fiscal_year DESC",
        [symbol],
    )
    for r in cands:
        usable = first_usable_date(r["announcement_date"])
        if usable is None or as_of.date() < usable:
            continue
        # skip reports already fully extracted
        done = db.query(
            "SELECT COUNT(*) n FROM financial_metrics WHERE source_document_id=?",
            [r["document_id"]],
        )
        if done and done[0]["n"] > 0:
            return r["document_id"]
        return extract_and_store(symbol, int(r["fiscal_year"]), cache=False)
    return None


def extract_and_store(
    symbol: str,
    fiscal_year: int,
    cache: bool = False,
    provider: Optional[SSEReportsProvider] = None,
) -> dict:
    """Lazy pipeline: metadata -> PDF fetch -> extract -> validate -> store.

    Returns a summary dict of extracted metrics. The temporary PDF bytes are
    discarded unless cache=True (or PQ_PDF_CACHE=1).
    """
    symbol = normalize_symbol(symbol)
    provider = provider or SSEReportsProvider()
    meta = provider.get_report_metadata(symbol, fiscal_year, "annual_report")
    if meta is None:
        raise NotAvailableError(f"NOT_AVAILABLE: no metadata for {symbol} FY{fiscal_year}")
    if not meta.get("source_url"):
        raise NotAvailableError(
            f"NOT_AVAILABLE: no fetchable URL for {symbol} FY{fiscal_year} "
            f"(source={meta.get('source')}, status={meta.get('status')})"
        )
    config.require_online(f"extract_and_store({symbol}, {fiscal_year})")
    pdf = provider.fetch_pdf(meta["source_url"])
    if cache or config.PDF_CACHE_ENABLED:
        config.ensure_dirs()
        dest = config.PDF_CACHE_DIR / f"{pdf.sha256}.pdf"
        if not dest.exists():
            dest.write_bytes(pdf.content)
        pdf.local_path = str(dest)

    extractor = FinancialDocumentExtractor(pdf.content)
    results = extractor.extract_all(fiscal_year)
    base = {k: r.value for k, r in results.items()}
    derived = derive_metrics(base)

    # growth metrics from the previous-year column
    growth = {}
    for m, prev_key in (("revenue_growth", "revenue_prev"),
                        ("net_profit_growth", "net_profit_prev")):
        cur = base.get(m.replace("_growth", ""))
        prev = base.get(prev_key)
        if cur is not None and prev not in (None, 0):
            growth[m] = (cur - prev) / prev
        else:
            growth[m] = None

    # fiscal period + PIT fields
    fiscal_period = pd.Timestamp(f"{fiscal_year}-12-31")
    ann = pd.Timestamp(meta["announcement_date"]) if meta["announcement_date"] else pd.NaT
    availability = ann if not pd.isna(ann) else pd.NaT
    availability_unknown = bool(pd.isna(ann))

    stored = {}
    for name, value in list(base.items()) + list(derived.items()) + list(growth.items()):
        if name.endswith("_prev"):
            continue
        context = {**base, "reason": None}
        status, note = sanity_checks(name, value, context)
        if status == "EXTRACTION_FAILED":
            stored[name] = {"value": None, "status": status, "note": note or
                            "metric not extractable"}
            continue
        record = {
            "symbol": symbol,
            "fiscal_period": fiscal_period,
            "fiscal_year": fiscal_year,
            "report_type": "annual",
            "announcement_date": ann if not pd.isna(ann) else None,
            "availability_date": availability if not pd.isna(availability) else None,
            "availability_date_unknown": availability_unknown,
            "metric_name": name,
            "metric_value": value,
            "unit": "CNY" if name not in {"roe", "roa", "gross_margin",
                                          "net_margin", "revenue_growth",
                                          "net_profit_growth", "debt_to_asset"}
                    else "fraction",
            "source_document_id": meta["document_id"],
            "source_url": meta["source_url"],
            "source_sha256": pdf.sha256,
            "extraction_method": (
                results.get(name).method if name in results else
                ("derived" if name in derived else "derived_growth")
            ),
            "extraction_version": EXTRACTION_VERSION,
            "extracted_at": datetime.now(),
            "raw_value": results.get(name).raw_value if name in results else None,
            "validation_status": status,
        }
        upsert_financial_metric(record)
        stored[name] = {"value": value, "status": status, "note": note}

        # audit trail row (page/section/method/raw/normalized/validation)
        res = results.get(name)
        insert_audit_row(
            {
                "symbol": symbol,
                "fiscal_year": fiscal_year,
                "metric_name": name,
                "source_document_id": meta["document_id"],
                "source_url": meta["source_url"],
                "source_sha256": pdf.sha256,
                "page": res.page if res else None,
                "section": res.section if res else None,
                "raw_value": res.raw_value if res else None,
                "normalized_value": value,
                "unit": record["unit"],
                "extraction_method": record["extraction_method"],
                "extraction_version": EXTRACTION_VERSION,
                "validation_status": status,
                "validation_note": note,
            }
        )
    update_report_extraction_status(meta["document_id"], "extracted")
    return {"symbol": symbol, "fiscal_year": fiscal_year,
            "document_id": meta["document_id"], "metrics": stored}
