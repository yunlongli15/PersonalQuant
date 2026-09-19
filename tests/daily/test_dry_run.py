# -*- coding: utf-8 -*-
"""§23：dry-run 只做检查 —— 不联网、不写 forward、不交易、不改 portfolio。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from pipeline import daily as D


def test_dry_run_writes_nothing(run, sandbox):
    res, _ = run(dry_run=True, force=True)
    assert res.dry_run is True
    assert not (sandbox / "reports").exists()
    assert not (sandbox / "manifests").exists()


def test_dry_run_skips_the_writing_tasks(real_run):
    res = real_run(date="2026-09-17", dry_run=True, force=True)
    for name in ("personal_snapshot", "report", "manifest"):
        assert res.task(name).status == D.SKIPPED, name


def test_dry_run_does_not_download_market_data(real_run, monkeypatch):
    """market_data 在 dry-run 下必须 SKIPPED —— 整份快照是几百 MB。"""
    import pipeline.refresh as refresh

    def boom(**kw):
        raise AssertionError("dry-run 不应该调用 market_update（会下载快照）")

    monkeypatch.setattr(refresh, "market_update", boom)
    monkeypatch.setattr(D, "duckdb_available", lambda: (True, "test"))
    # 用真实任务跑（只跑 dry-run 无害的那几步）
    res = real_run(date="2026-09-17", dry_run=True, force=True)
    assert res.task("market_data").status == D.SKIPPED


def test_dry_run_never_produces_a_forward_observation(real_run):
    res = real_run(date="2026-09-17", dry_run=True, force=True)
    assert res.forward_observation is False


def test_dry_run_does_not_record_history(run):
    res, _ = run(dry_run=True, force=True)
    ids = [r["run_id"] for r in D.history()]
    assert res.run_id not in ids
