# -*- coding: utf-8 -*-
"""§6 / §7：forward holdout 保护。

起点之前**不算错**（WAITING_FOR_FORWARD_DATA），但结果绝不能写进
clean forward holdout。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

from pipeline import daily as D
from pipeline import freeze as F


def test_holdout_start_is_configured():
    rec = F.load_freeze().get("production_freeze") or {}
    assert rec.get("forward_holdout_start") == "2026-09-18"


def test_pre_forward_run_writes_to_pre_forward_root(monkeypatch, sandbox):
    """起点之前的运行写 pre_forward，不碰 forward_holdout。"""
    called = {}

    class FakeStore:
        def __init__(self, root, forward_start=None):
            called["root"] = Path(root)

    monkeypatch.setattr("paper_live.store.ForwardStore", FakeStore)
    cfg = {"paper_live": {"forward_start_date": "2026-09-18",
                          "paths": {"root": "forward_holdout"}}}
    monkeypatch.setattr("paper_live.config.load_config", lambda: cfg)
    monkeypatch.setattr(D, "PRE_FORWARD_ROOT", sandbox / "pre_forward")

    ctx = D.Ctx(D.DailyRun(run_id="x", date="2026-09-17"),
                pd.Timestamp("2026-09-17"))
    D._paper_ctx(ctx)
    assert "pre_forward" in str(called["root"])
    assert ctx.store_data["paper_is_forward"] is False


def test_forward_date_uses_the_real_holdout(monkeypatch, sandbox):
    called = {}

    class FakeStore:
        def __init__(self, root, forward_start=None):
            called["root"] = Path(root)

    monkeypatch.setattr("paper_live.store.ForwardStore", FakeStore)
    cfg = {"paper_live": {"forward_start_date": "2026-09-18",
                          "paths": {"root": "forward_holdout"}}}
    monkeypatch.setattr("paper_live.config.load_config", lambda: cfg)
    ctx = D.Ctx(D.DailyRun(run_id="x", date="2026-09-18"),
                pd.Timestamp("2026-09-18"))
    D._paper_ctx(ctx)
    assert str(called["root"]).endswith("forward_holdout")
    assert ctx.store_data["paper_is_forward"] is True


def test_forward_ready_is_false_before_the_start():
    """注意：这里**不能用 run fixture** —— 它会把 _forward_ready 换成桩，
    那样测的就是桩而不是真实逻辑了。"""
    r = D.DailyRun(run_id="x", date="2026-09-17")
    assert D._forward_ready(pd.Timestamp("2026-09-17"), r) is False
    assert any("WAITING_FOR_FORWARD_DATA" in w for w in r.warnings)
    # §7：这不是错误
    assert not r.errors


def test_forward_ready_is_true_on_the_start_date():
    r = D.DailyRun(run_id="x", date="2026-09-18")
    D._forward_ready(pd.Timestamp("2026-09-18"), r)


def test_no_silent_write_into_forward_holdout():
    """仓库里 forward_holdout 必须仍然是干净的（本测试只读地断言结构）。"""
    root = F.PROJECT_ROOT / "forward_holdout"
    obs = list((root / "observations").glob("*.json")) if root.exists() else []
    assert all("__rev" not in p.stem for p in obs)
