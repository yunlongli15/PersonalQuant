# -*- coding: utf-8 -*-
"""执行模型的纯函数测试：限价入场判定、OHLC 出场判定、日历（spec §9-§19）。

这些是整条链上最容易被"想当然"改坏的地方，所以逐条钉死。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

from daily_exit_paper import execution as X

CAL = pd.DatetimeIndex(pd.bdate_range("2026-10-01", periods=8))


# ---------------------------------------------------------------------------
# 限价入场（§9 / §10）
# ---------------------------------------------------------------------------

def test_open_below_limit_fills_at_open():
    """价格改善：开盘低于限价 -> 按**开盘价**成交，不是限价。"""
    r = X.resolve_entry({"open": 9.90, "high": 10.10, "low": 9.80,
                         "close": 10.00}, limit_price=10.00)
    assert r["status"] == X.FILLED
    assert r["price"] == 9.90          # ← 不是 10.00
    assert "优于限价" in r["note"]


def test_open_equal_to_limit_fills_at_limit():
    r = X.resolve_entry({"open": 10.00, "high": 10.10, "low": 9.80,
                         "close": 10.00}, limit_price=10.00)
    assert r["status"] == X.FILLED and r["price"] == 10.00


def test_intraday_touch_fills_at_limit():
    """开盘高于限价但盘中回落触及 -> 以限价成交。"""
    r = X.resolve_entry({"open": 10.50, "high": 10.60, "low": 9.95,
                         "close": 10.20}, limit_price=10.00)
    assert r["status"] == X.FILLED and r["price"] == 10.00
    assert "盘中触及" in r["note"]


def test_not_touched_is_no_fill():
    r = X.resolve_entry({"open": 10.50, "high": 10.80, "low": 10.20,
                         "close": 10.60}, limit_price=10.00)
    assert r["status"] == X.NO_FILL and r["price"] is None


def test_missing_bar_is_not_decided_here():
    """没有 bar 时**不在这里判 NO_FILL** —— 那天能不能判由调用方决定。

    区分"数据未到"与"确认当日无 bar"是 C1 的核心教训：前者要保持挂单。
    """
    assert X.resolve_entry(None, limit_price=10.00) is None


def test_never_uses_close_as_the_fill_price():
    """收盘价只有在它**恰好**是成交价时才出现，绝不作为回落价格使用。"""
    r = X.resolve_entry({"open": 10.50, "high": 10.60, "low": 9.95,
                         "close": 9.98}, limit_price=10.00)
    assert r["price"] == 10.00         # 不是 close 9.98


# ---------------------------------------------------------------------------
# 目标价 / 止损（§15-§18）
# ---------------------------------------------------------------------------

def test_target_hit_fills_at_target():
    r = X.resolve_target_stop({"open": 10.00, "high": 10.50, "low": 9.90,
                               "close": 10.20}, target=10.40, stop=9.00)
    assert r["reason"] == X.TARGET_HIT and r["price"] == 10.40
    assert r["both_hit_same_day"] is False


def test_stop_hit_fills_at_stop():
    r = X.resolve_target_stop({"open": 10.00, "high": 10.10, "low": 9.20,
                               "close": 9.50}, target=11.00, stop=9.30)
    assert r["reason"] == X.STOP_HIT and r["price"] == 9.30


def test_gap_through_target_uses_the_open():
    """开盘已经跳过目标价 -> 以**开盘价**成交（更有利，但如实记录）。"""
    r = X.resolve_target_stop({"open": 11.00, "high": 11.20, "low": 10.90,
                               "close": 11.10}, target=10.40, stop=9.00)
    assert r["reason"] == X.TARGET_HIT and r["price"] == 11.00
    assert "跳空越过" in r["note"]


def test_gap_through_stop_uses_the_open():
    """开盘已经跌破止损 -> 以**开盘价**成交（更差，但绝不假装能按 stop 走）。"""
    r = X.resolve_target_stop({"open": 8.80, "high": 9.00, "low": 8.50,
                               "close": 8.60}, target=11.00, stop=9.30)
    assert r["reason"] == X.STOP_HIT and r["price"] == 8.80
    assert "跳空跌破" in r["note"]


def test_same_day_target_and_stop_resolves_to_stop():
    """同日双触发 -> 保守按止损，并留下判据（spec §16）。"""
    r = X.resolve_target_stop({"open": 10.00, "high": 11.00, "low": 9.00,
                               "close": 10.00}, target=10.40, stop=9.30)
    assert r["reason"] == X.STOP_HIT
    assert r["both_hit_same_day"] is True
    assert r["resolution_applied"] == "stop_first"
    assert r["price"] == 9.30


def test_neither_hit_returns_none():
    r = X.resolve_target_stop({"open": 10.00, "high": 10.20, "low": 9.80,
                               "close": 10.00}, target=10.40, stop=9.30)
    assert r is None


def test_close_never_becomes_the_exit_price():
    """收盘跌破止损但盘中未触及 -> **不触发**；close 不是成交价。"""
    r = X.resolve_target_stop({"open": 9.50, "high": 9.60, "low": 9.40,
                               "close": 9.00}, target=11.00, stop=9.30)
    assert r is None                   # low 9.40 > stop 9.30，整天没碰到


def test_disabled_sides_are_never_triggered():
    inf = float("inf")
    assert X.resolve_target_stop({"open": 10, "high": 99, "low": 1,
                                  "close": 10},
                                 target=inf, stop=-inf) is None


# ---------------------------------------------------------------------------
# 日历与持仓期数（§19）
# ---------------------------------------------------------------------------

def test_sessions_between_counts_entry_day_as_zero():
    entry = CAL[1]
    assert X.sessions_between(CAL, entry, CAL[1]) == 0     # 入场当天
    assert X.sessions_between(CAL, entry, CAL[2]) == 1
    assert X.sessions_between(CAL, entry, CAL[5]) == 4


def test_t1_availability_not_yet_when_calendar_ends_at_signal():
    cal = CAL[:3]
    avail, exec_date, detail = X.t1_availability(cal, cal[-1])
    assert avail is X.Availability.NOT_YET
    assert exec_date is None
    assert "尚无" in detail


def test_t1_availability_ready_once_the_next_session_exists():
    avail, exec_date, _ = X.t1_availability(CAL, CAL[1])
    assert avail is X.Availability.READY
    assert exec_date == CAL[2]


def test_next_session_is_strictly_after():
    assert X.next_session(CAL, CAL[0]) == CAL[1]
    assert X.next_session(CAL, CAL[-1]) is None
    assert X.next_session(CAL, CAL[2] - pd.Timedelta(hours=1)) == CAL[2]
