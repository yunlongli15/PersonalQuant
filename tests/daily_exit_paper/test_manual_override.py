# -*- coding: utf-8 -*-
"""人工干预：三层分离（spec §26-§28）。

核心断言：用户改过的东西**不会写回系统建议**。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from conftest import SESSIONS, SYMS, build_market, day, make_signals
from daily_exit_paper import config as C, decisions as D, engine, state as S

A, B = SYMS[0], SYMS[1]
CAP = 66_000.0
D0, D1 = day(SESSIONS, 0), day(SESSIONS, 1)


def _cost(cfg):
    from personal_quant.strategy.costs import TransactionCostModel

    return TransactionCostModel.from_config(
        {"transaction_costs": C.spec(cfg)["transaction_costs"]})


def _market():
    return build_market({}, {D0: make_signals(D0, [A, B])},
                        {D0: {A: 0.05, B: 0.05}})


# ---------------------------------------------------------------------------
# 缺省 = 完全采纳
# ---------------------------------------------------------------------------

def test_without_a_decision_file_everything_is_adopted(cfg, store):
    mkt = _market()
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    st = store.read_state()
    assert {o["symbol"] for o in S.pending_list(st)} == {A, B}
    assert D.load_decision(store, D0) is None
    rec = store.read_snapshot("recommendations", D0)
    assert rec["decision_layer"] == "system_recommendation"
    assert rec["entries"] and all("user_action" not in e for e in rec["entries"])


# ---------------------------------------------------------------------------
# SKIP
# ---------------------------------------------------------------------------

def test_skip_removes_the_order_but_keeps_the_recommendation(cfg, store):
    D.record_decision(store, D0, [
        {"symbol": B, "action": D.SKIP, "override_reason": "不想买这只"}])
    mkt = _market()
    r = engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)

    assert {o["symbol"] for o in S.pending_list(store.read_state())} == {A}
    assert {"symbol": B, "reason": "user_skip"} in r.reports[0].skipped
    ov = [o for o in r.reports[0].overrides if o["symbol"] == B][0]
    assert ov["user_action"] == D.SKIP and ov["override"] is True
    assert ov["override_reason"] == "不想买这只"
    assert ov["system_action"] == "BUY"

    # 系统建议原封不动 —— 这才回答得了"照系统做会怎样"
    rec = store.read_snapshot("recommendations", D0)
    assert {e["symbol"] for e in rec["entries"]} == {A, B}


# ---------------------------------------------------------------------------
# MODIFY
# ---------------------------------------------------------------------------

def test_modify_applies_the_users_price_and_quantity(cfg, store):
    """用户把限价调低、股数改成 200 -> 挂单按用户的走，
    但**系统建议里仍然是原来那份**（§27）。"""
    cost = _cost(cfg)
    # 先用一个独立的 store 探一次系统建议（避免污染被测的那一份）
    mkt = _market()
    from daily_exit_paper import store as ST
    probe = ST.ExperimentStore(store.root.parent / "probe").ensure()
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=probe, market=mkt)
    sys_a = {e["symbol"]: e
             for e in probe.read_snapshot("recommendations", D0)["entries"]}[A]

    user_limit = round(sys_a["limit_price"] - 0.50, 2)
    D.record_decision(store, D0, [
        {"symbol": A, "action": D.MODIFY, "limit_price": user_limit,
         "quantity": 200, "override_reason": "挂低一点"}])
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)

    order = [o for o in S.pending_list(store.read_state())
             if o["symbol"] == A][0]
    assert order["limit_price"] == pytest.approx(user_limit)
    assert order["quantity"] == 200
    assert order["reserved_cash"] == pytest.approx(
        200 * user_limit + cost.buy_cost(200 * user_limit), abs=0.01)

    # 系统建议没有被改写
    rec_a = [e for e in store.read_snapshot("recommendations", D0)["entries"]
             if e["symbol"] == A][0]
    assert rec_a["limit_price"] == pytest.approx(sys_a["limit_price"])
    assert rec_a["quantity"] == sys_a["quantity"]


def test_modify_requires_a_reason(store):
    with pytest.raises(D.DecisionError) as e:
        D.record_decision(store, D0, [{"symbol": A, "action": D.MODIFY,
                                       "limit_price": 9.0}])
    assert "override_reason" in str(e.value)


def test_unknown_action_is_rejected(store):
    with pytest.raises(D.DecisionError):
        D.record_decision(store, D0, [{"symbol": A, "action": "YOLO"}])


def test_modify_quantity_must_be_a_whole_lot(cfg, store):
    D.record_decision(store, D0, [
        {"symbol": A, "action": D.MODIFY, "quantity": 150,
         "override_reason": "零股"}])
    with pytest.raises(D.DecisionError) as e:
        engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store,
                   market=_market())
    assert "整数倍" in str(e.value)


# ---------------------------------------------------------------------------
# executions 层与统计
# ---------------------------------------------------------------------------

def test_actual_execution_is_stored_separately(store):
    D.record_execution(store, D0, [
        {"symbol": A, "filled": True, "price": 9.85, "shares": 300,
         "note": "券商实际成交价"}])
    ex = store.read_snapshot("executions", D0)
    assert ex["layer"] == "actual_execution"
    assert ex["executions"][0]["price"] == 9.85
    # 与系统建议完全分开
    assert store.read_snapshot("recommendations", D0) is None


def test_override_summary_counts_without_changing_anything(cfg, store):
    D.record_decision(store, D0, [
        {"symbol": A, "action": D.SKIP, "override_reason": "x"},
        {"symbol": B, "action": D.MODIFY, "limit_price": 9.0,
         "override_reason": "y"}])
    D.record_execution(store, D0, [{"symbol": A, "filled": True,
                                    "price": 9.9, "shares": 100}])
    s = D.override_summary(store)
    assert s["decisions"] == 2 and s["SKIP"] == 1 and s["MODIFY"] == 1
    assert s["executions_recorded"] == 1


def test_start_banner_and_daily_markdown_render(cfg, store):
    """正式启动当晚才会第一次调用的两个渲染函数，必须当场就能跑通。

    （横幅只在"实验第一次被创建"时打印；日报在每次正式运行后落盘。
    这两条路径平时走不到，所以要在这里钉住。）
    """
    from daily_exit_paper import preflight as PF
    from daily_exit_paper import report as R

    D.record_decision(store, D0, [
        {"symbol": B, "action": D.SKIP, "override_reason": "不想买"}])
    mkt = _market()
    limit = None
    r = engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    exp = store.read_experiment()
    overrides = [o for rep in r.reports for o in rep.overrides]

    banner = R.render_start_banner(exp, C.spec(cfg), {
        "market_data_last_date": str(D0.date()),
        "checks": {"feature_date": {"detail": "x"}}}, next_exec=None)
    assert "OFFICIAL START" in banner
    assert "CLEAN START" in banner
    assert f"{CAP:,.2f}" in banner
    assert str(D0.date()) in banner

    md = R.render_daily_markdown(r, C.spec(cfg), exp, {}, None, None,
                                 overrides)
    for heading in ("## Portfolio", "## Open Positions", "## New Entries",
                    "## Exits", "## No Fills", "## Pending Entries",
                    "## Fees", "## Manual Overrides", "## Status"):
        assert heading in md, heading
    assert "不想买" in md
    assert "只陈述事实" in md


def test_report_renders_the_override_block(cfg, store):
    from daily_exit_paper import report as R

    D.record_decision(store, D0, [
        {"symbol": B, "action": D.SKIP, "override_reason": "不想买"}])
    mkt = _market()
    r = engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    text = R.render_daily(r, C.spec(cfg), store.read_experiment(), {},
                          overrides=[o for rep in r.reports
                                     for o in rep.overrides])
    assert "MANUAL OVERRIDES (1)" in text
    assert "不想买" in text
    assert "系统 BUY → 用户 SKIP" in text


# ---------------------------------------------------------------------------
# executions 层：**纯记录**，绝不能改变实验
# ---------------------------------------------------------------------------

def test_recording_an_execution_does_not_change_the_experiment(cfg, store):
    """回填实际成交之后，重跑同一天必须产出**完全一样**的挂单。

    这是 `scripts/quant/record_paper_execution.py` 的核心承诺：用户只是
    "记一笔我在券商模拟盘做了什么"，实验该怎样还怎样。写错层（写成
    decisions）就会真的改掉实验，所以这条必须钉死。
    """
    mkt = _market()
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    before = [dict(o) for o in S.pending_list(store.read_state())]
    rec_before = store.read_snapshot("recommendations", D0)

    # 回填：A 成交、B 我选择不买
    D.record_execution(store, D0, [
        {"symbol": A, "filled": True, "price": 9.9, "shares": 100},
        {"symbol": B, "filled": False, "reason": "user_skip"},
    ], note="券商模拟盘")

    ex = store.read_snapshot("executions", D0)
    assert ex["layer"] == "actual_execution"
    assert len(ex["executions"]) == 2

    # 系统建议一字未改
    assert store.read_snapshot("recommendations", D0) == rec_before
    # decisions 层没有被本操作创建
    assert D.load_decision(store, D0) is None
    # 账本里的挂单没有因为回填而改变
    after = [dict(o) for o in S.pending_list(store.read_state())]
    assert after == before, f"回填成交改变了挂单：{before} -> {after}"


def test_execution_layer_never_overwrites_the_recommendation(cfg, store):
    """建议层是只读的 —— 回填不改它，这是三层分离的前提。"""
    mkt = _market()
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    rec = store.read_snapshot("recommendations", D0)
    assert rec["decision_layer"] == "system_recommendation"
    prices_before = {e["symbol"]: e["limit_price"] for e in rec["entries"]}

    D.record_execution(store, D0, [
        {"symbol": A, "filled": True, "price": 1.0, "shares": 100}])
    rec2 = store.read_snapshot("recommendations", D0)
    assert {e["symbol"]: e["limit_price"] for e in rec2["entries"]} == \
        prices_before, "回填的成交价被写回了系统建议"


def test_override_summary_counts_executions_separately(cfg, store):
    mkt = _market()
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    D.record_execution(store, D0, [
        {"symbol": A, "filled": True, "price": 9.9, "shares": 100}])
    s = D.override_summary(store)
    assert s["executions_recorded"] == 1
    assert s["decisions"] == 0        # 没写 decisions 就是 0
