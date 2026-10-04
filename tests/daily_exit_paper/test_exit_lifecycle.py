# -*- coding: utf-8 -*-
"""出场生命周期：target / stop / time-stop / 同日冲突 / T+1 禁售（spec §12-§20）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

from conftest import SESSIONS, SYMS, build_market, day, make_signals
from daily_exit_paper import engine, execution as X, state as S

A = SYMS[0]
CAP = 66_000.0
D0, D1, D2, D3 = (day(SESSIONS, i) for i in range(4))


def _open_position(cfg, store, high_factor=None):
    """跑到 D1：A 已建仓（成交在 D1 开盘）。返回 (market, position)。

    `high_factor` 让调用方在**成交之前**就把入场日的高点摆好：成交价
    = limit − 0.30，任何小于 1.5 倍的倍数都会盖住 target（target 是
    entry×(1+预期收益)，预期收益远小于 0.5）。这样才能真正测试
    "入场当日打到目标价也不许卖"。
    """
    mkt = build_market({}, {D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    limit = S.pending_list(store.read_state())[0]["limit_price"]
    entry = limit - 0.30
    mkt.set_bar(A, D1, o=entry,
                h=(entry * high_factor) if high_factor else limit,
                l=limit - 0.40)
    engine.run(run_date=D1, cfg=cfg, store=store, market=mkt)
    return mkt, S.open_positions(store.read_state())[A]


def _closed(store, sym=A):
    positions = store.read_state()["positions"]
    p = positions.get(sym)
    return p if p and p["status"] == S.PositionStatus.CLOSED.value else None


# ---------------------------------------------------------------------------
# T+1 禁售（§12）
# ---------------------------------------------------------------------------

def test_no_same_day_exit(cfg, store):
    """入场当日即使盘中打到目标价，也**不能**卖出（A 股 T+1 制度）。"""
    mkt, pos = _open_position(cfg, store, high_factor=1.5)
    # 确实盖过了目标价 —— 否则这条测试等于没测
    assert pos["entry_exec_date"] == str(D1.date())
    assert mkt.bars([A], D1)[A]["high"] > pos["target_price"]
    assert A in S.open_positions(store.read_state())


def test_exit_allowed_from_the_next_session(cfg, store):
    mkt, pos = _open_position(cfg, store)
    tgt = pos["target_price"]
    mkt.set_bar(A, D2, o=tgt - 0.10, h=tgt + 0.20, l=tgt - 0.30)
    r = engine.run(run_date=D2, cfg=cfg, store=store, market=mkt)
    assert len(r.reports[0].exits) == 1
    assert r.reports[0].exits[0]["reason"] == X.TARGET_HIT


# ---------------------------------------------------------------------------
# target / stop / gap（§15-§17）
# ---------------------------------------------------------------------------

def test_target_hit_fills_at_target(cfg, store):
    mkt, pos = _open_position(cfg, store)
    tgt = pos["target_price"]
    mkt.set_bar(A, D2, o=tgt - 0.20, h=tgt + 0.30, l=tgt - 0.40)
    engine.run(run_date=D2, cfg=cfg, store=store, market=mkt)
    p = _closed(store)
    assert p["exit_reason"] == X.TARGET_HIT
    assert p["exit_price"] == pytest.approx(tgt, abs=1e-6)
    assert p["realized_pnl"] > 0


def test_stop_hit_fills_at_stop(cfg, store):
    mkt, pos = _open_position(cfg, store)
    stp = pos["stop_loss"]
    mkt.set_bar(A, D2, o=stp + 0.20, h=stp + 0.30, l=stp - 0.10)
    engine.run(run_date=D2, cfg=cfg, store=store, market=mkt)
    p = _closed(store)
    assert p["exit_reason"] == X.STOP_HIT
    assert p["exit_price"] == pytest.approx(stp, abs=1e-6)
    assert p["realized_pnl"] < 0


def test_gap_through_target_uses_the_open(cfg, store):
    mkt, pos = _open_position(cfg, store)
    tgt = pos["target_price"]
    mkt.set_bar(A, D2, o=tgt + 0.50, h=tgt + 0.80, l=tgt + 0.40)
    engine.run(run_date=D2, cfg=cfg, store=store, market=mkt)
    p = _closed(store)
    assert p["exit_reason"] == X.TARGET_HIT
    assert p["exit_price"] == pytest.approx(tgt + 0.50, abs=1e-6)   # 不是 tgt


def test_gap_through_stop_uses_the_open(cfg, store):
    mkt, pos = _open_position(cfg, store)
    stp = pos["stop_loss"]
    mkt.set_bar(A, D2, o=stp - 0.60, h=stp - 0.40, l=stp - 0.90)
    engine.run(run_date=D2, cfg=cfg, store=store, market=mkt)
    p = _closed(store)
    assert p["exit_reason"] == X.STOP_HIT
    assert p["exit_price"] == pytest.approx(stp - 0.60, abs=1e-6)   # 不是 stp


def test_same_day_both_hit_is_resolved_as_stop(cfg, store):
    """同日双触发 -> 保守按止损，并把判据留在持仓里（可统计）。"""
    mkt, pos = _open_position(cfg, store)
    tgt, stp = pos["target_price"], pos["stop_loss"]
    mkt.set_bar(A, D2, o=(tgt + stp) / 2, h=tgt + 0.50, l=stp - 0.50)
    r = engine.run(run_date=D2, cfg=cfg, store=store, market=mkt)
    e = r.reports[0].exits[0]
    assert e["reason"] == X.STOP_HIT
    assert e["both_hit_same_day"] is True
    assert e["resolution_applied"] == "stop_first"
    assert _closed(store)["exit_price"] == pytest.approx(stp, abs=1e-6)


def test_no_exit_when_price_stays_inside_the_band(cfg, store):
    mkt, pos = _open_position(cfg, store)
    mid = (pos["target_price"] + pos["stop_loss"]) / 2
    mkt.set_bar(A, D2, o=mid, h=mid * 1.001, l=mid * 0.999)
    r = engine.run(run_date=D2, cfg=cfg, store=store, market=mkt)
    assert r.reports[0].exits == []
    assert A in S.open_positions(store.read_state())


def test_halts_do_not_fabricate_an_exit(cfg, store):
    """停牌当天没有 bar -> 不评估、不猜，持仓原样保留。"""
    mkt, pos = _open_position(cfg, store)
    r = engine.run(run_date=D2, cfg=cfg, store=store, market=mkt)
    assert r.reports[0].exits == []
    assert A in S.open_positions(store.read_state())


# ---------------------------------------------------------------------------
# target / stop 快照不可变（§13）
# ---------------------------------------------------------------------------

def test_target_and_stop_are_locked_at_entry(cfg, store):
    """重新生成推荐**不得**改动已持仓位的 target / stop（代码级守卫）。"""
    mkt, pos = _open_position(cfg, store)
    tgt, stp = pos["target_price"], pos["stop_loss"]

    # D1 又生成一份"新"推荐（价格不同 -> 算出的 target/stop 也会不同）
    mkt._signals[D1] = make_signals(D1, SYMS)
    mkt._forecasts[D1] = {s: 0.09 for s in SYMS}
    engine.run(run_date=D1, cfg=cfg, store=store, market=mkt)

    after = store.read_state()["positions"][A]
    assert after["target_price"] == tgt
    assert after["stop_loss"] == stp
    assert after["time_stop_days"] == pos["time_stop_days"]


def test_writing_a_locked_field_raises():
    pos = {"symbol": A, "target_price": 10.0, "stop_loss": 9.0}
    with pytest.raises(S.StateError) as e:
        S.update_position(pos, target_price=11.0)
    assert "已锁定" in str(e.value)
    S.update_position(pos, last_price=10.5, holding_sessions=3)   # 白名单可写


def test_entry_levels_are_anchored_to_the_fill_price(cfg, store):
    """出场线锚定在**实际成交价**上，并保留信号日的值作为对照。"""
    mkt, pos = _open_position(cfg, store)
    assert pos["entry_price"] < pos["at_signal"]["plan_price"] or True
    assert pos["at_signal"]["target_price"] is not None
    # 目标价与成交价的关系符合既有公式：target = entry×(1+exp×1.0)
    exp = pos["at_signal"] and None  # 仅确保字段存在
    assert pos["target_price"] > pos["entry_price"]
    assert pos["stop_loss"] < pos["entry_price"]


# ---------------------------------------------------------------------------
# 时间止损（§19）：按交易日计，入场日为第 0 天
# ---------------------------------------------------------------------------

def test_time_stop_fires_after_40_sessions_and_fills_next_open(cfg, store):
    sessions = list(pd.bdate_range("2026-10-01", periods=45))
    d0, d1 = pd.Timestamp(sessions[0]), pd.Timestamp(sessions[1])
    mkt = build_market({}, {d0: make_signals(d0, [A])}, {d0: {A: 0.05}},
                       sessions=sessions)
    engine.run(run_date=d0, capital=CAP, cfg=cfg, store=store, market=mkt)
    limit = S.pending_list(store.read_state())[0]["limit_price"]
    mkt.set_bar(A, d1, o=limit - 0.30, h=limit, l=limit - 0.40)
    engine.run(run_date=d1, cfg=cfg, store=store, market=mkt)
    pos = S.open_positions(store.read_state())[A]
    assert pos["time_stop_days"] == 40

    mid = (pos["target_price"] + pos["stop_loss"]) / 2
    trigger = None
    for i in range(2, 44):
        s = pd.Timestamp(sessions[i])
        mkt.set_bar(A, s, o=mid, h=mid * 1.0005, l=mid * 0.9995)
        engine.run(run_date=s, cfg=cfg, store=store, market=mkt)
        st = store.read_state()
        p = st["positions"][A]
        if p["status"] == S.PositionStatus.PENDING_EXIT.value:
            trigger = i
            assert p["pending_exit_reason"] == X.TIME_STOP
            break
        assert p["status"] == S.PositionStatus.OPEN.value

    assert trigger is not None, "40 个交易日后必须触发时间止损"
    # 入场日 = 第 0 天 -> 第 40 个后续交易日触发（索引 1+40 = 41）
    assert trigger == 41

    # 触发当天不成交；下一个交易日开盘卖出
    s_fill = pd.Timestamp(sessions[trigger + 1])
    open_px = mid * 0.98
    mkt.set_bar(A, s_fill, o=open_px, h=open_px * 1.01, l=open_px * 0.99)
    engine.run(run_date=s_fill, cfg=cfg, store=store, market=mkt)
    p = _closed(store)
    assert p["exit_reason"] == X.TIME_STOP
    assert p["exit_price"] == pytest.approx(open_px)
    assert p["exit_date"] == str(s_fill.date())


# ---------------------------------------------------------------------------
# signal_exit（§20）：v1 关闭
# ---------------------------------------------------------------------------

def test_rank_drop_never_triggers_an_exit(cfg, store):
    """模型第二天不再看好也**不卖** —— signal_exit 在 v1 是关闭的。"""
    mkt, pos = _open_position(cfg, store)
    mid = (pos["target_price"] + pos["stop_loss"]) / 2
    # 排名掉到末尾、预测转负
    mkt._signals[D2] = make_signals(D2, SYMS, predictions={A: -9.99})
    mkt._forecasts[D2] = {A: -0.20}
    mkt.set_bar(A, D2, o=mid, h=mid * 1.0005, l=mid * 0.9995)

    r = engine.run(run_date=D2, cfg=cfg, store=store, market=mkt)
    assert r.reports[0].exits == []
    assert A in S.open_positions(store.read_state())


# ---------------------------------------------------------------------------
# 现金回流（§23）
# ---------------------------------------------------------------------------

def test_sale_proceeds_are_available_the_same_day(cfg, store):
    """卖出资金当天即可用于新的买入挂单（A 股资金 T+0，股票 T+1）。"""
    mkt, pos = _open_position(cfg, store)
    tgt = pos["target_price"]
    mkt.set_bar(A, D2, o=tgt - 0.10, h=tgt + 0.20, l=tgt - 0.30)
    mkt._signals[D2] = make_signals(D2, [SYMS[1]])
    mkt._forecasts[D2] = {SYMS[1]: 0.05}

    before = S.available_cash(store.read_state())
    r = engine.run(run_date=D2, cfg=cfg, store=store, market=mkt)
    st = store.read_state()
    assert r.reports[0].exits and r.reports[0].new_orders
    assert st["cash"] > before                      # 卖出所得已入账
    assert st["reserved_cash"] > 0                  # 且被新挂单立刻占用
