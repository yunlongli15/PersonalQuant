# -*- coding: utf-8 -*-
"""执行模型：市场数据的**只读**访问 + T+1 可用性 + 限价入场 / OHLC 出场判定。

三条不许让步的规则
------------------
1. **每一次数据访问都必须显式带 `as_of`**（spec §32）。绝不出现"读数据库
   最新值"这种写法 —— 那在回放历史日期时会把未来数据混进来。
2. **T+1 铁律**：T 日收盘信号，T+1 开盘执行。`resolve_entry` 只在 T+1 的
   bar 上判定，绝不看 T 日的价格。
3. **不猜盘中**：只用 OHLC 里确实存在的信息。跳空一律以实际开盘价成交；
   日线不知道 target 与 stop 谁先到，交给配置里的保守策略决定。
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Tuple

import pandas as pd

#: 一次限价买单的判定结果。
FILLED = "FILLED"
NO_FILL = "NO_FILL"


class DataError(RuntimeError):
    """读取市场数据失败（DB / schema / 类型）。必须冒泡，不许吞。"""


class Availability(str, Enum):
    READY = "READY"        # 执行日已在已观测日历里 -> 可以判成交
    NOT_YET = "NOT_YET"    # 执行日尚未出现 -> 保持 PENDING（正常，不是失败）


# ---------------------------------------------------------------------------
# 日历
# ---------------------------------------------------------------------------

def observed_calendar() -> pd.DatetimeIndex:
    """**已经拿到行情**的交易日（最后一个就是数据里最后一天，没有未来日历）。

    刻意不用 `trading_calendar` 表：日历文件与 bars 是两次 ingest，
    万一日历说某天开市、而行情里根本没有那天的任何 bar，引擎就会把
    "数据还没到"误判成"整池停牌"，直接判出一堆 NO_FILL。
    以 `daily_bars` 里**实际存在**的交易日为准，就没有这个歧义。
    """
    from personal_quant import db

    try:
        df = db.connect().execute(
            "SELECT DISTINCT trade_date FROM daily_bars "
            "ORDER BY trade_date").fetch_df()
    except Exception as e:                                   # noqa: BLE001
        raise DataError(f"读取交易日历失败：{type(e).__name__}: {e}") from e
    return pd.DatetimeIndex(sorted(pd.Timestamp(d) for d in df["trade_date"]))


def last_observed_session(calendar: pd.DatetimeIndex) -> pd.Timestamp:
    if len(calendar) == 0:
        raise DataError("交易日历为空")
    return pd.Timestamp(calendar[-1])


def next_session(calendar: pd.DatetimeIndex, after) -> Optional[pd.Timestamp]:
    later = calendar[calendar > pd.Timestamp(after)]
    return pd.Timestamp(later[0]) if len(later) else None


def sessions_between(calendar: pd.DatetimeIndex, start, end) -> int:
    """`start` 之后、`end` 及之前有几个交易日（含 end，不含 start）。

    持仓期数的唯一定义：**入场成交当天 = 0**；此后每过一个交易日 +1。
    """
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    return int(((calendar > s) & (calendar <= e)).sum())


def t1_availability(calendar: pd.DatetimeIndex, signal_date
                    ) -> Tuple[Availability, Optional[pd.Timestamp], str]:
    """执行日到了吗？两态判定，完全显式。

    READY   —— 日历里存在 signal_date 之后的交易日。此时**单只股票没有 bar
               是可判定的 NO_FILL（停牌）**：那天出现在日历里说明市场有
               成交、数据已入库，那么这只票当天就是没交易。
    NOT_YET —— 日历里还没有 signal_date 之后的交易日。挂单保持 PENDING。

    读取失败不走这里 —— 那由调用方包成 DataError 直接抛，绝不 return False。
    """
    nxt = next_session(calendar, signal_date)
    if nxt is None:
        last = last_observed_session(calendar)
        return (Availability.NOT_YET, None,
                f"已观测交易日历止于 {last.date()}，尚无 "
                f"{pd.Timestamp(signal_date).date()} 之后的交易日")
    return Availability.READY, nxt, f"执行日 {nxt.date()}"


# ---------------------------------------------------------------------------
# 行情（只读，且永远带 as_of）
# ---------------------------------------------------------------------------

def bars_on(symbols: List[str], date) -> Dict[str, dict]:
    """某一交易日的原始 OHLC（`trade_date = date`，只可能是那一天）。"""
    if not symbols:
        return {}
    from personal_quant import db

    marks = ",".join("?" * len(symbols))
    try:
        df = db.connect().execute(
            f"SELECT symbol, open, high, low, close FROM daily_bars "
            f"WHERE trade_date = ? AND symbol IN ({marks})",
            [str(pd.Timestamp(date).date())] + list(symbols)).fetch_df()
    except Exception as e:                                   # noqa: BLE001
        raise DataError(f"读取 {date} 行情失败：{type(e).__name__}: {e}") \
            from e
    if df.empty:
        return {}
    return {r["symbol"]: {"open": float(r["open"]), "high": float(r["high"]),
                          "low": float(r["low"]), "close": float(r["close"])}
            for _, r in df.iterrows()}


def last_close_on_or_before(symbols: List[str], as_of) -> Dict[str, float]:
    """每只票 **<= as_of** 的最后一个收盘价（绝不越过 as_of 取数）。"""
    if not symbols:
        return {}
    from personal_quant import db

    marks = ",".join("?" * len(symbols))
    try:
        df = db.connect().execute(
            f"SELECT symbol, trade_date, close FROM daily_bars "
            f"WHERE trade_date <= ? AND symbol IN ({marks}) "
            f"QUALIFY row_number() OVER "
            f"(PARTITION BY symbol ORDER BY trade_date DESC) = 1",
            [str(pd.Timestamp(as_of).date())] + list(symbols)).fetch_df()
    except Exception as e:                                   # noqa: BLE001
        raise DataError(f"读取 {as_of} 收盘价失败：{type(e).__name__}: {e}") \
            from e
    return {r["symbol"]: float(r["close"]) for _, r in df.iterrows()}


# ---------------------------------------------------------------------------
# 限价入场判定（只用执行日的 OHLC）
# ---------------------------------------------------------------------------

def resolve_entry(bar: Optional[dict], limit_price: float) -> Optional[dict]:
    """T+1 限价买单的成交判定。

        open <= limit                    -> 成交 @ open    （**价格改善**）
        open > limit 且 low <= limit      -> 成交 @ limit   （盘中触及）
        open > limit 且 low >  limit      -> 不成交

    `bar` 为 None 表示该股当天没有 bar。**这一天能不能判 NO_FILL 由调用方
    决定**（只有在执行日已确认出现时才判），这里不替它猜。
    """
    if bar is None:
        return None
    o, low = float(bar["open"]), float(bar["low"])
    lim = float(limit_price)
    if o <= lim:
        return {"status": FILLED, "price": o, "note": "开盘价优于限价"}
    if low <= lim:
        return {"status": FILLED, "price": lim, "note": "盘中触及限价"}
    return {"status": NO_FILL, "price": None, "note": "全天未触及限价"}


# ---------------------------------------------------------------------------
# 出场判定（只用触发日的 OHLC）
# ---------------------------------------------------------------------------

TARGET_HIT = "TARGET_HIT"
STOP_HIT = "STOP_HIT"
TIME_STOP = "TIME_STOP"
MANUAL = "MANUAL"


def resolve_target_stop(bar: Optional[dict], target: float, stop: float,
                        conflict: str = "stop_first") -> Optional[dict]:
    """盘中挂着的止盈/止损单在今天的成交判定。

        high >= target                  -> 触及止盈
        low  <= stop                    -> 触及止损

    两者同日成立时，日线**无法知道盘中先后**，按 `conflict` 策略解：
    `stop_first` = 一律按止损（保守：宁可低估收益，不可高估）。

    成交价（跳空保守）：
        止盈：open >= target -> open（市场已跳过目标价）；否则 target
        止损：open <= stop   -> open（已经跌破）；否则 stop

    **绝不用 close 冒充成交价** —— close 是收盘才知道的，挂单不会等它。
    """
    if bar is None:
        return None
    o, high, low = float(bar["open"]), float(bar["high"]), float(bar["low"])
    hit_t = high >= float(target)
    hit_s = low <= float(stop)
    if not hit_t and not hit_s:
        return None

    both = hit_t and hit_s
    if both and conflict == "stop_first":
        reason = STOP_HIT
    elif both:
        raise ValueError(f"未知的冲突策略 {conflict!r}（v1 固定 stop_first）")
    else:
        reason = STOP_HIT if hit_s else TARGET_HIT

    if reason == STOP_HIT:
        price = o if o <= float(stop) else float(stop)
        note = "开盘跳空跌破止损，以开盘价成交" if o <= float(stop) \
            else "触及止损价成交"
    else:
        price = o if o >= float(target) else float(target)
        note = "开盘跳空越过目标价，以开盘价成交" if o >= float(target) \
            else "触及目标价成交"
    return {"reason": reason, "price": float(price), "note": note,
            "both_hit_same_day": bool(both),
            "resolution_applied": conflict if both else None}
