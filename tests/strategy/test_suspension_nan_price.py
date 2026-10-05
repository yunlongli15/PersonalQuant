# -*- coding: utf-8 -*-
"""停牌股的 NULL 价格必须走 NO_TRADE，不能变成 NaN 成交。

2026-10-06 实测事故：`daily_bars` 里停牌日是**有行但 OHLC 全为 NULL**
的（全库 57.7 万行，约 3.2%）。`float(NaN)` 不抛错，于是
`execute_order` 里所有 `if ... is None` 的守卫**全部形同虚设**：

- 守卫写的是 `if open_price is None`，而实际拿到的是 `nan`；
- `nan >= prev_close * 1.1` 恒为 False，涨跌停检查也不拦；
- 订单以 FILLED + NaN 价返回，`cash += -value - fee` 把现金变成 NaN，
  **此后每一天的 NAV 都是 NaN**，回测却一声不吭地跑完。

这里的断言盯两件事：守卫真的会触发；NAV 永远不会因为停牌变成 NaN。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import math

import pandas as pd
import pytest

from personal_quant.strategy.execution import (_price,
                                               t1_open_and_prev_close,
                                               execute_order, TradeStatus)
from personal_quant import db


# ---------------------------------------------------------------------------
# _price：NaN / None / 正常值 / 垃圾值
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expect", [
    (None, None),
    (float("nan"), None),
    (12.5, 12.5),
    (0.0, 0.0),
    (-1.0, -1.0),
    ("13.25", 13.25),
    ("abc", None),
])
def test_price_normalises_nan_to_none(raw, expect):
    assert _price(raw) == expect


def test_nan_open_does_not_become_a_fill():
    """核心回归：T+1 开盘价为 NaN 时必须是 NO_TRADE。"""
    # 找一只真实存在、且在某个交易日 open 为 NULL 的票
    row = db.query("""
        SELECT b.symbol, b.trade_date
        FROM daily_bars b
        WHERE b.open IS NULL AND b.volume IS NULL
          AND b.symbol LIKE '6%'
          AND b.trade_date >= DATE '2020-01-01'
        LIMIT 1
    """)
    if not row:
        pytest.skip("库里找不到停牌样例")
    sym = row[0]["symbol"]
    prev = db.query(
        "SELECT trade_date FROM trading_calendar WHERE is_open "
        "AND trade_date < ? ORDER BY trade_date DESC LIMIT 1",
        [row[0]["trade_date"]])
    if not prev:
        pytest.skip("没有前一交易日")
    signal = pd.Timestamp(prev[0]["trade_date"])
    res = execute_order(sym, signal, "SELL", 100, 0.10)
    assert res.status == TradeStatus.NO_TRADE, (
        f"{sym} 在 {row[0]['trade_date']} 停牌（open 为 NULL），"
        f"却返回了 {res.status}，成交价 {res.fill_price!r}")
    assert res.fill_price is None or not math.isnan(float(res.fill_price))


def test_no_nan_can_ever_escape_as_a_fill_price():
    """扫一批真实停牌样例，任何一个都不许带 NaN 价成交。"""
    rows = db.query("""
        SELECT symbol, trade_date FROM daily_bars
        WHERE open IS NULL AND volume IS NULL
          AND trade_date >= DATE '2021-01-01'
        USING SAMPLE 40 ROWS
    """)
    bad = []
    for r in rows:
        prev = db.query(
            "SELECT trade_date FROM trading_calendar WHERE is_open "
            "AND trade_date < ? ORDER BY trade_date DESC LIMIT 1",
            [r["trade_date"]])
        if not prev:
            continue
        res = execute_order(r["symbol"], pd.Timestamp(prev[0]["trade_date"]),
                            "BUY", 100, 0.10)
        if res.fill_price is not None and math.isnan(float(res.fill_price)):
            bad.append((r["symbol"], str(r["trade_date"])))
    assert not bad, f"以下停牌样例仍以 NaN 价成交：{bad[:5]}"


def test_t1_lookup_returns_none_not_nan_for_suspended():
    """取价函数本身就该把 NULL 变成 None（守卫才有东西可拦）。"""
    rows = db.query("""
        SELECT symbol, trade_date FROM daily_bars
        WHERE open IS NULL AND volume IS NULL
          AND trade_date >= DATE '2021-01-01'
        USING SAMPLE 20 ROWS
    """)
    checked = 0
    for r in rows:
        prev = db.query(
            "SELECT trade_date FROM trading_calendar WHERE is_open "
            "AND trade_date < ? ORDER BY trade_date DESC LIMIT 1",
            [r["trade_date"]])
        if not prev:
            continue
        _t1, op, _pc = t1_open_and_prev_close(
            r["symbol"], pd.Timestamp(prev[0]["trade_date"]))
        checked += 1
        assert op is None or not math.isnan(op), (
            f"{r['symbol']} 停牌日取到 open={op!r}，应为 None")
    if checked == 0:
        pytest.skip("没有可检查的样例")


# ---------------------------------------------------------------------------
# 端到端：回测 NAV 永远不该出现 NaN
# ---------------------------------------------------------------------------

def test_backtest_nav_has_no_nan():
    """用一段包含停牌股的行情跑一个最小回测，NAV 不许有 NaN。"""
    from personal_quant.strategy.backtest import MonthlyBacktest
    from personal_quant.strategy.costs import TransactionCostModel
    import yaml

    cfg_path = Path(__file__).resolve().parents[2] / "config" / "strategy_v1.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    cost = TransactionCostModel.from_config(cfg)

    # 直接持有 001314.SZ（2025-09-29 ~ 2025-10-17 停牌）看 NAV 会不会 NaN
    sym = "001314.SZ"
    got = db.query("SELECT COUNT(*) c FROM daily_bars WHERE symbol=? "
                   "AND open IS NULL", [sym])
    if not got or got[0]["c"] == 0:
        pytest.skip("样例股票已不在库中")

    def predictor(date, symbols):
        # 在引擎给的股票池里只给这一只高分 —— 把停牌暴露到最大
        return pd.Series({sym: 1.0}, index=[sym])

    bt = MonthlyBacktest(cfg, cost, 1_000_000.0)
    res = bt.run("2025-06-02", "2025-12-31", predictor, verbose=False)
    assert res.nav.notna().all(), (
        f"NAV 出现 {int(res.nav.isna().sum())} 个 NaN，"
        f"首个 {res.nav[res.nav.isna()].index[0]}")
