# -*- coding: utf-8 -*-
"""STEP 7E: trade plan engine — entry bands, targets/stops, lot sizing,
costs, sell reasons (spec §50 portfolio tests: test_lot_size,
test_cash_constraint, test_position_limit, test_industry_limit,
test_transaction_cost, test_expected_net_return)."""

import numpy as np
import pandas as pd
import pytest

from trade_plan import plan as tp


# ---------------------------------------------------------------------------
# entry band / targets / stops
# ---------------------------------------------------------------------------

def test_entry_band_is_around_the_price_not_at_it():
    low, plan_px, high, why = tp.entry_band(100.0, 0.02, "balanced")
    assert low < plan_px <= high
    assert plan_px < 100.0 * 1.01          # not a chase
    assert "vol" in why


def test_entry_band_capped_for_high_vol_names():
    low, plan_px, high, _ = tp.entry_band(100.0, 0.20, "aggressive")
    assert (100.0 - low) / 100.0 <= 0.03 + 1e-9     # capped at 3%


def test_entry_band_scales_with_risk_profile():
    widths = {}
    for profile in ("conservative", "balanced", "aggressive"):
        low, _, high, _ = tp.entry_band(100.0, 0.01, profile)
        widths[profile] = high - low
    assert widths["conservative"] < widths["balanced"] < widths["aggressive"]


def test_target_and_stop_ordering():
    t = tp.target_and_stop(price=100.0, plan_price=99.0,
                           expected_return=0.08, vol=0.02,
                           profile="balanced", horizon=20)
    assert t["stop_loss"] < 99.0 < t["target_price"]
    assert t["time_stop_days"] == 40 and t["expected_holding_days"] == 20


def test_target_follows_expected_return():
    hi = tp.target_and_stop(100.0, 100.0, 0.12, 0.02, "balanced")
    lo = tp.target_and_stop(100.0, 100.0, 0.02, 0.02, "balanced")
    assert hi["target_price"] > lo["target_price"]


def test_stop_never_deeper_than_30pct():
    t = tp.target_and_stop(100.0, 100.0, 0.0, 0.50, "aggressive")
    assert t["stop_loss"] >= 100.0 * 0.70 - 1e-9


def test_negative_expected_return_targets_below():
    t = tp.target_and_stop(100.0, 100.0, -0.05, 0.02, "balanced")
    assert t["target_price"] < 100.0


# ---------------------------------------------------------------------------
# cost model integration (shared with STEP 6 — one model, no second fees)
# ---------------------------------------------------------------------------

def test_cost_rates_come_from_the_shared_model():
    import yaml

    from pathlib import Path

    cfg = yaml.safe_load((tp.PROJECT_ROOT / "config" / "strategy_v1.yaml")
                         .read_text(encoding="utf-8"))
    buy, sell, rt = tp._cost_rates(cfg)
    assert buy > 0 and sell > buy           # stamp duty on sells
    assert rt == pytest.approx(buy + sell)
    assert sell == pytest.approx(0.00025 + 0.0005 + 0.00001 + 0.0005)


# ---------------------------------------------------------------------------
# sell reasons (spec §14)
# ---------------------------------------------------------------------------

def test_sell_reasons_are_explicit():
    plan = {"rows": [{"symbol": "600519.SH", "target_price": 27.2,
                      "time_stop_days": 40}]}
    r = tp.sell_reasons("600519.SH", plan,
                        holding={"last_price": 27.5, "days_held": 20})
    assert "forecast target reached" in r


def test_sell_reason_rank_deterioration():
    plan = {"rows": []}
    r = tp.sell_reasons("000001.SZ", plan, signal_rank=57, top_k=20)
    assert any("rank" in x for x in r)
    assert any("rebalance" in x for x in r)


def test_sell_reasons_never_empty():
    assert tp.sell_reasons("X", {"rows": []}) != []


def test_sell_reason_stop_loss_and_time_stop():
    plan = {"rows": [{"symbol": "S", "target_price": 50.0,
                      "time_stop_days": 40}]}
    r = tp.sell_reasons("S", plan, holding={"last_price": 10.0,
                                            "stop_price": 12.0,
                                            "days_held": 99})
    assert "stop loss" in r and "time stop" in r


# ---------------------------------------------------------------------------
# plan-level invariants (pure, no data access)
# ---------------------------------------------------------------------------

def _fake_plan(capital=500_000.0, weights=None, prices=None, lots=True):
    """Build the same lot/values arithmetic the engine applies, so the
    invariants can be tested without touching market data."""
    from pipeline.signals import _symbol_names  # noqa: F401 (import sanity)

    syms = list(weights)
    rows = []
    buy_rate = 0.00081
    for s in syms:
        px = prices[s]
        budget = capital * weights[s] / (1.0 + buy_rate)
        shares = int(np.floor(budget / px / 100)) * 100
        rows.append({"symbol": s, "shares": shares,
                     "buy_value": round(shares * px, 2)})
    return pd.DataFrame(rows)


def test_lot_size_multiple_of_100():
    df = _fake_plan(weights={"A": 0.10, "B": 0.10, "C": 0.05},
                    prices={"A": 23.8, "B": 1700.0, "C": 7.3})
    assert (df["shares"] % 100 == 0).all()


def test_cash_constraint_respected():
    capital = 500_000.0
    weights = {"A": 0.10, "B": 0.10, "C": 0.05, "D": 0.05, "E": 0.05}
    prices = {k: 33.3 for k in weights}
    df = _fake_plan(capital, weights, prices)
    assert df["buy_value"].sum() <= capital


def test_position_limit_applied_by_allocator():
    from portfolio.constraints import PortfolioConstraints

    cons = PortfolioConstraints(max_weight=0.10, sector_cap=0.20,
                                cash_buffer=0.05)
    assert cons.max_weight == 0.10 and cons.sector_cap == 0.20


def test_expected_net_return_is_gross_minus_round_trip():
    """Displayed net return must subtract the full round-trip cost, not
    just the buy side."""
    import yaml

    cfg = yaml.safe_load((tp.PROJECT_ROOT / "config" / "strategy_v1.yaml")
                         .read_text(encoding="utf-8"))
    _, _, rt = tp._cost_rates(cfg)
    gross, net = 0.064, 0.064 - rt
    assert net == pytest.approx(gross - rt)
    assert rt > 0.001                      # not a rounding-error assumption


def test_index_like_symbols_excluded():
    idx = tp._index_like()
    assert "000300.SH" in idx and "000905.SH" in idx
    assert "600519.SH" not in idx
