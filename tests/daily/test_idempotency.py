# -*- coding: utf-8 -*-
"""§4 / §5：幂等。同一天重复运行，输入相同 → ALREADY_COMPLETED。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from pipeline import daily as D


def test_second_run_same_day_is_already_completed(run):
    res1, _ = run(date="2026-09-17", force=False)
    assert res1.status in (D.OK, D.WARNING)
    res2, _ = run(date="2026-09-17", force=False)
    assert res2.status == D.ALREADY_COMPLETED
    assert res2.tasks == []


def test_force_reruns_and_keeps_the_original_record(run):
    res1, _ = run(date="2026-09-17", force=False)
    res2, _ = run(date="2026-09-17", force=True)
    assert res2.status != D.ALREADY_COMPLETED
    assert res2.tasks  # 真的跑了
    # 原始记录必须还在（--force 不覆盖）
    ids = [r["run_id"] for r in D.history(run_date="2026-09-17")]
    assert res1.run_id in ids and res2.run_id in ids
    assert res1.run_id != res2.run_id


def test_changed_fingerprint_is_not_already_completed(run, monkeypatch):
    res1, _ = run(date="2026-09-17", force=False)
    monkeypatch.setattr(D, "input_fingerprint", lambda d: "different")
    res2, _ = run(date="2026-09-17", force=False)
    assert res2.status != D.ALREADY_COMPLETED


def test_dry_run_is_never_marked_completed(run):
    res1, _ = run(date="2026-09-17", dry_run=True, force=False)
    assert res1.status != D.ALREADY_COMPLETED


def test_history_records_each_run(run):
    res, _ = run(date="2026-09-17")
    rows = D.history(run_date="2026-09-17")
    assert any(r["run_id"] == res.run_id for r in rows)
    assert rows[0]["status"]


def test_run_id_is_unique_per_attempt(run):
    a, _ = run(date="2026-09-17", force=True)
    b, _ = run(date="2026-09-17", force=True)
    assert a.run_id != b.run_id
