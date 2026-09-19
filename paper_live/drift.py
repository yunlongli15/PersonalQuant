# -*- coding: utf-8 -*-
"""漂移检查（spec §20 / §21 / §22 / §23）。

**只监控，绝不自动修复。** 发现漂移 → 生成 WARNING → 写进报告。
不重训、不调参、不改阈值、不换模型。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# §20 Strategy drift
# ---------------------------------------------------------------------------

def strategy_drift(cfg: dict) -> dict:
    """当前 strategy/model/feature 是否与冻结版本一致。"""
    from .config import verify_freeze
    v = verify_freeze(cfg)
    if not v["is_frozen"]:
        return {"status": "UNFROZEN", "drift": None, "detail": v["detail"],
                "mismatches": []}
    return {
        "status": "DRIFT_DETECTED" if v["drift"] else "OK",
        "drift": bool(v["drift"]),
        "mismatches": v["mismatches"] + v["new_keys"],
        "detail": v["detail"],
    }


# ---------------------------------------------------------------------------
# §21 Model drift
# ---------------------------------------------------------------------------

def load_model_baseline() -> Optional[pd.Series]:
    """历史（valid + test）预测分分布，作为 forward 的对照基线。

    注意：这是**只读对照**，绝不回流到任何选择路径。
    """
    parts = []
    for name in ("preds_s3_valid.parquet", "preds_s3_test.parquet"):
        p = PROJECT_ROOT / "experiments" / "portfolio" / name
        if p.exists():
            parts.append(pd.read_parquet(p)["prediction"])
    if not parts:
        return None
    return pd.concat(parts, ignore_index=True)


def model_drift(current: pd.Series, baseline: Optional[pd.Series],
                std_multiple: float = 3.0) -> dict:
    """预测分布漂移。score mean/std/偏度 与历史基线的 z 距离。"""
    cur = pd.Series(current).dropna()
    if cur.empty:
        return {"status": "NO_DATA", "detail": "本日无预测"}
    out = {"n": int(len(cur)), "score_mean": float(cur.mean()),
           "score_std": float(cur.std(ddof=0)),
           "score_skew": float(cur.skew()) if len(cur) > 3 else np.nan}
    base = pd.Series(baseline).dropna() if baseline is not None else \
        pd.Series(dtype=float)
    if base.empty:
        out["status"] = "NO_BASELINE"
        out["detail"] = "没有历史预测分布可对照"
        return out
    z_mean = (cur.mean() - base.mean()) / base.std(ddof=0) \
        if base.std(ddof=0) > 0 else np.nan
    z_std = (cur.std(ddof=0) - base.std(ddof=0)) / base.std(ddof=0) \
        if base.std(ddof=0) > 0 else np.nan
    out.update({"baseline_mean": float(base.mean()),
                "baseline_std": float(base.std(ddof=0)),
                "z_mean": float(z_mean), "z_std": float(z_std),
                "threshold": std_multiple})
    drift = (np.isfinite(z_mean) and abs(z_mean) > std_multiple) or \
            (np.isfinite(z_std) and abs(z_std) > std_multiple)
    out["status"] = "MODEL_DRIFT_WARNING" if drift else "OK"
    out["detail"] = ("预测分布相对历史漂移" if drift else "预测分布与历史一致")
    return out


def prediction_concentration(predictions: pd.Series,
                             top1_z_threshold: float = 3.0) -> dict:
    """Top-1 相对截面的极端程度（§31）。只报警，仍然使用冻结策略。"""
    s = pd.Series(predictions).dropna()
    if len(s) < 10 or s.std(ddof=0) == 0:
        return {"status": "NO_DATA"}
    z = float((s.max() - s.mean()) / s.std(ddof=0))
    return {"status": "CONCENTRATION_WARNING" if z > top1_z_threshold else "OK",
            "top1_z": z, "threshold": top1_z_threshold,
            "top1": float(s.max())}


# ---------------------------------------------------------------------------
# §22 News drift
# ---------------------------------------------------------------------------

def news_drift(current: Dict[str, float], baseline: Dict[str, dict]) -> dict:
    """新闻/公告因子的分布位移。current/baseline: {factor: 值 / 统计量}。"""
    if not current:
        return {"status": "NO_DATA", "detail": "本日未消费新闻因子"}
    if not baseline:
        return {"status": "NO_BASELINE", "detail": "没有历史新闻基线",
                "current": current}
    shifted = []
    for k, v in current.items():
        b = baseline.get(k)
        if not b or not np.isfinite(v):
            continue
        sd = b.get("std", 0.0)
        if sd and abs(v - b.get("mean", 0.0)) / sd > 3.0:
            shifted.append(k)
    return {"status": "NEWS_DRIFT_WARNING" if shifted else "OK",
            "shifted": shifted, "current": current,
            "detail": f"{len(shifted)} 个新闻因子分布位移超过 3σ" if shifted
            else "新闻因子分布与历史一致"}


# ---------------------------------------------------------------------------
# §23 Data drift
# ---------------------------------------------------------------------------

def data_drift(current: dict, baseline: Optional[dict] = None,
               tol: float = 0.30) -> dict:
    """股票数量 / 缺失率 / 覆盖率 相对基线的变化。"""
    if not current:
        return {"status": "NO_DATA"}
    if not baseline:
        return {"status": "NO_BASELINE", "current": current}
    issues = []
    for key in ("n_symbols", "feature_missing_rate", "custom_coverage"):
        c, b = current.get(key), baseline.get(key)
        if c is None or b is None or not np.isfinite(b) or b == 0:
            continue
        rel = abs(c - b) / abs(b)
        if rel > tol:
            issues.append(f"{key}: {b:.4f} -> {c:.4f} ({rel:+.0%})")
    return {"status": "DATA_QUALITY_WARNING" if issues else "OK",
            "issues": issues, "current": current, "baseline": baseline}


def load_baseline(path) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_baseline(path, payload: dict) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                 encoding="utf-8")
    return p
