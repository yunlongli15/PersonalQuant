# -*- coding: utf-8 -*-
"""S3_v2 的产出：只有一个变量变了。

S3_v1 与 S3_v2 的对比要成立，前提是**两者只差新闻那一部分** ——
模型类型、seed、时间切分、label、以及 7 个非新闻自定义特征必须逐位相同。
这些断言就是那个前提的看门人：谁哪天顺手改了一个量价特征或 seed，
对比结论会静默失效，但这些测试会响。

跑之前需要先训练 S3_v2（`scripts/news/run_news_strategy.py
--news-version v2 --out-dir experiments/news/strategy_s3_v2`）。
没训练就跳过 —— 它是实验产物，不是仓库的常驻件。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
V1 = PROJECT_ROOT / "experiments" / "news" / "strategy"
V2 = PROJECT_ROOT / "experiments" / "news" / "strategy_s3_v2"


def _summary(d: Path) -> dict:
    p = d / "summary.json"
    if not p.exists():
        pytest.skip(f"{d.name} 还没有训练结果")
    return json.loads(p.read_text(encoding="utf-8"))


def _manifest(d: Path) -> dict:
    p = d / "manifest.json"
    if not p.exists():
        pytest.skip(f"{d.name} 还没有 manifest")
    return json.loads(p.read_text(encoding="utf-8"))


def test_v2_run_records_the_v2_news_pack():
    m = _manifest(V2)
    extra = m.get("extra") or {}
    assert extra.get("news_version") == "factor_pack_news_v2", \
        f"S3_v2 的 manifest 没记录 v2 新闻包：{extra}"
    assert extra.get("news_run") == "news_factor_run_002"


def test_only_the_news_part_differs():
    """非新闻特征必须完全一致，且正好等于该版的新闻 pack 选中项。"""
    step4 = json.loads((PROJECT_ROOT / "experiments" / "factors"
                        / "factor_run_001" / "factor_pack_v1.json")
                       .read_text(encoding="utf-8"))["selected"]
    packs = {v: json.loads((PROJECT_ROOT / "experiments" / "news"
                            / (f"news_factor_run_00{i}") /
                            f"factor_pack_news_{v}.json")
                           .read_text(encoding="utf-8"))["selected"]
             for v, i in (("v1", 1), ("v2", 2))}

    f1 = _summary(V1)["features"]
    f2 = _summary(V2)["features"]

    n1 = [f for f in f1 if f in packs["v1"]]
    n2 = [f for f in f2 if f in packs["v2"]]
    assert n1 == packs["v1"], f"S3_v1 的新闻特征和 pack 对不上：{n1}"
    assert n2 == packs["v2"], f"S3_v2 的新闻特征和 pack 对不上：{n2}"

    non1 = [f for f in f1 if f not in packs["v1"]]
    non2 = [f for f in f2 if f not in packs["v2"]]
    assert non1 == non2 == step4, (
        f"非新闻特征两版不一致 —— 对比失去意义\n"
        f"  S3_v1: {non1}\n  S3_v2: {non2}\n  pack_v1: {step4}")


def test_v2_does_not_reuse_v1_news_factors():
    """v2 的特征里不能混进 v1 选中的新闻因子。"""
    packs = {v: set(json.loads((PROJECT_ROOT / "experiments" / "news"
                                / f"news_factor_run_00{i}" /
                                f"factor_pack_news_{v}.json")
                               .read_text(encoding="utf-8"))["selected"])
             for v, i in (("v1", 1), ("v2", 2))}
    f2 = set(_summary(V2)["features"])
    assert not (f2 & packs["v1"]), f"S3_v2 混进了 v1 的新闻因子：{f2 & packs['v1']}"


def test_split_and_seed_match():
    """训练切分与随机种子必须一致 —— 否则回测对比不成立。"""
    m1, m2 = _manifest(V1), _manifest(V2)
    assert m1["time_split"] == m2["time_split"], "时间切分变了"
    assert m1["model_seed"] == m2["model_seed"], "随机种子变了"
    assert m1["model_params"] == m2["model_params"], "超参变了"
    assert m1["label"] == m2["label"], "标签定义变了"
    assert m1["execution"] == m2["execution"], "执行模型变了"
    assert m1["transaction_costs"] == m2["transaction_costs"], "成本模型变了"
