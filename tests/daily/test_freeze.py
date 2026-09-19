# -*- coding: utf-8 -*-
"""§2 / §35：生产冻结守卫。改任何生产配置都会被发现。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
import yaml

from pipeline import daily as D
from pipeline import freeze as F


def test_freeze_record_exists_and_is_complete():
    rec = F.load_freeze().get("production_freeze") or {}
    assert rec, "还没有 config/production_freeze.yaml"
    for k in ("version", "freeze_date", "git_commit", "strategy_version",
              "feature_version", "news_feature_version", "model_version",
              "allocation_method", "execution_model",
              "forward_holdout_start", "hashes"):
        assert k in rec, k


def test_current_state_matches_the_freeze():
    st = F.verify()
    assert st.frozen and not st.drift, st.detail


def test_hashes_cover_every_production_artifact():
    st = F.verify()
    for k in ("paper_live_config", "strategy_v2_config", "strategy_v1_config",
              "feature_pack_v1", "news_factor_pack", "production_model"):
        assert k in st.current, k
        assert st.current[k] != "MISSING", f"{k} 指向的文件不存在"


def test_changing_a_frozen_hash_is_detected():
    st = F.verify()
    tampered = dict(st.recorded)
    tampered["production_model"] = "0" * 64
    mismatches = [k for k, v in st.current.items()
                  if k in tampered and tampered[k] != v]
    assert "production_model" in mismatches


def test_production_drift_stops_forward_observation(run, monkeypatch, sandbox):
    """冻结不一致 → PRODUCTION_DRIFT，且**不做** forward 观测。"""
    _, panel = run(force=True)
    drift = F.FreezeStatus(frozen=True, drift=True,
                           mismatches=["production_model"], detail="测试用漂移")
    monkeypatch.setattr(F, "verify", lambda: drift)
    res, _ = run(date="2026-09-17", force=True)
    assert res.status == D.PRODUCTION_DRIFT
    assert res.forward_observation is False
    assert any("PRODUCTION_DRIFT" in w for w in res.warnings)


def test_one_click_stop_disables_forward_observation(monkeypatch):
    """§36：production_enabled = false 时不产生正式 forward observation。"""
    rec = {"production_freeze": F.load_freeze()["production_freeze"]}
    rec["production_freeze"] = dict(rec["production_freeze"])
    rec["production_freeze"]["production_enabled"] = False
    monkeypatch.setattr(F, "load_freeze", lambda: rec)
    assert F.production_enabled() is False


def test_write_freeze_refuses_to_overwrite_on_drift(monkeypatch, tmp_path):
    """已冻结且有变化时，拒绝重新冻结（防止悄悄改掉生产状态）。"""
    monkeypatch.setattr(F, "verify",
                        lambda: F.FreezeStatus(frozen=True, drift=True,
                                               mismatches=["x"], detail="d"))
    with pytest.raises(F.ProductionDrift):
        F.write_freeze()
