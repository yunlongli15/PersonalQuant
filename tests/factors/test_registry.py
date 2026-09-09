# -*- coding: utf-8 -*-
"""Factor registry integrity."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from factors.registry import FACTOR_REGISTRY, FACTORS, categories, registry_df

ALLOWED_CATEGORIES = {"momentum", "reversal", "volatility", "liquidity",
                      "price_position", "volume", "valuation", "quality",
                      "growth", "cash_flow"}
REQUIRED = {"factor_name", "category", "formula", "source",
            "required_fields", "pit", "direction", "description",
            "version", "status"}


def test_registry_nonempty_and_unique():
    assert len(FACTOR_REGISTRY) >= 25
    assert len(FACTOR_REGISTRY) == len(set(FACTOR_REGISTRY))


def test_every_factor_has_required_metadata():
    for name, meta in FACTOR_REGISTRY.items():
        missing = REQUIRED - set(meta)
        assert not missing, f"{name} missing {missing}"
        assert meta["factor_name"] == name
        assert meta["category"] in ALLOWED_CATEGORIES, name
        assert meta["direction"] in ("positive", "negative", "neutral"), name
        assert isinstance(meta["pit"], bool), name
        assert meta["required_fields"], name


def test_every_factor_has_a_callable():
    for name in FACTOR_REGISTRY:
        assert callable(FACTORS[name]), name


def test_categories_grouping():
    cats = categories()
    assert set(cats) <= ALLOWED_CATEGORIES
    all_names = [n for names in cats.values() for n in names]
    assert sorted(all_names) == sorted(FACTOR_REGISTRY)


def test_spec_first_batch_present():
    # the STEP 4 first candidate batch must all be registered (or, where
    # data cannot support them, registered with a documented limitation)
    expected = {
        "momentum_20", "momentum_60", "momentum_120",
        "reversal_5", "reversal_20",
        "volatility_20", "volatility_60", "downside_volatility_60",
        "turnover_20", "turnover_60",
        "amount_20", "amount_60",
        "price_vs_ma20", "price_vs_ma60", "price_vs_ma120",
        "volume_ratio_5_20", "volume_ratio_20_60",
        "pe", "pb", "ps", "earnings_yield",
        "roe", "roa", "gross_margin", "net_margin", "debt_to_asset",
        "revenue_growth", "net_profit_growth",
        "operating_cash_flow", "ocf_to_assets", "ocf_to_net_profit",
    }
    missing = expected - set(FACTOR_REGISTRY)
    assert not missing, f"first-batch factors not registered: {missing}"


def test_registry_df():
    df = registry_df()
    assert set(df.index) == set(FACTOR_REGISTRY)
    assert "formula" in df.columns


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
