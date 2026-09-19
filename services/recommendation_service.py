# -*- coding: utf-8 -*-
"""调仓建议与模拟（spec §24 / §25 / §26 / §27 / §63）。

**只生成建议，永不执行。** 页面只有 Export，没有 Submit Order（§27）。
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ._common import PROJECT_ROOT, read_json, safe, to_float, unavailable

TAGS = ["PAPER ONLY", "NO BROKER", "RESEARCH ONLY"]


def _latest_plan() -> Optional[dict]:
    """读最近的交易计划（权威来源：data/quant/trade_plans/）。"""
    d = PROJECT_ROOT / "data" / "quant" / "trade_plans"
    if not d.exists():
        return None
    files = sorted(d.glob("trade_plan_*.json"))
    if not files:
        return None
    return read_json(files[-1])


@safe(label="调仓建议")
def latest(capital: Optional[float] = None) -> dict:
    """§63：信号日 / 执行日 / 版本 / 快照 / 预测 / 排名 / 权重 / 交易 / 理由。"""
    plan = _latest_plan()
    if plan is None:
        return unavailable("还没有交易计划（先跑 scripts/quant/refresh_all.py）")

    cap = float(capital) if capital else to_float(plan.get("capital"))
    rows = []
    for r in plan.get("rows", []):
        rows.append({
            "symbol": r.get("symbol"), "name": r.get("name"),
            "action": r.get("action"),
            "prediction": r.get("signal_prediction"),
            "rank": r.get("raw_rank"),
            "current_price": r.get("current_price"),
            "entry_low": r.get("entry_low"), "entry_high": r.get("entry_high"),
            "recommended_entry_price": r.get("recommended_entry_price"),
            "current_weight": r.get("weight"),
            "target_weight": r.get("target_weight"),
            "delta_weight": (to_float(r.get("target_weight"))
                             - to_float(r.get("weight"))),
            "target_value": (to_float(r.get("target_weight")) * cap),
            "estimated_shares": r.get("shares"),
            "estimated_trade_value": r.get("buy_value"),
            "estimated_fee": None,
            "target_price": r.get("target_price"),
            "stop_loss": r.get("stop_loss"),
            "reasons": r.get("reasons") or [],
            "board": r.get("board_name"),
            "can_buy": r.get("can_buy"),
            "restriction_reason": r.get("restriction_reason"),
            # §25：结构化理由优先，不用 LLM 编造
            "reason_fields": {
                "rank": r.get("raw_rank"),
                "prediction": r.get("signal_prediction"),
                "target_weight": r.get("target_weight"),
                "volatility": (r.get("risk") or {}).get("volatility"),
                "industry": (r.get("risk") or {}).get("industry"),
                "expected_net_return": r.get("expected_net_return"),
                "holding_days": r.get("expected_holding_days"),
            },
        })
    return {
        "available": True,
        "signal_date": plan.get("as_of"),
        "execution_date": None,          # 由页面按 T+1 规则推导展示
        "strategy_version": plan.get("signal_version"),
        "data_snapshot": plan.get("price_source"),
        "model_version": plan.get("signal_version"),
        "forecast_version": plan.get("forecast_version"),
        "capital": cap,
        "n_rows": len(rows),
        "total_buy_value": plan.get("total_buy_value"),
        "remaining_cash": plan.get("remaining_cash"),
        "cash_residual_pct": plan.get("cash_residual_pct"),
        "estimated_fees": plan.get("estimated_fees"),
        "expected_net_return_pct": plan.get("expected_net_return_pct"),
        "expected_volatility": plan.get("expected_volatility"),
        "excluded_restricted": plan.get("excluded_restricted") or [],
        "rows": rows,
        "tags": TAGS,
    }


@safe(label="调仓模拟")
def simulate(capital: float = 500_000.0,
             holdings: Optional[Dict[str, int]] = None,
             top_k: Optional[int] = None) -> dict:
    """§26：给定资金与现有持仓，算出"如果照做会怎样"。

    复用 `trade_plan.build_trade_plan`（同一条引擎路径），
    因此手数、板块权限、费用口径与生产完全一致。
    """
    from trade_plan.plan import build_trade_plan

    plan = build_trade_plan(capital=float(capital),
                            top_k=int(top_k) if top_k else 20,
                            holdings=holdings or {})
    rows = []
    for r in plan.get("rows", []):
        rows.append({
            "symbol": r.get("symbol"), "name": r.get("name"),
            "action": r.get("action"),
            "price": r.get("current_price"),
            "shares": r.get("shares"),
            "value": r.get("buy_value"),
            "weight": r.get("target_weight"),
            "board": r.get("board_name"),
            "can_buy": r.get("can_buy"),
        })
    return {
        "available": True,
        "as_of": plan.get("as_of"), "capital": capital,
        "n_buys": sum(1 for r in rows if r["action"] == "BUY"),
        "total_buy_value": plan.get("total_buy_value"),
        "remaining_cash": plan.get("remaining_cash"),
        "cash_residual_pct": plan.get("cash_residual_pct"),
        "estimated_fees": plan.get("estimated_fees"),
        "expected_net_return_pct": plan.get("expected_net_return_pct"),
        "excluded_restricted": plan.get("excluded_restricted") or [],
        "rows": rows,
        "tags": TAGS,
        "note": "模拟结果仅供参考；系统不会下单，也不连接券商",
    }


def export_csv(payload: dict) -> str:
    """把建议导成 CSV 文本（§27 的 Export，是唯一的"动作"）。"""
    import csv
    import io

    buf = io.StringIO()
    rows = payload.get("rows") or []
    if not rows:
        return ""
    cols = [c for c in rows[0] if c not in ("reasons", "reason_fields")]
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()
