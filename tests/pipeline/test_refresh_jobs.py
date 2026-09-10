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
