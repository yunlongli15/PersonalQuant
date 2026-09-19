# -*- coding: utf-8 -*-
"""§35：同一天 + 同一数据快照 + 同一策略配置 → 结果必须一致。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

from paper_live.alerts import check_alerts
from paper_live.engine import run_day
from paper_live.store import ForwardStore


def _run(cfg, provider, date, dry=False, force=True, rerun=False):
    store = ForwardStore(Path(cfg["paper_live"]["paths"]["root"]),
                         cfg["paper_live"]["forward_start_date"])
    return store, run_day(date, cfg, store, provider, dry_run=dry,
                          force_rebalance=force, alerts_fn=check_alerts,
                          force_rerun=rerun)


def test_rerunning_the_same_day_is_a_noop(pl_cfg, fake_provider):
    """§35：同一天重跑必须是无操作 —— 否则调度器重复触发会把账户交易两次。"""
    d = pd.Timestamp("2026-09-30")
    store, r1 = _run(pl_cfg, fake_provider, d)
    assert not r1.idempotent and r1.n_fills > 0
    store2, r2 = _run(pl_cfg, fake_provider, d)
    assert r2.idempotent
    assert r2.n_fills == r1.n_fills
    assert r2.metrics["portfolio_value"] == pytest.approx(
        r1.metrics["portfolio_value"])
    assert all(w.get("kind") == "idempotent" for w in r2.writes)


def test_two_runs_from_the_same_starting_state_are_identical(
        pl_cfg, fake_provider):
    """§35 的正确读法：**同一初始状态**下，同样的输入必须给出同样的输出。

    （强制重跑一个已经交易过的日期不算"同样的输入"——那时持仓已经变了，
    引擎看到的是另一组 holdings，输出本来就应当不同。）
    """
    d = pd.Timestamp("2026-09-30")
    store_a, ra = _run(pl_cfg, fake_provider, d)

    cfg_b = {**pl_cfg, "paper_live": {**pl_cfg["paper_live"], "paths": {
        **pl_cfg["paper_live"]["paths"],
        "root": str(Path(pl_cfg["paper_live"]["paths"]["root"]).parent
                    / "holdout_b")}}}
    store_b, rb = _run(cfg_b, fake_provider, d)

    pd.testing.assert_frame_equal(store_a.read_frame("predictions", d),
                                  store_b.read_frame("predictions", d))
    pd.testing.assert_frame_equal(store_a.read_frame("trades", d),
                                  store_b.read_frame("trades", d))
    assert ra.metrics["portfolio_value"] == pytest.approx(
        rb.metrics["portfolio_value"])
    assert ra.metrics["turnover"] == pytest.approx(rb.metrics["turnover"])
    assert ra.metrics["transaction_cost"] == pytest.approx(
        rb.metrics["transaction_cost"])


def test_repeated_runs_are_byte_identical(pl_cfg, fake_provider):
    d = pd.Timestamp("2026-09-30")
    store, _ = _run(pl_cfg, fake_provider, d)
    a = store.read_frame("predictions", d)
    store2, _ = _run(pl_cfg, fake_provider, d)
    b = store2.read_frame("predictions", d)
    pd.testing.assert_frame_equal(a, b)
    assert store.revisions_of("predictions", d) == [0]


def test_a_second_day_advances_the_timeline(pl_cfg, fake_provider):
    store, r1 = _run(pl_cfg, fake_provider, pd.Timestamp("2026-09-30"))
    _, r2 = _run(pl_cfg, fake_provider, pd.Timestamp("2026-10-30"))
    assert r2.signal_date == "2026-10-30"
    assert len(store.observation_dates()) == 2
    assert r2.metrics["portfolio_value"] > 0


def test_holdings_carry_across_runs(pl_cfg, fake_provider):
    store, r1 = _run(pl_cfg, fake_provider, pd.Timestamp("2026-09-30"))
    assert r1.metrics["n_positions"] > 0
    _, r2 = _run(pl_cfg, fake_provider, pd.Timestamp("2026-10-30"))
    assert r2.metrics["n_positions"] > 0
    assert r2.portfolio["cash"] >= 0


def test_dry_run_changes_nothing_on_disk(pl_cfg, fake_provider):
    d = pd.Timestamp("2026-09-30")
    store, r = _run(pl_cfg, fake_provider, d, dry=True)
    assert r.dry_run
    assert store.observation_dates() == []
    assert store.read_frame("predictions", d) is None
