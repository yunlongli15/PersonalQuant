# -*- coding: utf-8 -*-
"""Financial query API tests (PIT lookups over the real extracted data).

These run against the canonical DuckDB; the FY2023 Moutai extraction was
created by the demo (announcement 2024-04-03). They do not need network.
"""

import pytest

from personal_quant.errors import NotAvailableAtTimeError, NotAvailableError
from personal_quant.financial.query import get_financial_metric


def test_moutai_roe_pit():
    # FY2023 announced 2024-04-03 -> not usable on 2024-04-01; the API then
    # returns the newest value that IS usable at that date (FY2022, announced
    # 2023-03-31). From 2024-04-04 onward FY2023 becomes the answer.
    r_before = get_financial_metric("600519.SH", "roe", "2024-04-01", online=False)
    assert r_before["fiscal_year"] == 2022
    assert r_before["value"] == pytest.approx(0.3026, abs=0.01)
    r = get_financial_metric("600519.SH", "roe", "2024-06-01", online=False)
    assert r["value"] == pytest.approx(0.3419, abs=0.01)
    assert r["fiscal_year"] == 2023
    assert r["unit"] == "fraction"
    assert r["source_document_id"] == "sse-600519-2023-annual_report"
    assert r["source_sha256"]  # audit trail present
    # before the first available report: no usable value exists
    with pytest.raises(NotAvailableAtTimeError):
        get_financial_metric("600519.SH", "roe", "2023-03-31", online=False)


def test_moutai_revenue():
    r = get_financial_metric("600519.SH", "revenue", "2024-06-01", online=False)
    assert r["value"] == pytest.approx(147_693_604_994, rel=0.01)
    assert r["unit"] == "CNY"


def test_earlier_asof_returns_prior_year():
    # as-of before FY2023 announcement -> the FY2022 value (announced
    # 2023-03-31) must be returned, never the not-yet-public FY2023
    r = get_financial_metric("600519.SH", "revenue", "2023-08-01", online=False)
    assert r["fiscal_year"] == 2022
    assert r["value"] == pytest.approx(124_099_843_771, rel=0.01)


def test_before_first_report_not_available():
    with pytest.raises((NotAvailableError, NotAvailableAtTimeError)):
        get_financial_metric("600519.SH", "revenue", "2010-01-01", online=False)


def test_unknown_symbol():
    with pytest.raises((NotAvailableError, NotAvailableAtTimeError)):
        get_financial_metric("699999.SH", "revenue", "2026-01-01", online=False)


def test_unknown_metric():
    with pytest.raises(NotAvailableError):
        get_financial_metric("600519.SH", "does_not_exist", "2026-01-01", online=False)
