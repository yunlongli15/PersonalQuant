# -*- coding: utf-8 -*-
"""幂等与隔离（spec §34 / §37 / §38 / §39 / §43 / §48）。"""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from conftest import SESSIONS, SYMS, build_market, day, make_signals
from daily_exit_paper import config as C, engine, state as S, store as ST

A = SYMS[0]
CAP = 66_000.0
D0, D1, D2 = day(SESSIONS, 0), day(SESSIONS, 1), day(SESSIONS, 2)
PKG = C.PROJECT_ROOT / "daily_exit_paper"


# ---------------------------------------------------------------------------
# 幂等（§37）
# ---------------------------------------------------------------------------

def test_rerunning_the_same_day_changes_nothing(cfg, store):
    mkt = build_market({}, {D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    before_state = store.read_state()
    before_ledger = store.read_ledger()
    before_recs = store.snapshot_dates("recommendations")

    r = engine.run(run_date=D0, cfg=cfg, store=store, market=mkt)

    assert r.noop is True and r.sessions == []
    assert store.read_state() == before_state          # 零重复现金变动
    assert store.read_ledger() == before_ledger        # 零重复事件
    assert store.snapshot_dates("recommendations") == before_recs


def test_rerunning_after_a_fill_does_not_trade_twice(cfg, store):
    mkt = build_market({}, {D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    limit = S.pending_list(store.read_state())[0]["limit_price"]
    mkt.set_bar(A, D1, o=limit - 0.30, h=limit, l=limit - 0.40)
    engine.run(run_date=D1, cfg=cfg, store=store, market=mkt)
    cash_after = store.read_state()["cash"]
    n_trades = len([e for e in store.read_ledger()
                    if e["type"] == "ORDER_FILLED"])

    engine.run(run_date=D1, cfg=cfg, store=store, market=mkt)
    assert store.read_state()["cash"] == pytest.approx(cash_after)
    assert len([e for e in store.read_ledger()
                if e["type"] == "ORDER_FILLED"]) == n_trades


def test_recommendation_snapshots_are_immutable(cfg, store):
    st = ST.ExperimentStore(store.root)
    st.write_immutable("recommendations", D0, {"symbol": A, "qty": 100})
    with pytest.raises(ST.AlreadyWritten):
        st.write_immutable("recommendations", D0, {"symbol": A, "qty": 200})
    # 同样的内容再写一次是无操作，不是错误
    _, written = st.write_immutable("recommendations", D0,
                                    {"symbol": A, "qty": 100})
    assert written is False


def test_dry_run_writes_nothing(cfg, store):
    mkt = build_market({}, {D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    r = engine.run(run_date=D0, capital=CAP, dry_run=True, cfg=cfg,
                   store=store, market=mkt)
    assert r.reports and r.reports[0].new_orders     # 算出来了
    assert store.read_state() is None                # 但什么都没写
    assert store.read_ledger() == []
    assert store.snapshot_dates("recommendations") == []


# ---------------------------------------------------------------------------
# 本金与配置锁定（§34 / §35）
# ---------------------------------------------------------------------------

def test_capital_is_locked_after_the_first_run(cfg, store):
    mkt = build_market({}, {D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    assert store.read_experiment()["initial_capital"] == pytest.approx(CAP)

    with pytest.raises(engine.EngineError) as e:
        engine.run(run_date=D1, capital=CAP + 1.0, cfg=cfg, store=store,
                   market=mkt)
    assert "本金已锁定" in str(e.value)
    assert "新建实验版本" in str(e.value)


def test_first_run_requires_an_explicit_capital(cfg, store):
    mkt = build_market({}, {D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    with pytest.raises(engine.EngineError) as e:
        engine.run(run_date=D0, cfg=cfg, store=store, market=mkt)
    assert "--capital" in str(e.value)


def test_config_drift_is_refused(cfg, store):
    mkt = build_market({}, {D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    exp = store.read_experiment()
    exp["config_sha256"] = "0" * 64
    store._write_json(store.root / "experiment.json", exp)
    with pytest.raises(C.ConfigDrift):
        engine.run(run_date=D1, cfg=cfg, store=store, market=mkt)


def test_experiment_metadata_records_what_matters(cfg, store):
    mkt = build_market({}, {D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    exp = store.read_experiment()
    for k in ("experiment_id", "strategy_version", "base_strategy",
              "initial_capital", "first_signal_date", "config_sha256",
              "git_commit", "working_tree", "created_at"):
        assert exp.get(k) is not None, k
    assert exp["base_strategy"] == "strategy_v2"
    # first_signal_date 记的是**实验第一天用的信号日**，不是程序安装日
    assert exp["first_signal_date"] == str(D0.date())
    assert exp["working_tree"] in ("clean", "dirty")


def test_experiment_creation_also_creates_the_incident_log(cfg, store):
    """incident log 在实验创建时一并建好（spec §25），且带规则说明。"""
    mkt = build_market({}, {D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    p = store.root / "incidents.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "Incident Log" in text
    assert "错误也必须保留" in text
    assert "因为最近几笔盈亏而调参" in text
    assert "STOP EXPERIMENT" in text


# ---------------------------------------------------------------------------
# 实验从零状态起步（§43）
# ---------------------------------------------------------------------------

def test_experiment_starts_from_a_clean_state(cfg, store):
    st = S.empty_state(CAP, as_of=None)
    assert st["cash"] == CAP and st["positions"] == {}
    assert st["pending_entries"] == [] and st["reserved_cash"] == 0.0
    mkt = build_market({}, {D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    assert store.ledger_len() > 0
    assert len(store.snapshot_dates("recommendations")) == 1


# ---------------------------------------------------------------------------
# 代码级隔离（§2 / §48）
# ---------------------------------------------------------------------------

def _imported_modules(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.add(a.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_core_modules_never_import_paper_live():
    """order/position/cash/lifecycle 必须属于本包自己 —— 不借 paper_live。"""
    core = ["engine.py", "state.py", "execution.py", "ledger.py", "store.py",
            "config.py", "report.py"]
    offenders = {}
    for name in core:
        mods = _imported_modules(PKG / name)
        bad = sorted(m for m in mods if m.split(".")[0] == "paper_live")
        if bad:
            offenders[name] = bad
    assert offenders == {}, f"daily_exit_paper 引用了 paper_live：{offenders}"


def test_package_never_touches_the_forward_holdout_or_wealth_layer():
    """源码层面不得出现对 forward_holdout / wealth 的路径引用。"""
    offenders = {}
    for p in PKG.glob("*.py"):
        text = p.read_text(encoding="utf-8")
        hits = [token for token in ("forward_holdout", "data/wealth",
                                    "wealth.db", "experiments/paper_live")
                if token in text]
        if hits:
            offenders[p.name] = hits
    assert offenders == {}, f"越界引用：{offenders}"


def test_engine_run_does_not_touch_protected_trees(cfg, store):
    """行为层面：跑完整一天后，受保护目录的 mtime 一个都没变。

    特别包含 `data/quant/trade_plans` 与 `reports/paper_live` —— 那是
    `write_recommendation_note.py` 写的共享推荐（spec §17 要求确认
    daily_exit 的 recommendation 快照**不会**被它覆盖，也不会覆盖它）。
    """
    protected = [C.PROJECT_ROOT / "forward_holdout",
                 C.PROJECT_ROOT / "experiments" / "paper_live",
                 C.PROJECT_ROOT / "data" / "wealth",
                 C.PROJECT_ROOT / "data" / "quant" / "trade_plans",
                 C.PROJECT_ROOT / "reports" / "paper_live"]
    before = {p: _mtimes(p) for p in protected}

    mkt = build_market({}, {D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)

    after = {p: _mtimes(p) for p in protected}
    for p in protected:
        assert after[p] == before[p], f"{p} 被改动了"


def test_shared_recommendation_paths_do_not_overlap(cfg, store):
    """daily_exit 的推荐目录与共享交易计划目录必须是两个地方（spec §17）。"""
    mkt = build_market({}, {D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)

    mine = store.root / "recommendations"
    assert mine.exists() and list(mine.glob("*.json"))
    assert not any(str(p).startswith(str(C.PROJECT_ROOT / "data"))
                   for p in mine.rglob("*"))
    assert not any(str(p).startswith(str(C.PROJECT_ROOT / "reports"))
                   for p in mine.rglob("*"))


def _mtimes(root: Path):
    if not root.exists():
        return {}
    return {str(f): f.stat().st_mtime_ns for f in root.rglob("*") if f.is_file()}


def test_writes_stay_inside_the_experiment_directory(cfg, store):
    mkt = build_market({}, {D0: make_signals(D0, [A])}, {D0: {A: 0.05}})
    engine.run(run_date=D0, capital=CAP, cfg=cfg, store=store, market=mkt)
    produced = sorted(p.name for p in store.root.rglob("*") if p.is_file())
    assert "state.json" in produced
    assert "ledger.jsonl" in produced
    assert "experiment.json" in produced
    assert "recommendations" in [p.name for p in store.root.iterdir()]
