# -*- coding: utf-8 -*-
"""tests/forward 的共用夹具：一个不碰数据库的假 provider。

forward 引擎的全部数据接触面都收在 provider 上，所以这里替换掉它，
就能在毫秒级、无副作用地跑完整条信号→执行→落盘路径。
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

TRADING_DAYS = pd.bdate_range("2025-01-01", "2026-12-31")


@dataclass
class FakeStats:
    latest_trading_day: Optional[str] = None
    latest_bar_date: Optional[str] = None
    n_universe: int = 0
    n_features: int = 0
    n_custom_factors: int = 0
    feature_source: str = "fake"
    news_latest: Optional[str] = None
    financial_latest: Optional[str] = None
    data_snapshot_id: str = "fake-snapshot"
    consumed_factors: List[str] = field(default_factory=list)


class FakeProvider:
    """可编程的假数据源。

    - 价格：每只票一条确定性的等比序列
    - `halt`    里的票没有 T+1 行情（停牌）→ NO_TRADE
    - `limit_up` 里的票 T+1 开盘涨停 → BUY NO_TRADE
    - `limit_dn` 里的票 T+1 开盘跌停 → SELL NO_TRADE
    """

    def __init__(self, n_symbols: int = 40, n_features: int = 5,
                 start: str = "2025-01-01", end: str = "2026-12-31",
                 halt=(), limit_up=(), limit_dn=()):
        self.symbols = [f"S{i:04d}.SH" for i in range(n_symbols)]
        self.features = [f"f{i}" for i in range(n_features)]
        self.calendar = pd.bdate_range(start, end)
        self.halt = set(halt)
        self.limit_up = set(limit_up)
        self.limit_dn = set(limit_dn)
        self.stats = FakeStats()
        rng = np.random.default_rng(0)
        base = {s: 10.0 + 5.0 * ((i % 7) / 7.0)
                for i, s in enumerate(self.symbols)}
        drift = {s: rng.normal(0.0004, 0.0002) for s in self.symbols}
        px = {}
        for s in self.symbols:
            px[s] = pd.Series(
                base[s] * np.exp(np.cumsum(np.full(len(self.calendar),
                                                   drift[s]))),
                index=self.calendar)
        self._close = pd.DataFrame(px)
        # 真实的预测：与下一期收益弱相关，其余是噪声
        self._score = pd.DataFrame(rng.normal(0, 1, (len(self.calendar),
                                                     n_symbols)),
                                   index=self.calendar, columns=self.symbols)
        self.calls = {"prices": 0, "execute": 0}

    # ---------------------------------------------------------------- 日历
    def trading_calendar(self):
        return self.calendar

    def latest_trading_day(self, on_or_before=None):
        cal = self.calendar
        if on_or_before is None:
            return pd.Timestamp(cal[-1])
        sub = cal[cal <= pd.Timestamp(on_or_before)]
        return pd.Timestamp(sub[-1]) if len(sub) else None

    def latest_bar_date(self, symbols=None, on_or_before=None):
        cal = self.calendar
        if on_or_before is not None:
            cal = cal[cal <= pd.Timestamp(on_or_before)]
        return pd.Timestamp(cal[-1]) if len(cal) else None

    # ---------------------------------------------------------------- 数据
    def universe(self, date):
        self.stats.n_universe = len(self.symbols)
        return list(self.symbols)

    def feature_matrix(self, date, symbols):
        d = pd.Timestamp(date)
        rows = self._close.loc[[d]] if d in self._close.index else \
            self._close.iloc[[0]]
        out = pd.DataFrame(
            {f: rows.iloc[0].to_numpy() * (i + 1) for i, f in
             enumerate(self.features)}, index=self.symbols)
        self.stats.n_features = len(self.features)
        return out.reindex(symbols)

    def custom_factors(self, date, symbols):
        d = pd.Timestamp(date)
        vals = {"amount_20": 1.0, "momentum_60": 0.5,
                "announcement_count_20d": 1.0}
        out = pd.DataFrame({k: np.full(len(symbols), v)
                            for k, v in vals.items()}, index=symbols)
        self.stats.n_custom_factors = out.shape[1]
        self.stats.consumed_factors = list(vals)
        return out

    def predict(self, features, custom):
        """确定性打分：截面排名稳定，便于断言。"""
        n = len(features)
        return pd.Series(np.linspace(1.0, 0.0, n), index=features.index)

    def prices(self, symbols, date):
        self.calls["prices"] += 1
        d = pd.Timestamp(date)
        if d not in self._close.index:
            return pd.Series(dtype=float)
        s = self._close.loc[d].reindex(list(symbols)).dropna()
        return s

    def names(self, symbols):
        return {s: f"名称{s[:4]}" for s in symbols}

    # ---------------------------------------------------------------- 执行
    def execute(self, symbol, signal_date, side, shares, limit_threshold):
        self.calls["execute"] += 1
        from personal_quant.strategy.execution import (OrderResult,
                                                       TradeStatus)
        nxt = self.calendar[self.calendar > pd.Timestamp(signal_date)]
        if not len(nxt):
            return OrderResult(symbol, TradeStatus.NO_TRADE, 0, None,
                               "no T+1 bar (suspended/halted)")
        t1 = pd.Timestamp(nxt[0])
        if symbol in self.halt:
            return OrderResult(symbol, TradeStatus.NO_TRADE, 0, None,
                               "no T+1 bar (suspended/halted)")
        prev = self._close.loc[pd.Timestamp(signal_date), symbol]
        op = self._close.loc[t1, symbol]
        if side == "BUY" and symbol in self.limit_up:
            return OrderResult(symbol, TradeStatus.NO_TRADE, 0, None,
                               "limit up")
        if side == "SELL" and symbol in self.limit_dn:
            return OrderResult(symbol, TradeStatus.NO_TRADE, 0, None,
                               "limit down")
        signed = shares if side == "BUY" else -shares
        return OrderResult(symbol, TradeStatus.FILLED, signed, float(op), "")

    # ---------------------------------------------------------------- 其它
    def benchmark_nav(self, symbol, start, end):
        s = self._close.mean(axis=1)
        s = s[(s.index >= pd.Timestamp(start)) & (s.index <= pd.Timestamp(end))]
        return s / s.iloc[0]

    def financial_availability(self, symbols):
        return pd.DataFrame(columns=["symbol", "availability_date"])

    def news_availability(self, symbols, on_or_before=None):
        d = pd.Timestamp(on_or_before or self.calendar[-1])
        return pd.DataFrame({"symbol": list(symbols),
                             "published_at": [d] * len(symbols)})


@pytest.fixture
def fake_provider():
    return FakeProvider()


@pytest.fixture
def pl_cfg(tmp_path):
    """一份指向临时目录的 paper_live 配置（不碰仓库里的真配置）。"""
    from paper_live.config import load_config
    cfg = load_config()
    cfg["paper_live"] = dict(cfg["paper_live"])
    cfg["paper_live"]["paths"] = dict(cfg["paper_live"]["paths"])
    cfg["paper_live"]["paths"]["root"] = str(tmp_path / "forward_holdout")
    cfg["paper_live"]["paths"]["validation_root"] = str(
        tmp_path / "validation")
    return cfg
