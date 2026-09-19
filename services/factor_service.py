# -*- coding: utf-8 -*-
"""因子排行榜与增量 IC（spec §31 / §34）。

**只读展示。** GUI 不允许改因子选择（§31）。
"""

from __future__ import annotations

import pandas as pd

from ._common import PROJECT_ROOT, safe, unavailable

LEADERBOARDS = [
    ("factor_run_001", "experiments/factors/factor_run_001/leaderboard.csv",
     "STEP 4 全因子研究"),
    ("micro_run_001", "experiments/factors/micro_run_001/leaderboard.csv",
     "STEP 8 微结构因子"),
    ("news_factor_run_001",
     "experiments/news/news_factor_run_001/leaderboard_news.csv",
     "STEP 5 新闻因子"),
]
COLS = ["factor", "category", "IC_research", "RankIC_research", "ICIR_research",
        "coverage", "turnover", "RankIC_test", "ICIR_test"]


def _read(path: str):
    p = PROJECT_ROOT / path
    if not p.exists():
        return None
    try:
        return pd.read_csv(p)
    except Exception:                                          # noqa: BLE001
        return None


@safe(label="因子排行榜")
def leaderboards() -> dict:
    out = []
    for key, path, label in LEADERBOARDS:
        df = _read(path)
        if df is None or df.empty:
            continue
        have = [c for c in COLS if c in df.columns]
        sub = df[have].copy()
        if "ICIR_research" in sub.columns:
            sub = sub.reindex(
                sub["ICIR_research"].abs().sort_values(ascending=False).index)
        out.append({"key": key, "label": label,
                    "rows": sub.head(40).to_dict("records"),
                    "n": int(len(df))})
    if not out:
        return unavailable("还没有因子研究结果"
                           "（跑 scripts/research_all_factors.py）")
    return {"available": True, "boards": out}


@safe(label="增量 IC")
def incremental() -> dict:
    """STEP 9 的增量 IC 结论（research candidate，**不是生产策略**）。"""
    p = PROJECT_ROOT / "reports" / "incremental_factor_candidates.csv"
    if not p.exists():
        return unavailable("还没有增量 IC 结果（跑 STEP 9 选择流程）")
    df = pd.read_csv(p)
    keep = ["factor", "research_icir", "incremental_ic", "incremental_rank_ic",
            "incremental_icir", "bootstrap_ci_low", "bootstrap_ci_high",
            "prediction_corr", "r2_existing", "coverage", "evidence_score",
            "status"]
    have = [c for c in keep if c in df.columns]
    sub = df[have].copy()
    if "evidence_score" in sub.columns:
        sub = sub.sort_values("evidence_score", ascending=False)
    return {"available": True, "rows": sub.to_dict("records"),
            "n": int(len(df)),
            "tag": "RESEARCH CANDIDATE",
            "note": "研究候选，未进入 strategy_v2；显著性见 "
                    "reports/incremental_factor_selection_v2.md"}


@safe(label="当前信号")
def current_signals(limit: int = 50) -> dict:
    from pipeline.signals import load_signals, signals_state
    df = load_signals()
    if df is None or df.empty:
        return unavailable("还没有信号快照（先跑 refresh_all.py）")
    top = df.nsmallest(int(limit), "raw_rank")
    return {"available": True, "rows": top.to_dict("records"),
            "n": int(len(df)), "state": signals_state()}
