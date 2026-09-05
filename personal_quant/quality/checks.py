# -*- coding: utf-8 -*-
"""Data quality checks over the canonical layer.

Every check returns (name, passed: bool, detail: str). Checks run as
DuckDB aggregates where possible (daily_bars has ~18M rows).
"""

from __future__ import annotations

from typing import List, Tuple

import pandas as pd

from .. import db

CheckResult = Tuple[str, bool, str]


def _scalar(sql: str) -> object:
    return db.connect().execute(sql).fetchone()[0]


def check_duplicate_symbol_date() -> CheckResult:
    n = _scalar(
        "SELECT COUNT(*) FROM (SELECT symbol, trade_date FROM daily_bars "
        "GROUP BY 1, 2 HAVING COUNT(*) > 1)"
    )
    return ("duplicate symbol-date (daily_bars)", n == 0, f"{n} duplicates")


def check_invalid_price() -> CheckResult:
    n = _scalar(
        "SELECT COUNT(*) FROM daily_bars WHERE close <= 0 OR open <= 0 "
        "OR high < low OR close < low OR close > high"
    )
    return ("invalid price (non-positive / OHLC inconsistent)", n == 0, f"{n} rows")


def check_negative_volume() -> CheckResult:
    n = _scalar("SELECT COUNT(*) FROM daily_bars WHERE volume < 0")
    return ("negative volume", n == 0, f"{n} rows")


def check_missing_symbols() -> CheckResult:
    n = _scalar(
        "SELECT COUNT(DISTINCT b.symbol) FROM daily_bars b "
        "LEFT JOIN securities s USING (symbol) WHERE s.symbol IS NULL"
    )
    return ("bars without securities-master entry", n == 0, f"{n} symbols")


def check_invalid_symbol_format() -> CheckResult:
    n = _scalar(
        "SELECT COUNT(*) FROM securities "
        "WHERE symbol IS NULL OR symbol !~ '^[0-9]{6}\\.(SH|SZ|BJ)$'"
    )
    return ("invalid symbol format (securities)", n == 0, f"{n} rows")


def check_invalid_dates() -> CheckResult:
    # trading days must be weekdays and members of the canonical calendar
    n = _scalar(
        "SELECT COUNT(*) FROM daily_bars b LEFT JOIN trading_calendar c "
        "ON b.trade_date = c.trade_date "
        "WHERE c.trade_date IS NULL OR dayofweek(b.trade_date) IN (0, 6)"
    )
    return ("invalid trade dates (non-calendar / weekend)", n == 0, f"{n} rows")


def check_future_financial_data() -> CheckResult:
    n = _scalar(
        "SELECT COUNT(*) FROM financial_metrics "
        "WHERE fiscal_period > announcement_date"
    )
    return ("future financial data (fiscal_period > announcement_date)", n == 0, f"{n} rows")


def check_duplicate_reports() -> CheckResult:
    n = _scalar(
        "SELECT COUNT(*) FROM (SELECT symbol, fiscal_year, document_role "
        "FROM report_documents GROUP BY 1, 2, 3 HAVING COUNT(*) > 1)"
    )
    return ("duplicate report documents", n == 0, f"{n} groups")


def check_announcement_inconsistency() -> CheckResult:
    # annual reports must be announced after the fiscal year end and within
    # ~18 months of it (beyond that is almost certainly a data error)
    n = _scalar(
        "SELECT COUNT(*) FROM report_documents WHERE document_role='annual_report' "
        "AND announcement_date IS NOT NULL AND "
        "(announcement_date <= MAKE_DATE(fiscal_year, 12, 31) "
        " OR announcement_date > MAKE_DATE(fiscal_year + 1, 6, 30))"
    )
    return ("announcement_date inconsistency", n == 0, f"{n} rows")


def check_delisted_errors() -> CheckResult:
    # bars after a recorded delist date are suspicious
    n = _scalar(
        "SELECT COUNT(*) FROM daily_bars b JOIN securities s USING (symbol) "
        "WHERE s.delist_date IS NOT NULL AND b.trade_date > s.delist_date"
    )
    return ("bars after delist_date", n == 0, f"{n} rows")


def check_pit_violations() -> CheckResult:
    # extracted metrics must carry an availability date consistent with the
    # source document's announcement date
    n = _scalar(
        "SELECT COUNT(*) FROM financial_metrics f "
        "LEFT JOIN report_documents d ON f.source_document_id = d.document_id "
        "WHERE d.document_id IS NOT NULL AND d.announcement_date IS NOT NULL "
        "AND f.announcement_date IS NOT NULL "
        "AND f.announcement_date != d.announcement_date"
    )
    return ("PIT violations (metric vs document announcement mismatch)", n == 0, f"{n} rows")


def check_pdf_hash_mismatch() -> CheckResult:
    n = _scalar(
        "SELECT COUNT(DISTINCT source_document_id) FROM extraction_audit a "
        "JOIN report_documents d ON a.source_document_id = d.document_id "
        "WHERE d.sha256 IS NOT NULL AND a.source_sha256 IS NOT NULL "
        "AND a.source_sha256 != d.sha256"
    )
    return ("PDF hash mismatch (audit vs archive)", n == 0, f"{n} documents")


def check_extraction_value_errors() -> CheckResult:
    n = _scalar(
        "SELECT COUNT(*) FROM financial_metrics WHERE "
        "metric_name IN ('total_assets','total_liabilities','net_assets',"
        "'revenue','operating_cash_flow') AND metric_value <= 0"
    )
    return ("extraction value errors (non-positive accounting values)", n == 0, f"{n} rows")


def check_roe_range() -> CheckResult:
    n = _scalar(
        "SELECT COUNT(*) FROM financial_metrics WHERE metric_name='roe' "
        "AND (metric_value < -1 OR metric_value > 3)"
    )
    return ("roe out of plausible range [-1, 3]", n == 0, f"{n} rows")


def check_calendar_completeness() -> CheckResult:
    n = _scalar("SELECT COUNT(*) FROM trading_calendar WHERE is_open")
    return ("trading_calendar populated", n > 4000, f"{n} open days")


def check_source_registry() -> CheckResult:
    n = _scalar("SELECT COUNT(*) FROM source_registry")
    return ("source_registry populated", n >= 4, f"{n} sources registered")


def run_all_checks() -> pd.DataFrame:
    checks = [
        check_duplicate_symbol_date,
        check_invalid_price,
        check_negative_volume,
        check_missing_symbols,
        check_invalid_symbol_format,
        check_invalid_dates,
        check_future_financial_data,
        check_duplicate_reports,
        check_announcement_inconsistency,
        check_delisted_errors,
        check_pit_violations,
        check_pdf_hash_mismatch,
        check_extraction_value_errors,
        check_roe_range,
        check_calendar_completeness,
        check_source_registry,
    ]
    rows = []
    for fn in checks:
        name, ok, detail = fn()
        rows.append({"check": name, "passed": ok, "detail": detail})
    return pd.DataFrame(rows)
