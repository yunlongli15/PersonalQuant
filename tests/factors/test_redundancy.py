# -*- coding: utf-8 -*-
"""冗余判据：主判据必须是**原始因子**秩相关，不是残差相关。

这一条直接编码 reports/步骤9-独立信息研究.md 的失败：
上一轮用残差相关聚类，R² 高的因子残差以噪声为主 → 残差相关被系统性
压低 → 最冗余的因子看起来最"独立"（3 个波动率因子就这样逃过了聚类）。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from incremental.redundancy import redundancy_diagnostics

CONFIG = {"factor_selection_v2": {"redundancy": {
    "method": "raw_rank_correlation", "max_corr_threshold": 0.85,
    "r2_threshold": 0.90, "require_both": True}}}

DATES = pd.date_range("2021-01-31", periods=6, freq="ME")
SYMS = [f"S{i:04d}" for i in range(300)]


def _panel(scale=1.0, seed=0, base=None):
    """Date × symbol 面板（与 FACTORS 输出同向：index=日期, columns=股票）。"""
    rng = np.random.default_rng(seed)
    rows = {}
    for s in SYMS:
        v = rng.normal(0, scale, len(DATES))
        rows[s] = pd.Series(v, index=DATES) if base is None else \
            pd.Series(base[s].to_numpy() + v, index=DATES)
    return pd.DataFrame(rows)


def _feats(**panels):
    """{date: DataFrame(symbol × feature)} —— redundancy 的 feature_panel 形态。"""
    return {d: pd.DataFrame({k: p.loc[d] for k, p in panels.items()})
            for d in DATES}


def test_near_duplicate_of_existing_is_redundant():
    e = _panel(1.0, seed=1)
    cand = _panel(0.05, seed=2, base=e)
    r = redundancy_diagnostics(cand, {"E": e}, _feats(E=e), CONFIG)
    assert r["max_corr_existing"] > 0.9
    assert r["max_corr_with"] == "E"
    assert r["r2_existing"] > 0.9
    assert r["redundant"]                      # 两个判据同时越线
    assert r["redundant_reason"]


def test_independent_candidate_is_not_redundant():
    e = _panel(1.0, seed=3)
    cand = _panel(1.0, seed=4)
    r = redundancy_diagnostics(cand, {"E": e}, _feats(E=e), CONFIG)
    assert abs(r["max_corr_existing"]) < 0.2
    assert not r["redundant"]
    assert r["redundant_reason"] is None


def test_residual_correlation_is_blind_to_the_redundancy_it_must_catch():
    """step9 失败的最小复现。

    两个候选都是同一个既有因子的"加噪副本"（概念上完全冗余），
    但它们的**残差**几乎不相关——按残差聚类会双双放过。
    协议修正后必须仍然判为 redundant。
    """
    e = _panel(1.0, seed=5)
    a1 = _panel(0.3, seed=6, base=e)
    a2 = _panel(0.3, seed=7, base=e)

    # 残差相关：对 e 做完横截面正交后，两者几乎无关
    resid_corrs = []
    for d in DATES:
        x = pd.concat([a1.loc[d], a2.loc[d], e.loc[d]], axis=1)
        x.columns = ["a1", "a2", "e"]
        r1 = x["a1"] - x["a1"].cov(x["e"]) / x["e"].var() * x["e"]
        r2 = x["a2"] - x["a2"].cov(x["e"]) / x["e"].var() * x["e"]
        resid_corrs.append(r1.corr(r2))
    assert np.mean(resid_corrs) < 0.5          # 残差相关看不出冗余

    # 原始秩相关看得很清楚
    raw = [a1.loc[d].corr(a2.loc[d], method="spearman") for d in DATES]
    assert np.mean(raw) > 0.9

    for cand in (a1, a2):
        r = redundancy_diagnostics(cand, {"E": e}, _feats(E=e), CONFIG)
        assert abs(r["max_corr_existing"]) > 0.8
        assert r["redundant"]


def test_r2_alone_does_not_mark_redundant_when_require_both():
    """§10：候选是若干个既有特征的组合时，R² 很高但与任何**单个**因子
    相关都不高 —— require_both 下不算 redundant。"""
    f1 = _panel(1.0, seed=8)
    f2 = _panel(1.0, seed=9)
    cand = f1 + f2
    r = redundancy_diagnostics(cand, {"f1": f1, "f2": f2},
                               _feats(f1=f1, f2=f2), CONFIG)
    assert r["r2_existing"] > 0.85             # 被既有特征基本张成
    assert abs(r["max_corr_existing"]) < 0.85
    assert not r["redundant"]


def test_r2_is_reported_separately_from_validity():
    """§11：R² 只说明"像不像"，不说明"有没有 alpha"。函数只报告，
    不下有效性结论。"""
    f1 = _panel(1.0, seed=10)
    feats = _feats(F1=f1)
    r = redundancy_diagnostics(f1, {"F1": f1}, feats, CONFIG)
    assert r["r2_existing"] == pytest.approx(1.0, abs=1e-6)
    assert r["redundant"]
    assert "alpha" not in r and "validity" not in r
