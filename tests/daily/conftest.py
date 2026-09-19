# -*- coding: utf-8 -*-
"""tests/daily 共用夹具。

编排逻辑的测试**不应该需要 DuckDB**（单进程独占，而且很慢）。
这里把任务函数替换成可控的假实现，只测编排本身：依赖图、幂等、
守卫、失败传播。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from pipeline import daily as D


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """把日志/日报/manifest/历史都指到临时目录。"""
    monkeypatch.setattr(D, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(D, "REPORT_DIR", tmp_path / "reports")
    monkeypatch.setattr(D, "MANIFEST_DIR", tmp_path / "manifests")
    monkeypatch.setattr(D, "PRE_FORWARD_ROOT", tmp_path / "pre_forward")
    # 运行历史必须隔离，否则会读到真实运行记录（测试之间互相污染）
    monkeypatch.setattr("pipeline.jobs.JOBS_DB", tmp_path / "jobs.db")
    return tmp_path


@pytest.fixture
def fake_tasks(monkeypatch):
    """把所有任务替换成可控假任务；返回控制面板。

    用法：
        fake_tasks.set("market_data", D.INVALID)
        fake_tasks.calls  # 记录每个任务是否被调用
    """
    class Panel:
        def __init__(self):
            self.status = {}
            self.calls = []
            self.detail = {}

        def set(self, name, status, detail="", exc=None):
            self.status[name] = (status, detail, exc)

    panel = Panel()

    def make(name):
        def _fn(ctx):
            panel.calls.append(name)
            st = panel.status.get(name)
            if st is None:
                return D.OK, f"{name} ok"
            status, detail, exc = st
            if exc is not None:
                raise exc
            return status, detail or f"{name} {status}"
        return _fn

    new_tasks = [(n, make(n), deps, blocking)
                 for n, _fn, deps, blocking in D.TASKS]
    monkeypatch.setattr(D, "TASKS", new_tasks)

    # 环境检查里有 DuckDB 探测，测试里直接放行
    monkeypatch.setattr(D, "duckdb_available", lambda: (True, "test"))
    # 冻结校验在编排测试里也放行（另有专门的 freeze 测试）
    monkeypatch.setattr(D, "_forward_ready", lambda t, r: False)
    return panel


# 测试里替换成桩的任务：联网的 + 跑模型的（都太慢/不确定），
# 其余（report / manifest / summary）用真实实现 —— 那些才是有文件产出的。
NETWORK_TASKS = ("market_data", "news", "financial_lazy",
                 "paper_prediction", "personal_snapshot")


@pytest.fixture
def mixed_run(monkeypatch, sandbox):
    """**只有联网任务被替换**，report / manifest / summary 用真实实现。

    日报与 manifest 的测试必须用它 —— 全桩的话根本不会写文件。
    """
    monkeypatch.setattr(D, "duckdb_available", lambda: (True, "test"))

    def _stub(name):
        def _fn(ctx):
            return D.SKIPPED, f"{name} stub（测试不联网）"
        return _fn

    new_tasks = [(n, _stub(n) if n in NETWORK_TASKS else fn, deps, blocking)
                 for n, fn, deps, blocking in D.TASKS]
    monkeypatch.setattr(D, "TASKS", new_tasks)

    def _run(**kw):
        kw.setdefault("force", True)
        return D.run_daily(**kw)
    return _run


@pytest.fixture
def real_run(monkeypatch, sandbox):
    """用**真实任务**跑（dry-run 安全），只把 DuckDB 探测放行。

    dry-run 相关断言必须用它 —— fake_tasks 会把所有任务替换成返回 OK 的桩，
    那样测不到"dry-run 下 report 应该是 SKIPPED"。
    """
    monkeypatch.setattr(D, "duckdb_available", lambda: (True, "test"))

    def _run(**kw):
        return D.run_daily(**kw)
    return _run


@pytest.fixture
def run(monkeypatch, sandbox, fake_tasks):
    """跑一次编排；返回 (result, panel)。默认非 dry-run。"""
    def _run(**kw):
        kw.setdefault("force", True)
        res = D.run_daily(**kw)
        return res, fake_tasks
    return _run
