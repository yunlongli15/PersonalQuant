# -*- coding: utf-8 -*-
"""STEP 7C: job store, offline behaviour, failure handling, incremental
and duplicate-safety (spec §20/§38/§50 data tests)."""

import os

import pandas as pd
import pytest

from pipeline import jobs, refresh


def test_job_recorded_success(jobstore):
    run = jobs.run_job("demo", lambda: {"n": 3}, conn=jobstore)
    assert run.status == "SUCCESS" and "n" in run.detail
    hist = jobs.history(jobstore)
    assert hist[0]["job_name"] == "demo"
    assert hist[0]["duration_s"] is not None


def test_job_failure_recorded_and_reraised(jobstore):
    def boom():
        raise ValueError("kaboom")

    with pytest.raises(ValueError):
        jobs.run_job("bad", boom, conn=jobstore)
    last = jobs.last_run(jobstore, "bad")
    assert last["status"] == "FAILED"
    assert "kaboom" in last["error"]


def test_skip_job_recorded(jobstore):
    jobs.skip_job("networky", "offline mode", conn=jobstore)
    last = jobs.last_run(jobstore, "networky")
    assert last["status"] == "SKIPPED"


def test_status_summary_keeps_latest_per_job(jobstore):
    jobs.run_job("a", lambda: None, conn=jobstore)
    jobs.run_job("a", lambda: None, conn=jobstore)
    s = jobs.status_summary(jobstore)
    assert s["a"]["job_id"] == 2


def test_offline_mode_blocks_network_jobs(monkeypatch):
    monkeypatch.setenv("PQ_MODE", "offline")
    with pytest.raises(refresh.OfflineMode):
        refresh.market_update()
    with pytest.raises(refresh.OfflineMode):
        refresh.news_update()


def test_run_all_records_offline_as_skipped(jobstore, monkeypatch):
    monkeypatch.setenv("PQ_MODE", "offline")
    results = refresh.run_all(conn=jobstore,
                              jobs={"market_update": refresh.market_update})
    assert results[0]["status"] == "SKIPPED_OFFLINE"
    assert jobs.last_run(jobstore, "market_update")["status"] == "SKIPPED"


def test_run_all_stops_on_failure_by_default(jobstore):
    calls = []

    def ok():
        calls.append("a")
        return "done"

    def bad():
        raise RuntimeError("nope")

    with pytest.raises(RuntimeError):
        refresh.run_all(conn=jobstore, jobs={"a": ok, "b": bad})
    assert calls == ["a"]


def test_run_all_continue_on_error(jobstore):
    def bad():
        raise RuntimeError("nope")

    results = refresh.run_all(conn=jobstore,
                              jobs={"b": bad, "c": lambda: "fine"},
                              continue_on_error=True)
    assert [r["status"] for r in results] == ["FAILED", "SUCCESS"]


def test_run_all_only_subset(jobstore):
    results = refresh.run_all(conn=jobstore, only=["c"],
                              jobs={"b": lambda: "no", "c": lambda: "yes"})
    assert [r["job"] for r in results] == ["c"]


def test_job_order_is_dependency_order():
    names = refresh.JOB_NAMES
    assert names.index("market_update") < names.index("factor_refresh")
    assert names.index("factor_refresh") < names.index("signal_refresh")
    assert names.index("signal_refresh") < names.index("forecast_refresh")
    assert names.index("forecast_refresh") < names.index("portfolio_refresh")


def test_signal_snapshot_roundtrip(tmp_path, monkeypatch):
    """Duplicate-safety/incremental: saving the same date twice replaces
    the snapshot rather than appending."""
    from pipeline import signals

    monkeypatch.setattr(signals, "QUANT_DIR", tmp_path)
    monkeypatch.setattr(signals, "SIGNALS_LATEST",
                        tmp_path / "signals_latest.parquet")
    monkeypatch.setattr(signals, "SIGNALS_STATE", tmp_path / "state.json")
    df = pd.DataFrame({
        "symbol": ["600519.SH", "000001.SZ"],
        "prediction": [0.03, 0.02], "signal_date":
            pd.to_datetime(["2026-09-10"] * 2),
        "raw_rank": [1, 2], "name": ["贵州茅台", "平安银行"],
        "is_top": [True, True]})
    signals.save_signals(df, "2026-09-10")
    signals.save_signals(df, "2026-09-10")           # idempotent
    assert (tmp_path / "signals_2026-09-10.parquet").exists()
    dated = sorted(tmp_path.glob("signals_20*.parquet"))
    assert len(dated) == 1                           # no duplicate snapshot
    loaded = pd.read_parquet(tmp_path / "signals_latest.parquet")
    assert len(loaded) == 2
    state = signals.signals_state()
    assert state["as_of"] == "2026-09-10"
    assert state["n_symbols"] == 2


def test_freshness_reads_signal_state(fake_data_tree, monkeypatch, tmp_path):
    from pipeline import freshness, signals

    quant = tmp_path / "data" / "quant"
    quant.mkdir(parents=True)
    monkeypatch.setattr(freshness, "PROJECT_ROOT", tmp_path)
    (quant / "signals_state.json").write_text(
        '{"as_of": "2026-09-10"}', encoding="utf-8")
    f = {x.domain: x for x in freshness.data_status(now="2026-09-10")}
    # Forecast is stamped by forecast_state.json (7D); signals stamp is
    # reported through the same freshness family
    assert f["Forecast"].status in (freshness.OK, freshness.UNKNOWN)


# ---------------------------------------------------------------------------
# 默认作业集合（2026-09-21/22 用户反馈）
# ---------------------------------------------------------------------------

def test_financial_update_is_opt_in():
    """财务是 lazy/按需的：一次全量抓取实测 2 小时以上（7904 秒），
    而 S3 特征集根本不含财务因子。它必须留在列表里（--only 可用），
    但**默认不跑**。"""
    assert "financial_update" in refresh.JOB_NAMES
    assert "financial_update" in refresh.OPT_IN_JOBS


def test_live_price_runs_between_signals_and_portfolio():
    """实时价要在信号之后取（要按排名选标的）、在组合之前用。"""
    names = [n for n, _ in refresh.REFRESH_JOBS]
    assert "live_price_refresh" in names
    assert names.index("signal_refresh") < names.index("live_price_refresh")
    assert names.index("live_price_refresh") < names.index("portfolio_refresh")


def test_run_all_skips_opt_in_jobs_by_default(jobstore):
    calls = []

    def make(name):
        def _fn(**kw):
            calls.append(name)
            return f"{name} ok"
        return _fn

    table = {n: make(n) for n in ("market_update", "financial_update")}
    refresh.run_all(conn=jobstore, jobs=table)
    assert "market_update" in calls
    assert "financial_update" not in calls


def test_run_all_runs_opt_in_when_explicitly_asked(jobstore):
    calls = []

    def make(name):
        def _fn(**kw):
            calls.append(name)
            return f"{name} ok"
        return _fn

    table = {n: make(n) for n in ("market_update", "financial_update")}
    refresh.run_all(only=["financial_update"], conn=jobstore, jobs=table)
    assert calls == ["financial_update"]


# ---------------------------------------------------------------------------
# 复权因子修复 + 新闻派生层跳过（2026-09-27）
# ---------------------------------------------------------------------------

def test_factor_rebase_repair_runs_right_after_market_update():
    """每次换快照都会把上游的因子跳变带回来，所以修复必须紧跟
    market_update、早于 factor_refresh —— 漏跑一次，信号就可能吃到
    跳变的复权价。"""
    names = [n for n, _ in refresh.REFRESH_JOBS]
    assert "factor_rebase_repair" in names
    assert names.index("market_update") < names.index("factor_rebase_repair")
    assert names.index("factor_rebase_repair") < names.index("factor_refresh")


def test_factor_rebase_repair_raises_when_jumps_remain(monkeypatch):
    """还有未修复的跳变就抛出去，不能带着坏数据继续往下跑。"""
    from scripts.quant import repair_factor_rebase

    monkeypatch.setattr(repair_factor_rebase, "main", lambda: 1)
    with pytest.raises(RuntimeError):
        refresh.factor_rebase_repair()


class _FakeConn:
    def __init__(self, n, m):
        self._r = (n, m)

    def execute(self, *a, **k):
        return self

    def fetchone(self):
        return self._r


def _stamp(tmp_path, payload):
    p = tmp_path / "data" / "derived" / "news" / ".build_stamp.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(payload, encoding="utf-8")
    return p


def test_news_events_skips_rebuild_when_canonical_unchanged(monkeypatch,
                                                            tmp_path):
    """全量重建 18 万条文档要 ~8 分钟，canonical 没变就不该重建。"""
    from personal_quant import db as pqdb
    from scripts.news import build_events

    monkeypatch.setattr(refresh, "PROJECT_ROOT", tmp_path)
    _stamp(tmp_path, '{"n": 10, "max": "2026-09-24 10:00:00"}')
    monkeypatch.setattr(pqdb, "connect",
                        lambda: _FakeConn(10, "2026-09-24 10:00:00"))
    called = []
    monkeypatch.setattr(build_events, "main", lambda: called.append(1) or 0)

    detail = refresh.news_events_refresh()
    assert called == [], "canonical 没变却重建了"
    assert "跳过重建" in detail


def test_news_events_rebuilds_when_new_documents_arrive(monkeypatch, tmp_path):
    from personal_quant import db as pqdb
    from scripts.news import build_events

    monkeypatch.setattr(refresh, "PROJECT_ROOT", tmp_path)
    _stamp(tmp_path, '{"n": 10, "max": "2026-09-24 10:00:00"}')
    monkeypatch.setattr(pqdb, "connect",
                        lambda: _FakeConn(12, "2026-09-25 09:00:00"))
    called = []
    monkeypatch.setattr(build_events, "main", lambda: called.append(1) or 0)

    detail = refresh.news_events_refresh()
    assert called == [1], "有新文档却没有重建"
    assert "已重建" in detail
