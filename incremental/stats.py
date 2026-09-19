# -*- coding: utf-8 -*-
"""DeltaIC 的统计：block bootstrap、Evidence Score、候选门槛。

§7 的核心要求：DeltaIC(t) 必须**配对**统计，而且不能当 iid 处理——
横截面 IC 序列有时间自相关，普通 bootstrap 会把置信区间做得过窄。
这里同时算 block bootstrap（主）与 iid bootstrap（对照），
两者差距就是"忽略时间相关性"的代价。
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# block bootstrap
# ---------------------------------------------------------------------------

def block_bootstrap(x, block: int = 3, n_resamples: int = 1000,
                    confidence: float = 0.95, seed: int = 0) -> dict:
    """Circular block bootstrap of the mean of a time-ordered series.

    x 必须按时间排序（每月一个观测）。block = 连续月数；block=1 即 iid。
    """
    s = pd.Series(x).dropna().to_numpy(dtype=float)
    n = len(s)
    if n == 0:
        return {"n": 0, "mean": np.nan, "ci_low": np.nan, "ci_high": np.nan,
                "iid_ci_low": np.nan, "iid_ci_high": np.nan, "block": block}
    mean = float(s.mean())

    def _ci(blk: int) -> tuple:
        # 每次都从同一个种子重开：block 与 iid 两条曲线必须用同一串随机数，
        # 否则 block=1 时两者只是"两次不同的抽样"，无法作对照。
        rng = np.random.default_rng(seed)

        def _resample() -> np.ndarray:
            if blk <= 1:
                return rng.choice(s, size=n, replace=True)
            n_blocks = int(np.ceil(n / blk))
            starts = rng.integers(0, n, size=n_blocks)
            idx = (starts[:, None] + np.arange(blk)[None, :]).ravel() % n
            return s[idx][:n]

        means = np.array([_resample().mean() for _ in range(n_resamples)])
        a = (1 - confidence) / 2
        return (float(np.quantile(means, a)),
                float(np.quantile(means, 1 - a)))

    lo, hi = _ci(int(block))
    ilo, ihi = _ci(1)
    return {
        "n": n, "mean": mean, "block": int(block),
        "n_resamples": int(n_resamples), "confidence": float(confidence),
        "ci_low": lo, "ci_high": hi,
        "iid_ci_low": ilo, "iid_ci_high": ihi,
        "ci_width": hi - lo, "iid_ci_width": ihi - ilo,
    }


# ---------------------------------------------------------------------------
# evidence score (§15)
# ---------------------------------------------------------------------------

def _clip01(v: float) -> float:
    if not np.isfinite(v):
        return 0.0
    return float(min(max(v, 0.0), 1.0))


def evidence_score(metrics: dict, config: dict) -> dict:
    """透明加权分。每个分量先归一到 [0,1] 再加权——权重全在 yaml 里。

    只奖励**正向**增量：负的 DeltaIC 在 LightGBM 里无法靠翻转救回。
    """
    comp = config["factor_selection_v2"]["evidence_score"]["components"]
    parts: Dict[str, float] = {}

    if "incremental_icir" in comp:
        c = comp["incremental_icir"]
        parts["incremental_icir"] = _clip01(
            (metrics.get("delta_icir") or 0.0) / float(c["cap"]))
    if "incremental_rankicir" in comp:
        c = comp["incremental_rankicir"]
        parts["incremental_rankicir"] = _clip01(
            (metrics.get("delta_rank_icir") or 0.0) / float(c["cap"]))
    if "positive_fold_ratio" in comp:
        parts["positive_fold_ratio"] = _clip01(
            metrics.get("positive_fold_ratio") or 0.0)
    if "positive_month_ratio" in comp:
        parts["positive_month_ratio"] = _clip01(
            metrics.get("delta_ic_positive_ratio") or 0.0)
    if "independence" in comp:
        parts["independence"] = _clip01(1.0 - (metrics.get("r2_existing") or 0.0))
    if "coverage" in comp:
        c = comp["coverage"]
        parts["coverage"] = _clip01(
            (metrics.get("coverage") or 0.0) / float(c["target"]))
    if "turnover" in comp:
        c = comp["turnover"]
        parts["turnover"] = _clip01(
            1.0 - (metrics.get("turnover") or 0.0) / float(c["cap"]))
    if "stability" in comp:
        c = comp["stability"]
        # 稳定性 = 各 fold DeltaIC 均值之间的离散度（越小越稳）。
        # 用 fold 数少，所以只在 fold >= 2 时算；否则给 0 分（不奖励没证据）。
        folds = [v["delta_ic_mean"] for v in
                 (metrics.get("per_fold") or {}).values()]
        mean = metrics.get("delta_ic_mean") or 0.0
        if len(folds) >= 2 and abs(mean) > 1e-12 and mean > 0:
            cv = float(np.std(folds, ddof=0) / abs(mean))
            parts["stability"] = _clip01(1.0 - cv / float(c["cv_cap"]))
        else:
            parts["stability"] = 0.0

    total_w = sum(float(comp[k].get("weight", 0.0))
                  for k in parts if k in comp)
    score = 0.0
    for k, v in parts.items():
        w = float(comp[k].get("weight", 0.0))
        score += w * v
    if total_w > 0:
        score /= total_w          # 归一到 [0,1]，便于跨候选比较
    return {"evidence_score": float(score), "components": parts,
            "total_weight": float(total_w)}


# ---------------------------------------------------------------------------
# gates (§14)
# ---------------------------------------------------------------------------

def evaluate_gates(metrics: dict, config: dict, *, pit_pass: bool,
                   redundant: bool) -> dict:
    """9 项候选门槛。**不要求统计显著**——A 股低频横截面 effect size 本来就小，
    机械的 p < 0.05 会筛掉所有真实但微弱的增量。"""
    g = config["factor_selection_v2"]["gates"]
    boot = metrics.get("bootstrap") or {}
    checks = {
        "gate1_research_direction": bool(
            (metrics.get("delta_ic_mean") or 0.0) > 0
            and (metrics.get("delta_rank_ic_mean") or 0.0) > 0),
        "gate2_min_positive_folds": bool(
            (metrics.get("n_positive_folds") or 0) >= int(g["min_positive_folds"])),
        "gate3_inc_ic_not_negative": bool(
            (metrics.get("delta_ic_mean") or 0.0) > 0),
        "gate4_inc_rankic_not_negative": bool(
            (metrics.get("delta_rank_ic_mean") or 0.0) > 0),
        "gate5_bootstrap_not_fully_negative": bool(
            (boot.get("ci_high") or 0.0) > 0.0)
        if g["require_bootstrap_not_fully_negative"] else True,
        "gate6_coverage": bool(
            (metrics.get("coverage") or 0.0) >= float(g["min_coverage"])),
        "gate7_pit": bool(pit_pass) if g["require_pit_pass"] else True,
        "gate8_turnover": bool(
            (metrics.get("turnover") or 0.0) <= float(g["max_turnover"])),
        "gate9_not_redundant": (not redundant)
        if g["require_not_fully_redundant"] else True,
    }
    failed = [k for k, v in checks.items() if not v]
    return {
        "gates": checks,
        "gates_passed": len(checks) - len(failed),
        "gates_failed": failed,
        "status": "PASS" if not failed else "REJECT",
    }
