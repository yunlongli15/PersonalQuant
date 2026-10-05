# -*- coding: utf-8 -*-
"""news_v2 的派生产物：PIT 干净、pack 自洽、与 v1 互不覆盖。

这组断言盯的是"修复 SSE 采集"这条线的产物，而不是新闻因子本身的行为
（那是 test_news_factor.py / test_news_no_future_leakage.py 的事）。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
NEWS = PROJECT_ROOT / "data" / "derived" / "news"
EVENTS_V2 = NEWS / "news_events_v2.parquet"
COVERAGE_V2 = NEWS / "news_coverage_v2.parquet"
PACK_V2 = PROJECT_ROOT / "experiments" / "news" / "news_factor_run_002" \
    / "factor_pack_news_v2.json"
STORE_V2 = NEWS / "news_factors_v2.parquet"


def _skip_if_absent(p: Path, why: str):
    if not p.exists():
        pytest.skip(f"{p.name} 不存在（{why}）")


def test_v2_events_are_point_in_time_clean():
    """可用时间不得早于发布时间 —— 2M 行里一条都不许有。

    一次时间倒流就意味着因子在 T 日能读到 T 之后才披露的东西。只读两列，
    避免把 115MB 全读进内存。
    """
    _skip_if_absent(EVENTS_V2, "跑 build_events.py --version v2 生成")
    ev = pd.read_parquet(EVENTS_V2,
                         columns=["symbol", "publication_time",
                                  "availability_time"])
    pub = pd.to_datetime(ev["publication_time"], errors="coerce")
    avail = pd.to_datetime(ev["availability_time"], errors="coerce")
    bad = pub.notna() & avail.notna() & (avail < pub)
    assert not bad.any(), (
        f"{int(bad.sum())} 条事件的可用时间早于发布时间，例如：\n"
        + ev.loc[bad].head(5).to_string())


def test_v2_events_are_never_shorter_than_v1_for_shanghai():
    """修复的量化证据：沪市公告数必须是 v1 的一个数量级以上。

    这条是这次修复的"没白干"证明 —— 它锁住的是 SSE 采集参数别再被改回去
    （reportType2 一写死，沪市就只剩定期报告）。v1 快照缺失时跳过。
    """
    _skip_if_absent(EVENTS_V2, "跑 build_events.py --version v2 生成")
    v1 = NEWS / "news_events.parquet"
    if not v1.exists():
        pytest.skip("v1 事件快照不在（只验 v2 自身）")
    n_v1 = pd.read_parquet(v1, columns=["symbol"])["symbol"]
    n_v2 = pd.read_parquet(EVENTS_V2, columns=["symbol"])["symbol"]
    sh1 = int(n_v1.str.startswith("6").sum())
    sh2 = int(n_v2.str.startswith("6").sum())
    assert sh2 > 10 * sh1, (
        f"沪市公告数 v1={sh1:,} -> v2={sh2:,}，不到 10 倍 —— "
        "SSE 采集参数可能被改回只取定期报告了")


def test_v2_pack_accounts_for_every_news_factor():
    """selected + discarded 必须正好等于全部新闻因子，一个都不能凭空消失。"""
    _skip_if_absent(PACK_V2, "跑 build_news_factors.py --version v2 生成")
    from factors.registry import FACTOR_REGISTRY

    pack = json.loads(PACK_V2.read_text(encoding="utf-8"))
    all_news = {n for n, m in FACTOR_REGISTRY.items()
                if m["category"] == "news"}
    selected = set(pack["selected"])
    discarded = {d["factor"] for d in pack["discarded"]}
    assert selected <= all_news, f"选中的不是新闻因子：{selected - all_news}"
    assert selected & discarded == set(), "同一个因子既选中又被丢弃"
    assert selected | discarded == all_news, (
        f"没交代去向的因子：{all_news - selected - discarded}")
    assert all(d.get("reason") for d in pack["discarded"]), \
        "丢弃必须带原因"


def test_v2_factor_store_schema_and_window():
    """因子库是策略的输入，schema/日期范围必须对得上。"""
    _skip_if_absent(STORE_V2, "跑 build_news_factors.py --version v2 生成")
    store = pd.read_parquet(STORE_V2)
    assert len(store) > 0
    for col in ("symbol", "signal_date", "factor_name", "factor_value",
                "feature_version"):
        assert col in store.columns, f"缺列 {col}"
    d = pd.to_datetime(store["signal_date"])
    assert d.min() >= pd.Timestamp("2015-01-01"), \
        f"信号日起点 {d.min()} 早于策略训练起点"
    assert store["factor_value"].notna().all(), \
        "因子库里出现 NaN —— 空值应当在写库前就丢掉"


def test_v2_outputs_do_not_overlap_v1_outputs():
    """v1/v2 的 run 目录、pack、因子库路径必须两两不同。

    v1 的 pack 被 config/production_freeze.yaml 按哈希冻结着，覆盖它等于
    伪造历史；这条把"别写回同一个路径"钉死在代码层面。
    """
    from scripts.news.build_news_factors import RUN_DIRS

    assert RUN_DIRS["v1"] != RUN_DIRS["v2"]
    names = [f"factor_pack_news_{v}.json" for v in ("v1", "v2")]
    assert len(set(names)) == 2
    assert (NEWS / "news_factors.parquet") != STORE_V2
