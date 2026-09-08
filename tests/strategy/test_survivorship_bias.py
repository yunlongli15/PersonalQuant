# -*- coding: utf-8 -*-
"""Survivorship-bias tests: the historical universe must be dynamic."""

import pandas as pd
import pytest
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG = yaml.safe_load(
    (PROJECT_ROOT / "config" / "strategy_v1.yaml").read_text(encoding="utf-8")
)


@pytest.fixture(scope="module")
def universe_2019():
    from personal_quant.strategy.universe import build_universe

    return build_universe(pd.Timestamp("2019-06-28"), CONFIG)


@pytest.fixture(scope="module")
def universe_2024():
    from personal_quant.strategy.universe import build_universe

    return build_universe(pd.Timestamp("2024-06-28"), CONFIG)


def test_historical_universe_differs_from_current(universe_2019, universe_2024):
    s2019 = set(universe_2019["symbol"])
    s2024 = set(universe_2024["symbol"])
    assert s2019 != s2024, "historical and current universes must differ"
    assert len(s2019) > 500 and len(s2024) > 500


def test_no_future_stock_in_past(universe_2019):
    """A stock listed after 2019 must not appear in the 2019 universe."""
    from personal_quant import db

    conn = db.connect()
    late = conn.execute(
        "SELECT symbol FROM securities WHERE list_date > '2019-06-28' AND is_active LIMIT 20"
    ).fetch_df()["symbol"].tolist()
    for s in late:
        assert s not in set(universe_2019["symbol"]), f"{s} listed after 2019 leaked in"


def test_delisted_stock_still_in_historical_universe(universe_2019):
    """A stock that delisted later must exist in the 2019 universe if it traded."""
    from personal_quant import db

    conn = db.connect()
    # stocks delisted AFTER mid-2019 must still appear in the 2019 universe
    delisted = conn.execute(
        "SELECT symbol FROM securities WHERE delist_date > '2019-06-28' LIMIT 50"
    ).fetch_df()["symbol"].tolist()
    s2019 = set(universe_2019["symbol"])
    found = [s for s in delisted if s in s2019]
    assert found, "no later-delisted stocks present in 2019 universe (survivorship bias!)"


def test_listing_day_filter(universe_2019):
    from personal_quant import db

    conn = db.connect()
    min_days = CONFIG["universe"]["min_listing_days"]
    # every universe member must have list_date well before the date, or a
    # first-bar proxy older than the date
    df = conn.execute(
        "SELECT symbol, list_date FROM securities WHERE symbol IN (SELECT unnest(?::VARCHAR[]))",
        [universe_2019["symbol"].tolist()],
    ).fetch_df()
    for _, r in df.iterrows():
        if pd.notna(r["list_date"]):
            assert (pd.Timestamp("2019-06-28") - pd.Timestamp(r["list_date"])).days >= min_days
