# -*- coding: utf-8 -*-
"""Candidate Freeze（§28）：选完之后不能再根据历史数据反复挑。

冻结的可靠性来自"manifest 记录了复现所需的一切"，而不是来自"记得别改"。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CFG_PATH = ROOT / "config" / "factor_selection_v2.yaml"


def _cfg():
    return yaml.safe_load(CFG_PATH.read_text(encoding="utf-8"))[
        "factor_selection_v2"]


def _manifest():
    p = ROOT / _cfg()["final"]["manifest"]
    if not p.exists():
        pytest.skip("尚未运行选择流程，manifest 不存在")
    return json.loads(p.read_text(encoding="utf-8"))


def test_weights_live_in_config_not_in_code():
    c = _cfg()["evidence_score"]["components"]
    assert set(c) == {
        "incremental_icir", "incremental_rankicir", "positive_fold_ratio",
        "positive_month_ratio", "independence", "coverage", "turnover",
        "stability"}
    for name, spec in c.items():
        assert "weight" in spec, name
        assert 0 < spec["weight"] <= 1, name


def test_priority_is_incremental_ic_not_portfolio_return():
    """§16：优先级 Incremental IC > stability > independence > 可复现 >
    portfolio 收益。权重必须体现这个次序，且组合收益不得进 score。"""
    c = _cfg()["evidence_score"]["components"]
    assert c["incremental_icir"]["weight"] >= c["stability"]["weight"]
    assert c["stability"]["weight"] >= c["independence"]["weight"]
    assert c["independence"]["weight"] >= c["turnover"]["weight"]
    assert not any("portfolio" in k or "sharpe" in k for k in c)


def test_final_candidates_are_capped_and_not_production():
    f = _cfg()["final"]
    assert 3 <= f["min_candidates"] <= f["max_candidates"] <= 5
    assert f["status"] == "research_candidate"


def test_final_candidates_are_not_referenced_by_strategy_v2():
    """研究候选不得悄悄进入生产策略配置。"""
    p = ROOT / "config" / "strategy_v2.yaml"
    if not p.exists():
        pytest.skip("没有 strategy_v2.yaml")
    text = p.read_text(encoding="utf-8")
    p2 = ROOT / _cfg()["final"]["manifest"]
    if not p2.exists():
        pytest.skip("尚未运行选择流程")
    for f in json.loads(p2.read_text(encoding="utf-8"))["final_candidates"]:
        assert f not in text, f"{f} 出现在 strategy_v2.yaml"


def test_manifest_records_everything_needed_to_reproduce():
    m = _manifest()
    for key in ("protocol", "version", "selected_at", "git_commit",
                "data_snapshot", "selection_window", "model", "folds",
                "m0_features", "final_candidates", "stage_a_kept",
                "historical_test_status", "forward_holdout_start"):
        assert key in m, key
    assert m["selection_window"] == ["2018-01-01", "2023-12-31"]
    assert m["model"]["seed"] == _cfg()["model"]["seed"]
    assert len(m["folds"]) == len(_cfg()["walk_forward"]["folds"])
    for f in m["folds"]:
        assert f["train"][1] < f["valid"][0]
        assert f["n_valid_dates"] > 0


def test_manifest_declares_the_test_set_was_already_observed():
    """§29：不得再声称 2024-2025 是 untouched test。"""
    m = _manifest()
    s = m["historical_test_status"]
    assert "HISTORICAL TEST" in s or "已被评估" in s
    assert "untouched" not in s.lower()


def test_manifest_respects_the_candidate_cap():
    m = _manifest()
    cap = _cfg()["final"]["max_candidates"]
    assert len(m["final_candidates"]) <= cap
    assert m["n_candidates_tested"] <= _cfg()["stage_a"][
        "max_candidates_to_stage_b"]


def test_manifest_hashes_the_configuration():
    """冻结必须能回答"当时用的是哪一版参数"。"""
    m = _manifest()
    import hashlib
    digest = hashlib.sha256(CFG_PATH.read_bytes()).hexdigest()
    assert m.get("config_sha256") == digest, \
        "配置在 freeze 之后被改动过，必须新开 run 并记录"
