# -*- coding: utf-8 -*-
"""人工干预层（spec §26-§28）。

三层分开存，**绝不互相覆盖**：

    recommendations/<signal_date>.json   ① 系统建议（引擎写，写后只读）
    decisions/<signal_date>.json         ② 用户决定（人写；缺省 = 全部采纳）
    executions/<signal_date>.json        ③ 实际执行（人回填）

两条铁律
--------
1. **用户改过的价格绝不写回 ①**。系统建议永远是当时引擎给出的那一份，
   所以"如果完全照系统做会怎样"这个问题永远可回答。
2. 干预**只记录、不自动调参**（spec §28）。统计出来是给人看的，
   绝不用来反过来改 target / stop / top_k / 仓位规模。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

ADOPT_ALL = "ADOPT_ALL"      # 缺省：完全采纳系统建议
ADOPT = "ADOPT"
SKIP = "SKIP"
MODIFY = "MODIFY"
ACTIONS = (ADOPT, SKIP, MODIFY)


class DecisionError(RuntimeError):
    """干预文件格式不对或与建议对不上 —— 停下来，不猜。"""


def decision_path(store, signal_date) -> Path:
    return store.root / "decisions" / f"{pd.Timestamp(signal_date).date()}.json"


def load_decision(store, signal_date) -> Optional[dict]:
    p = decision_path(store, signal_date)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def record_decision(store, signal_date, decisions: List[dict],
                    default_action: str = ADOPT_ALL,
                    note: str = "") -> Path:
    """写一份用户决定。`decisions` 里每项至少要有 symbol 和 action。"""
    for d in decisions:
        if d.get("action") not in ACTIONS:
            raise DecisionError(
                f"未知的 action {d.get('action')!r}（只能是 {ACTIONS}）")
        if not d.get("symbol"):
            raise DecisionError("每条决定都必须有 symbol")
        if d["action"] in (SKIP, MODIFY) and not d.get("override_reason"):
            raise DecisionError(
                f"{d['symbol']} 的 {d['action']} 必须写 override_reason —— "
                f"干预要留痕，将来才解释得清")
    payload = {
        "signal_date": str(pd.Timestamp(signal_date).date()),
        "default_action": default_action,
        "decisions": decisions,
        "note": note,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "layer": "user_decision",
    }
    p = decision_path(store, signal_date)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                 encoding="utf-8")
    return p


def record_execution(store, signal_date, executions: List[dict],
                     note: str = "") -> Path:
    """回填**实际**执行（成交价 / 股数 / 是否成交），与系统建议分开存。"""
    payload = {
        "signal_date": str(pd.Timestamp(signal_date).date()),
        "executions": executions,
        "note": note,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "layer": "actual_execution",
    }
    p = store.root / "executions" / f"{pd.Timestamp(signal_date).date()}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                 encoding="utf-8")
    return p


def apply_decisions(entries: List[dict], decision: Optional[dict],
                    cost_model, lot: int
                    ) -> Tuple[List[dict], List[dict], List[dict]]:
    """把用户决定套在系统建议上，返回 (生效的挂单, 被跳过的, 干预记录)。

    **系统建议本身不被修改** —— 这里只产出"实际要挂的单"。
    """
    by_symbol = {}
    default_action = ADOPT_ALL
    if decision:
        default_action = decision.get("default_action", ADOPT_ALL)
        for d in decision.get("decisions") or []:
            by_symbol[d["symbol"]] = d

    orders: List[dict] = []
    skipped: List[dict] = []
    overrides: List[dict] = []

    for e in entries:
        d = by_symbol.get(e["symbol"])
        action = (d or {}).get("action", ADOPT if d else default_action)
        if action not in ACTIONS and action != ADOPT_ALL:
            raise DecisionError(f"{e['symbol']}: 未知 action {action!r}")

        if action == SKIP:
            skipped.append({"symbol": e["symbol"], "reason": "user_skip"})
            overrides.append(_override(e, d, "BUY", "SKIP"))
            continue

        if action == MODIFY:
            limit = float(d.get("limit_price", e["limit_price"]))
            qty = int(d.get("quantity", e["quantity"]))
            if qty % lot:
                raise DecisionError(
                    f"{e['symbol']} 的 quantity {qty} 不是 {lot} 的整数倍")
            if qty <= 0:
                skipped.append({"symbol": e["symbol"],
                                "reason": "user_modify_to_zero"})
                overrides.append(_override(e, d, "BUY", "SKIP"))
                continue
            value = qty * limit
            fee = cost_model.buy_cost(value)
            order = dict(e, limit_price=limit, quantity=qty,
                         estimated_value=value, estimated_fee=fee,
                         reserved_cash=value + fee,
                         user_action=MODIFY,
                         override_reason=d.get("override_reason"))
            orders.append(order)
            overrides.append(_override(e, d, "BUY", MODIFY,
                                       applied_limit=limit, applied_qty=qty))
            continue

        if d:                                  # 显式 ADOPT
            overrides.append(_override(e, d, "BUY", ADOPT))
        orders.append(e)

    return orders, skipped, overrides


def _override(entry: dict, decision: Optional[dict], system_action: str,
              user_action: str, **extra) -> dict:
    rec = {
        "symbol": entry["symbol"],
        "system_action": system_action,
        "system_limit_price": entry.get("limit_price"),
        "system_quantity": entry.get("quantity"),
        "user_action": user_action,
        "override": user_action != system_action,
        "override_reason": (decision or {}).get("override_reason"),
    }
    rec.update(extra)
    return rec


def override_summary(store) -> Dict[str, int]:
    """干预统计 —— **只用于事后解释，绝不用来自动调参**（spec §28）。"""
    counts = {"decisions": 0, "SKIP": 0, "MODIFY": 0, "ADOPT": 0,
              "executions_recorded": 0}
    for p in sorted((store.root / "decisions").glob("*.json")):
        payload = json.loads(p.read_text(encoding="utf-8"))
        for d in payload.get("decisions") or []:
            counts["decisions"] += 1
            counts[d["action"]] = counts.get(d["action"], 0) + 1
    for p in sorted((store.root / "executions").glob("*.json")):
        counts["executions_recorded"] += len(
            json.loads(p.read_text(encoding="utf-8")).get("executions") or [])
    return counts


def all_overrides(store) -> List[dict]:
    """跨日汇总的干预记录（日报里展示用）。"""
    out = []
    for p in sorted((store.root / "decisions").glob("*.json")):
        payload = json.loads(p.read_text(encoding="utf-8"))
        for d in payload.get("decisions") or []:
            out.append({"signal_date": payload.get("signal_date"),
                        "symbol": d["symbol"], "system_action": "BUY",
                        "user_action": d["action"],
                        "override_reason": d.get("override_reason")})
    return out
