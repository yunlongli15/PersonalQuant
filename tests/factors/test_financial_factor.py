# -*- coding: utf-8 -*-
"""Financial factor formulas (PE/PB/PS/earnings-yield/turnover) from
synthetic PIT data — including denominator guards and negative-EPS
handling."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from factors.base import FactorData
from factors.fundamental import pit_metric_panel, shares_panel
from factors.valuation import earnings_yield, pb, pe, ps

DATES = pd.DatetimeIndex([pd.Timestamp("2025-06-30")])


def make_data():
    """One report announced 2025-04-01 for three stocks."""
    syms = ["AAA.SH", "BBB.SZ", "CCC.SH"]
    n = len(syms)
    fin = pd.DataFrame({
        "symbol": syms * 4,
        "metric_name": (["eps"] * n + ["bps"] * n + ["net_assets"] * n
                        + ["revenue"] * n),
        "metric_value": [2.0, -1.5, 5.0,          # eps (BBB loss-making)
                         10.0, 3.0, 0.0,          # bps (CCC bps=0 -> PB undefined)
                         1e10, 3e9, 5e9,          # net_assets
                         2e10, 6e9, 1e10],        # revenue
        "fiscal_year": [2024] * (4 * n),
        "fiscal_period": [pd.Timestamp("2024-12-31")] * (4 * n),
        "availability_date": [pd.Timestamp("2025-04-01")] * (4 * n),
        "availability_date_unknown": [False] * (4 * n),
    })
    cal = pd.DatetimeIndex([pd.Timestamp("2025-06-30")])
    close = pd.DataFrame({"AAA.SH": [100.0], "BBB.SZ": [50.0], "CCC.SH": [80.0]},
                         index=cal)
    vol = pd.DataFrame(1e6, index=cal, columns=syms)
    return FactorData(
        calendar=cal, bars=pd.DataFrame(), adj_close=close, close_raw=close,
        volume_raw=vol, volume_shares=vol, amount_cny=vol * close,
        scale=pd.DataFrame(), financial=fin, industries=pd.Series(dtype=object),
        scale_available=False,
    )


@pytest.fixture
def data():
    return make_data()


def test_pe_formula(data):
    v = pe(data, DATES)
    assert v.loc["2025-06-30", "AAA.SH"] == pytest.approx(50.0)  # 100/2


def test_negative_eps_kept_as_negative_pe(data):
    v = pe(data, DATES)
    assert v.loc["2025-06-30", "BBB.SZ"] == pytest.approx(50.0 / -1.5)


def test_pb_formula_and_zero_bps_guard(data):
    v = pb(data, DATES)
    assert v.loc["2025-06-30", "AAA.SH"] == pytest.approx(10.0)
    assert np.isnan(v.loc["2025-06-30", "CCC.SH"])  # bps = 0 -> undefined


def test_shares_panel_from_net_assets_bps(data):
    sh = shares_panel(data, DATES)
    assert sh.loc["2025-06-30", "AAA.SH"] == pytest.approx(1e9)  # 1e10/10
    assert sh.loc["2025-06-30", "BBB.SZ"] == pytest.approx(1e9)


def test_ps_formula(data):
    v = ps(data, DATES)
    # AAA: shares = 1e10/10 = 1e9, mcap = 100*1e9, revenue 2e10 -> PS = 5
    assert v.loc["2025-06-30", "AAA.SH"] == pytest.approx(5.0)
    # CCC: bps = 0 -> shares undefined -> PS undefined
    assert np.isnan(v.loc["2025-06-30", "CCC.SH"])


def test_earnings_yield_formula(data):
    v = earnings_yield(data, DATES)
    assert v.loc["2025-06-30", "AAA.SH"] == pytest.approx(0.02)


def test_pit_join_respects_availability(data):
    data.financial.loc[:, "availability_date"] = pd.Timestamp("2025-07-01")
    v = pe(data, DATES)  # announced after the signal date -> not usable
    assert v.isna().all().all()
