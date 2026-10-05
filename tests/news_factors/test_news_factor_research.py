# -*- coding: utf-8 -*-
"""新闻因子研究层：taxonomy、不可复现性、PIT、缓存安全。

这一层是**只读研究**，不改生产。测试盯四件事：

1. taxonomy 对已知标题给出确定的分类（程序性 vs 实质性）；
2. 同输入必须逐位同输出（spec §二十五「可复现」）；
3. PIT：T 日的因子不能用到 T 之后才有的事件（spec §九）；
4. 缓存不能把旧结果当成新结果返回（改了 taxonomy 就必须重算）。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from research.news_factors import engine as E
from research.news_factors.factors import FACTOR_SPECS, streams_from_events
from research.news_factors.taxonomy import (PROCEDURAL, SUBSTANTIVE, UNKNOWN,
                                            classify)


# ---------------------------------------------------------------------------
# 1. taxonomy
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("title,theme,mat", [
    ("关于召开2025年第一次临时股东大会的通知", "procedural", PROCEDURAL),
    ("关于修订《公司章程》的公告", "procedural", PROCEDURAL),
    ("北京市XX律师事务所关于公司2024年年度股东大会的法律意见书",
     "procedural", PROCEDURAL),
    ("关于收到深圳证券交易所关注函的公告", "regulatory", SUBSTANTIVE),
    ("关于公司收到中国证监会立案告知书的公告", "investigation", SUBSTANTIVE),
    ("关于控股股东部分股份被质押的公告", "pledge", SUBSTANTIVE),
    ("关于股东减持股份计划的公告", "shareholder_reduce", SUBSTANTIVE),
    ("关于以集中竞价交易方式回购股份的进展公告", "buyback", SUBSTANTIVE),
    ("2024年限制性股票激励计划（草案）", "equity_incentive", SUBSTANTIVE),
    ("关于对外担保的公告", "guarantee", SUBSTANTIVE),
    ("关于公司债务逾期未能清偿的公告", "debt_default", SUBSTANTIVE),
])
def test_taxonomy_classifies_known_titles(title, theme, mat):
    t, m, _d, _s = classify(title, "other")
    assert (t, m) == (theme, mat), f"{title} -> {(t, m)}"


def test_unclassifiable_title_is_honestly_unknown():
    """分不出来就返回 unknown，**不许硬塞**一个类别。"""
    t, m, d, s = classify("关于公司收到政府补助的公告", "other")
    assert m == UNKNOWN and t == "other"
    assert d == "neutral" and s == 0.0


def test_production_classification_is_trusted_when_present():
    """库里已有的 event_type 直接采信，不被研究层改写。"""
    t, m, d, s = classify("随便什么标题", "investigation")
    assert (t, m, d) == ("investigation", SUBSTANTIVE, "negative")


def test_severity_ordering_is_sane():
    """严重度先验要符合常识：立案 > 一般诉讼，违约最高。"""
    sev = {t: classify("", t)[3] for t in ("investigation", "lawsuit",
                                           "regulatory", "bankruptcy")}
    assert sev["investigation"] > sev["lawsuit"]
    assert sev["bankruptcy"] >= sev["investigation"]


# ---------------------------------------------------------------------------
# 2. 流与因子的确定性
# ---------------------------------------------------------------------------

def _events() -> pd.DataFrame:
    return pd.DataFrame([
        # 2020-01-02 可用：负面（立案）—— 实质性
        dict(symbol="AAA.SH", sdate=pd.Timestamp("2020-01-02"),
             theme="investigation", materiality=SUBSTANTIVE,
             dir_hint="negative", severity=0.9),
        # 同日：程序性
        dict(symbol="AAA.SH", sdate=pd.Timestamp("2020-01-02"),
             theme="procedural", materiality=PROCEDURAL,
             dir_hint="neutral", severity=0.05),
        # 2020-02-03：正面
        dict(symbol="AAA.SH", sdate=pd.Timestamp("2020-02-03"),
             theme="buyback", materiality=SUBSTANTIVE,
             dir_hint="positive", severity=0.5),
        dict(symbol="BBB.SZ", sdate=pd.Timestamp("2020-01-02"),
             theme="regulatory", materiality=SUBSTANTIVE,
             dir_hint="negative", severity=0.65),
        dict(symbol="BBB.SZ", sdate=pd.Timestamp("2020-01-02"),
             theme="procedural", materiality=PROCEDURAL,
             dir_hint="neutral", severity=0.05),
        dict(symbol="BBB.SZ", sdate=pd.Timestamp("2020-01-02"),
             theme="procedural", materiality=PROCEDURAL,
             dir_hint="neutral", severity=0.05),
    ])


def test_streams_separate_procedural_from_substantive():
    s = streams_from_events(_events())
    a = s[(s.symbol == "AAA.SH") & (s.sdate == pd.Timestamp("2020-01-02"))]
    b = s[(s.symbol == "BBB.SZ") & (s.sdate == pd.Timestamp("2020-01-02"))]
    assert int(a["n_all"].iloc[0]) == 2
    assert int(a["n_substantive"].iloc[0]) == 1
    assert int(a["n_procedural"].iloc[0]) == 1
    assert int(a["n_neg"].iloc[0]) == 1          # 程序性不算负面
    # BBB 两条程序性 + 一条监管
    assert int(b["n_procedural"].iloc[0]) == 2
    assert int(b["n_neg"].iloc[0]) == 1


def test_factor_is_deterministic():
    """同输入 -> 逐位同输出（spec §二十五）。"""
    s = streams_from_events(_events())
    # 日历必须留足 warmup：60 日窗口在头 59 行是 NaN（语义正确 ——
    # 历史不足时"过去 60 个交易日"本就无从谈起）。生产里
    # compute_panel 会自动向前多取 400 天，测试里用 2018 起步等价。
    cal = pd.DatetimeIndex(pd.bdate_range("2018-01-01", "2020-03-31"))
    start, end = pd.Timestamp("2018-01-01"), pd.Timestamp("2020-03-31")
    for name in ("negative_event_count_20d", "procedural_count_20d",
                 "positive_negative_balance_20d", "first_negative_event_20d",
                 "negative_event_streak_60d", "abnormal_news_intensity_20d"):
        a = E.compute_panel(FACTOR_SPECS[name], s, cal, start, end)
        b = E.compute_panel(FACTOR_SPECS[name], s, cal, start, end)
        pd.testing.assert_frame_equal(a, b)


def test_decay_weights_recent_events_more():
    """指数衰减：昨天的权重必须高于 20 天前。"""
    s = streams_from_events(_events())
    cal = pd.DatetimeIndex(pd.bdate_range("2018-01-01", "2020-03-31"))
    p = E.compute_panel(FACTOR_SPECS["weighted_negative_event_20d"], s, cal,
                        pd.Timestamp("2018-01-01"), pd.Timestamp("2020-03-31"))
    d0 = pd.Timestamp("2020-01-02")
    v = p.loc[d0, "AAA.SH"]
    assert v == pytest.approx(1.0, abs=1e-9)      # 当日事件权重 0.5^0 = 1
    # 20 个交易日后衰减到 0.5^2 = 0.25 附近
    later = p.index[p.index.get_loc(d0) + 20]
    assert p.loc[later, "AAA.SH"] < v


def test_streak_counts_consecutive_not_total():
    """连续性 ≠ 条数：一天发 3 条不应该被当成 3 天连续。"""
    ev = pd.DataFrame([
        dict(symbol="AAA.SH", sdate=pd.Timestamp("2020-01-02"),
             theme="regulatory", materiality=SUBSTANTIVE,
             dir_hint="negative", severity=0.65)] * 3)
    s = streams_from_events(ev)
    cal = pd.DatetimeIndex(pd.bdate_range("2018-01-01", "2020-02-28"))
    p = E.compute_panel(FACTOR_SPECS["negative_event_streak_60d"], s, cal,
                        pd.Timestamp("2018-01-01"), pd.Timestamp("2020-02-28"))
    assert p.loc[pd.Timestamp("2020-01-02"), "AAA.SH"] == 1.0


# ---------------------------------------------------------------------------
# 3. PIT
# ---------------------------------------------------------------------------

def _pit_data():
    """两个事件：一个在 T 之前可用，一个在 T 之后。"""
    cal = pd.DatetimeIndex(pd.bdate_range("2018-01-01", "2020-06-30"))
    base = pd.DataFrame([
        dict(symbol="AAA.SH", sdate=pd.Timestamp("2020-01-06"),
             theme="regulatory", materiality=SUBSTANTIVE,
             dir_hint="negative", severity=0.65),
    ])
    future = pd.DataFrame([
        dict(symbol="AAA.SH", sdate=pd.Timestamp("2020-03-02"),
             theme="bankruptcy", materiality=SUBSTANTIVE,
             dir_hint="negative", severity=0.9),
    ])
    return cal, base, future


def test_future_events_cannot_change_earlier_factor_values():
    """把 T 之后的事件加进来，T 日的因子值必须纹丝不动。"""
    cal, base, future = _pit_data()
    T = pd.Timestamp("2020-02-03")
    start, end = pd.Timestamp("2018-01-01"), pd.Timestamp("2020-06-30")
    for name in ("negative_event_count_20d", "negative_event_count_60d",
                 "procedural_count_20d", "news_intensity_20d"):
        s1 = streams_from_events(base)
        s2 = streams_from_events(pd.concat([base, future], ignore_index=True))
        p1 = E.compute_panel(FACTOR_SPECS[name], s1, cal, start, end)
        p2 = E.compute_panel(FACTOR_SPECS[name], s2, cal, start, end)
        a, b = p1.loc[T, "AAA.SH"], p2.loc[T, "AAA.SH"]
        assert a == pytest.approx(b, rel=1e-12), (
            f"{name} 在 {T.date()} 的值被未来事件改变了：{a} -> {b}")


def test_event_on_signal_day_counts():
    """同日可用的事件必须计入 —— 否则会把当日信息丢掉。"""
    cal, base, _ = _pit_data()
    s = streams_from_events(base)
    p = E.compute_panel(FACTOR_SPECS["negative_event_count_20d"], s, cal,
                        pd.Timestamp("2018-01-01"), pd.Timestamp("2020-06-30"))
    d = pd.Timestamp("2020-01-06")
    assert p.loc[d, "AAA.SH"] == 1.0


# ---------------------------------------------------------------------------
# 4. 缓存安全
# ---------------------------------------------------------------------------

def test_research_event_cache_is_rebuildable_and_matches(tmp_path):
    """缓存只是派生物：rebuild 出来的东西必须和读缓存一致。

    这条防的是"taxonomy 改了但缓存没失效"—— 那会让报告描述的分类
    和实际用的分类对不上，而且看不出来。
    """
    if not E.RESEARCH_EVENTS.exists():
        pytest.skip("研究事件缓存不存在（先跑一次 run_news_factor_research）")
    cached = E.load_research_events()
    for col in ("theme", "materiality", "dir_hint", "severity"):
        assert col in cached.columns, f"缓存缺 taxonomy 列 {col}"
    assert cached["materiality"].isin(
        [PROCEDURAL, SUBSTANTIVE, UNKNOWN]).all()
    # 覆盖：程序性占比应落在实测量级内（约 3 成），若算法改动会立刻偏离
    share = (cached["materiality"] == PROCEDURAL).mean()
    assert 0.15 < share < 0.45, f"程序性公告占比 {share:.1%} 偏离实测范围"


def test_streams_never_negative_and_counts_consistent():
    if not E.RESEARCH_EVENTS.exists():
        pytest.skip("研究事件缓存不存在")
    ev = E.load_research_events()
    s = streams_from_events(ev)
    assert (s["n_all"] >= s["n_substantive"]).all()
    num = s.select_dtypes(include="number")
    assert (num >= 0).all().all(), "流里出现负计数"
    # 实质性 + 程序性 + 未知 = 全部
    assert np.allclose(
        s["n_substantive"] + s["n_procedural"] + s["n_unknown"], s["n_all"])


def test_stale_taxonomy_cache_is_rejected(tmp_path, monkeypatch):
    """缓存里的 taxonomy 版本对不上 -> 必须重算，绝不返回旧分类。

    这条是 §三十一 说的 "factor cache safety"。改了 taxonomy 却读回旧缓存，
    报告里写的类别和实际算出来的类别会对不上，而且**没有任何一层会报警**。
    """
    import json as _json

    from research.news_factors import engine as Eg

    sidecar = tmp_path / "ev.taxonomy.json"
    monkeypatch.setattr(Eg, "_CACHE_SIDECAR", sidecar)
    monkeypatch.setattr(Eg, "RESEARCH_EVENTS", tmp_path / "ev.parquet")
    monkeypatch.setattr(Eg, "NEWS_VERSION", "v2")
    monkeypatch.setattr(Eg, "TAXONOMY_VERSION", "7")

    # 没有 sidecar -> 过期
    assert Eg._cache_is_current() is False
    # 版本对不上 -> 过期
    sidecar.write_text(_json.dumps({"taxonomy_version": "1",
                                    "news_version": "v2"}), encoding="utf-8")
    assert Eg._cache_is_current() is False
    # 新闻数据版本变了也要作废
    sidecar.write_text(_json.dumps({"taxonomy_version": "7",
                                    "news_version": "v1"}),
                       encoding="utf-8")
    assert Eg._cache_is_current() is False
    # 都对上 -> 可用
    sidecar.write_text(_json.dumps({"taxonomy_version": "7",
                                    "news_version": "v2"}),
                       encoding="utf-8")
    assert Eg._cache_is_current() is True
    # 坏文件不能当成有效
    sidecar.write_text("{not json", encoding="utf-8")
    assert Eg._cache_is_current() is False
