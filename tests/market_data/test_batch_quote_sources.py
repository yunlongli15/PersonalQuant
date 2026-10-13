# -*- coding: utf-8 -*-
"""批量行情两个源：解析、单位归一、以及"别把别的 session 当今天"。

全部离线。腾讯和新浪的返回都是**已经被实测核对过**的形状（见
providers/batch_quote.py 的模块说明），这里的假数据照那个形状造，
不照文档猜。
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from personal_quant.errors import FetchError  # noqa: E402
from personal_quant.providers import batch_quote as bq  # noqa: E402


# ---------------------------------------------------------------------------
# payload builders (mirror the REAL wire format)
# ---------------------------------------------------------------------------

def tencent_line(code="sh600519", name="贵州茅台", close="1288.00",
                 prev="1263.00", open_="1262.95", high="1288.00",
                 low="1261.00", lots="31556", amount_wan="404286",
                 stamp="20261012161454"):
    """`v_<code>="1~名称~code~现价~昨收~今开~...~量(手)~...~时间~...~高~低~...~额(万元)~"`"""
    f = [""] * 38
    f[1], f[2] = name, code[2:]
    f[3], f[4], f[5], f[6] = close, prev, open_, lots
    f[30], f[33], f[34], f[37] = stamp, high, low, amount_wan
    return f'v_{code}="' + "~".join(f) + '";'


def sina_line(code="sh600519", name="贵州茅台", open_="1262.950",
              prev="1263.000", close="1288.000", high="1288.000",
              low="1261.000", shares="3155604", amount_yuan="4042857559.000",
              date="2026-10-12", time_="15:34:58", fields=34):
    """`var hq_str_<code>="名称,今开,昨收,现价,最高,最低,...(34/39 段)..."`"""
    f = [""] * fields
    f[0] = name
    f[1], f[2], f[3], f[4], f[5] = open_, prev, close, high, low
    f[8], f[9] = shares, amount_yuan
    f[30], f[31] = date, time_
    return f'var hq_str_{code}="' + ",".join(f) + '";'


# ---------------------------------------------------------------------------
# parsing + unit normalisation
# ---------------------------------------------------------------------------

def test_tencent_parses_into_real_units():
    rows, bad = bq._parse_tencent(tencent_line())
    assert not bad
    r = rows[0]
    assert r["symbol"] == "600519.SH"
    assert r["close"] == 1288.00 and r["prev_close"] == 1263.00
    # 腾讯给的是 手 / 万元，出口必须是 股 / 元
    assert r["volume_shares"] == pytest.approx(31_556 * 100)
    assert r["amount_yuan"] == pytest.approx(404_286 * 1e4)
    assert r["quote_time"] == "20261012161454"
    assert r["source"] == "tencent_batch_quote"


def test_tencent_volume_unit_depends_on_the_board():
    """科创板（688/689）腾讯报的是**股**，其余板块报的是**手**。

    这个差异是被第二个源逼出来的（2026-10-14）：统一乘 100 会让 621 只
    科创板标的的 volume 大 100 倍。证据是成交额 —— 两个源对 688001.SH
    的成交额完全一致（6.494e8 元），而 成交额 ÷ 收盘价 ≈ 1.17e7 股，
    与新浪的 12,123,933 吻合、与 `f6 × 100` 差两个数量级。
    """
    assert bq._volume_unit("688001.SH") == 1.0
    assert bq._volume_unit("689009.SH") == 1.0
    assert bq._volume_unit("600519.SH") == 100.0
    assert bq._volume_unit("300750.SZ") == 100.0
    assert bq._volume_unit("920000.BJ") == 100.0

    star, _ = bq._parse_tencent(tencent_line(code="sh688001", lots="12123933"))
    main, _ = bq._parse_tencent(tencent_line(code="sh600519", lots="31556"))
    assert star[0]["volume_shares"] == pytest.approx(12_123_933)
    assert main[0]["volume_shares"] == pytest.approx(3_155_600)


def test_sina_parses_into_the_same_contract():
    rows, bad = bq._parse_sina(sina_line())
    assert not bad
    r = rows[0]
    assert r["symbol"] == "600519.SH"
    assert r["close"] == 1288.000 and r["prev_close"] == 1263.000
    # 新浪给的就是 股 / 元 —— 归一之后两个源同一套单位
    assert r["volume_shares"] == pytest.approx(3_155_604)
    assert r["amount_yuan"] == pytest.approx(4_042_857_559.0)
    # 日期 + 时间合成与腾讯同格式的戳
    assert r["quote_time"] == "20261012153458"
    assert r["source"] == "sina_hq"


def test_the_two_sources_agree_on_every_price_field():
    """同样一条 bar，两条解析路径必须给出同样的价格与数量。

    这是"每个 chunk 各自回退"能成立的前提 —— 混起来用才可以。
    """
    t, _ = bq._parse_tencent(tencent_line(
        close="1288.00", prev="1263.00", open_="1262.95", high="1288.00",
        low="1261.00", lots="31556", amount_wan="404286"))
    s, _ = bq._parse_sina(sina_line(
        close="1288.000", prev="1263.000", open_="1262.950", high="1288.000",
        low="1261.000", shares="3155600", amount_yuan="4042860000.000"))
    for a, b in (("close", "close"), ("prev_close", "prev_close"),
                 ("open", "open"), ("high", "high"), ("low", "low"),
                 ("volume_shares", "volume_shares"),
                 ("amount_yuan", "amount_yuan")):
        assert t[0][a] == pytest.approx(s[0][b]), a


def test_sina_handles_bse_field_variance():
    """北交所是 39 段、沪深的 34 段 —— 只差尾巴，一个解析器要全吃下。"""
    rows, bad = bq._parse_sina(sina_line(code="bj920000", name="安徽凤凰",
                                         close="13.830", date="2026-10-13",
                                         fields=39))
    assert not bad and rows[0]["symbol"] == "920000.BJ"
    assert rows[0]["quote_time"] == "20261013153458"


def test_empty_sina_payload_is_skipped_not_zero_filled():
    """查不到的代码新浪返回空串。绝不能当成"价格 0"的有效 bar。"""
    rows, bad = bq._parse_sina('var hq_str_sh600519="";')
    assert rows == [] and bad == ["sh600519"]


def test_symbol_conversion_rejects_non_a_share_codes():
    assert bq._symbol_of("sh600519") == "600519.SH"
    assert bq._symbol_of("bj920000") == "920000.BJ"
    assert bq._symbol_of("sh000300") == "000300.SH"   # 指数伪标的留给下游排除
    assert bq._symbol_of("hk00700") is None
    assert bq._symbol_of("sh60051") is None
    assert bq._symbol_of("sh60051X") is None


# ---------------------------------------------------------------------------
# the stale-session guard
# ---------------------------------------------------------------------------

def _patch_sources(monkeypatch, tencent_lines, sina_lines):
    monkeypatch.setattr(bq, "_SOURCES", (
        bq._Source("tencent_batch_quote", "https://t/", {}, "utf-8",
                   500, lambda text: (bq._parse_tencent(text))),
        bq._Source("sina_hq", "https://s/", {}, "utf-8",
                   800, lambda text: (bq._parse_sina(text))),
    ))

    class Resp:
        def __init__(self, text):
            self.text, self.status_code, self.encoding = text, 200, "utf-8"

    def fake_get(url, headers=None, timeout=None):
        lines = tencent_lines if url.startswith("https://t/") else sina_lines
        return Resp("\n".join(lines))

    monkeypatch.setattr(bq.requests, "get", fake_get)


def test_rows_from_another_session_are_dropped(monkeypatch):
    """新浪会一直供应**退市股最后一次成交**的快照。

    实测 2026-10-13：000004.SZ 国华退 返回的戳是 20260713，四个价格全
    非零、成交量也正常 —— 它能原样通过"是不是停牌"的检查（停牌股是
    OHLC 全 0），然后以七月的价格被写成当天的 bar。
    """
    _patch_sources(monkeypatch,
                   [tencent_line(code="sh600519"),
                    tencent_line(code="sz000001", name="平安银行",
                                 stamp="20261012151000")],
                   [])
    b = bq.BatchQuoteProvider(attempts=1).fetch_quotes(
        ["600519.SH", "000001.SZ", "000004.SZ"])
    # 补抓的三只在腾讯里都有；再造一条"退市残留"由新浪补上
    _patch_sources(monkeypatch,
                   [tencent_line(code="sh600519"),
                    tencent_line(code="sz000001", name="平安银行",
                                 stamp="20261012151000")],
                   [sina_line(code="sz000004", name="国华退", close="0.510",
                              prev="0.460", open_="0.510", high="0.510",
                              low="0.510", shares="3488617",
                              date="2026-07-13", time_="16:34:30")])
    b = bq.BatchQuoteProvider(attempts=1).fetch_quotes(
        ["600519.SH", "000001.SZ", "000004.SZ"])
    assert "000004.SZ" not in set(b.quotes["symbol"]), "退市残留被当成今天了"
    assert b.trade_date == "20261012"
    assert any("20260713" in f for f in b.failures)


def test_a_batch_entirely_from_another_session_is_refused(monkeypatch):
    _patch_sources(monkeypatch, [], [])
    monkeypatch.setattr(bq, "_SOURCES", (
        bq._Source("tencent_batch_quote", "https://t/", {}, "utf-8", 500,
                   bq._parse_tencent),))
    monkeypatch.setattr(bq.requests, "get", lambda *a, **k: type(
        "R", (), {"text": "", "status_code": 200, "encoding": "utf-8"})())
    with pytest.raises(FetchError):
        bq.BatchQuoteProvider(attempts=1).fetch_quotes(["600519.SH"])


# ---------------------------------------------------------------------------
# fallback
# ---------------------------------------------------------------------------

def test_falls_back_to_sina_when_tencent_is_down(monkeypatch):
    _patch_sources(monkeypatch,
                   ["<html>nope</html>"],          # 腾讯返回垃圾
                   [sina_line(code="sh600519"),
                    sina_line(code="sz000001", name="平安银行")])
    b = bq.BatchQuoteProvider(attempts=1).fetch_quotes(
        ["600519.SH", "000001.SZ"])
    assert len(b.quotes) == 2
    assert b.sources == {"sina_hq": 2}
    assert b.fallback_reason and "tencent" in b.fallback_reason
    assert set(b.quotes["source"]) == {"sina_hq"}


def test_tencent_is_used_when_it_works(monkeypatch):
    _patch_sources(monkeypatch,
                   [tencent_line(code="sh600519"),
                    tencent_line(code="sz000001", name="平安银行")],
                   [sina_line(code="sh600519")])
    b = bq.BatchQuoteProvider(attempts=1).fetch_quotes(
        ["600519.SH", "000001.SZ"])
    assert b.sources == {"tencent_batch_quote": 2}
    assert b.fallback_reason is None, "主源没坏就不该写回退理由"


def test_missing_symbols_are_filled_from_the_other_source(monkeypatch):
    """一个源漏了几只，另一个源补上 —— 每只都带自己的来源。"""
    _patch_sources(monkeypatch,
                   [tencent_line(code="sh600519")],
                   [sina_line(code="sz000001", name="平安银行")])
    b = bq.BatchQuoteProvider(attempts=1).fetch_quotes(
        ["600519.SH", "000001.SZ"])
    assert b.sources == {"tencent_batch_quote": 1, "sina_hq": 1}
    got = b.quotes.set_index("symbol")["source"].to_dict()
    assert got == {"600519.SH": "tencent_batch_quote",
                   "000001.SZ": "sina_hq"}


def test_both_sources_down_raises_instead_of_returning_a_partial_market(
        monkeypatch):
    """两个源都不可用 -> 抛错。一小撮行情被当成"整个市场"是最坏的结果。"""
    _patch_sources(monkeypatch, ["junk"], ["junk2"])
    with pytest.raises(FetchError) as e:
        bq.BatchQuoteProvider(attempts=1).fetch_quotes(["600519.SH"])
    assert "两个源" in str(e.value)


def test_empty_symbol_list_is_a_caller_bug():
    with pytest.raises(ValueError):
        bq.BatchQuoteProvider().fetch_quotes([])
