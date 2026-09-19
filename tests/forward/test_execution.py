# -*- coding: utf-8 -*-
"""§8 / §46：T+1 开盘执行、停牌/涨跌停 NO_TRADE、先卖后买、现金非负。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

from paper_live.execution import build_orders, execute_orders
from personal_quant.strategy.costs import TransactionCostModel

CM = TransactionCostModel(commission_rate=0.00025, min_commission=5.0,
                          stamp_duty=0.0005, transfer_fee=0.00001,
                          slippage=0.0005)


def _orders(provider, tw, holdings, prices, nav=200_000.0, cash=200_000.0):
    preds = pd.Series({s: 1.0 / (i + 1)
                       for i, s in enumerate(provider.symbols)})
    return build_orders(tw, preds, provider.names(provider.symbols), prices,
                        holdings, nav, cash, CM)


def test_fill_happens_at_t1_not_at_signal(fake_provider):
    p = fake_provider
    d = p.calendar[10]
    tw = {s: 0.10 for s in p.symbols[:4]}
    prices = p.prices(p.symbols, d).to_dict()
    res = execute_orders(_orders(p, tw, {}, prices), {}, 200_000.0, d,
                         0.095, CM, executor=p.execute)
    assert res.n_trades == 4
    fills = res.orders[res.orders["status"] == "FILLED"]
    t1 = p.calendar[11]
    for _, r in fills.iterrows():
        assert r["fill_price"] == pytest.approx(p._close.loc[t1, r["symbol"]])


def test_suspended_symbol_is_no_trade_with_reason(fake_provider):
    p = fake_provider
    d = p.calendar[10]
    p.halt = {p.symbols[0]}
    prices = p.prices(p.symbols, d).to_dict()
    res = execute_orders(_orders(p, {p.symbols[0]: 0.5}, {}, prices), {},
                         200_000.0, d, 0.095, CM, executor=p.execute)
    row = res.orders.iloc[0]
    assert row["status"] == "NO_TRADE"
    assert "suspended" in row["reason"] or "no T+1" in row["reason"]


def test_limit_up_blocks_buy_limit_down_blocks_sell(fake_provider):
    p = fake_provider
    d = p.calendar[10]
    p.limit_up = {p.symbols[0]}
    p.limit_dn = {p.symbols[1]}
    prices = p.prices(p.symbols, d).to_dict()
    buys = execute_orders(_orders(p, {p.symbols[0]: 0.3}, {}, prices), {},
                          200_000.0, d, 0.095, CM, executor=p.execute)
    assert buys.orders.iloc[0]["reason"] == "limit up"
    holds = {p.symbols[1]: {"shares": 1000, "price": 10.0}}
    sells = execute_orders(_orders(p, {}, holds, prices), holds, 10_000.0, d,
                           0.095, CM, executor=p.execute)
    assert sells.orders.iloc[0]["reason"] == "limit down"
    assert sells.orders.iloc[0]["status"] == "NO_TRADE"


def test_sells_execute_before_buys(fake_provider):
    """先卖后买：否则按代码顺序执行时中间现金会变负。"""
    p = fake_provider
    d = p.calendar[10]
    prices = p.prices(p.symbols, d).to_dict()
    holds = {p.symbols[0]: {"shares": 5000, "price": prices[p.symbols[0]]}}
    tw = {p.symbols[1]: 0.9}          # 卖掉 0 号，买入 1 号
    res = execute_orders(_orders(p, tw, holds, prices, nav=60_000.0,
                                 cash=1_000.0), holds, 1_000.0, d, 0.095, CM,
                         executor=p.execute)
    order = list(res.orders["action"])
    assert order.index("SELL") < order.index("BUY")


def test_cash_never_negative_after_a_full_rebalance(fake_provider):
    p = fake_provider
    d = p.calendar[10]
    prices = p.prices(p.symbols, d).to_dict()
    tw = {s: 0.95 / 20 for s in p.symbols[:20]}
    res = execute_orders(_orders(p, tw, {}, prices, nav=500_000.0,
                                 cash=500_000.0), {}, 500_000.0, d, 0.095, CM,
                         executor=p.execute)
    assert res.cash >= 0


def test_no_orders_when_already_at_target(fake_provider):
    p = fake_provider
    d = p.calendar[10]
    prices = p.prices(p.symbols, d).to_dict()
    tw = {p.symbols[0]: 0.10}
    nav = 100_000.0
    shares = int(0.10 * nav / prices[p.symbols[0]] // 100 * 100)
    holds = {p.symbols[0]: {"shares": shares, "price": prices[p.symbols[0]]}}
    orders = _orders(p, tw, holds, prices, nav=nav)
    assert orders[0].estimated_shares == 0
    assert orders[0].action == "HOLD"


def test_a_gap_up_never_overdraws_the_account(fake_provider):
    """下单按 T 日收盘价算，成交在 T+1 开盘。跳空高开时钱不够必须减量，
    绝不能把现金打成负数。"""
    p = fake_provider
    d = p.calendar[10]
    t1 = p.calendar[11]
    # 人为制造一次 +20% 的跳空
    p._close.loc[t1] = p._close.loc[t1] * 1.20
    prices = p.prices(p.symbols, d).to_dict()
    tw = {s: 0.95 / 20 for s in p.symbols[:20]}
    res = execute_orders(_orders(p, tw, {}, prices, nav=500_000.0,
                                 cash=500_000.0), {}, 500_000.0, d, 0.095, CM,
                         executor=p.execute)
    assert res.cash >= -1e-6, f"现金被透支：{res.cash}"


def test_insufficient_cash_is_recorded_as_no_trade(monkeypatch, fake_provider):
    p = fake_provider
    d = p.calendar[10]
    prices = p.prices(p.symbols, d).to_dict()
    # 只给 100 元现金，却要买 5 万元
    res = execute_orders(_orders(p, {p.symbols[0]: 0.5}, {}, prices,
                                 nav=100_000.0, cash=100.0),
                         {}, 100.0, d, 0.095, CM, executor=p.execute)
    row = res.orders.iloc[0]
    assert row["status"] == "NO_TRADE"
    assert row["reason"] == "insufficient cash"
    assert res.cash == pytest.approx(100.0)
