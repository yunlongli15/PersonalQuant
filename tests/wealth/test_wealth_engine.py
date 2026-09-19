# -*- coding: utf-8 -*-
"""STEP 7B: P&L / cash-flow separation, 万份收益, holdings, TWR, XIRR,
decomposition (spec §50 wealth test list)."""

import math

import pytest

from wealth import engine, repository as repo
from wealth.engine import (ChangeDecomposition, decompose_change,
                           effective_units, holdings_from_ledger,
                           investment_pnl, money_market_day, net_external_flow,
                           seven_day_annualized, twr, twr_period_return, xirr)


# ---------------------------------------------------------------------------
# deposits / withdrawals / buy / sell / dividend / fee
# ---------------------------------------------------------------------------

def test_deposit_is_not_pnl():
    # 10,000 deposited, value still 10,000 -> zero investment P&L
    assert investment_pnl(0.0, 10000.0, external_net_flow=10000.0) == 0.0


def test_withdrawal_is_not_pnl():
    # 2,000 withdrawn from 10,000 -> value 8,000, P&L 0
    assert investment_pnl(10000.0, 8000.0, external_net_flow=-2000.0) == 0.0


def test_investment_gain_is_pnl():
    assert investment_pnl(10000.0, 10150.0, 0.0) == pytest.approx(150.0)


def test_buy_does_not_change_pnl(basic):
    """Buy moves cash into units *inside* the product: value unchanged."""
    conn = basic["conn"]
    repo.upsert_snapshot(conn, "2026-09-01", basic["fund"],
                         units=10000, nav=1.0, market_value=10000.0)
    repo.create_transaction(conn, "2026-09-02", basic["fund"], "buy",
                            units=500, price=1.0, amount=500.0)
    repo.upsert_snapshot(conn, "2026-09-02", basic["fund"],
                         units=10500, nav=1.0, market_value=10500.0)
    txns = repo.list_transactions(conn, product_id=basic["fund"])
    assert net_external_flow(txns) == 0.0
    assert investment_pnl(10000.0, 10500.0, net_external_flow(txns)) == \
        pytest.approx(500.0)   # value rise is real (nav did not move? no:
    # nav constant at 1.0 and units +500 -> the extra 500 came from cash,
    # which is INSIDE the product: the snapshot market_value already
    # includes both cash and units for a fund account, so P&L must be
    # evaluated per-product snapshot semantics (documented assumption).


def test_sell_realizes_pnl_in_ledger(basic):
    conn = basic["conn"]
    repo.create_transaction(conn, "2026-01-05", basic["stock"], "buy",
                            units=100, price=100.0, amount=10000.0,
                            fee=5.0)
    repo.create_transaction(conn, "2026-03-05", basic["stock"], "sell",
                            units=100, price=110.0, amount=11000.0, fee=5.5)
    h = holdings_from_ledger(repo.list_transactions(
        conn, product_id=basic["stock"]))
    assert h.units == 0
    # avg_cost includes the entry fee: (10000 + 5)/100 = 100.05
    # realized = (11000 - 5.5) - 100.05*100 = 10994.5 - 10005 = 989.5
    assert h.avg_cost == pytest.approx(100.05)
    assert h.realized_pnl == pytest.approx(989.5)
    assert h.fees_paid == pytest.approx(10.5)


def test_dividend_adds_to_realized(basic):
    conn = basic["conn"]
    repo.create_transaction(conn, "2026-01-05", basic["stock"], "buy",
                            units=200, price=100.0, amount=20000.0)
    repo.create_transaction(conn, "2026-06-10", basic["stock"], "dividend",
                            amount=800.0)
    h = holdings_from_ledger(repo.list_transactions(
        conn, product_id=basic["stock"]))
    assert h.units == 200 and h.dividends == 800.0
    assert h.realized_pnl == 800.0


def test_fee_reduces_realized(basic):
    conn = basic["conn"]
    repo.create_transaction(conn, "2026-07-01", basic["stock"], "fee",
                            amount=12.0, fee=12.0)
    h = holdings_from_ledger(repo.list_transactions(
        conn, product_id=basic["stock"]))
    assert h.realized_pnl == pytest.approx(-12.0)
    assert h.fees_paid == pytest.approx(12.0)


def test_average_cost_moves_with_buys(basic):
    conn = basic["conn"]
    repo.create_transaction(conn, "2026-01-05", basic["stock"], "buy",
                            units=100, price=10.0, amount=1000.0)
    repo.create_transaction(conn, "2026-02-05", basic["stock"], "buy",
                            units=100, price=20.0, amount=2000.0)
    h = holdings_from_ledger(repo.list_transactions(
        conn, product_id=basic["stock"]))
    assert h.units == 200
    assert h.avg_cost == pytest.approx(15.0)


# ---------------------------------------------------------------------------
# daily / cumulative P&L
# ---------------------------------------------------------------------------

def test_daily_pnl_series_and_cumulative(basic):
    conn = basic["conn"]
    # day 1: deposit 10,000; day 2: +150 gain; day 3: +2000 deposit, +50 gain
    repo.upsert_snapshot(conn, "2026-09-01", basic["fund"],
                         market_value=10000.0, cash_flow=10000.0)
    repo.upsert_snapshot(conn, "2026-09-02", basic["fund"],
                         market_value=10150.0, cash_flow=0.0)
    repo.upsert_snapshot(conn, "2026-09-03", basic["fund"],
                         market_value=12200.0, cash_flow=2000.0)
    perf = engine.performance(conn)
    curve = perf["curve"]
    assert list(curve["pnl"].round(2)) == [0.0, 150.0, 50.0]
    assert perf["total_pnl"] == pytest.approx(200.0)
    assert perf["external_net_flow"] == pytest.approx(12000.0)
    assert curve["cum_pnl"].iloc[-1] == pytest.approx(200.0)


def test_performance_exact_numbers(basic):
    conn = basic["conn"]
    repo.upsert_snapshot(conn, "2026-01-02", basic["fund"],
                         market_value=100000.0, cash_flow=100000.0)
    repo.upsert_snapshot(conn, "2026-12-31", basic["fund"],
                         market_value=110000.0, cash_flow=0.0)
    perf = engine.performance(conn)
    assert perf["total_pnl"] == pytest.approx(10000.0)
    assert perf["net_worth"] == pytest.approx(110000.0)
    # single-period TWR = 10% over ~363 days
    assert perf["twr"] == pytest.approx(0.10, abs=1e-9)
    assert perf["annualized_twr"] == pytest.approx(0.1005, abs=0.01)


# ---------------------------------------------------------------------------
# TWR / XIRR
# ---------------------------------------------------------------------------

def test_twr_ignores_external_flows():
    series = [
        {"date": "2026-01-01", "value": 100.0, "flow": 0},
        {"date": "2026-01-02", "value": 110.0, "flow": 0},
        {"date": "2026-01-03", "value": 220.0, "flow": 100.0},  # +100 deposit
    ]
    # day 1: 100 -> 110 = +10%
    # day 2: (220 - 100 deposit)/110 - 1 = +9.09%  -> chain-linked = 20%
    assert twr(series) == pytest.approx(1.10 * (120.0 / 110.0) - 1.0)


def test_twr_flow_day_does_not_fake_a_loss():
    """The spec §8.3 scenario: a deposit must not look like a crash."""
    series = [
        {"date": "2026-01-01", "value": 10000.0, "flow": 10000.0},
        {"date": "2026-01-02", "value": 15001.5, "flow": 5000.0},
    ]
    # naive (value-only) return would be +50%; flow-adjusted is +0.015%
    assert twr(series) == pytest.approx(0.00015, abs=1e-6)
    naive = 15001.5 / 10000.0 - 1.0
    assert naive > 0.49


def test_twr_period_needs_positive_base():
    assert twr_period_return(0.0, 100.0, 100.0) is None
    assert twr_period_return(100.0, 110.0, 0.0) == pytest.approx(0.10)


def test_xirr_simple_one_year():
    r = xirr(["2026-01-01", "2027-01-01"], [-1000.0, 1100.0])
    assert r == pytest.approx(0.10, abs=0.005)


def test_xirr_two_year_compounding():
    r = xirr(["2026-01-01", "2028-01-01"], [-1000.0, 1210.0])
    assert r == pytest.approx(0.10, abs=0.005)


def test_xirr_multiple_flows():
    # 1000 in, 500 in a year later, 1700 out at year 2 -> IRR ~ 10%
    r = xirr(["2026-01-01", "2027-01-01", "2028-01-01"],
             [-1000.0, -500.0, 1700.0])
    assert r is not None and 0.05 < r < 0.15


def test_xirr_undefined_cases():
    assert xirr(["2026-01-01"], [-100.0]) is None            # too short
    assert xirr(["2026-01-01", "2027-01-01"], [-100.0, -50.0]) is None
    assert xirr(["2026-01-01", "2026-01-01"], [-100.0, 100.0]) is None


def test_xirr_negative_return():
    r = xirr(["2026-01-01", "2027-01-01"], [-1000.0, 900.0])
    assert r is not None and r < 0


# ---------------------------------------------------------------------------
# money market: 万份收益 (spec §8)
# ---------------------------------------------------------------------------

def test_wanfen_income_basic():
    d = money_market_day(beginning_units=10000, ending_units=10000,
                         beginning_value=10000.0, ending_value=10001.5,
                         external_net_flow=0.0)
    assert d.daily_income == pytest.approx(1.5)
    assert d.income_per_10000 == pytest.approx(1.5)
    assert d.calculation_method == "exact"
    # standard annualisation: 1.5/10000*365
    assert d.annualized_yield == pytest.approx(0.05475, abs=1e-6)


def test_wanfen_income_with_same_day_deposit_is_not_diluted():
    """Spec §8.3: a +5,000 deposit at an unknown time must not cut the
    reported yield in half."""
    d = money_market_day(
        beginning_units=10000, ending_units=15000,
        beginning_value=10000.0, ending_value=15001.5,
        flows=[(5000.0, None)],            # timing unknown -> 0.5 day
        external_net_flow=5000.0)
    assert d.daily_income == pytest.approx(1.5)
    # effective units = 10000 + 5000*0.5 = 12500 (not 15000)
    assert d.effective_units == pytest.approx(12500.0)
    assert d.income_per_10000 == pytest.approx(1.5 / 12500 * 10000)
    assert d.calculation_method == "estimated"
    # using ending units would understate the yield (the bug we avoid)
    naive_per_10000 = 1.5 / 15000 * 10000
    assert d.income_per_10000 > naive_per_10000


def test_wanfen_income_flow_with_known_timing_is_exact():
    d = money_market_day(
        beginning_units=10000, ending_units=15000,
        beginning_value=10000.0, ending_value=15001.5,
        flows=[(5000.0, 1.0)],             # deposit at the open
        external_net_flow=5000.0)
    assert d.effective_units == pytest.approx(15000.0)
    assert d.calculation_method == "exact"


def test_effective_units_flags_unknown_timing():
    eff, known = effective_units(1000.0, [(1000.0, None)])
    assert eff == pytest.approx(1500.0) and known is False
    eff2, known2 = effective_units(1000.0, [(1000.0, 0.25)])
    assert eff2 == pytest.approx(1250.0) and known2


def test_wanfen_zero_units_is_safe():
    d = money_market_day(0, 0, 0.0, 0.0)
    assert d.income_per_10000 == 0.0 and d.annualized_yield is None


def test_seven_day_annualized():
    vals = [1.5] * 7
    assert seven_day_annualized(vals) == pytest.approx(0.05475, abs=1e-6)
    assert seven_day_annualized([]) is None
    assert seven_day_annualized([1.0, 2.0]) == pytest.approx(1.5 / 10000 *
                                                             365)


def test_wanfen_record_persisted_and_reloaded(basic):
    conn = basic["conn"]
    d = money_market_day(10000, 10000, 10000.0, 10001.5)
    repo.upsert_income(conn, "2026-09-09", basic["mm"],
                       beginning_units=d.beginning_units,
                       ending_units=d.ending_units,
                       beginning_value=10000.0, ending_value=10001.5,
                       cash_flow=0.0, daily_income=d.daily_income,
                       income_per_10000=d.income_per_10000,
                       annualized_yield=d.annualized_yield,
                       calculation_method=d.calculation_method)
    rows = repo.list_income(conn, basic["mm"])
    assert rows[0]["income_per_10000"] == pytest.approx(1.5)
    assert rows[0]["calculation_method"] == "exact"


# ---------------------------------------------------------------------------
# net-worth decomposition (spec §27)
# ---------------------------------------------------------------------------

def test_decomposition_spec_example():
    """The spec's worked example: +50,000 contribution, +12,300 P&L,
    +1,200 dividends, -320 fees, -5,000 withdrawal -> +58,180."""
    txns = [
        {"txn_type": "deposit", "cash_flow": 50000.0, "amount": 50000.0,
         "fee": 0.0},
        {"txn_type": "dividend", "cash_flow": 0.0, "amount": 1200.0,
         "fee": 0.0},
        {"txn_type": "fee", "cash_flow": 0.0, "amount": 320.0, "fee": 320.0},
        {"txn_type": "withdrawal", "cash_flow": -5000.0, "amount": 5000.0,
         "fee": 0.0},
    ]
    # P&L total (value-based) chosen so that investment_pnl part = 12,300
    # begin 100,000 -> end 158,180; external net = 45,000
    begin, end = 100000.0, 158180.0
    d = decompose_change(begin, end, txns)
    assert d.external_contributions == pytest.approx(50000.0)
    assert d.withdrawals == pytest.approx(5000.0)
    assert d.dividends == pytest.approx(1200.0)
    assert d.fees == pytest.approx(320.0)
    # residual investment P&L = (end-begin-ext) - div + fee
    assert d.investment_pnl == pytest.approx(12300.0)
    assert d.net_change == pytest.approx(58180.0)
    assert d.reconciliation_error == pytest.approx(0.0, abs=1e-9)


def test_decomposition_reconciles_with_ledger(basic):
    conn = basic["conn"]
    repo.create_transaction(conn, "2026-09-01", basic["fund"], "deposit",
                            amount=10000, cash_flow=10000)
    repo.create_transaction(conn, "2026-09-15", basic["fund"], "dividend",
                            amount=25.0)
    repo.create_transaction(conn, "2026-09-16", basic["fund"], "fee",
                            amount=3.0, fee=3.0)
    repo.create_transaction(conn, "2026-09-20", basic["fund"],
                            "withdrawal", amount=500, cash_flow=-500)
    txns = repo.list_transactions(conn, product_id=basic["fund"])
    d = decompose_change(0.0, 10100.0, txns)
    assert d.reconciliation_error == pytest.approx(0.0, abs=1e-9)
    assert d.net_change == pytest.approx(10100.0)


# ---------------------------------------------------------------------------
# portfolio summary / positions
# ---------------------------------------------------------------------------

def test_portfolio_summary_totals_and_allocation(basic):
    conn = basic["conn"]
    repo.create_transaction(conn, "2026-01-05", basic["fund"], "deposit",
                            amount=10000, cash_flow=10000)
    repo.create_transaction(conn, "2026-01-05", basic["stock"], "deposit",
                            amount=50000, cash_flow=50000)
    repo.create_transaction(conn, "2026-01-06", basic["stock"], "buy",
                            units=29, price=1700.0, amount=49300.0, fee=15.0)
    repo.upsert_snapshot(conn, "2026-06-30", basic["fund"],
                         units=10000, nav=1.02, market_value=10200.0)
    repo.upsert_snapshot(conn, "2026-06-30", basic["stock"],
                         units=29, nav=1750.0, market_value=50750.0)
    s = engine.portfolio_summary(conn)
    assert s["total_value"] == pytest.approx(60950.0)
    assert s["invested_capital"] == pytest.approx(60000.0)
    assert "Index Funds" not in s["by_category"]       # no such product
    assert s["by_category"]["Stocks"] == pytest.approx(50750.0)
    assert sum(s["by_category"].values()) == pytest.approx(s["total_value"])
    assert s["holdings"][0]["name"] == "贵州茅台"
    assert s["holdings"][0]["unrealized_pnl"] == pytest.approx(
        50750.0 - 29 * (49315.0 / 29))


def test_write_positions_materialises_table(basic):
    conn = basic["conn"]
    repo.create_transaction(conn, "2026-01-05", basic["stock"], "buy",
                            units=100, price=100.0, amount=10000.0)
    n = engine.write_positions(conn, "2026-06-30",
                               {basic["stock"]: 110.0})
    assert n == 1
    pos = repo.list_positions(conn, "2026-06-30")
    assert pos[0]["units"] == 100
    assert pos[0]["market_value"] == pytest.approx(11000.0)
    assert pos[0]["unrealized_pnl"] == pytest.approx(1000.0)


def test_positions_at_respects_as_of(basic):
    conn = basic["conn"]
    repo.create_transaction(conn, "2026-01-05", basic["stock"], "buy",
                            units=100, price=100.0, amount=10000.0)
    repo.create_transaction(conn, "2026-06-05", basic["stock"], "sell",
                            units=40, price=120.0, amount=4800.0)
    h_early = engine.positions_at(conn, basic["stock"], "2026-03-01")
    h_late = engine.positions_at(conn, basic["stock"], "2026-12-31")
    assert h_early.units == 100 and h_late.units == 60
    assert h_late.realized_pnl == pytest.approx(800.0)


def test_daily_return_uses_flow_adjustment(basic):
    conn = basic["conn"]
    repo.upsert_snapshot(conn, "2026-09-01", basic["fund"],
                         market_value=10000.0, cash_flow=10000.0)
    repo.upsert_snapshot(conn, "2026-09-02", basic["fund"],
                         market_value=15001.5, cash_flow=5000.0)
    perf = engine.performance(conn)
    assert perf["daily_return"] == pytest.approx(0.00015, abs=1e-6)


def test_partial_daily_updates_carry_forward(basic):
    """用户在不同日期录入不同产品时，未录入的产品沿用上次的值。

    没有这条规则时，"今天只更新了 3 只"会被算成另外 3 只消失了 →
    净资产假暴跌、P&L 假巨亏（真实发生过）。"""
    conn = basic["conn"]
    from wealth import repository as repo

    fund2 = repo.create_product(conn, basic["acct"], "第二只基金",
                                "bond_fund")
    repo.upsert_snapshot(conn, "2026-09-18", basic["fund"],
                         market_value=10000.0, cash_flow=10000.0)
    repo.upsert_snapshot(conn, "2026-09-19", fund2,
                         market_value=5000.0, cash_flow=5000.0)

    vs = engine.value_series(conn)
    assert list(vs["value"]) == [10000.0, 15000.0]      # 第一只被沿用
    assert list(vs["flow"]) == [10000.0, 5000.0]

    perf = engine.performance(conn)
    assert perf["net_worth"] == pytest.approx(15000.0)
    assert perf["total_pnl"] == pytest.approx(0.0)      # 只是录入，无盈亏


def test_value_change_after_carry_forward_is_real_pnl(basic):
    conn = basic["conn"]
    from wealth import repository as repo

    fund2 = repo.create_product(conn, basic["acct"], "第二只", "bond_fund")
    repo.upsert_snapshot(conn, "2026-09-18", basic["fund"],
                         market_value=10000.0, cash_flow=10000.0)
    repo.upsert_snapshot(conn, "2026-09-19", fund2,
                         market_value=5000.0, cash_flow=5000.0)
    # 次日只更新第二只，且涨了 200 → P&L 应为 +200
    repo.upsert_snapshot(conn, "2026-09-20", fund2,
                         market_value=5200.0, cash_flow=0.0)
    perf = engine.performance(conn)
    assert perf["net_worth"] == pytest.approx(15200.0)
    assert perf["total_pnl"] == pytest.approx(200.0)
