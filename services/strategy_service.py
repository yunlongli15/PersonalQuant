# -*- coding: utf-8 -*-
"""策略状态卡、Paper Live、策略 vs 实际账户（spec §23 / §28 / §37 / §56）。

**只读。** GUI 不得修改 strategy_v1 / strategy_v2 / factor_pack /
paper_live 的任何冻结配置（spec §55）。
"""

from __future__ import annotations

from typing import Optional

from ._common import PROJECT_ROOT, read_json, safe, to_float, unavailable


def _pl():
    from paper_live.config import load_config
    return load_config()["paper_live"]


@safe(label="策略状态")
def status_card() -> dict:
    """§56：用户每天要知道"系统现在到底运行的是什么"。

    全部字段来自**冻结配置本身**，不是从任何结果倒推的。
    """
    from paper_live.config import verify_freeze

    s = _pl()
    fr = verify_freeze({"paper_live": s})
    sig = read_json(PROJECT_ROOT / "data/quant/signals_state.json") or {}
    return {
        "available": True,
        "strategy_version": s["strategy_version"],
        "status": "FROZEN" if fr.get("is_frozen") and not fr.get("drift")
                  else "DRIFT_DETECTED",
        "freeze_detail": fr.get("detail"),
        "frozen_at": s.get("frozen_at"),
        "alpha_signal": s["alpha"]["signal"],
        "model": s["alpha"]["model"],
        "feature_packs": s["alpha"]["feature_packs"],
        "label_horizon_days": s["alpha"]["label_horizon_days"],
        "allocation_method": s["portfolio"]["allocation_method"],
        "top_k": s["portfolio"]["top_k"],
        "rebalance": s["portfolio"]["rebalance"],
        "constraints": s["portfolio"]["constraints"],
        "execution": s["execution"],
        "capital_initial": s["capital"]["initial"],
        "forward_start_date": s["forward_start_date"],
        "record_only": s["record_only"],
        "tags": ["FROZEN", "LIVE PAPER", "RESEARCH ONLY"],
        "last_signal": sig.get("as_of"),
        "last_signal_at": sig.get("computed_at"),
        "n_signal_symbols": sig.get("n_symbols"),
    }


@safe(label="Paper Live")
def paper_live() -> dict:
    """§28：forward holdout 的观察状态。没有数据就是 NOT ENOUGH DATA。"""
    from paper_live.report import build_dashboard, metrics_frame, nav_series
    from paper_live.store import ForwardStore

    s = _pl()
    root = PROJECT_ROOT / s["paths"]["root"]
    store = ForwardStore(root, forward_start=s["forward_start_date"])
    met = metrics_frame(store)
    nav = nav_series(store)
    cfg = {"paper_live": s}
    df, payload = build_dashboard(store, cfg)

    n_periods = int(len(df))
    enough = n_periods >= 20
    return {
        "available": True,
        "strategy_version": s["strategy_version"],
        "forward_start_date": s["forward_start_date"],
        "record_only": s["record_only"],
        "n_observation_days": n_periods,
        "first_date": payload.get("first_date"),
        "last_date": payload.get("last_date"),
        "current_value": float(nav.iloc[-1]) if len(nav) else None,
        "capital_initial": s["capital"]["initial"],
        "cumulative_return": (payload.get("performance") or {})
        .get("cumulative_return"),
        "max_drawdown": (payload.get("performance") or {}).get("max_drawdown"),
        "prediction_quality": payload.get("prediction_quality"),
        "rows": df.to_dict("records") if len(df) else [],
        "enough_data": enough,
        "tags": ["LIVE PAPER", "RECORD ONLY"],
        "note": ("观察期不足 20 个交易日 —— 按 §29 显示 NOT ENOUGH DATA，"
                 "不做任何年化" if not enough else ""),
    }


@safe(label="策略 vs 实际")
def versus_actual() -> dict:
    """§37：真实账户 vs 量化 paper 组合的偏离。

    只比较，不调整。持有重合度 / 权重偏离都是**事实**，不是指令。
    """
    from pipeline.signals import load_signals
    from . import portfolio_service

    pos = portfolio_service.positions()
    if not pos.get("available"):
        return pos
    sig = load_signals()
    if sig is None or sig.empty:
        return unavailable("还没有信号快照（先跑 refresh_all.py）")

    top = sig.nsmallest(int(_pl()["portfolio"]["top_k"]), "raw_rank")
    target = {r["symbol"]: 1.0 / len(top) for _, r in top.iterrows()} \
        if len(top) else {}
    actual = {r["symbol"]: to_float(r["weight"]) for r in pos["rows"]}

    overlap = sorted(set(target) & set(actual))
    rows = []
    for sym in sorted(set(target) | set(actual)):
        tw, aw = target.get(sym, 0.0), actual.get(sym, 0.0)
        rows.append({"symbol": sym, "target_weight": tw,
                     "actual_weight": aw, "drift": aw - tw,
                     "status": "both" if sym in target and sym in actual
                     else ("target_only" if sym in target else "actual_only")})
    rows.sort(key=lambda r: -abs(r["drift"]))
    return {
        "available": True, "signal_date": str(sig["signal_date"].iloc[0]),
        "n_target": len(target), "n_actual": len(actual),
        "n_overlap": len(overlap),
        "overlap_ratio": (len(overlap) / len(target)) if target else None,
        "rows": rows,
        "max_drift": rows[0]["drift"] if rows else None,
        "note": "仅提示偏离，不产生交易指令（spec §38）",
    }
