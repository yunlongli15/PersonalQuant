# -*- coding: utf-8 -*-
"""Factor selection for factor_pack_v1.

Gates (in order, all configurable in config/factor_research.yaml):
1. coverage on research dates >= min_coverage
2. |rank-ICIR| at the primary horizon on research >= min_icir (the sign is
   reported, never flipped — a factor with ICIR = -0.6 has strong inverse
   predictive power and is kept with its empirical direction recorded)
3. direction-signed IC consistency ratio >= min_positive_ic_ratio
   (max(frac IC>0, frac IC<0) — an inverse factor is consistent too)
4. sign consistency: research and valid rank-IC means share a sign
5. redundancy: from each |corr| >= cluster_threshold cluster keep the
   representative with the highest |research rank-ICIR|; the others are
   discarded with the cluster as the reason

Selection uses RESEARCH + VALID only (2018-2023). Test (2024-2025) and
2026 never enter this module.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from .evaluator import cluster_correlated


def _rank_ic(eval_res: dict, horizon: int = 20) -> dict:
    """rank-IC summary at the primary horizon for the rank normalization."""
    norm = eval_res.get("normalizations", {}).get("rank")
    if norm is None:
        return {"n": 0, "mean": np.nan, "icir": np.nan, "positive_ratio": np.nan}
    hh = norm.get("horizons", {}).get(str(horizon), {})
    return hh.get("rank_ic", {"n": 0, "mean": np.nan, "icir": np.nan,
                              "positive_ratio": np.nan})


def _sign_ratio(ic_summary: dict) -> float:
    """Direction-signed consistency: max(frac>0, frac<0)."""
    p = ic_summary.get("positive_ratio", np.nan)
    if np.isnan(p):
        return np.nan
    return float(max(p, 1.0 - p))


def select_factor_pack(
    research: Dict[str, dict],
    valid: Dict[str, dict],
    corr_matrix,
    config: dict,
    min_coverage_map: Optional[dict] = None,
) -> dict:
    """Return {selected: [...], discarded: [{factor, reason}], clusters}.

    research/valid: evaluate_factor() outputs per factor for the two
    periods. corr_matrix: pairwise correlation DataFrame (research).
    min_coverage_map: per-factor coverage threshold override (financial
    factors are selected on their restricted-universe evaluations, whose
    coverage ceiling is data-availability-limited).
    """
    sel = config.get("selection", {})
    min_cov = float(sel.get("min_coverage", 0.6))
    min_icir = float(sel.get("min_icir", 0.3))
    min_pos = float(sel.get("min_positive_ic_ratio", 0.5))
    sign_consistency = bool(sel.get("require_sign_consistency", True))
    thr = float(config.get("correlation", {}).get("cluster_threshold", 0.8))
    min_coverage_map = min_coverage_map or {}

    discarded: List[dict] = []
    passed: List[str] = []
    for name, er in research.items():
        cov = float(er.get("coverage", 0.0))
        ric = _rank_ic(er)
        cov_thr = float(min_coverage_map.get(name, min_cov))
        if cov < cov_thr:
            discarded.append({
                "factor": name,
                "reason": f"coverage {cov:.2f} < {cov_thr}",
            })
            continue
        if not np.isfinite(ric["icir"]) or abs(ric["icir"]) < min_icir:
            discarded.append({
                "factor": name,
                "reason": f"|research rank-ICIR| "
                          f"{abs(ric['icir']):.3f} < {min_icir}",
            })
            continue
        sr = _sign_ratio(ric)
        if not np.isfinite(sr) or sr < min_pos:
            discarded.append({
                "factor": name,
                "reason": f"direction consistency {sr:.2f} < {min_pos}",
            })
            continue
        if sign_consistency and name in valid:
            v_ric = _rank_ic(valid[name])
            if (np.isfinite(ric["mean"]) and np.isfinite(v_ric["mean"])
                    and ric["mean"] * v_ric["mean"] < 0):
                discarded.append({
                    "factor": name,
                    "reason": (f"research IC {ric['mean']:+.4f} vs valid IC "
                               f"{v_ric['mean']:+.4f}: sign flips"),
                })
                continue
        passed.append(name)

    # redundancy: keep the strongest representative per correlation cluster
    clusters = cluster_correlated(corr_matrix.reindex(passed), thr)
    keep = []
    for cluster in clusters:
        best = max(cluster, key=lambda n: abs(_rank_ic(research[n])["icir"]))
        keep.append(best)
        for other in cluster:
            if other != best:
                discarded.append({
                    "factor": other,
                    "reason": (f"|corr| >= {thr} with {best} "
                               f"(cluster: {', '.join(cluster)})"),
                })
    keep.sort()
    return {
        "selected": keep,
        "discarded": discarded,
        "clusters": clusters,
        "n_candidates": len(research),
    }
