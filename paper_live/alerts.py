# -*- coding: utf-8 -*-
"""告警（spec §29 / §30 / §31）。

**只生成 warning，绝不执行交易、绝不修改仓位、绝不改参数。**
每条告警都带 level / code / detail，写进 forward_holdout/alerts/<date>.json。
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

INFO, WARNING, CRITICAL = "INFO", "WARNING", "CRITICAL"


def _alert(level: str, code: str, detail: str, **extra) -> dict:
    return {"level": level, "code": code, "detail": detail, **extra}


def _num(v, fmt: str = ".2f", default: str = "NA") -> str:
    """漂移字典里的字段可能缺失，格式化前必须先挡住 None。"""
    try:
        return format(float(v), fmt) if v is not None and np.isfinite(v) \
            else default
    except (TypeError, ValueError):
        return default


def check_alerts(metrics: Optional[dict] = None,
                 drift: Optional[dict] = None,
                 audit: Optional[dict] = None,
                 cfg: Optional[dict] = None,
                 history: Optional[dict] = None,
                 **_) -> List[dict]:
    """由当日状态生成告警列表。history 可选，含 turnover_median / ic_series。"""
    s = (cfg or {}).get("paper_live", {})
    cfg_alerts = s.get("alerts", {})
    out: List[dict] = []
    metrics = metrics or {}
    drift = drift or {}
    audit = audit or {}
    history = history or {}

    # ---- §24 PIT / 数据完整性 -------------------------------------------
    st = audit.get("status")
    if st == "INVALID":
        bad = [c["name"] for c in audit.get("checks", [])
               if c.get("status") == "INVALID"]
        out.append(_alert(CRITICAL, "PIT_FAILURE",
                          f"PIT 审计未通过：{bad}；本日不得作为 forward 观测"))
    elif st == "WARNING":
        bad = [c["name"] for c in audit.get("checks", [])
               if c.get("status") == "WARNING"]
        out.append(_alert(WARNING, "DATA_QUALITY_WARNING",
                          f"检查项告警：{bad}"))

    # ---- §20 strategy drift ---------------------------------------------
    sd = drift.get("strategy", {})
    if sd.get("status") == "DRIFT_DETECTED":
        out.append(_alert(CRITICAL, "STRATEGY_DRIFT",
                          f"冻结工件不一致：{sd.get('mismatches')}"))
    elif sd.get("status") == "UNFROZEN":
        out.append(_alert(WARNING, "STRATEGY_UNFROZEN",
                          "配置尚未冻结，无法证明策略未变"))

    # ---- §21 model drift ------------------------------------------------
    md = drift.get("model", {})
    if md.get("status") == "MODEL_DRIFT_WARNING":
        out.append(_alert(WARNING, "MODEL_DRIFT",
                          f"预测分布漂移（z_mean={_num(md.get('z_mean'))}, "
                          f"z_std={_num(md.get('z_std'))}）；不自动修复"))
    cd = drift.get("concentration", {})
    if cd.get("status") == "CONCENTRATION_WARNING":
        out.append(_alert(WARNING, "CONCENTRATION_WARNING",
                          f"Top1 预测 z={_num(cd.get('top1_z'))} 极端偏高；"
                          f"仍然使用冻结策略，不调整"))

    # ---- §30 drawdown ----------------------------------------------------
    dd = metrics.get("drawdown")
    if dd is not None and np.isfinite(dd):
        for thr in sorted(cfg_alerts.get("drawdown_thresholds", []),
                          reverse=True):
            if dd <= thr:
                out.append(_alert(
                    WARNING, "DRAWDOWN_ALERT",
                    f"回撤 {dd:.2%} 触发阈值 {thr:.0%}；只报警，不自动减仓",
                    drawdown=float(dd), threshold=float(thr)))
                break

    # ---- 换手异常 --------------------------------------------------------
    to = metrics.get("turnover")
    med = history.get("turnover_median")
    mult = float(cfg_alerts.get("turnover_warn_multiple", 3.0))
    if to is not None and med and np.isfinite(to) and med > 0 and \
            to > mult * med:
        out.append(_alert(WARNING, "ABNORMAL_TURNOVER",
                          f"换手 {to:.2f} 超过历史中位数 {med:.2f} 的 "
                          f"{mult:.1f} 倍", turnover=float(to),
                          median=float(med)))

    # ---- §17 连续 IC 为负（只提示，不改模型）-----------------------------
    ic_series = history.get("ic_series")
    n_warn = int(cfg_alerts.get("ic_negative_months_warn", 2))
    if ic_series is not None and len(ic_series) >= n_warn:
        recent = list(ic_series)[-n_warn:]
        if all(x is not None and np.isfinite(x) and x < 0 for x in recent):
            out.append(_alert(WARNING, "IC_NEGATIVE_STREAK",
                              f"连续 {n_warn} 期 IC < 0；只记录，"
                              f"不调参、不换模型"))

    return out


def summarize(alerts: List[dict]) -> dict:
    by_level: Dict[str, int] = {}
    for a in alerts:
        by_level[a["level"]] = by_level.get(a["level"], 0) + 1
    return {"n": len(alerts), "by_level": by_level,
            "codes": [a["code"] for a in alerts]}
