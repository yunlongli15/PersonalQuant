# -*- coding: utf-8 -*-
"""Part B 的标题必须由数据说了算。

原来的输出写死了"canonical vs EastMoney"，但 `fetch_daily_history` 在本机
几乎总是回退到腾讯 K 线（东财 push2his 持续封禁本机 IP）。2026-09-05 那份
报告是人手核对后发现并写明"实为腾讯"的 —— 脚本自己打印的那一行从头到尾
都是错的。所以现在：供应商名从数据里读，逐只记录，标题据此生成。

这些测试不碰 DuckDB（用户在跑 financial_update 时会独占它）。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

from scripts.crosscheck_qlib import (
    SOURCE_LABELS, describe_sources, part_b, source_mix,
)


def _row(symbol, source=None, error=None):
    if error:
        return {"symbol": symbol, "n_days": 0, "error": error}
    return {"symbol": symbol, "n_days": 484, "source": source}


# ---------------------------------------------------------------------------
# 标题跟着数据走
# ---------------------------------------------------------------------------

def test_header_names_tencent_when_tencent_served():
    """这就是原来那个 bug：数据是腾讯的，标题却写 EastMoney。"""
    rows = [_row("600519.SH", "tencent_kline"),
            _row("000001.SZ", "tencent_kline")]
    desc = describe_sources(rows)
    assert "Tencent kline" in desc
    assert "EastMoney" not in desc


def test_header_names_eastmoney_when_eastmoney_served():
    rows = [_row("600519.SH", "eastmoney_push2his")]
    assert "EastMoney push2his" in describe_sources(rows)


def test_mixed_sources_are_all_reported():
    """部分回退时必须两边都报，不能只报一家。"""
    rows = [_row("600519.SH", "eastmoney_push2his"),
            _row("000001.SZ", "tencent_kline"),
            _row("600036.SH", "tencent_kline")]
    desc = describe_sources(rows)
    assert "Tencent kline 2" in desc and "EastMoney push2his 1" in desc


def test_failed_symbols_are_not_counted_as_a_vendor():
    rows = [_row("600519.SH", "tencent_kline"),
            _row("000001.SZ", error="ConnectionError")]
    mix = source_mix(rows)
    assert mix["tencent_kline"] == 1
    assert mix["fetch_failed"] == 1
    assert describe_sources(rows).count("Tencent kline") == 1


def test_an_unknown_source_is_shown_as_is_not_guessed():
    assert "weird_source" in describe_sources([_row("600519.SH", "weird_source")])


def test_empty_input_does_not_crash():
    assert describe_sources([]) == "no data"
    assert source_mix([]) == {}


def test_every_label_points_at_a_real_source_value():
    """标签表不能出现 provider 永远不会返回的名字。"""
    assert set(SOURCE_LABELS) <= {"eastmoney_push2his", "tencent_kline"}


# ---------------------------------------------------------------------------
# part_b 真的把来源写进每一行（用假的 provider + 假的连接，不碰 DuckDB）
# ---------------------------------------------------------------------------

class _FakeResult:
    def __init__(self, df):
        self._df = df

    def fetch_df(self):
        return self._df


class _FakeConn:
    def __init__(self, df):
        self._df = df

    def execute(self, *a, **kw):
        return _FakeResult(self._df)


class _FakeProvider:
    """逐只返回不同来源，模拟"部分回退"。"""

    def __init__(self, sources):
        self._sources = sources

    def fetch_daily_history(self, symbol, start, end):
        src = self._sources[symbol]
        return pd.DataFrame({
            "trade_date": [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03")],
            "close": [10.0, 10.5],
            "source": [src, src],
        })


BASE = pd.DataFrame({"trade_date": [pd.Timestamp("2024-01-02"),
                                    pd.Timestamp("2024-01-03")],
                     "close": [10.0, 10.5]})


def test_part_b_records_the_source_on_every_row(monkeypatch):
    sources = {f"{c}.SH" if c.startswith(("6", "68")) else f"{c}.SZ":
               ("eastmoney_push2his" if i == 0 else "tencent_kline")
               for i, c in enumerate(["600519", "000001"])}
    monkeypatch.setattr("scripts.crosscheck_qlib.PART_B_STOCKS",
                        ["600519", "000001"])
    monkeypatch.setattr("scripts.crosscheck_qlib.AkShareMarketProvider",
                        lambda: _FakeProvider(sources), raising=False)
    monkeypatch.setattr("personal_quant.providers.akshare_market."
                        "AkShareMarketProvider", lambda: _FakeProvider(sources))
    monkeypatch.setattr("scripts.crosscheck_qlib.db.connect",
                        lambda *a, **kw: _FakeConn(BASE))

    out = part_b()
    got = {r["symbol"]: r["source"] for r in out["rows"]}
    assert got == {"600519.SH": "eastmoney_push2his",
                   "000001.SZ": "tencent_kline"}
    # 标题用的就是这个 mix
    assert "Tencent kline 1" in describe_sources(out["rows"])
