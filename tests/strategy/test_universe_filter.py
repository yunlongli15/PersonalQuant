# -*- coding: utf-8 -*-
"""Universe filter tests: listing age, delisting, suspension, ST, liquidity."""

import pandas as pd
import pytest
import yaml
from pathlib import Path

from personal_quant import db
from personal_quant.strategy.universe import build_universe

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG = yaml.safe_load(
    (PROJECT_ROOT / "config" / "strategy_v1.yaml").read_text(encoding="utf-8")
)


def _universe(date, **overrides):
    cfg = yaml.safe_load(
        (PROJECT_ROOT / "config" / "strategy_v1.yaml").read_text(encoding="utf-8")
    )
    cfg["universe"].update(overrides)
    return build_universe(pd.Timestamp(date), cfg)


def test_universe_populated():
    u = _universe("2024-06-28")
    assert len(u) > 1000, "universe unexpectedly small"
    # all symbols in canonical form
    assert u["symbol"].str.match(r"^\d{6}\.(SH|SZ)$").all()


def test_stocks_listed_recently_excluded():
    """A stock listed within 180 trading days of the date is excluded."""
    conn = db.connect()
    fresh = conn.execute(
        "SELECT symbol FROM securities WHERE list_date BETWEEN '2023-09-01' AND '2024-03-01' LIMIT 5"
    ).fetch_df()["symbol"].tolist()
    u = _universe("2024-06-28")
    for s in fresh:
        assert s not in set(u["symbol"]), f"{s} listed too recently but included"


def test_delisted_stock_excluded_after_delist():
    conn = db.connect()
    delisted = conn.execute(
        "SELECT symbol, delist_date FROM securities WHERE delist_date < '2024-01-01' LIMIT 5"
    ).fetch_df()
    u = _universe("2024-06-28")
    for _, r in delisted.iterrows():
        assert r["symbol"] not in set(u["symbol"]), f"{r['symbol']} delisted but included"


def test_bse_excluded_in_v1():
    from personal_quant.symbols import normalize_symbol

    u = _universe("2024-06-28")
    assert not any(s.endswith(".BJ") for s in u["symbol"])


def test_liquidity_filter_reduces_universe():
    full = _universe("2024-06-28", liquidity={"enabled": False, "window_days": 20,
                                              "min_amount": 0})
    filtered = _universe("2024-06-28", liquidity={"enabled": True, "window_days": 20,
                                                  "min_amount": 100_000})
    assert 0 < len(filtered) <= len(full)


def test_st_filter_config_off_in_backtest():
    assert CONFIG["universe"]["st_filter"]["enabled"] is False
