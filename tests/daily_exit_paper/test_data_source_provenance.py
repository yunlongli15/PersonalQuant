# -*- coding: utf-8 -*-
"""数据来源必须留在实验里，不能无痕切换（§七）。

2026-10-13 起，日常信号链路会把当日日线（overlay）叠加进模型输入。
这不改实验规则，却改了**观测从哪来**，所以冻结实验必须能回答
"这一笔观测是哪条链路产出的、用的是哪一版 bar"。
"""

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from daily_exit_paper import engine  # noqa: E402
from tests.daily_exit_paper.conftest import (  # noqa: E402
    SYMS, build_market, run_to)


@pytest.fixture
def state_file(tmp_path, monkeypatch):
    """把信号来源文件指到临时目录 —— 不读真实仓库的状态。"""
    p = tmp_path / "signals_state.json"
    monkeypatch.setattr(engine, "SIGNALS_STATE", p)

    def write(payload):
        p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    return write


def test_run_summary_carries_the_data_source(
        cfg, store, calendar_session, state_file):
    """每一笔 RUN_SUMMARY 都自带来源，事后可查。"""
    state_file({"as_of": "2026-10-02", "bar_source": "canonical+overlay",
                "overlay_sessions": ["2026-10-02"],
                "overlay_bars_sha256": "deadbeef"})
    mkt = build_market({})
    run_to(engine, cfg, store, mkt, run_date=calendar_session[0], capital=100000.0)

    summary = [e for e in store.read_ledger() if e["type"] == "RUN_SUMMARY"][-1]
    assert summary["data_source"]["bar_source"] == "canonical+overlay"
    assert summary["data_source"]["overlay_bars_sha256"] == "deadbeef"


def test_switching_the_data_source_leaves_a_trace(
        cfg, store, calendar_session, state_file):
    """来源从 canonical 变成 canonical+overlay 时必须有事件。

    没有这条的话，把 overlay 打开就等于在同一个实验名下**无痕**换了
    数据来源，前面的观测和后面的没法区分。
    """
    state_file({"as_of": calendar_session[0].strftime("%Y-%m-%d"),
                "bar_source": "canonical"})
    mkt = build_market({})
    run_to(engine, cfg, store, mkt, run_date=calendar_session[0], capital=100000.0)
    assert not [e for e in store.read_ledger()
                if e["type"] == "DATA_SOURCE_CHANGED"]

    state_file({"as_of": calendar_session[1].strftime("%Y-%m-%d"),
                "bar_source": "canonical+overlay",
                "overlay_sessions": [calendar_session[1].strftime("%Y-%m-%d")],
                "overlay_bars_sha256": "abc123"})
    run_to(engine, cfg, store, mkt, run_date=calendar_session[1])

    ev = [e for e in store.read_ledger() if e["type"] == "DATA_SOURCE_CHANGED"]
    assert len(ev) == 1
    assert ev[0]["from"] == "canonical"
    assert ev[0]["to"] == "canonical+overlay"
    assert ev[0]["overlay_bars_sha256"] == "abc123"


def test_first_record_does_not_claim_a_change_it_cannot_prove(
        cfg, store, calendar_session, state_file):
    """在"记录来源"之前就在跑的老实验：第一笔记下来时**不能**声称
    "来源变了"（之前是什么没人知道），但必须写清楚"从本笔起才有记录"。"""
    state_file({"as_of": calendar_session[0].strftime("%Y-%m-%d"),
                "bar_source": "canonical+overlay"})
    mkt = build_market({})
    run_to(engine, cfg, store, mkt, run_date=calendar_session[0], capital=100000.0)
    # 第一笔：state 里还没有 data_source，但实验也还没有历史 -> 不记事件
    assert not [e for e in store.read_ledger()
                if e["type"].startswith("DATA_SOURCE")]

    # 第二笔：state 里已经有上一笔的来源了，正常比较
    state_file({"as_of": calendar_session[1].strftime("%Y-%m-%d"),
                "bar_source": "canonical"})
    run_to(engine, cfg, store, mkt, run_date=calendar_session[1])
    ev = [e for e in store.read_ledger() if e["type"] == "DATA_SOURCE_CHANGED"]
    assert len(ev) == 1 and ev[0]["to"] == "canonical"


def test_unreadable_provenance_is_unknown_not_a_guess(cfg, store, calendar_session,
                                                      monkeypatch, tmp_path):
    """读不到来源就记 unknown —— 账本里"不知道"和"来自上游快照"是两件事。"""
    monkeypatch.setattr(engine, "SIGNALS_STATE", tmp_path / "nope.json")
    mkt = build_market({})
    run_to(engine, cfg, store, mkt, run_date=calendar_session[0], capital=100000.0)
    summary = [e for e in store.read_ledger() if e["type"] == "RUN_SUMMARY"][-1]
    assert summary["data_source"]["bar_source"] == "unknown"


def test_first_run_of_a_brand_new_experiment_records_no_transition(
        cfg, store, calendar_session, state_file, tmp_path, monkeypatch):
    """新实验的第一笔不是"切换" —— 没有"以前"可言。

    这一条是回归：判断用的是 n_runs 自增**之后**的值，而那时它必然 > 0，
    于是每个新实验的第一笔都会记一条假的 DATA_SOURCE_FIRST_RECORDED。
    """
    state_file({"as_of": calendar_session[0].strftime("%Y-%m-%d"),
                "bar_source": "canonical+overlay"})
    mkt = build_market({})
    run_to(engine, cfg, store, mkt, run_date=calendar_session[0],
           capital=100000.0)
    assert not [e for e in store.read_ledger()
                if e["type"].startswith("DATA_SOURCE")]
