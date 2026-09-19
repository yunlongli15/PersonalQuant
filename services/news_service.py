# -*- coding: utf-8 -*-
"""新闻 / 公告事件（spec §32）。

数据来自 `data/derived/news/news_events.parquet`（176k 行 × 18 列）。
LLM 分析如果存在，**必须单独标注 AI GENERATED**（§25 / §32）。
"""

from __future__ import annotations

from typing import List, Optional

import pandas as pd

from ._common import PROJECT_ROOT, read_parquet, safe, unavailable

EVENTS = PROJECT_ROOT / "data" / "derived" / "news" / "news_events.parquet"
COLS = ["publication_time", "symbol", "event_type", "direction",
        "importance", "confidence", "novelty", "risk"]

DIRECTION_CN = {"positive": "利好", "negative": "利空", "neutral": "中性",
                "unknown": "未知", "": "未知"}


@safe(label="新闻事件")
def latest(limit: int = 100, symbols: Optional[List[str]] = None,
           min_importance: Optional[float] = None) -> dict:
    df = read_parquet(EVENTS)
    if df is None or df.empty:
        return unavailable("还没有新闻事件数据（跑 scripts/news/update_news.py）")
    have = [c for c in COLS if c in df.columns]
    df = df[have].copy()
    df["publication_time"] = pd.to_datetime(df["publication_time"],
                                            errors="coerce")
    df = df.dropna(subset=["publication_time"])
    if symbols:
        df = df[df["symbol"].isin(symbols)]
    if min_importance is not None and "importance" in df.columns:
        df = df[pd.to_numeric(df["importance"], errors="coerce")
                >= float(min_importance)]
    df = df.sort_values("publication_time", ascending=False).head(int(limit))

    rows = []
    for _, r in df.iterrows():
        d = str(r.get("direction") or "")
        rows.append({
            "date": str(pd.Timestamp(r["publication_time"]).date()),
            "time": str(pd.Timestamp(r["publication_time"])),
            "symbol": r.get("symbol"),
            "event_type": r.get("event_type"),
            "direction": d,
            "direction_cn": DIRECTION_CN.get(d, d or "未知"),
            "importance": _f(r.get("importance")),
            "confidence": _f(r.get("confidence")),
            "novelty": _f(r.get("novelty")),
            "risk": _f(r.get("risk")),
        })
    return {"available": True, "rows": rows, "n": len(rows),
            "total_events": int(len(df)),
            "source": "data/derived/news/news_events.parquet",
            "tag": "RULE-BASED"}


def _f(v):
    try:
        return None if v is None or pd.isna(v) else float(v)
    except (TypeError, ValueError):
        return None


@safe(label="LLM 分析")
def llm_analysis(symbol: Optional[str] = None) -> dict:
    """LLM 输出单独一条通道，**明确标注 AI GENERATED**（§25 / §32）。

    没有 DEEPSEEK_API_KEY 时这里永远是 not available —— 如实说明，
    绝不把规则结果包装成 LLM 结论。
    """
    import os
    if not os.environ.get("DEEPSEEK_API_KEY", "").strip():
        return unavailable("未配置 DEEPSEEK_API_KEY —— LLM 层未启用"
                           "（系统按 RULE_BASED_ONLY 运行）")
    return unavailable("LLM 分析通道尚未产出可展示的结果")


@safe(label="新闻覆盖")
def coverage() -> dict:
    p = PROJECT_ROOT / "data" / "derived" / "news" / "news_coverage.parquet"
    df = read_parquet(p)
    if df is None or df.empty:
        return unavailable("没有覆盖数据")
    return {"available": True, "n_symbols": int(len(df)),
            "note": "SZSE 回填仅 top-60 大市值（已知限制）"}
