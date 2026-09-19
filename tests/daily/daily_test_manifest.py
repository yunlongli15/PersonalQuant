# -*- coding: utf-8 -*-
"""§20 / §29：运行清单与运行历史。"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from pipeline import daily as D
from pipeline import daily_report as R

REQUIRED = ("run_id", "date", "status", "start_time", "end_time",
            "git_commit", "strategy_version", "model_version",
            "feature_version", "news_version", "data_snapshot_id",
            "tasks", "warnings", "errors")


def test_manifest_is_written_with_required_fields(mixed_run, sandbox):
    mixed_run(date="2026-09-17")
    files = list((sandbox / "manifests").glob("*.json"))
    assert files, "没有写出 manifest"
    m = json.loads((sandbox / "manifests" / "2026-09-17.json").read_text(
        encoding="utf-8"))
    missing = [k for k in REQUIRED if k not in m]
    assert not missing, f"manifest 缺字段：{missing}"


def test_manifest_records_every_task(mixed_run, sandbox):
    mixed_run(date="2026-09-17")
    m = json.loads((sandbox / "manifests" / "2026-09-17.json").read_text(
        encoding="utf-8"))
    assert len(m["tasks"]) == len(D.TASKS)
    for t in m["tasks"]:
        assert {"name", "status", "duration_s"} <= set(t)


def test_latest_pointer_is_written(mixed_run, sandbox):
    mixed_run(date="2026-09-17")
    assert (sandbox / "manifests" / "latest.json").exists()


def test_history_row_has_counts_and_commit(run):
    res, _ = run(date="2026-09-17")
    row = [r for r in D.history(run_date="2026-09-17")
           if r["run_id"] == res.run_id][0]
    for k in ("run_id", "run_date", "status", "duration_s",
              "n_warnings", "n_errors", "git_commit"):
        assert k in row, k


def test_manifest_marks_dry_run(run, sandbox):
    res, _ = run(dry_run=True, force=True)
    assert res.as_dict()["dry_run"] is True
