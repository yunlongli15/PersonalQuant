# -*- coding: utf-8 -*-
"""Point-in-time semantics tests (pure logic + DuckDB-backed lookups)."""

from datetime import date

import pandas as pd
import pytest

from personal_quant.financial.pit import (
    availability_status,
    first_usable_date,
    get_financial_report,
    get_latest_available_annual_report,
)
from personal_quant.errors import NotAvailableAtTimeError, NotAvailableError


class TestFirstUsableDate:
    def test_next_day(self):
        assert first_usable_date("2025-04-01") == date(2025, 4, 2)

    def test_unknown(self):
        assert first_usable_date(None) is None


@pytest.fixture(scope="module")
def seeded_db():
    """Seed report_documents with a small PIT scenario."""
    from personal_quant import db

    conn = db.connect()
    conn.execute("DELETE FROM report_documents WHERE symbol LIKE 'TST%'")
    rows = [
        # FY2024 announced 2025-04-01
        ("TST699999-2024-annual_report", "699999.SH", "SH", 2024, "annual",
         "annual_report", None, "2025-04-01", "url_derived", "2025-04-01", False,
         "cninfo", "https://static.cninfo.com.cn/finalpage/2025-04-01/x.PDF",
         None, "available", None, None, None, None, None, "not_started"),
        # FY2023 announced 2024-03-28
        ("TST699999-2023-annual_report", "699999.SH", "SH", 2023, "annual",
         "annual_report", None, "2024-03-28", "url_derived", "2024-03-28", False,
         "cninfo", "https://static.cninfo.com.cn/finalpage/2024-03-28/x.PDF",
         None, "available", None, None, None, None, None, "not_started"),
        # FY2022: announcement date unknown
        ("TST699999-2022-annual_report", "699999.SH", "SH", 2022, "annual",
         "annual_report", None, None, None, None, True,
         "sse", None, None, "source_unavailable", None, None, None, None, None,
         "not_started"),
    ]
    for r in rows:
        ph = ",".join(["?"] * len(r))
        conn.execute(
            f"INSERT OR REPLACE INTO report_documents VALUES ({ph})",
            list(r),
        )
    yield
    conn.execute("DELETE FROM report_documents WHERE symbol LIKE 'TST%'")


def test_availability_status(seeded_db):
    # FY2024 (announced 2025-04-01): usable from 2025-04-02
    assert availability_status("699999.SH", 2024, "2025-03-31") == "not_available_at_time"
    assert availability_status("699999.SH", 2024, "2025-04-01") == "not_available_at_time"
    assert availability_status("699999.SH", 2024, "2025-04-02") == "available"
    assert availability_status("699999.SH", 2024, "2026-01-01") == "available"
    # FY2023 (announced 2024-03-28)
    assert availability_status("699999.SH", 2023, "2024-03-28") == "not_available_at_time"
    assert availability_status("699999.SH", 2023, "2024-03-29") == "available"
    # FY2022: unknown announcement -> unusable in strict mode
    assert availability_status("699999.SH", 2022, "2026-01-01") == "not_available"
    # missing
    assert availability_status("699999.SH", 1999, "2026-01-01") == "not_available"


def test_get_financial_report_pit(seeded_db):
    with pytest.raises(NotAvailableAtTimeError):
        get_financial_report("699999.SH", 2024, as_of_date="2025-03-31")
    r = get_financial_report("699999.SH", 2024, as_of_date="2025-04-02")
    assert r["fiscal_year"] == 2024 and pd.Timestamp(r["announcement_date"]).date() == date(2025, 4, 1)
    with pytest.raises(NotAvailableError):
        get_financial_report("699999.SH", 2022, as_of_date="2026-01-01")
    with pytest.raises(NotAvailableError):
        get_financial_report("699999.SH", 1999, as_of_date="2026-01-01")


def test_get_latest_available_annual_report(seeded_db):
    r = get_latest_available_annual_report("699999.SH", as_of_date="2025-04-01")
    assert r is not None and r["fiscal_year"] == 2023  # FY2024 not yet usable
    r2 = get_latest_available_annual_report("699999.SH", as_of_date="2025-04-02")
    assert r2["fiscal_year"] == 2024
    # unknown-announcement report must not leak through
    r3 = get_latest_available_annual_report("699999.SH", as_of_date="2026-01-01")
    assert r3["fiscal_year"] == 2024
