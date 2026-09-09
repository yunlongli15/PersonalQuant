# -*- coding: utf-8 -*-
"""PIT semantics of the financial factor join engine.

Rule: a report with announcement date A is usable for a signal date d only
when d > A (the announcement day itself is excluded — the data is usable
from the NEXT trading day). availability_date_unknown reports are never
used (strict mode).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from factors.fundamental import pit_metric_panel


def make_financial():
    """Two reports: FY2023 announced 2024-03-30; FY2024 announced
    2025-04-01; one unknown-availability report that must never leak."""
    return pd.DataFrame({
        "symbol": ["600000.SH"] * 3,
        "fiscal_year": [2023, 2024, 2025],
        "fiscal_period": [pd.Timestamp("2023-12-31"),
                          pd.Timestamp("2024-12-31"),
                          pd.Timestamp("2025-12-31")],
        "availability_date": [pd.Timestamp("2024-03-30"),
                              pd.Timestamp("2025-04-01"),
                              pd.NaT],
        "availability_date_unknown": [False, False, True],
        "metric_name": ["roe"] * 3,
        "metric_value": [0.15, 0.18, 0.30],
    })


class D:
    financial = make_financial()


@pytest.fixture
def data():
    return D()


def test_before_announcement_only_older_reports_available(data):
    # 2025-03-31: FY2024 not yet usable; latest available = FY2023
    panel, fy = pit_metric_panel(data, "roe", [pd.Timestamp("2025-03-31")])
    assert panel.iloc[0, 0] == pytest.approx(0.15)
    assert fy.iloc[0, 0] == 2023


def test_not_available_on_announcement_day(data):
    # 2025-04-01 (the announcement day itself): FY2024 still excluded
    panel, fy = pit_metric_panel(data, "roe", [pd.Timestamp("2025-04-01")])
    assert panel.iloc[0, 0] == pytest.approx(0.15)  # strict: as_of > availability
    assert fy.iloc[0, 0] == 2023


def test_available_after_announcement(data):
    panel, fy = pit_metric_panel(data, "roe", [pd.Timestamp("2025-04-02")])
    assert panel.iloc[0, 0] == pytest.approx(0.18)
    assert fy.iloc[0, 0] == 2024


def test_latest_available_is_forward_filled(data):
    panel, fy = pit_metric_panel(data, "roe",
                                 [pd.Timestamp("2024-06-30"),
                                  pd.Timestamp("2025-06-30")])
    assert panel.iloc[0, 0] == pytest.approx(0.15)  # FY2023 (before FY2024 ann)
    assert fy.iloc[0, 0] == 2023
    assert panel.iloc[1, 0] == pytest.approx(0.18)
    assert fy.iloc[1, 0] == 2024


def test_unknown_availability_never_used(data):
    panel, fy = pit_metric_panel(data, "roe", [pd.Timestamp("2026-06-30")])
    # FY2025 report has unknown availability -> excluded; FY2024 still holds
    assert panel.iloc[0, 0] == pytest.approx(0.18)
    assert fy.iloc[0, 0] == 2024


def test_missing_metric_panel_is_nan(data):
    panel, _ = pit_metric_panel(data, "net_profit", [pd.Timestamp("2025-06-30")])
    assert panel.isna().all().all()
