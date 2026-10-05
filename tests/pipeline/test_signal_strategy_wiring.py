# -*- coding: utf-8 -*-
"""策略切换时，信号计算读的特征必须跟着换版本。

2026-10-05 的 bug：`_feature_names()` 把 v1 的新闻 pack 写死在模块里，
于是 `compute_signals(strategy="S3_v2")` 会把 v1 的三个新闻因子喂给
一个只认识 `regulatory_event_count_20d` 的模型 —— 要么 KeyError，
要么（更糟）列对不上一声不响地算错。这类"切换时读错东西"的 bug
不会在单策略测试里暴露，只有把两个策略并排断言才看得见。
"""

import json

import pytest

from pipeline import signals


def test_feature_names_follow_the_strategy():
    v1 = signals._feature_names("S3_v1")
    v2 = signals._feature_names("S3_v2")
    assert v1 != v2, "两个版本的新闻特征集一样 —— 版本没接上"

    from factors.registry import FACTOR_REGISTRY

    pack = {v: json.loads(signals.NEWS_PACKS[v].read_text(encoding="utf-8"))
            for v in ("v1", "v2")}
    for ver, feats in (("v1", v1), ("v2", v2)):
        selected = pack[ver]["selected"]
        assert selected, f"{ver} 的 pack 选空"
        assert feats[-len(selected):] == selected, (
            f"{ver} 的特征没接上对应的 pack：{feats[-len(selected):]} "
            f"vs {selected}")
        for n in selected:
            assert FACTOR_REGISTRY[n]["category"] == "news"


def test_other_side_news_factors_never_leak_in():
    """v1 的新闻因子绝不能出现在 v2 的特征表里，反之亦然。"""
    both = {v: set(json.loads(signals.NEWS_PACKS[v].read_text(
        encoding="utf-8"))["selected"]) for v in ("v1", "v2")}
    assert not (both["v1"] & both["v2"]), \
        f"两版选中的新闻因子有重叠：{both['v1'] & both['v2']}"
    for ver in ("v1", "v2"):
        other = "v2" if ver == "v1" else "v1"
        feats = set(signals._feature_names(f"S3_{ver}"))
        assert not (feats & both[other]), (
            f"S3_{ver} 的特征表里混进了 {other} 的新闻因子："
            f"{feats & both[other]}")


def test_unknown_strategy_is_rejected_not_defaulted():
    with pytest.raises(ValueError):
        signals.strategy_spec("S3_v9")


def test_signal_paths_are_versioned_and_disjoint():
    """信号落盘路径必须带版本 —— 否则切策略会覆盖正在跑的实验中读的文件。"""
    p1 = signals.signal_path("2026-09-30", "S3_v1")
    p2 = signals.signal_path("2026-09-30", "S3_v2")
    assert p1 != p2
    assert "S3_v1" in p1.name and "S3_v2" in p2.name


def test_production_strategy_is_a_registered_one():
    assert signals.PRODUCTION_STRATEGY in signals.STRATEGIES


# ---------------------------------------------------------------------------
# PHASE 7：干净生产策略
# ---------------------------------------------------------------------------

def test_production_clean_has_no_custom_and_no_news_features():
    """生产策略只用 Alpha158 —— 自定义特征必须真的为空，且不读新闻。

    这是 PHASE 7 的核心承诺。它一旦被"顺手加一个特征"破坏，
    影响的不是研究结论，而是**每天真实的推荐**。
    """
    spec = signals.strategy_spec("production_clean_v1")
    assert spec["uses_news"] is False
    assert spec["custom_features"] == []
    assert signals._feature_names("production_clean_v1") == []
    assert spec["feature_version"] == "alpha158"


def test_production_model_exists_and_is_the_clean_one():
    spec = signals.strategy_spec()
    assert spec["name"] == signals.PRODUCTION_STRATEGY
    assert "clean" in spec["model"], \
        f"生产模型指向 {spec['model']}，看起来不是 clean 候选"
    assert spec["model_path"].exists(), f"生产模型不存在：{spec['model']}"


def test_news_strategies_are_still_switchable():
    """旧策略必须还能切回去做历史对比（§十五）。"""
    for name in ("S3_v1", "S3_v2"):
        s = signals.strategy_spec(name)
        assert s["uses_news"] is True
        assert s["model_path"].exists(), f"{name} 的模型不存在"
        assert signals.signal_path("2026-09-30", name).name == \
            f"signals_{name}_2026-09-30.parquet"


def test_clean_and_news_strategies_have_disjoint_feature_sets():
    clean = set(signals._feature_names("production_clean_v1"))
    for name in ("S3_v1", "S3_v2"):
        news = set(signals._feature_names(name))
        assert not (clean & news), f"生产策略混进了 {name} 的特征"
