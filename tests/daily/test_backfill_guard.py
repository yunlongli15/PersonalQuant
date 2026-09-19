# -*- coding: utf-8 -*-
"""§24：默认禁止回写历史；backfill 必须显式 --force，且不进入 forward 选择。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from pipeline import daily as D


def test_backfill_without_force_is_refused(run):
    res, _ = run(date="2026-08-03", backfill=True, force=False)
    assert res.status == D.INVALID
    assert any("backfill" in e for e in res.errors)


def test_backfill_with_force_is_allowed(run):
    res, _ = run(date="2026-08-03", backfill=True, force=True)
    assert res.status != D.INVALID
    assert res.backfill is True


def test_backfill_never_produces_a_forward_observation(run):
    """回填是历史模拟，绝不能变成正式 forward 观测。"""
    res, _ = run(date="2026-08-03", backfill=True, force=True)
    assert res.forward_observation is False


def test_backfill_marker_is_recorded(run):
    res, _ = run(date="2026-08-03", backfill=True, force=True)
    assert res.as_dict()["backfill"] is True
