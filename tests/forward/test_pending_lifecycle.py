# -*- coding: utf-8 -*-
"""C1 修复的回归测试：挂单生命周期。

铁律：**"T+1 行情还没到"不是失败**。

T 日收盘后运行时，交易日历的最后一天就是 T 本身（系统里没有未来日历），
所以"下一个交易日"必然查不到。旧实现把这个正常状态：
    * 写进挂单文件的 execution_date 为 null；
    * 下次运行读出来变成 NaT，绕过 `is None` 守卫；
    * DuckDB 对 'NaT' 的类型错误被 `except Exception: return False` 吞掉；
    * 而每次运行又无条件**覆盖**挂单文件 —— 上一批挂单无声消失。
结果是 paper-live 三次前瞻观测全部 0 成交（reports/前瞻实验-执行链审计.md §3.1）。

这里逐条锁死修复后的行为。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

from paper_live.engine import (PENDING_FORMAT, Availability, LedgerMismatch,
                               PendingError, order_id, run_day)
from paper_live.store import ForwardStore

SIGNAL = pd.Timestamp("2026-09-30")


def _store(cfg) -> ForwardStore:
    return ForwardStore(Path(cfg["paper_live"]["paths"]["root"]),
                        cfg["paper_live"]["forward_start_date"])


def _limit_calendar(provider, cut) -> None:
    """把 provider 的日历截断到 cut —— 模拟"那一天还没发生"。

    真实系统里 `trading_calendar` 只装已经入库的交易日；FakeProvider 默认
    给的是到 2026-12-31 的完整日历，所以必须显式截断才能复现 NOT_YET。
    """
    full = provider.calendar
    provider.trading_calendar = lambda: full[full <= pd.Timestamp(cut)]


def _pending(store) -> dict:
    return store.read_state("pending_orders") or {}


# ---------------------------------------------------------------------------
# 1. T+1 尚不存在 -> PENDING，不是失败
# ---------------------------------------------------------------------------

def test_signal_on_the_last_observed_session_stays_pending(pl_cfg, fake_provider):
    """**核心用例**：signal_date == 数据库最后一个交易日时，
    订单必须挂起保持 PENDING —— 绝不能被判成 NO_FILL / FAILED / CANCELLED。"""
    _limit_calendar(fake_provider, SIGNAL)          # T+1 还不存在
    store = _store(pl_cfg)

    r = run_day(SIGNAL, pl_cfg, store, fake_provider, force_rebalance=True)

    assert r.pending is True
    assert r.n_fills == 0
    assert r.is_rebalance is True                   # 是调仓日，只是还没成交
    assert r.status != "INVALID"                    # 挂起 ≠ 失败

    pend = _pending(store)
    assert pend["format"] == PENDING_FORMAT
    assert len(pend["orders"]) > 0
    assert all(o["status"] == "PENDING" for o in pend["orders"])
    assert all(o["exec_rule"] == "NEXT_SESSION_OPEN" for o in pend["orders"])
    assert all(o["resolved_exec_date"] is None for o in pend["orders"])
    last = pend["attempts"][-1]
    assert last["availability_state"] == Availability.NOT_YET.value
    assert last["result"] == "KEEP_PENDING"
    assert last["observed_run_date"] == str(SIGNAL.date())
    assert last["resolved_exec_date"] is None


def test_pending_orders_carry_stable_unique_ids(pl_cfg, fake_provider):
    """order_id 必须稳定且唯一，否则去重无从谈起。"""
    _limit_calendar(fake_provider, SIGNAL)
    store = _store(pl_cfg)
    run_day(SIGNAL, pl_cfg, store, fake_provider, force_rebalance=True)

    orders = _pending(store)["orders"]
    ids = [o["order_id"] for o in orders]
    assert len(ids) == len(set(ids))
    for o in orders:
        side = "BUY" if o["estimated_shares"] > 0 else "SELL"
        assert o["order_id"] == order_id(
            pl_cfg["paper_live"]["strategy_version"], SIGNAL, o["symbol"], side)


# ---------------------------------------------------------------------------
# 2. 重复运行：不丢、不重复
# ---------------------------------------------------------------------------

def test_rerun_keeps_pending_and_creates_no_duplicates(pl_cfg, fake_provider):
    """重复运行**不得**丢掉上一批挂单，也不得重复创建同一笔订单。

    旧实现每次都写一个全新的 payload，09-18 与 09-24 两批就是这样消失的。
    """
    _limit_calendar(fake_provider, SIGNAL)
    store = _store(pl_cfg)

    run_day(SIGNAL, pl_cfg, store, fake_provider, force_rebalance=True)
    first = _pending(store)["orders"]
    assert first

    run_day(SIGNAL, pl_cfg, store, fake_provider, force_rebalance=True,
            force_rerun=True)
    again = _pending(store)["orders"]

    assert [o["order_id"] for o in again] == [o["order_id"] for o in first]
    # 两次尝试都留痕（第一次挂单、第二次重跑）
    assert len(_pending(store)["attempts"]) == 2


def test_pending_survives_across_repeated_runs(pl_cfg, fake_provider):
    """连续多次运行（日历始终没前进）-> 挂单一直在。"""
    _limit_calendar(fake_provider, SIGNAL)
    store = _store(pl_cfg)

    for _ in range(3):
        r = run_day(SIGNAL, pl_cfg, store, fake_provider,
                    force_rebalance=True, force_rerun=True)
        assert r.pending is True

    pend = _pending(store)
    assert len(pend["orders"]) > 0
    assert len(pend["attempts"]) == 3
    assert all(a["result"] == "KEEP_PENDING" for a in pend["attempts"])


# ---------------------------------------------------------------------------
# 3. T+1 到货 -> READY -> 结算
# ---------------------------------------------------------------------------

def test_pending_settles_once_the_next_session_appears(pl_cfg, fake_provider):
    """日历出现下一个交易日 -> READY -> 按 T+1 开盘价成交。"""
    _limit_calendar(fake_provider, SIGNAL)
    store = _store(pl_cfg)
    run_day(SIGNAL, pl_cfg, store, fake_provider, force_rebalance=True)
    assert _pending(store)["orders"]

    nxt = SIGNAL + pd.Timedelta(days=1)             # 2026-10-01，bdate
    _limit_calendar(fake_provider, nxt)

    r = run_day(nxt, pl_cfg, store, fake_provider)

    assert r.pending is False
    assert r.n_fills > 0
    assert r.execution_date == str(nxt.date())
    assert _pending(store)["orders"] == []
    assert _pending(store)["attempts"][-1]["availability_state"] == \
        Availability.READY.value
    assert _pending(store)["attempts"][-1]["resolved_exec_date"] == \
        str(nxt.date())

    # 成交价就是 T+1 开盘（FakeProvider 用收盘序列当开盘）
    trades = store.read_frame("trades", nxt)
    filled = trades[trades["status"] == "FILLED"]
    assert not filled.empty
    for _, row in filled.iterrows():
        assert row["fill_price"] == pytest.approx(
            fake_provider._close.loc[nxt, row["symbol"]])


def test_ready_but_symbol_has_no_bar_is_a_settled_no_fill(pl_cfg, fake_provider):
    """T+1 **已经存在**但该股当天没有 bar -> 可判定的 NO_FILL（停牌）。

    这是"当天在日历里 ⇒ 市场有成交、数据已入库 ⇒ 这只票就是没交易"，
    不是"再等等" —— 所以挂单要结算掉，而不是继续挂着。
    """
    _limit_calendar(fake_provider, SIGNAL)
    store = _store(pl_cfg)
    run_day(SIGNAL, pl_cfg, store, fake_provider, force_rebalance=True)

    fake_provider.halt = set(fake_provider.symbols)  # T+1 整池停牌
    nxt = SIGNAL + pd.Timedelta(days=1)
    _limit_calendar(fake_provider, nxt)

    r = run_day(nxt, pl_cfg, store, fake_provider)

    assert r.n_fills == 0
    assert r.pending is False                       # 判定完成，不是还挂着
    assert _pending(store)["orders"] == []
    assert _pending(store)["attempts"][-1]["availability_state"] == \
        Availability.READY.value
    trades = store.read_frame("trades", nxt)
    assert (trades["status"] == "NO_TRADE").all()


# ---------------------------------------------------------------------------
# 4. 系统异常必须 raise，绝不能被吞
# ---------------------------------------------------------------------------

def test_data_error_raises_and_is_recorded(pl_cfg, fake_provider):
    """读取日历本身失败是**系统错误**，必须抛出去并留痕。

    旧实现的 `except Exception: return False` 把 NaT 引起的 DuckDB 类型
    错误静默吞掉 —— 于是一个坏掉的查询看起来就像"今天没行情"。
    """
    _limit_calendar(fake_provider, SIGNAL)
    store = _store(pl_cfg)
    run_day(SIGNAL, pl_cfg, store, fake_provider, force_rebalance=True)
    n_before = len(_pending(store)["orders"])
    assert n_before > 0

    def boom():
        raise RuntimeError("Conversion Error: could not convert 'NaT'")

    fake_provider.trading_calendar = boom

    with pytest.raises(PendingError) as ei:
        run_day(SIGNAL + pd.Timedelta(days=1), pl_cfg, store, fake_provider)

    assert "NaT" in str(ei.value)
    pend = _pending(store)
    assert pend["attempts"][-1]["availability_state"] == \
        Availability.ERROR.value
    assert pend["attempts"][-1]["result"] == "RAISED"
    assert "NaT" in (pend["attempts"][-1]["error_if_any"] or "")
    # 出错也不能把挂单丢掉
    assert len(pend["orders"]) == n_before


# ---------------------------------------------------------------------------
# 5. 旧格式挂单：归档，不结算
# ---------------------------------------------------------------------------

def test_legacy_pending_is_archived_not_settled(pl_cfg, fake_provider):
    """旧格式（execution_date=null、无 format 标记）既不结算也不覆盖。

    拿今天的日历去"补成交"等于用一个早已过去的开盘价伪造历史成交。

    为了把"旧单有没有被结算"与"本次运行自己有没有调仓"分开，这里把日历
    截断到 SIGNAL —— 本次运行不是调仓日，账户的任何变化都只可能来自旧单。
    """
    _limit_calendar(fake_provider, SIGNAL)
    store = _store(pl_cfg)
    store.write_state("pending_orders", {
        "signal_date": "2026-09-18",
        "execution_date": None,
        "orders": [{"symbol": fake_provider.symbols[0], "name": "遗留",
                    "action": "BUY", "estimated_shares": 100,
                    "predicted_return": 0.01}],
    })

    r = run_day(SIGNAL, pl_cfg, store, fake_provider)

    assert any(w.get("kind") == "legacy_pending_archived" for w in r.writes)
    archived = list((store.root / "state").glob("pending_orders.legacy-*.json"))
    assert archived, "旧挂单必须留下归档副本"
    assert "2026-09-18" in archived[0].read_text(encoding="utf-8")
    # 账户没有因为这笔旧单发生任何变化
    assert r.n_fills == 0
    assert r.portfolio["cash"] == pytest.approx(
        pl_cfg["paper_live"]["capital"]["initial"])
    assert r.portfolio["holdings"] == {}
    assert _pending(store)["orders"] == []


# ---------------------------------------------------------------------------
# 6. 账本是真相，状态文件只是缓存
# ---------------------------------------------------------------------------

def test_cash_mismatch_raises_and_never_auto_corrects(pl_cfg, fake_provider):
    """paper_portfolio.json 与账本对不上 -> raise，**不自动改账**。"""
    store = _store(pl_cfg)
    cap = float(pl_cfg["paper_live"]["capital"]["initial"])
    store.write_state("paper_portfolio", {
        "as_of": str(SIGNAL.date()), "cash": cap + 1.0,
        "holdings": {}, "capital_initial": cap,
        "strategy_version": "strategy_v2", "nav": cap + 1.0,
        "peak_nav": cap + 1.0,
    })

    with pytest.raises(LedgerMismatch) as ei:
        run_day(SIGNAL, pl_cfg, store, fake_provider)

    assert "不自动改账" in str(ei.value)
    # 出错之后状态文件必须原样不动
    assert _pending(store) == {}
    assert store.read_state("paper_portfolio")["cash"] == pytest.approx(cap + 1.0)
