# -*- coding: utf-8 -*-
"""§35：生产冻结的独立测试（tests/production/）。

改 model / feature / strategy / allocation 任何一项配置，
都必须触发 production drift detection。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from pipeline import freeze as F

# 每一项都对应一个真实的生产工件
PRODUCTION_CONFIGS = {
    "paper_live_config": "config/paper_live.yaml",
    "strategy_v2_config": "config/strategy_v2.yaml",
    "strategy_v1_config": "config/strategy_v1.yaml",
    "feature_pack_v1":
        "experiments/factors/factor_run_001/factor_pack_v1.json",
    "news_factor_pack":
        "experiments/news/news_factor_run_001/factor_pack_news_v1.json",
    "production_model": "experiments/news/strategy/model.txt",
}


@pytest.mark.parametrize("key,rel", sorted(PRODUCTION_CONFIGS.items()))
def test_every_production_config_is_hashed(key, rel):
    st = F.verify()
    assert key in st.current, f"{key} 没有被纳入冻结哈希"
    assert st.current[key] != "MISSING", f"{rel} 不存在"


@pytest.mark.parametrize("key,rel", sorted(PRODUCTION_CONFIGS.items()))
def test_changing_this_config_would_detected_as_drift(key, rel, monkeypatch):
    """模拟该文件被改动 → verify() 必须报 drift。"""
    st = F.verify()
    recorded = dict(st.recorded)
    recorded[key] = "0" * 64          # 假装记录的是另一个哈希
    monkeypatch.setattr(F, "load_freeze",
                        lambda: {"production_freeze": {
                            "hashes": recorded,
                            "production_enabled": True}})
    v = F.verify()
    assert v.drift is True
    assert key in v.mismatches


def test_assert_frozen_raises_on_drift(monkeypatch):
    monkeypatch.setattr(F, "verify",
                        lambda: F.FreezeStatus(frozen=True, drift=True,
                                               mismatches=["model"],
                                               detail="模型变了"))
    with pytest.raises(F.ProductionDrift):
        F.assert_frozen()


def test_assert_frozen_passes_when_consistent():
    assert F.assert_frozen().ok is True


def test_freeze_records_the_forward_holdout_start():
    rec = F.load_freeze()["production_freeze"]
    assert rec["forward_holdout_start"] == "2026-09-18"


def test_freeze_records_execution_and_allocation():
    """§46：执行模型与分配方法属于冻结内容，不能被 pipeline 改。"""
    rec = F.load_freeze()["production_freeze"]
    assert rec["execution_model"] == "T1_open"
    assert rec["allocation_method"] == "equal_weight"
    assert rec["top_k"] == 20
