# -*- coding: utf-8 -*-
"""每日告警（STEP 12, spec §17 / §18）。

    DATA_ERROR / DATA_WARNING / PIT_FAILURE / STRATEGY_DRIFT / MODEL_DRIFT /
    NEWS_DRIFT / EXCESS_TURNOVER / DRAWDOWN_WARNING / FORWARD_INVALID /
    PIPELINE_FAILURE

**只报警。** 绝不自动调整策略、绝不重训模型、绝不改组合权重（§18）。
本模块没有任何写入口，只返回列表。
"""

from __future__ import annotations

from typing import Dict, List

INFO, WARNING, ERROR, CRITICAL = "INFO", "WARNING", "ERROR", "CRITICAL"

CODES = ("DATA_ERROR", "DATA_WARNING", "PIT_FAILURE", "STRATEGY_DRIFT",
         "MODEL_DRIFT", "NEWS_DRIFT", "EXCESS_TURNOVER", "DRAWDOWN_WARNING",
         "FORWARD_INVALID", "PIPELINE_FAILURE")

DRAWDOWN_THRESHOLDS = (-0.05, -0.10, -0.15)


def _a(level: str, code: str, detail: str, **extra) -> dict:
    assert code in CODES, f"未登记的告警码 {code}"
    return {"level": level, "code": code, "detail": detail,
            "action": "none（只报警，不调整任何东西）", **extra}


def evaluate(ctx) -> List[dict]:
    """由一次运行上下文生成告警列表。"""
    from pipeline import daily as D

    run = ctx.run
    out: List[dict] = []
    sd = ctx.store_data

    # ---- 流水线级 -------------------------------------------------------
    for name in run.failed():
        out.append(_a(ERROR, "PIPELINE_FAILURE", f"任务失败：{name}"))
    if run.blocked():
        out.append(_a(WARNING, "PIPELINE_FAILURE",
                      f"因依赖失败被跳过：{run.blocked()}"))

    for w in run.warnings:
        if w.startswith(D.PRODUCTION_DRIFT):
            out.append(_a(CRITICAL, "STRATEGY_DRIFT", w))
        elif w.startswith(D.WAITING_FOR_FORWARD_DATA):
            out.append(_a(INFO, "FORWARD_INVALID", w))
        elif w.startswith("source_health"):
            out.append(_a(WARNING, "DATA_WARNING", w))

    # ---- 冻结 / 漂移 -----------------------------------------------------
    fz = sd.get("freeze") or {}
    if fz.get("drift"):
        out.append(_a(CRITICAL, "STRATEGY_DRIFT",
                      f"生产工件与冻结记录不一致：{fz.get('mismatches')}"))
    elif not fz.get("frozen"):
        out.append(_a(WARNING, "STRATEGY_DRIFT", "尚未建立生产冻结记录"))

    # ---- 数据健康 --------------------------------------------------------
    fresh = sd.get("freshness") or []
    for r in fresh:
        if r.get("status") == "MISSING":
            out.append(_a(ERROR, "DATA_ERROR",
                          f"{r.get('domain')} 缺失"))
        elif r.get("status") == "STALE" and r.get("domain") != "News":
            out.append(_a(WARNING, "DATA_WARNING",
                          f"{r.get('domain')} 滞后至 {r.get('latest')}"))

    # ---- Paper live ------------------------------------------------------
    paper = sd.get("paper_result")
    if paper is not None:
        audit = (getattr(paper, "audit", None) or {})
        if audit.get("status") == "INVALID":
            bad = [c["name"] for c in audit.get("checks", [])
                   if c.get("status") == "INVALID"]
            out.append(_a(CRITICAL, "PIT_FAILURE",
                          f"PIT 审计未通过：{bad}；本日不作为 forward 观测"))
        for d in (getattr(paper, "alerts", None) or []):
            code = {"MODEL_DRIFT": "MODEL_DRIFT",
                    "DATA_QUALITY_WARNING": "DATA_WARNING",
                    "CONCENTRATION_WARNING": "DATA_WARNING"}.get(
                        d.get("code"), None)
            if code:
                out.append(_a(WARNING, code, d.get("detail", "")))
        drift = getattr(paper, "drift", None) or {}
        if (drift.get("model") or {}).get("status") == "MODEL_DRIFT_WARNING":
            out.append(_a(WARNING, "MODEL_DRIFT",
                          (drift["model"] or {}).get("detail", "")))
        metrics = getattr(paper, "metrics", None) or {}
        to = metrics.get("turnover")
        if to is not None and to > 1.0:
            out.append(_a(WARNING, "EXCESS_TURNOVER",
                          f"本期换手 {to:.2f} > 1.0", turnover=float(to)))

    # ---- 回撤 ------------------------------------------------------------
    perf = sd.get("performance") or {}
    dd = perf.get("max_drawdown")
    if dd is not None and dd == dd:
        for thr in DRAWDOWN_THRESHOLDS:
            if dd <= thr:
                out.append(_a(WARNING, "DRAWDOWN_WARNING",
                              f"回撤 {dd:.2%} 触及 {thr:.0%}；只报警，"
                              f"不自动减仓", drawdown=float(dd)))
                break

    # ---- 新闻漂移 --------------------------------------------------------
    news_task = run.task("news")
    if news_task is not None and news_task.status == WARNING:
        out.append(_a(WARNING, "NEWS_DRIFT", news_task.detail))

    return out


def summarize(alerts: List[dict]) -> dict:
    by_level: Dict[str, int] = {}
    for a in alerts:
        by_level[a["level"]] = by_level.get(a["level"], 0) + 1
    return {"n": len(alerts), "by_level": by_level,
            "codes": sorted({a["code"] for a in alerts})}
