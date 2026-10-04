# -*- coding: utf-8 -*-
"""C2 修复的回归测试：调仓日判定。

旧实现把窗口取成 `[d-70天, d]` 去算"本月最后一个交易日"，而该窗口每个
周期分组的最后一个元素**恒等于 d 自己** —— 于是只要 d 是交易日就返回
True。2026-08 全月 21 个交易日里 20 个被误判
（reports/前瞻实验-执行链审计.md §3.2）。

修复后的语义只有一句：

    d 是调仓日 ⟺ d 之后**已观测到**的第一个交易日落在下一个周期

最后一条是必需的：系统里没有未来交易日历（`trading_calendar` 只装已经
发生的交易日），所以"d 所在周期是否已经结束"在 d 当天**无法确认**，
此时保守返回 False，而不是猜。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

from paper_live.engine import is_rebalance_date, rebalance_signal_date

JUL_TO_OCT = pd.bdate_range("2026-07-01", "2026-10-31")


# ---------------------------------------------------------------------------
# 1. 基本判定
# ---------------------------------------------------------------------------

def test_midmonth_dates_are_not_rebalance_dates(pl_cfg):
    for d in ["2026-08-03", "2026-08-14", "2026-08-28",
              "2026-09-18", "2026-09-24", "2026-10-15"]:
        assert not is_rebalance_date(pd.Timestamp(d), pl_cfg, JUL_TO_OCT), d


def test_confirmed_month_ends_are_rebalance_dates(pl_cfg):
    """已结束月份的最后一个交易日 -> True。"""
    for d in ["2026-07-31", "2026-08-31", "2026-09-30"]:
        assert is_rebalance_date(pd.Timestamp(d), pl_cfg, JUL_TO_OCT), d


def test_non_trading_day_is_never_a_rebalance_date(pl_cfg):
    """周末/节假日（不在交易日历里）-> False，不做工作日近似。"""
    assert pd.Timestamp("2026-08-30").dayofweek == 6      # 周日
    assert not is_rebalance_date(pd.Timestamp("2026-08-30"), pl_cfg, JUL_TO_OCT)
    assert not is_rebalance_date(pd.Timestamp("2026-08-01"), pl_cfg, JUL_TO_OCT)


def test_month_end_falling_on_a_weekend_rolls_back(pl_cfg):
    """月末落在周末 -> 该月最后一个**交易日**才是调仓日。"""
    assert pd.Timestamp("2026-05-31").dayofweek == 6      # 2026-05-31 是周日
    cal = pd.bdate_range("2026-04-01", "2026-06-30")
    assert is_rebalance_date(pd.Timestamp("2026-05-29"), pl_cfg, cal)   # 周五
    assert not is_rebalance_date(pd.Timestamp("2026-05-28"), pl_cfg, cal)


def test_holiday_spans_use_the_trading_calendar_not_weekdays(pl_cfg):
    """含长假的月份以**交易日历**为准。

    构造 2026 年国庆：10-01..10-07 全休市，10-08 才开市。
    那么九月的最后一个交易日是 09-30（而不是"最后一个工作日"）。
    """
    cal = pd.DatetimeIndex([
        d for d in pd.bdate_range("2026-09-01", "2026-10-31")
        if not (pd.Timestamp("2026-10-01") <= d <= pd.Timestamp("2026-10-07"))
    ])
    assert is_rebalance_date(pd.Timestamp("2026-09-30"), pl_cfg, cal)
    assert not is_rebalance_date(pd.Timestamp("2026-09-29"), pl_cfg, cal)
    assert not is_rebalance_date(pd.Timestamp("2026-10-08"), pl_cfg, cal)


# ---------------------------------------------------------------------------
# 2. 三个指定日期 + 未确认即保守
# ---------------------------------------------------------------------------

def test_the_three_historical_dates_are_false(pl_cfg):
    """2026-09-18 / 09-24 / 09-29 都必须是 False。

    真实的九月最后一个交易日是 09-30；这三个日期在当时的日历上都被误判
    成了"月末"，是三次观测全部失真的直接原因之一。
    """
    cal = pd.bdate_range("2026-07-01", "2026-09-29")      # 数据止于 09-29
    for d in ["2026-09-18", "2026-09-24", "2026-09-29"]:
        assert not is_rebalance_date(pd.Timestamp(d), pl_cfg, cal), d


def test_unconfirmed_month_end_is_conservative(pl_cfg):
    """日历止于 d 时**无法确认** d 是否月末 -> False（保守，不是猜）。"""
    cal = pd.bdate_range("2026-07-01", "2026-08-31")
    assert not is_rebalance_date(pd.Timestamp("2026-08-31"), pl_cfg, cal)
    # 一旦观测到 09-01，08-31 立刻被确认
    assert is_rebalance_date(pd.Timestamp("2026-08-31"), pl_cfg,
                             pd.bdate_range("2026-07-01", "2026-09-01"))


# ---------------------------------------------------------------------------
# 3. 与 backtest 语义一致（真实已观测日历，逐日比对）
# ---------------------------------------------------------------------------

def test_matches_backtest_semantics_on_the_observed_calendar(pl_cfg):
    """日历完整时，逐日判定必须与 backtest 的 `rebalance_dates` 逐位一致。

    这是"signal date 一致"的直接证据：`rebalance_dates` 是被历史回测用了
    很久的、正确的实现；paper_live 的逐日谓词不能给出不同的答案。
    唯一允许的差别是**确认时间**：日历最后一个月尚未结束，判不出来。
    """
    from personal_quant.strategy.rebalance import rebalance_dates, trading_days

    cal = pd.DatetimeIndex(trading_days())
    if len(cal) < 100:
        pytest.skip("trading calendar unavailable")

    ref = set(rebalance_dates(str(cal[0].date()), str(cal[-1].date()),
                              "monthly", "last_trading_day"))
    last = pd.Timestamp(cal[-1])
    # 日历最后一个月是否结束无法确认 -> 从参照物里排除（这正是唯一允许的差别）
    ref = {d for d in ref if (d.year, d.month) != (last.year, last.month)}
    probe = [d for d in cal if (d.year, d.month) != (last.year, last.month)]
    assert len(probe) > 100

    mismatches = [str(pd.Timestamp(d).date()) for d in probe
                  if is_rebalance_date(d, pl_cfg, cal) != (d in ref)]
    assert mismatches == [], f"与回测调仓日不一致：{mismatches[:10]}"


def test_matches_backtest_on_a_synthetic_complete_range(pl_cfg):
    """不依赖 DB 的同类比对：日历完整时逐日等于 `rebalance_dates`。"""
    from personal_quant.strategy.rebalance import rebalance_dates

    cal = pd.bdate_range("2026-01-01", "2026-09-30")
    ref = set(rebalance_dates("2026-01-01", "2026-08-31", "monthly",
                              "last_trading_day"))
    mismatches = [str(d.date()) for d in cal
                  if is_rebalance_date(d, pl_cfg, cal) != (d in ref)]
    assert mismatches == []


# ---------------------------------------------------------------------------
# 4. 信号日不得被挪动
# ---------------------------------------------------------------------------

def test_rebalance_signal_date_is_the_previous_session_on_the_first_session(pl_cfg):
    """下个周期第一个交易日 -> 信号日 = 上一个交易日（= 上月末，已确认）。"""
    sig = rebalance_signal_date(pd.Timestamp("2026-10-01"), pl_cfg, JUL_TO_OCT)
    assert sig == pd.Timestamp("2026-09-30")


def test_rebalance_signal_date_never_moves_the_signal_into_the_new_month(pl_cfg):
    """**信号日必须留在上个月**，不能被写成下个月第一天。

    这是 C2 修复中最容易搞反的一点：确认发生在下月首日，但信号日仍然是
    上月末 —— 否则月末策略就悄悄变成了月初策略。
    """
    sig = rebalance_signal_date(pd.Timestamp("2026-10-01"), pl_cfg, JUL_TO_OCT)
    assert sig.to_period("M") == pd.Period("2026-09", freq="M")
    assert sig != pd.Timestamp("2026-10-01")
    assert sig == pd.Timestamp("2026-09-30")


def test_rebalance_signal_date_is_none_on_ordinary_days(pl_cfg):
    """普通交易日（不是某个月的第一个交易日）没有要补做的调仓。"""
    for d in ["2026-07-02", "2026-08-04", "2026-09-18", "2026-10-15"]:
        assert rebalance_signal_date(pd.Timestamp(d), pl_cfg, JUL_TO_OCT) is None, d


def test_rebalance_signal_date_fires_on_every_first_session(pl_cfg):
    """每个月的第一个交易日都要返回上月末 —— 这是"每月调仓一次"的落地点。"""
    expected = {"2026-08-03": "2026-07-31", "2026-09-01": "2026-08-31",
                "2026-10-01": "2026-09-30"}
    for first_session, sig in expected.items():
        assert rebalance_signal_date(
            pd.Timestamp(first_session), pl_cfg, JUL_TO_OCT) == pd.Timestamp(sig)


def test_rebalance_signal_date_is_none_before_the_calendar_starts(pl_cfg):
    cal = pd.bdate_range("2026-09-01", "2026-09-30")
    assert rebalance_signal_date(pd.Timestamp("2026-09-01"), pl_cfg, cal) is None


# ---------------------------------------------------------------------------
# 5. 端到端：补做的调仓在**运行日**开盘成交
# ---------------------------------------------------------------------------

def test_deferred_rebalance_executes_at_the_run_dates_open(pl_cfg, fake_provider):
    """月末信号 + 下月首个交易日运行 -> 成交价 = 运行日开盘。

    证明"确认晚一天"不会让成交价用到未来数据：执行用的是**今天已经发生**
    的开盘价，而特征与预测停在 09-30。
    """
    from paper_live.engine import run_day
    from paper_live.store import ForwardStore

    p = fake_provider
    run_d = pd.Timestamp("2026-10-01")
    sig = rebalance_signal_date(run_d, pl_cfg, p.calendar)
    assert sig == pd.Timestamp("2026-09-30")

    store = ForwardStore(Path(pl_cfg["paper_live"]["paths"]["root"]),
                         pl_cfg["paper_live"]["forward_start_date"])
    r = run_day(run_d, pl_cfg, store, p, signal_date=sig)

    assert r.is_rebalance is True
    assert r.signal_date == "2026-09-30"
    assert r.date == "2026-10-01"
    assert r.execution_date == "2026-10-01"
    assert r.n_fills > 0

    trades = store.read_frame("trades", run_d)
    filled = trades[trades["status"] == "FILLED"]
    assert not filled.empty
    for _, row in filled.iterrows():
        assert row["fill_price"] == pytest.approx(p._close.loc[run_d, row["symbol"]])

    # 预测落在信号日，观测落在运行日 —— 两者都必须记清楚
    preds = store.read_frame("predictions", run_d)
    assert (preds["signal_date"] == "2026-09-30").all()


def test_signal_date_may_not_be_after_the_run_date(pl_cfg, fake_provider):
    """信号日晚于运行日 = 用未来的横截面下单 -> 直接拒绝。"""
    from paper_live.engine import run_day
    from paper_live.store import ForwardStore

    store = ForwardStore(Path(pl_cfg["paper_live"]["paths"]["root"]),
                         pl_cfg["paper_live"]["forward_start_date"])
    with pytest.raises(ValueError):
        run_day(pd.Timestamp("2026-09-30"), pl_cfg, store, fake_provider,
                signal_date=pd.Timestamp("2026-10-01"))
