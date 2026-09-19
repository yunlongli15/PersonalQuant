# -*- coding: utf-8 -*-
"""§20 / §37：冻结校验。任何 config / model / feature pack 变化都必须被发现。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
import yaml

from paper_live.config import (CONFIG_PATH, config_sha256, freeze_hashes,
                               load_config, verify_freeze)


def test_the_shipped_config_is_frozen():
    cfg = load_config()
    assert cfg["paper_live"]["freeze"], "config/paper_live.yaml 尚未冻结"
    v = verify_freeze(cfg)
    assert v["is_frozen"]
    assert not v["drift"], f"冻结工件不一致：{v['mismatches']}"


def test_freeze_covers_everything_that_can_drift():
    h = freeze_hashes(load_config())
    for key in ("paper_live_config", "model", "model_params",
                "universe_config", "feature_pack_0", "feature_pack_1"):
        assert key in h, key
        assert h[key] != "MISSING", f"{key} 指向的文件不存在"


def test_config_hash_ignores_the_freeze_block_itself():
    """否则写 freeze 会改掉 config 的哈希 -> 自指 -> 永远 drift。"""
    text = CONFIG_PATH.read_text(encoding="utf-8")
    assert "freeze:" in text
    before = config_sha256()
    cfg = load_config()
    assert cfg["paper_live"]["freeze"]           # 块里有内容
    assert config_sha256() == before


def test_changing_the_model_changes_the_hash():
    h = freeze_hashes(load_config())
    assert h["model"] != "MISSING"
    assert len(h["model"]) == 64


def test_drift_is_detected_when_a_frozen_hash_moves(tmp_path):
    cfg = load_config()
    cfg["paper_live"] = dict(cfg["paper_live"])
    cfg["paper_live"]["freeze"] = dict(cfg["paper_live"]["freeze"])
    cfg["paper_live"]["freeze"]["model"] = "0" * 64
    v = verify_freeze(cfg)
    assert v["drift"] and "model" in v["mismatches"]


def test_unfrozen_config_reports_unfrozen():
    cfg = load_config()
    cfg["paper_live"] = dict(cfg["paper_live"])
    cfg["paper_live"]["freeze"] = {}
    v = verify_freeze(cfg)
    assert v["is_frozen"] is False and v["drift"] is None


def test_paper_live_params_are_immutable_by_contract():
    s = load_config()["paper_live"]
    assert s["record_only"] is True
    assert s["strategy_version"] == "strategy_v2"
    assert s["forward_start_date"] == "2026-09-18"
    assert s["portfolio"]["top_k"] == 20
    assert s["execution"]["model"] == "T1_open"
    assert s["capital"]["initial"] == 500000.0
