# -*- coding: utf-8 -*-
"""EastMoney 被 WAF 挡下时，一轮只试一次。

背景：`refresh_live_prices.py` 一次循环 60 个标的。EastMoney 的 push2his
一旦把本机 IP 判定为要拦，就直接断连（不返回任何响应），而且会持续一段
时间，于是 60 个标的全都失败一次、打 60 行一模一样的报错 —— 报错内容还
是"每个标的各自失败"，掩盖了真正的原因（是整条线路被封，不是某个标的
取不到数据）。

修法是一轮只试一次：第一次失败后整轮走 Tencent kline。Tencent 是本项目
既定的日线来源（CLAUDE.md：日线对照用腾讯 K 线），所以这不是"绕过错误"，
但仍然要留下痕迹 —— 供应商记录原因，脚本把它写进 live_prices.json。

这里不碰网络：假 akshare + 假的 Tencent 抓取。
"""

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

from personal_quant.providers.akshare_market import AkShareMarketProvider


def _tencent_frame(symbol: str) -> pd.DataFrame:
    return pd.DataFrame({
        "trade_date": [pd.Timestamp("2026-09-30")],
        "open": [10.0], "close": [10.5], "high": [10.6], "low": [9.9],
        "volume": [1000.0], "amount": [None], "source": ["tencent_kline"],
    })


@pytest.fixture
def wired(monkeypatch):
    """Provider with a fake akshare and a counting Tencent fetcher."""
    calls = {"eastmoney": 0, "tencent": 0}

    def boom(**kwargs):
        calls["eastmoney"] += 1
        raise ConnectionError("('Connection aborted.', RemoteDisconnected(...))")

    monkeypatch.setitem(sys.modules, "akshare",
                        types.SimpleNamespace(stock_zh_a_hist=boom))

    def fake_tencent(self, symbol, start, end):
        calls["tencent"] += 1
        return _tencent_frame(symbol)

    monkeypatch.setattr(AkShareMarketProvider, "_fetch_daily_history_tencent",
                        fake_tencent)
    monkeypatch.setattr("personal_quant.config.require_online", lambda *a: None)
    return AkShareMarketProvider(), calls


def test_eastmoney_is_attempted_once_per_run_not_once_per_symbol(wired, capsys):
    provider, calls = wired
    for sym in ["600519.SH", "000001.SZ", "300750.SZ"]:
        df = provider.fetch_daily_history(sym, "2026-09-01", "2026-09-30")
        assert df["source"].iloc[0] == "tencent_kline"

    assert calls["eastmoney"] == 1, "每个标的都去试一次才是要修的问题"
    assert calls["tencent"] == 3, "每一次调用都必须拿到数据"

    out = capsys.readouterr().out
    assert out.count("eastmoney") == 1, f"应该只有一行，实际：{out!r}"
    assert "tencent" in out


def test_the_block_is_recorded_not_swallowed(wired):
    """不能被静默吞掉：调用方必须能查出来这一轮的数据来自哪里。"""
    provider, _ = wired
    assert provider.eastmoney_blocked is None          # 还没试过
    provider.fetch_daily_history("600519.SH", "2026-09-01", "2026-09-30")
    assert "ConnectionError" in provider.eastmoney_blocked


def test_every_call_still_returns_data_while_blocked(wired):
    """降级不等于失败：被封期间 60 个标的仍然全部要有价格。"""
    provider, calls = wired
    for _ in range(5):
        df = provider.fetch_daily_history("600519.SH", "2026-09-01",
                                          "2026-09-30")
        assert not df.empty
        assert df["symbol"].iloc[0] == "600519.SH"
    assert calls["eastmoney"] == 1


def test_a_working_eastmoney_never_touches_tencent(monkeypatch):
    """主源正常时一行都不该打印，也不该降级。"""
    calls = {"tencent": 0}

    def ok(**kwargs):
        return pd.DataFrame({
            "日期": ["2026-09-30"], "开盘": [10.0], "收盘": [10.5],
            "最高": [10.6], "最低": [9.9], "成交量": [1000], "成交额": [1e8],
            "振幅": [7.0], "涨跌幅": [5.0]})

    monkeypatch.setitem(sys.modules, "akshare",
                        types.SimpleNamespace(stock_zh_a_hist=ok))

    def fake_tencent(self, symbol, start, end):
        calls["tencent"] += 1
        return _tencent_frame(symbol)

    monkeypatch.setattr(AkShareMarketProvider, "_fetch_daily_history_tencent",
                        fake_tencent)
    monkeypatch.setattr("personal_quant.config.require_online", lambda *a: None)

    provider = AkShareMarketProvider()
    df = provider.fetch_daily_history("600519.SH", "2026-09-01", "2026-09-30")
    assert df["source"].iloc[0] == "eastmoney_push2his"
    assert calls["tencent"] == 0
    assert provider.eastmoney_blocked is None
