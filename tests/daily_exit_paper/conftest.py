# -*- coding: utf-8 -*-
"""tests/daily_exit_paper 的共用夹具。

`FakeMarket` 把整条数据接触面（交易日历 / OHLC / 信号快照 / 预测 / 价格历史）
都替换成可控的合成数据，于是**整个状态机可以在毫秒级、零副作用地跑完整条
路径**，而且每个场景的手工数字都能直接对照。

引擎的数据访问全部走 `market` 对象，就是为了让这件事成立。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest


def bar(o, h, l, c=None):
    """OHLC 一条。c 省略时用 open 当收盘。"""
    return {"open": float(o), "high": float(h), "low": float(l),
            "close": float(c if c is not None else o)}


class FakeMarket:
    def __init__(self, sessions, bars, signals=None, forecasts=None,
                 history=None):
        self._cal = pd.DatetimeIndex([pd.Timestamp(d) for d in sessions])
        self._bars = {(_k(s), pd.Timestamp(d)): v
                      for (s, d), v in bars.items()}
        self._signals = {pd.Timestamp(d): v
                         for d, v in (signals or {}).items()}
        self._forecasts = {pd.Timestamp(d): v
                           for d, v in (forecasts or {}).items()}
        self._history = history

    def set_bar(self, symbol, date, o, h, l, c=None):
        """事后往某一天补一条 bar。

        测试需要"先看到挂单的限价、再决定 T+1 怎么走"，这个入口让场景
        可以分两步搭起来，而不必去猜引擎算出的限价。
        """
        self._bars[(symbol, pd.Timestamp(date))] = bar(o, h, l, c)
        return self

    # ---- 数据接触面 -----------------------------------------------------
    def calendar(self):
        return self._cal

    def bars(self, symbols, date):
        d = pd.Timestamp(date)
        return {s: self._bars[(s, d)] for s in symbols
                if (s, d) in self._bars}

    def closes(self, symbols, as_of):
        a = pd.Timestamp(as_of)
        out = {}
        for s in symbols:
            dates = sorted(d for (sym, d) in self._bars
                           if sym == s and d <= a)
            if dates:
                out[s] = self._bars[(s, dates[-1])]["close"]
        return out

    def signals(self, session):
        return self._signals.get(pd.Timestamp(session))

    def forecasts(self, session, horizon):
        return self._forecasts.get(pd.Timestamp(session), {})

    def price_history(self, symbols, as_of):
        if self._history is not None:
            return self._history.loc[:pd.Timestamp(as_of), list(symbols)]
        a = pd.Timestamp(as_of)
        dates = self._cal[self._cal <= a]
        cols = {}
        for s in symbols:
            closes = []
            for d in dates:
                b = self._bars.get((s, d))
                closes.append(np.nan if b is None else b["close"])
            cols[s] = closes
        return pd.DataFrame(cols, index=dates)


def _k(s):
    return s


def make_signals(date, symbols, predictions=None, start_rank=1):
    """信号快照。`predictions` 里没给的标的用递减默认值补上。"""
    given = dict(predictions or {})
    df = pd.DataFrame({
        "symbol": list(symbols),
        "prediction": [given.get(s, 1.0 - i * 0.01)
                       for i, s in enumerate(symbols)],
        "raw_rank": list(range(start_rank, start_rank + len(symbols))),
        "signal_date": pd.Timestamp(date),
        "name": [f"名称{s[:4]}" for s in symbols],
    })
    return df.sort_values("prediction", ascending=False).reset_index(drop=True)


def flat_history(symbols, sessions, price=10.0, drift=0.0, wiggle=0.005):
    """略带锯齿的价格历史。

    必须有非零波动：`_daily_vol` 为 0 时候选会被判 `no_vol` 跳过
    （停牌/无波动不该被当成可交易标的）。锯齿只是为了让 vol 有定义，
    不改变"价格基准"这个用途。
    """
    dates = pd.DatetimeIndex([pd.Timestamp(d) for d in sessions])
    data = {}
    for i, s in enumerate(symbols):
        base = price + i
        vals = []
        for j in range(len(dates)):
            v = base * (1.0 + drift) ** j
            v *= (1.0 + wiggle) if j % 2 else (1.0 - wiggle)
            vals.append(v)
        data[s] = vals
    return pd.DataFrame(data, index=dates)


@pytest.fixture
def cfg():
    from daily_exit_paper import config as C

    return C.load_config()


@pytest.fixture
def s_cfg(cfg):
    from daily_exit_paper import config as C

    return C.validate(cfg)


@pytest.fixture
def store(tmp_path):
    from daily_exit_paper.store import ExperimentStore

    return ExperimentStore(tmp_path / "exp").ensure()


@pytest.fixture
def calendar_session():
    """交易日历：连续 8 个工作日。"""
    return list(pd.bdate_range("2026-10-01", periods=8))


#: 主板标的（无板块门槛），保证本金 6.6 万时仍可买。
SYMS = ["600001.SH", "600002.SH", "600003.SH", "600004.SH"]

#: 当日盈亏等需要"上一个交易日"时的公共日历。
SESSIONS = list(pd.bdate_range("2026-10-01", periods=8))


def build_market(bars, signals=None, forecasts=None, symbols=None,
                 price=10.0, sessions=None):
    """造一个可直接喂给引擎的假市场。

    价格历史固定为 80 个交易日（`_daily_vol` 需要 60 日窗口），
    所以候选不会被 `no_vol` 跳过。
    """
    sessions = list(sessions or SESSIONS)
    hist_dates = pd.bdate_range(end=sessions[-1], periods=80)
    return FakeMarket(sessions, bars, signals, forecasts,
                      history=flat_history(symbols or SYMS, hist_dates,
                                           price=price))


def run_to(engine, cfg, store, market, run_date, capital=None, **kw):
    return engine.run(run_date=run_date, capital=capital, cfg=cfg,
                      store=store, market=market, **kw)


def day(cal, i):
    return pd.Timestamp(cal[i])
