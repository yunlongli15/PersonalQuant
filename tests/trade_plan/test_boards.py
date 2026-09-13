# -*- coding: utf-8 -*-
"""Board detection and trading-permission rules (科创板 50万 / 创业板 10万)."""

import pytest

from trade_plan import boards as bd
from trade_plan.plan import _effective_max_weight, suggest_top_k


def test_board_detection():
    assert bd.board_of("688416.SH") == bd.STAR        # 科创板
    assert bd.board_of("600519.SH") == bd.MAIN
    assert bd.board_of("601398.SH") == bd.MAIN
    assert bd.board_of("603259.SH") == bd.MAIN
    assert bd.board_of("300750.SZ") == bd.CHINEXT     # 创业板
    assert bd.board_of("301053.SZ") == bd.CHINEXT
    assert bd.board_of("000001.SZ") == bd.MAIN
    assert bd.board_of("002594.SZ") == bd.MAIN
    assert bd.board_of("510300.SH") == bd.FUND
    assert bd.board_of("159915.SZ") == bd.FUND
    assert bd.board_of("830799.BJ") == bd.BSE
    assert bd.board_of("garbage") == bd.UNKNOWN


def test_star_market_blocked_below_500k():
    e = bd.eligibility("688416.SH", 100_055)
    assert e.board == bd.STAR and e.board_name == "科创板"
    assert e.can_buy is False and e.restricted
    assert "50万元" in e.reason and "10.0万元" in e.reason


def test_star_market_allowed_at_500k():
    e = bd.eligibility("688416.SH", 600_000, account_experience_months=36)
    assert e.can_buy is True


def test_chinext_threshold_and_borderline_warning():
    # clearly below
    low = bd.eligibility("300750.SZ", 50_000)
    assert low.can_buy is False
    # just above: allowed, but flagged as borderline (20-day average rule)
    edge = bd.eligibility("300750.SZ", 100_055)
    assert edge.can_buy is True
    assert "临界" in edge.reason


def test_main_board_has_no_threshold():
    e = bd.eligibility("600519.SH", 1_000)
    assert e.can_buy is True and e.reason == ""
    assert e.capital_required == 0.0


def test_experience_unknown_warns_but_does_not_block():
    e = bd.eligibility("688416.SH", 600_000, account_experience_months=None)
    assert e.can_buy is True
    assert "交易经验" in e.reason


def test_experience_known_below_requirement_blocks():
    e = bd.eligibility("688416.SH", 600_000, account_experience_months=6)
    assert e.can_buy is False
    assert "24个月" in e.reason


def test_max_weight_derivation_keeps_step6_default():
    # K=20 -> the configured 10% is untouched (STEP 6 anchor preserved)
    assert _effective_max_weight(20, 0.95, 0.10) == 0.10
    # small K must lift the cap or the problem is infeasible
    assert _effective_max_weight(5, 0.95, 0.10) > 0.19
    assert 5 * _effective_max_weight(5, 0.95, 0.10) >= 0.95


def test_suggest_top_k_ignores_returns_and_follows_lot_feasibility(
        monkeypatch):
    """Behavioural check: the K choice follows lot feasibility, never the
    expected return. Here a high-return K invests badly (lots do not fit)
    and a low-return K invests well — the low-return one must win."""
    import trade_plan.plan as tp

    fake = {
        5: {"invested": 0.90, "n_positions": 6,
            "expected_net_return_pct": 0.005},      # poor alpha, good fit
        8: {"invested": 0.30, "n_positions": 3,
            "expected_net_return_pct": 0.090},      # great alpha, unusable
    }

    def fake_build(capital, top_k, risk_profile="balanced", **kw):
        d = fake[top_k]
        return {"capital": capital, "top_k": top_k,
                "total_buy_value": capital * d["invested"],
                "n_positions": d["n_positions"],
                "expected_net_return_pct": d["expected_net_return_pct"]}

    monkeypatch.setattr(tp, "build_trade_plan", fake_build)
    sel = tp.suggest_top_k(100_000, candidates=(5, 8))
    assert sel["chosen_top_k"] == 5            # feasibility, not return
    assert sel["scans"][1]["expected_net_return_pct"] > \
        sel["scans"][0]["expected_net_return_pct"]
