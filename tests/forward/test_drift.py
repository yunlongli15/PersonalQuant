# -*- coding: utf-8 -*-
"""§20-§23：漂移只监控，绝不自动修复。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from paper_live import drift as D
from paper_live.config import load_config


def test_strategy_drift_is_ok_on_the_frozen_config():
    r = D.strategy_drift(load_config())
    assert r["status"] == "OK"
    assert r["drift"] is False


def test_strategy_drift_detects_a_moved_hash():
    cfg = load_config()
    cfg["paper_live"] = dict(cfg["paper_live"])
    cfg["paper_live"]["freeze"] = dict(cfg["paper_live"]["freeze"])
    cfg["paper_live"]["freeze"]["feature_pack_0"] = "0" * 64
    r = D.strategy_drift(cfg)
    assert r["status"] == "DRIFT_DETECTED"
    assert "feature_pack_0" in r["mismatches"]


def test_strategy_drift_reports_unfrozen():
    cfg = load_config()
    cfg["paper_live"] = dict(cfg["paper_live"])
    cfg["paper_live"]["freeze"] = {}
    assert D.strategy_drift(cfg)["status"] == "UNFROZEN"


def test_model_drift_flags_a_shifted_distribution():
    rng = np.random.default_rng(0)
    base = pd.Series(rng.normal(0, 1, 5000))
    same = pd.Series(rng.normal(0, 1, 500))
    far = pd.Series(rng.normal(6, 1, 500))
    assert D.model_drift(same, base)["status"] == "OK"
    assert D.model_drift(far, base)["status"] == "MODEL_DRIFT_WARNING"


def test_model_drift_without_baseline_says_so():
    r = D.model_drift(pd.Series([1.0, 2.0]), None)
    assert r["status"] == "NO_BASELINE"


def test_model_drift_never_fixes_anything():
    """漂移检查的返回里不得出现任何"已调整/已重训"的动作。"""
    r = D.model_drift(pd.Series(np.linspace(0, 1, 100)),
                      pd.Series(np.linspace(0, 1, 100)))
    for k in r:
        assert "retrain" not in k and "adjust" not in k
    assert r["status"] in ("OK", "MODEL_DRIFT_WARNING", "NO_BASELINE",
                           "NO_DATA")


def test_prediction_concentration_warns_on_an_outlier():
    s = pd.Series(np.concatenate([[100.0], np.zeros(199)]))
    r = D.prediction_concentration(s, top1_z_threshold=3.0)
    assert r["status"] == "CONCENTRATION_WARNING"
    assert r["top1_z"] > 3


def test_news_drift_reports_shifted_factors():
    base = {"news_count": {"mean": 1.0, "std": 0.2}}
    assert D.news_drift({"news_count": 1.1}, base)["status"] == "OK"
    assert D.news_drift({"news_count": 5.0}, base)["status"] == \
        "NEWS_DRIFT_WARNING"


def test_news_drift_without_baseline_says_so():
    assert D.news_drift({"a": 1.0}, {})["status"] == "NO_BASELINE"


def test_data_drift_flags_a_big_change():
    base = {"n_symbols": 3000, "feature_missing_rate": 0.01}
    assert D.data_drift(dict(base), base)["status"] == "OK"
    assert D.data_drift({"n_symbols": 100, "feature_missing_rate": 0.01},
                        base)["status"] == "DATA_QUALITY_WARNING"


# ---------------------------------------------------------------------------
# 接线：§22 news / §23 data 必须真的被算出来
#
# 回归测试。修之前 engine 只算 strategy/model/concentration 三类，
# news_drift / data_drift 两个函数定义了却没有任何生产调用者 ——
# 文档写着"每天监控四类漂移"，实际那两条保护根本不存在，而且无论漂移
# 多大都不会产生告警。
# ---------------------------------------------------------------------------

from paper_live.engine import run_day                      # noqa: E402
from paper_live.store import ForwardStore                   # noqa: E402

SIGNAL = pd.Timestamp("2026-09-30")


def _store(pl_cfg):
    return ForwardStore(pl_cfg["paper_live"]["paths"]["root"])


def test_the_engine_computes_all_four_drift_categories(pl_cfg, fake_provider):
    store = _store(pl_cfg)
    r = run_day(SIGNAL, pl_cfg, store, fake_provider, force_rebalance=True)
    assert set(r.drift) == {"strategy", "model", "concentration",
                            "news", "data"}
    for key in ("news", "data"):
        assert "status" in r.drift[key], key


def test_no_baseline_is_reported_honestly_not_as_ok(pl_cfg, fake_provider):
    """没上膛就直说 NO_BASELINE —— 绝不能返回 OK 让人以为查过了。"""
    store = _store(pl_cfg)
    r = run_day(SIGNAL, pl_cfg, store, fake_provider, force_rebalance=True)
    assert r.drift["news"]["status"] == "NO_BASELINE"
    assert r.drift["data"]["status"] == "NO_BASELINE"


def test_the_baseline_lives_under_the_store_not_a_global_path(pl_cfg,
                                                             fake_provider):
    """基线是实验状态，必须跟着 store 走；写死全局路径的话，跑一次测试
    就会用假 provider 的 40 只股票顶掉正式基线。"""
    store = _store(pl_cfg)
    assert store.state_path("news_baseline").parent == store.root / "state"
    assert store.state_path("data_baseline").parent == store.root / "state"


def test_news_shift_raises_the_news_drift_alert(pl_cfg, fake_provider):
    """基线说 3σ 之外 -> 必须有 NEWS_DRIFT 告警（修之前永远不会出现）。"""
    from paper_live import alerts as A

    store = _store(pl_cfg)
    D.save_baseline(store.state_path("news_baseline"),
                    {"announcement_count_20d": {"mean": 0.7, "std": 2.7}})
    r = run_day(SIGNAL, pl_cfg, store, fake_provider, force_rebalance=True)

    con = D.news_drift({"announcement_count_20d": 1.0},
                       {"announcement_count_20d": {"mean": 0.7, "std": 2.7}})
    assert con["status"] == "OK"                      # 0.11σ，不该报

    shifted = D.news_drift({"announcement_count_20d": 99.0},
                           {"announcement_count_20d": {"mean": 0.7, "std": 2.7}})
    assert shifted["status"] == "NEWS_DRIFT_WARNING"
    codes = [a["code"] for a in A.check_alerts(drift={"news": shifted})]
    assert "NEWS_DRIFT" in codes
    assert r.drift["news"]["status"] == "OK"          # 这次运行的值确实正常


def test_data_shift_raises_the_data_quality_alert(pl_cfg, fake_provider):
    from paper_live import alerts as A

    store = _store(pl_cfg)
    D.save_baseline(store.state_path("data_baseline"),
                    {"n_symbols": 3000, "feature_missing_rate": 0.01,
                     "custom_coverage": 0.9})
    out = D.data_drift_vs_state(
        {"n_symbols": 40, "feature_missing_rate": 0.01, "custom_coverage": 0.9},
        store.state_path("data_baseline"))
    assert out["status"] == "DATA_QUALITY_WARNING"
    codes = [a["code"] for a in A.check_alerts(drift={"data": out})]
    assert "DATA_QUALITY_WARNING" in codes
    assert any("n_symbols" in i for i in out["issues"])


def test_drift_never_triggers_an_order(pl_cfg, fake_provider):
    """漂移只报警，绝不自动修复/下单（§20-§23 的总原则）。"""
    from paper_live import alerts as A

    out = D.data_drift({"n_symbols": 1},
                       {"n_symbols": 3000, "feature_missing_rate": 0.01})
    for a in A.check_alerts(drift={"data": out}):
        assert a["level"] == "WARNING"
        assert "买" not in a["detail"] and "卖" not in a["detail"]


def test_history_baseline_has_a_real_std():
    """只用一天当基线的话 std=0，"超过 3σ"永远不触发 —— 等于没监控。"""
    base = D.build_news_baseline()
    if not base:
        pytest.skip("历史新闻因子快照不在本地")
    assert len(base) >= 1
    for name, stat in base.items():
        assert np.isfinite(stat["mean"]), name
        assert stat["std"] > 0, f"{name} 的 std=0，无法判定位移"
