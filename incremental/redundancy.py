# -*- coding: utf-8 -*-
"""冗余诊断（**协议修正版**）。

上一轮（reports/step9_independent_info.md）用**残差**相关做聚类，是错的：

    R² 高达 0.9 的因子，残差只剩 10% 的方差且以噪声为主 →
    两个同样冗余的因子，残差相关反而很低 → 最冗余的看起来最"独立"。
    实测 3 个波动率因子（R² 0.89~0.93）就这样逃过了聚类。

本版修正（§10）：
  主判据 = **原始因子**的横截面秩相关（概念冗余是原始量纲上的事）；
  残差相关 + 回归 R² 只作诊断输出，不参与判据。

同时严守 §11：**R² 高只说明"这个因子与现有因子像"，不说明它有没有 alpha。**
有效性一律以 incremental IC 为准。
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd


def _rank_cross_section(frame: pd.DataFrame) -> pd.DataFrame:
    """Rank each column across stocks (axis=0). 见 step9 的轴 bug 记录。"""
    return frame.rank(axis=0, pct=True, method="average")


def _mean_spearman(a: pd.DataFrame, b: pd.DataFrame) -> float:
    """Average per-date cross-sectional Spearman between two panels."""
    vals = []
    for d in a.index.intersection(b.index):
        m = pd.concat([a.loc[d], b.loc[d]], axis=1).dropna()
        if len(m) < 30:
            continue
        vals.append(m.iloc[:, 0].corr(m.iloc[:, 1], method="spearman"))
    return float(np.nanmean(vals)) if vals else np.nan


def redundancy_diagnostics(candidate_panel: pd.DataFrame,
                           existing_panels: Dict[str, pd.DataFrame],
                           feature_panel: Optional[pd.DataFrame] = None,
                           config: Optional[dict] = None) -> dict:
    """Return raw-correlation redundancy + (diagnostic) regression R².

    candidate_panel:  date × symbol，候选因子原始值
    existing_panels:  {name: date × symbol}，M0 里的自定义因子
    feature_panel:    date × symbol × feature 不可行，故传 {date: DataFrame}
                      形式的既有特征面板；缺省则跳过 R²
    """
    cfg = (config or {}).get("factor_selection_v2", {}).get("redundancy", {})
    corr_thr = float(cfg.get("max_corr_threshold", 0.85))
    r2_thr = float(cfg.get("r2_threshold", 0.90))
    require_both = bool(cfg.get("require_both", True))

    cors = {n: _mean_spearman(candidate_panel, p)
            for n, p in existing_panels.items()}
    cors = {k: v for k, v in cors.items() if np.isfinite(v)}
    max_corr = max((abs(v) for v in cors.values()), default=np.nan)
    argmax = (max(cors, key=lambda k: abs(cors[k])) if cors else None)

    r2 = np.nan
    resid_ic_placeholder = None      # 残差相关只作诊断，由调用方补充
    if feature_panel is not None:
        r2 = _regression_r2(candidate_panel, feature_panel)
    resid_ic_placeholder = None

    corr_hit = np.isfinite(max_corr) and max_corr >= corr_thr
    r2_hit = np.isfinite(r2) and r2 >= r2_thr
    redundant = (corr_hit and r2_hit) if require_both else (corr_hit or r2_hit)

    return {
        "max_corr_existing": float(max_corr) if np.isfinite(max_corr) else np.nan,
        "max_corr_with": argmax,
        "corr_with_existing": {k: float(v) for k, v in cors.items()},
        "r2_existing": float(r2) if np.isfinite(r2) else np.nan,
        "corr_threshold": corr_thr,
        "r2_threshold": r2_thr,
        "redundant": bool(redundant),
        "redundant_reason": (
            None if not redundant else
            f"原始秩相关 {max_corr:.2f} >= {corr_thr} 且 R² {r2:.2f} >= {r2_thr}"
            if (corr_hit and r2_hit) else
            (f"原始秩相关 {max_corr:.2f} >= {corr_thr}" if corr_hit
             else f"R² {r2:.2f} >= {r2_thr}")),
    }


def residual_ic(candidate_panel: pd.DataFrame,
                feature_by_date: Dict[pd.Timestamp, pd.DataFrame],
                label: pd.DataFrame,
                min_stocks: int = 30) -> dict:
    """候选因子对既有特征正交化之后的残差 IC（**辅助诊断**，§19）。

    和 step9 一样是真·横截面正交投影（不是"贴个残差标签"）。但按 §19
    它只作辅助：主指标永远是 incremental_model_IC（DeltaIC）。
    """
    rows = []
    for d in candidate_panel.index:
        feat = feature_by_date.get(d)
        if feat is None or feat.empty or d not in label.index:
            continue
        y = label.loc[d]
        df = feat.reindex(index=candidate_panel.columns)
        m = pd.concat([candidate_panel.loc[d].rename("__f"), df,
                       y.rename("__y")], axis=1).dropna()
        if len(m) < min_stocks:
            continue
        X = _rank_cross_section(m.drop(columns=["__f", "__y"])).to_numpy(
            dtype=float)
        xv = m["__f"].rank(pct=True).to_numpy(dtype=float)
        yv = m["__y"].rank(pct=True).to_numpy(dtype=float)
        if xv.std() == 0 or yv.std() == 0:
            continue
        r = xv - X @ (np.linalg.pinv(X) @ xv)
        if r.std() == 0:
            continue
        rows.append({"date": d,
                     "residual_ic": float(pd.Series(r).corr(
                         pd.Series(yv), method="spearman"))})
    if not rows:
        return {"residual_ic_mean": np.nan, "residual_icir": np.nan,
                "residual_ic_series": pd.DataFrame(columns=["date",
                                                            "residual_ic"])}
    s = pd.DataFrame(rows).set_index("date")["residual_ic"]
    sd = s.std(ddof=0)
    return {
        "residual_ic_mean": float(s.mean()),
        "residual_icir": float(s.mean() / sd) if sd > 0 else np.nan,
        "residual_ic_series": s,
    }


def _regression_r2(candidate_panel: pd.DataFrame,
                   feature_by_date: Dict[pd.Timestamp, pd.DataFrame],
                   min_stocks: int = 30) -> float:
    """Cross-sectional R² of candidate rank on the existing feature ranks.

    PIT-safe：只用当日横截面。数值上用伪逆最小二乘（唯一解 = 投影）。
    """
    r2s = []
    for d in candidate_panel.index:
        feat = feature_by_date.get(d)
        if feat is None or feat.empty:
            continue
        y = candidate_panel.loc[d]
        df = feat.reindex(index=y.index)
        m = pd.concat([y.rename("__y"), df], axis=1).dropna()
        if len(m) < min_stocks:
            continue
        X = _rank_cross_section(m.drop(columns="__y")).to_numpy(dtype=float)
        yv = m["__y"].rank(pct=True).to_numpy(dtype=float)
        if yv.std() == 0:
            continue
        fit = X @ (np.linalg.pinv(X) @ yv)
        resid = yv - fit
        r2s.append(float(1.0 - resid.var() / yv.var()))
    return float(np.mean(r2s)) if r2s else np.nan
