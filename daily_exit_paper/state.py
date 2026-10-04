# -*- coding: utf-8 -*-
"""订单 / 持仓 / 现金状态。

这一层属于本实验自己（spec §2）：**不 import paper_live**，两套执行语义
必须彻底分开，避免"改一处影响两处"。

两条铁律
--------
1. **入场时快照的 target / stop / time_stop 永不改变**。入场之后再生成
   推荐，也绝不能改写已持仓位的这三个字段 —— 那等于每天用最新价格重新
   优化出场线，是把未来信息泄回决策。代码级守卫：写锁定字段直接 raise。
2. **部分成交不支持**（`PARTIAL_FILL_SUPPORTED = False`）。日线数据不足以
   判断一笔委托成交了多少手，凭开盘价猜"成交了 60%"是编造。
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

import pandas as pd

#: 明确声明：本执行模型不支持部分成交。所有成交都是全量或全量不成交。
PARTIAL_FILL_SUPPORTED = False


class PositionStatus(str, Enum):
    OPEN = "OPEN"
    PENDING_EXIT = "PENDING_EXIT"     # 已触发退出，等待成交（时间止损走这条）
    CLOSED = "CLOSED"                 # 终态


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"                 # 终态
    NO_FILL = "NO_FILL"               # 终态：本次入场作废，不重试
    EXPIRED = "EXPIRED"               # 终态
    CANCELLED = "CANCELLED"           # 终态


class StateError(RuntimeError):
    """状态被非法修改（例如试图改写已锁定的 target/stop）。"""


#: 入场成交那一刻锁定；之后**任何**更新都不允许碰。
LOCKED_POSITION_FIELDS = frozenset({
    "symbol", "name",
    "entry_signal_date", "entry_order_date", "entry_exec_date",
    "entry_price", "entry_shares", "entry_value", "entry_fee",
    "target_price", "stop_loss", "time_stop_days", "horizon_days",
    "risk_profile", "plan_price_at_signal", "at_signal", "locked_at",
    "order_id",
})

#: 持仓期间允许更新的字段。
MUTABLE_POSITION_FIELDS = frozenset({
    "status", "last_price", "mark_date", "holding_sessions",
    "market_value", "unrealized_pnl", "pending_exit_since",
    "exit_date", "exit_reason", "exit_price", "exit_shares",
    "exit_value", "exit_fee", "realized_pnl", "resolution_applied",
    "both_hit_same_day", "closed_at",
})


def assert_updatable(pos: dict, fields) -> None:
    """拒绝改写已锁定的持仓字段。"""
    bad = sorted(set(fields) & LOCKED_POSITION_FIELDS)
    if bad:
        raise StateError(
            f"持仓 {pos.get('symbol')} 的字段 {bad} 在入场成交时已锁定，"
            f"不允许再修改（重算出场线 = 把未来信息泄回决策）。")


def update_position(pos: dict, **fields) -> dict:
    assert_updatable(pos, fields)
    pos.update(fields)
    return pos


# ---------------------------------------------------------------------------
# 组合状态
# ---------------------------------------------------------------------------

def empty_state(initial_capital: float, as_of: str,
                experiment_id: str = "") -> dict:
    """**零状态**起步：不读取任何其它 experiment / 财富库的持仓（spec §43）。"""
    return {
        "experiment_id": experiment_id,
        "as_of": as_of,
        "run_date": None,
        "initial_capital": float(initial_capital),
        "cash": float(initial_capital),
        "reserved_cash": 0.0,
        "positions": {},
        "pending_entries": [],
        "last_signal_date": None,
        "n_runs": 0,
    }


def available_cash(state: dict) -> float:
    return float(state["cash"]) - float(state.get("reserved_cash") or 0.0)


def reserve(state: dict, amount: float) -> None:
    if amount < 0:
        raise StateError("预留金额不能为负")
    state["reserved_cash"] = float(state.get("reserved_cash") or 0.0) + amount


def release(state: dict, amount: float) -> None:
    new = float(state.get("reserved_cash") or 0.0) - float(amount)
    state["reserved_cash"] = max(0.0, new)


def open_positions(state: dict) -> Dict[str, dict]:
    return {s: p for s, p in (state.get("positions") or {}).items()
            if p.get("status") in (PositionStatus.OPEN.value,
                                   PositionStatus.PENDING_EXIT.value)}


def held_symbols(state: dict) -> set:
    """已持有的标的（含正在退出的）—— 退出前不再加仓。"""
    return set(open_positions(state))


def position_value(state: dict, prices: Dict[str, float]) -> float:
    total = 0.0
    for sym, p in open_positions(state).items():
        px = prices.get(sym, p.get("last_price"))
        if px is None or not pd.notna(px):
            px = p.get("entry_price", 0.0)
        total += int(p.get("entry_shares", 0)) * float(px or 0.0)
    return float(total)


def portfolio_value(state: dict, prices: Dict[str, float]) -> float:
    return float(state["cash"]) + position_value(state, prices)


def mark_positions(state: dict, prices: Dict[str, float],
                   as_of: str, sessions_held: Dict[str, int]) -> None:
    """按最新收盘价给持仓打标记。**只碰可变字段**。"""
    for sym, p in open_positions(state).items():
        px = prices.get(sym)
        if px is None or not pd.notna(px):
            continue
        shares = int(p.get("entry_shares", 0))
        mv = shares * float(px)
        cost = float(p.get("entry_value", 0.0)) + float(p.get("entry_fee", 0.0))
        update_position(p, last_price=float(px), mark_date=as_of,
                        market_value=mv, unrealized_pnl=mv - cost,
                        holding_sessions=int(sessions_held.get(sym, 0)))


def build_position(order: dict, fill_price: float, shares: int,
                   exit_levels: dict, at_signal: dict,
                   locked_at: str) -> dict:
    """入场成交时构造持仓 —— target/stop 在这一刻**锁定**。"""
    value = float(fill_price) * int(shares)
    return {
        "symbol": order["symbol"],
        "name": order.get("name", ""),
        "order_id": order["order_id"],
        "status": PositionStatus.OPEN.value,
        "entry_signal_date": order["signal_date"],
        "entry_order_date": order["order_date"],
        "entry_exec_date": locked_at,
        "entry_price": float(fill_price),
        "entry_shares": int(shares),
        "entry_value": value,
        "entry_fee": 0.0,               # 由 ledger 填入实际值
        "plan_price_at_signal": float(order.get("planned_entry_price") or 0.0),
        "at_signal": at_signal,          # 仅留痕：信号日的 target/stop
        "target_price": float(exit_levels["target_price"]),
        "stop_loss": float(exit_levels["stop_loss"]),
        "time_stop_days": int(exit_levels["time_stop_days"]),
        "horizon_days": int(exit_levels.get("expected_holding_days",
                                            exit_levels["time_stop_days"] // 2)),
        "risk_profile": exit_levels.get("risk_profile"),
        "locked_at": locked_at,
        "last_price": float(fill_price),
        "mark_date": locked_at,
        "market_value": value,
        "unrealized_pnl": 0.0,
        "holding_sessions": 0,
    }


def pending_entry(order_id: str, symbol: str, name: str, signal_date: str,
                  order_date: str, planned_entry_price: float,
                  limit_price: float, quantity: int, reserved_cash: float,
                  planned: dict) -> dict:
    """挂出的限价买单（T 日晚上产生，T+1 开盘判成交）。

    `estimated_value` / `estimated_fee` 是**下单时**的预估：成交后会与账本
    实际扣费逐笔比对（spec §24：预估口径与账本口径必须一致），
    预估与实际不一致要能立刻看见，而不是永远只有账本一侧有数。
    """
    est_value = int(quantity) * float(limit_price)
    return {
        "order_id": order_id,
        "symbol": symbol,
        "name": name,
        "side": "BUY",
        "status": OrderStatus.PENDING.value,
        "signal_date": signal_date,
        "order_date": order_date,
        "exec_rule": "NEXT_SESSION_OPEN",
        "resolved_exec_date": None,
        "planned_entry_price": float(planned_entry_price),
        "limit_price": float(limit_price),
        "quantity": int(quantity),
        "estimated_value": float(est_value),
        "estimated_fee": float(planned.get("estimated_fee") or 0.0),
        "reserved_cash": float(reserved_cash),
        "target_price_at_signal": float(planned["target_price"]),
        "stop_loss_at_signal": float(planned["stop_loss"]),
        "expected_return": planned.get("expected_return"),
        "vol": planned.get("vol"),
        "entry_low": planned.get("entry_low"),
        "entry_high": planned.get("entry_high"),
        "raw_rank": planned.get("raw_rank"),
        "attempts": [],
        "created_at": None,
    }


def record_attempt(order: dict, run_date: str, availability: str,
                   result: str, exec_date: Optional[str] = None,
                   detail: Optional[str] = None,
                   error: Optional[str] = None) -> dict:
    rec = {
        "observed_run_date": run_date,
        "resolved_exec_date": exec_date,
        "availability_state": availability,
        "result": result,
        "detail": detail,
        "error_if_any": error,
    }
    order.setdefault("attempts", []).append(rec)
    return rec


def pending_list(state: dict) -> List[dict]:
    return list(state.get("pending_entries") or [])


def set_pending(state: dict, orders: List[dict]) -> None:
    state["pending_entries"] = list(orders)
