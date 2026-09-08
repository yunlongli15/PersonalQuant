# -*- coding: utf-8 -*-
"""Backtest holdings invariants (regression: the engine must SELL names that
drop out of the top-k, never accumulate unbounded positions)."""

import pandas as pd
import pytest
import yaml
from pathlib import Path

from personal_quant.strategy.backtest import MonthlyBacktest
from personal_quant.strategy.costs import TransactionCostModel
from personal_quant.strategy.rebalance import trading_days

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG = yaml.safe_load(
    (PROJECT_ROOT / "config" / "strategy_v1.yaml").read_text(encoding="utf-8")
)


def _predictor(dates, symbols):
    """Deterministic pseudo-predictor: rank by symbol hash for stability."""
    d0 = dates[0]
    return pd.Series(
        {s: sum(map(ord, s)) % 97 + (d0.day * 3 % 11) for s in symbols}
    ).sort_values(ascending=False)


def test_position_count_bounded():
    """After several months, holdings must stay at/under top_k (+remainders)."""
    bt = MonthlyBacktest(CONFIG, TransactionCostModel.from_config(CONFIG),
                         initial_capital=500_000.0)
    res = bt.run("2024-01-01", "2024-06-30",
                 lambda d, syms: _predictor([d], syms))
    assert len(res.nav) > 100
    # positions frame: number of held names per day must never exceed top_k
    # (a partial-lot remainder can leave at most a handful extra, so allow a
    # small slack of 5)
    held = (res.positions > 0).sum(axis=1)
    assert held.max() <= CONFIG["portfolio"]["top_k"] + 5, \
        f"engine accumulated too many positions: {held.max()}"
    # cash must never go deeply negative
    assert (res.cash / res.nav).min() > -0.1, "cash went negative beyond buffer"


def test_sells_happen():
    """The engine must generate SELL trades (not only buys)."""
    bt = MonthlyBacktest(CONFIG, TransactionCostModel.from_config(CONFIG),
                         initial_capital=500_000.0)
    res = bt.run("2024-01-01", "2024-12-31",
                 lambda d, syms: _predictor([d], syms))
    assert not res.trades.empty
    sides = set(res.trades["side"])
    assert "SELL" in sides, "no sell trades generated (stale positions kept)"
    assert len(res.trades) > 20


def test_cash_buffer_respected():
    """Stock exposure stays near (1-buffer); cash never wildly negative."""
    bt = MonthlyBacktest(CONFIG, TransactionCostModel.from_config(CONFIG),
                         initial_capital=1_000_000.0)
    res = bt.run("2024-01-01", "2024-09-30",
                 lambda d, syms: _predictor([d], syms))
    exposure = 1.0 - res.cash / res.nav
    assert exposure.max() < 1.02, f"exposure too high: {exposure.max():.3f}"
    assert exposure.min() > -0.05
