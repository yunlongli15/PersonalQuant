# -*- coding: utf-8 -*-
"""Point-in-time availability semantics.

A financial fact (report / metric) becomes usable for research decisions only
AFTER its announcement: usable iff as_of_date > announcement_date (i.e. from
the day after the announcement). Data whose announcement date is unknown is
marked availability_date_unknown and is excluded from strict PIT queries.

Examples:
  FY2024 annual report, announcement_date = 2025-04-01
    - as_of 2025-03-31 -> NOT_AVAILABLE_AT_TIME
    - as_of 2025-04-01 -> NOT_AVAILABLE_AT_TIME (announcement day itself)
    - as_of 2025-04-02 -> available
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import pandas as pd

from .. import db
from ..errors import NotAvailableAtTimeError, NotAvailableError
from ..symbols import normalize_symbol

AVAILABLE = "available"
NOT_AVAILABLE = "not_available"
NOT_AVAILABLE_AT_TIME = "not_available_at_time"


def first_usable_date(announcement_date) -> Optional[date]:
    """The first calendar day on which data announced on `d` may be used."""
    d = pd.Timestamp(announcement_date).date() if announcement_date is not None else None
    if d is None:
        return None
    return d + timedelta(days=1)


def availability_status(
    symbol: str, fiscal_year: int, as_of_date: Optional[str] = None
) -> str:
    """Availability of the FY annual report of `symbol` at `as_of_date`."""
    symbol = normalize_symbol(symbol)
    as_of = pd.Timestamp(as_of_date or pd.Timestamp.now()).date()
    rows = db.query(
        "SELECT announcement_date, availability_date_unknown FROM report_documents "
        "WHERE symbol=? AND fiscal_year=? AND document_role='annual_report' "
        "ORDER BY announcement_date DESC NULLS LAST LIMIT 1",
        [symbol, fiscal_year],
    )
    if not rows:
        return NOT_AVAILABLE
    r = rows[0]
    if r["availability_date_unknown"]:
        return NOT_AVAILABLE  # strict mode: unknown availability is unusable
    ann = r["announcement_date"]
    usable = first_usable_date(ann)
    if usable is None or as_of < usable:
        return NOT_AVAILABLE_AT_TIME
    return AVAILABLE


def get_latest_available_annual_report(
    symbol: str, as_of_date: Optional[str] = None
) -> Optional[dict]:
    """Newest annual report usable at as_of_date (strict PIT)."""
    symbol = normalize_symbol(symbol)
    as_of = pd.Timestamp(as_of_date or pd.Timestamp.now()).date()
    rows = db.query(
        "SELECT * FROM report_documents "
        "WHERE symbol=? AND document_role='annual_report' "
        "AND availability_date_unknown=false AND announcement_date IS NOT NULL "
        "ORDER BY fiscal_year DESC",
        [symbol],
    )
    for r in rows:
        usable = first_usable_date(r["announcement_date"])
        if usable is not None and as_of >= usable:
            return r
    return None


def get_financial_report(
    symbol: str,
    fiscal_year: int,
    as_of_date: Optional[str] = None,
    strict: bool = True,
) -> dict:
    """Return the annual-report row for (symbol, fiscal_year) honoring PIT.

    Raises NotAvailableError / NotAvailableAtTimeError per the availability
    semantics; strict=False skips the PIT check (documented, for audits).
    """
    symbol = normalize_symbol(symbol)
    rows = db.query(
        "SELECT * FROM report_documents WHERE symbol=? AND fiscal_year=? "
        "AND document_role='annual_report' LIMIT 1",
        [symbol, fiscal_year],
    )
    if not rows:
        raise NotAvailableError(f"NOT_AVAILABLE: no annual report for {symbol} FY{fiscal_year}")
    r = rows[0]
    if strict:
        status = availability_status(symbol, fiscal_year, as_of_date)
        if status == NOT_AVAILABLE_AT_TIME:
            raise NotAvailableAtTimeError(
                f"NOT_AVAILABLE_AT_TIME: {symbol} FY{fiscal_year} announced "
                f"{r['announcement_date']}, not usable at {as_of_date}"
            )
        if status == NOT_AVAILABLE:
            raise NotAvailableError(
                f"NOT_AVAILABLE: {symbol} FY{fiscal_year} announcement date unknown"
            )
    return r
