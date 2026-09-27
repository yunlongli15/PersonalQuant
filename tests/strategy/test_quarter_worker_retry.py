# -*- coding: utf-8 -*-
"""季度特征 worker 的降级重试（2026-09-22 实际故障）。

`signal_refresh` 因 worker 超时 1800s 而 FAILED，整条刷新链断在中途 ——
实时价、预测、交易计划全都没跑。超时（qlib joblib 池在 Windows 上偶发
死锁）和 MemoryError（并发内存峰值）都是暂时性的，降并发重跑一次通常
就过；真正的错误则必须立刻抛出，不能靠重试掩盖。
"""

import re
import subprocess
import types

import pandas as pd
import pytest

from personal_quant.strategy import features as F


def _fake(calls, *, fail_times=0, mode="timeout", stderr=""):
    """假 subprocess.run：前 `fail_times` 次按 mode 失败，之后成功。"""
    def run(cmd, **kw):
        code = open(cmd[-1], encoding="utf-8").read()
        calls.append({"kernels": int(re.search(r"kernels=(\d+)", code).group(1)),
                      "timeout": kw.get("timeout")})
        if mode == "error":          # 真错误：永远返回失败，不会自愈
            return types.SimpleNamespace(returncode=1, stdout="", stderr=stderr)
        if len(calls) <= fail_times:
            if mode == "timeout":
                raise subprocess.TimeoutExpired(cmd, kw.get("timeout"))
            return types.SimpleNamespace(returncode=1, stdout="",
                                         stderr="MemoryError: nope")
        return types.SimpleNamespace(returncode=0, stdout="WROTE 12\n",
                                     stderr=stderr)
    return run


def _setup(monkeypatch, tmp_path, run):
    monkeypatch.setattr(F, "FEATURE_CACHE", tmp_path / "features")
    monkeypatch.setattr(subprocess, "run", run)


def _run_quarter():
    F._compute_quarter_subprocess(["600519.SH"], [pd.Timestamp("2026-09-22")],
                                  kernels=10, verbose=False)


def test_timeout_retries_with_lower_concurrency(monkeypatch, tmp_path):
    calls = []
    _setup(monkeypatch, tmp_path, _fake(calls, fail_times=1, mode="timeout"))
    _run_quarter()

    assert len(calls) == 2, "超时后必须重试，而不是把整条链子抛死"
    assert calls[0]["kernels"] == 10
    assert calls[1]["kernels"] < calls[0]["kernels"]


def test_memory_error_retries_too(monkeypatch, tmp_path):
    calls = []
    _setup(monkeypatch, tmp_path, _fake(calls, fail_times=2, mode="memory"))
    _run_quarter()

    assert [c["kernels"] for c in calls] == [10, 4, 1]


def test_real_error_raises_without_retrying(monkeypatch, tmp_path):
    """真正的错误（不是超时/内存）立刻抛出 —— 重试掩盖不了它。"""
    calls = []
    _setup(monkeypatch, tmp_path,
           _fake(calls, mode="error", stderr="ValueError: bad"))

    with pytest.raises(RuntimeError) as e:
        _run_quarter()
    assert len(calls) == 1
    assert "ValueError: bad" in str(e.value)


def test_all_attempts_exhausted_reports_ladder(monkeypatch, tmp_path):
    calls = []
    _setup(monkeypatch, tmp_path, _fake(calls, fail_times=99, mode="timeout"))

    with pytest.raises(RuntimeError) as e:
        _run_quarter()
    assert len(calls) == 3
    assert "after 3 attempts" in str(e.value)


def test_ladder_never_raises_concurrency():
    """阶梯必须单调下降 —— 降并发才是重试的意义。"""
    ks = [k for k, _ in F.WORKER_LADDER]
    assert ks == sorted(ks, reverse=True)
    assert ks[-1] == 1, "最后一定要退到单进程（不依赖 joblib 池）"


def test_attempt_sequence_never_raises_concurrency():
    assert F._worker_attempts(10) == list(F.WORKER_LADDER)
    assert [k for k, _ in F._worker_attempts(4)] == [4, 1]
    assert [k for k, _ in F._worker_attempts(1)] == [1]
