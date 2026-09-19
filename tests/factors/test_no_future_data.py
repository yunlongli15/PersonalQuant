# -*- coding: utf-8 -*-
"""Technical factors must be invariant to future data.

For every technical factor: compute the panel on the intact series, then
corrupt ALL rows after date t (multiply by 7), recompute, and assert the
factor at t is unchanged. A factor that moved has a future-data leak.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from factors.base import FactorData
from factors.registry import FACTOR_REGISTRY, FACTORS
from factors import technical  # noqa: F401  (registration)

TECH_NAMES = [n for n, m in FACTOR_REGISTRY.items()
              if m["source"] == "market"]


def make_data(n_days: int = 400, seed: int = 7) -> FactorData:
    rng = np.random.default_rng(seed)
    cal = pd.date_range("2020-01-01", periods=n_days, freq="B")
    symbols = ["AAA.SH", "BBB.SZ", "CCC.SH"]
    closes = {}
    for i, s in enumerate(symbols):
        rets = rng.normal(0.0005, 0.02, n_days)
        closes[s] = 10.0 * np.exp(np.cumsum(rets)) * (1 + 0.3 * i)
    close = pd.DataFrame(closes, index=cal)
    vol = pd.DataFrame(rng.uniform(1e5, 1e6, (n_days, len(symbols))),
                       index=cal, columns=symbols)
    # bars 必须是完整的 long 表：微结构因子（隔夜/日内、Parkinson、
    # 跳空）读 open/high/low，空表会让它们无法被 PIT 测试覆盖。
    open_ = close * (1 + rng.normal(0, 0.004, close.shape))
    high = np.maximum(close, open_) * (1 + np.abs(rng.normal(
        0, 0.004, close.shape)))
    low = np.minimum(close, open_) * (1 - np.abs(rng.normal(
        0, 0.004, close.shape)))
    bars = []
    for s in symbols:
        bars.append(pd.DataFrame({
            "symbol": s, "trade_date": cal,
            "open": open_[s].to_numpy(), "high": high[s].to_numpy(),
            "low": low[s].to_numpy(), "close": close[s].to_numpy(),
            "volume": vol[s].to_numpy(), "amount": (vol[s] * close[s]).to_numpy(),
            "factor": 1.0}))
    bars = pd.concat(bars, ignore_index=True)
    return FactorData(
        calendar=cal,
        bars=bars,
        adj_close=close,
        close_raw=close,
        volume_raw=vol,
        volume_shares=vol,
        amount_cny=vol * close,
        scale=pd.DataFrame(),
        financial=pd.DataFrame(),
        industries=pd.Series(dtype=object),
        scale_available=False,
    )


@pytest.mark.parametrize("name", TECH_NAMES)
def test_factor_invariant_to_future_corruption(name):
    data = make_data()
    fn = FACTORS[name]
    intact = fn(data, dates=None)
    t = intact.index[len(intact) // 2]

    # corrupt every row strictly after t
    data2 = make_data()
    mask = data2.calendar > t
    for attr in ("adj_close", "close_raw", "volume_raw", "volume_shares",
                 "amount_cny"):
        frame = getattr(data2, attr)
        frame.loc[mask] = frame.loc[mask] * 7.0 + 3.0
    # bars 也要污染：微结构因子读 open/high/low，只污染宽表等于没测到它们
    if len(data2.bars):
        bmask = data2.bars["trade_date"] > t
        for col in ("open", "high", "low", "close", "volume", "amount"):
            if col in data2.bars.columns:
                data2.bars.loc[bmask, col] = \
                    data2.bars.loc[bmask, col] * 7.0 + 3.0
    corrupted = fn(data2, dates=None)

    for col in intact.columns:
        a, b = intact.loc[t, col], corrupted.loc[t, col]
        if np.isnan(a) and np.isnan(b):
            continue
        assert a == pytest.approx(b, rel=1e-9), \
            f"{name} changed at {t.date()} for {col} after future corruption"


def test_momentum_uses_only_past_rows():
    data = make_data(n_days=120)
    p = data.adj_close
    m20 = FACTORS["momentum_20"](data, dates=None)
    expected = p.iloc[100] / p.iloc[80] - 1.0
    got = m20.iloc[100]["AAA.SH"]
    assert got == pytest.approx(expected["AAA.SH"], rel=1e-9)


def test_rolling_windows_count_trading_rows_not_calendar_rows():
    # NaN rows (suspension) must not count toward rolling windows: a
    # min_periods=20 window that still contains the suspension gap is NaN,
    # and the first clean window equals the std of its 20 trading returns
    data = make_data(n_days=80)
    data.adj_close.iloc[50:55, 0] = np.nan  # 5 suspended days for AAA.SH
    v20 = FACTORS["volatility_20"](data, dates=None)
    assert np.isnan(v20.iloc[74]["AAA.SH"])  # window 55..74 contains the gap
    r = data.adj_close.pct_change(fill_method=None)
    manual = r.iloc[56:76]["AAA.SH"].std()  # window 56..75: 20 clean rows
    assert v20.iloc[75]["AAA.SH"] == pytest.approx(manual, rel=1e-9)
