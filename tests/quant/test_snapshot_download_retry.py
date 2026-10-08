# -*- coding: utf-8 -*-
"""快照下载的**重试**：网络抖动不该等价于"今晚没数据"。

2026-10-08 实测：`latest_release()` 一次 30 秒超时（WinError 10060）就把
整条 `refresh_all.py` 打断 —— 后面 9 个不需要联网的作业一个都没跑。
而同一分钟手工测 GitHub 是 0.5 秒 200，纯属抖动。

根因是不对称：旁边的 `manifest_info()` 一直带重试，**最外层、最先执行的
那个调用反而没有**。这里把重试行为钉住。
"""

import importlib.util
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

SCRIPT = (Path(__file__).resolve().parents[2]
          / "scripts" / "quant" / "update_market_snapshot.py")


@pytest.fixture
def ums():
    spec = importlib.util.spec_from_file_location("ums_under_test", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class _Resp:
    def __init__(self, payload=b'{"tag_name": "test"}', status=200):
        self._p = payload
        self.status = status

    def read(self):
        return self._p

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _patch(monkey, fail_times: int, sink: dict):
    real = urllib.request.urlopen

    def fake(req, timeout=30):
        sink["n"] = sink.get("n", 0) + 1
        if sink["n"] <= fail_times:
            raise urllib.error.URLError("simulated WinError 10060")
        return real(req, timeout=timeout) if sink.get("real") else _Resp()
    monkey.setattr(urllib.request, "urlopen", fake)
    return sink


def test_transient_failure_is_retried_and_succeeds(ums, monkeypatch):
    """抖动几次之后必须能成功 —— 这正是用户 10-08 遇到的情形。"""
    calls = _patch(monkeypatch, fail_times=2, sink={})
    monkeypatch.setattr(ums.time, "sleep", lambda *_: None)
    rel = ums.latest_release()
    assert rel["tag_name"] == "test"
    assert calls["n"] == 3, "没有重试到第 3 次"


def test_permanent_failure_raises_an_actionable_message(ums, monkeypatch):
    """一直连不上要报错，而且错误信息要能指导用户下一步。"""
    calls = _patch(monkeypatch, fail_times=99, sink={})
    monkeypatch.setattr(ums.time, "sleep", lambda *_: None)
    with pytest.raises(RuntimeError) as e:
        ums.latest_release()
    assert calls["n"] == 3
    msg = str(e.value)
    assert "refresh_all" in msg, "错误信息没告诉用户怎么重跑"
    assert "PQ_MODE=offline" in msg, "错误信息没提离线选项"
    assert "WinError 10060" in msg, "原始网络错误被吞掉了"


def test_retry_count_is_bounded(ums, monkeypatch):
    """重试次数必须有上限 —— 不能无限撞墙把夜间任务挂死。"""
    calls = _patch(monkeypatch, fail_times=99, sink={})
    monkeypatch.setattr(ums.time, "sleep", lambda *_: None)
    with pytest.raises(RuntimeError):
        ums.latest_release(attempts=5)
    assert calls["n"] == 5


def test_success_on_first_try_does_not_retry(ums, monkeypatch):
    calls = _patch(monkeypatch, fail_times=0, sink={})
    monkeypatch.setattr(ums.time, "sleep", lambda *_: None)
    assert ums.latest_release()["tag_name"] == "test"
    assert calls["n"] == 1


# ---------------------------------------------------------------------------
# 大文件下载：567 MB 断了要能续，不能重头再来
# ---------------------------------------------------------------------------

def test_download_resumes_from_the_part_file(ums, tmp_path, monkeypatch):
    """第一次下到一半断掉，第二次必须**带 Range 从断点续传**。

    567 MB 重头再来一次要十几分钟，续传让重试的代价变成几秒。

    ⚠️ 这条测试第一版是**假的**：它在假响应里定义了 Partial 类却立刻
    抛异常，`.part` 里一个字节都没写，于是"续传"断言恒真。
    现在第一次必须真的**先写进去 3 个字节**再断。
    """
    monkeypatch.setattr(ums.time, "sleep", lambda *_: None)
    payload = b"0123456789"
    seen = []

    class Resp:
        def __init__(self, body, status, chunk=None, fail_after=None):
            self.body, self.status = body, status
            self.headers = {"Content-Length": str(len(body))}
            self.chunk, self.fail_after, self.n = chunk, fail_after, 0

        def read(self, n=-1):
            if self.fail_after is not None and self.n >= self.fail_after:
                raise urllib.error.URLError("connection reset mid-download")
            self.n += 1
            take = self.chunk or n
            out, self.body = self.body[:take], self.body[take:]
            return out

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=120):
        rng = req.headers.get("Range")
        seen.append(rng)
        if rng is None:
            # 第一次：只给 3 个字节，然后断
            return Resp(payload, 200, chunk=3, fail_after=1)
        start_at = int(rng.split("=")[1].rstrip("-"))
        return Resp(payload[start_at:], 206)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    dest = tmp_path / "snap.tar"
    ums.download("https://example.test/x.tar", dest)

    assert dest.read_bytes() == payload
    assert seen[0] is None, "第一次不该带 Range"
    assert seen[1] == f"bytes=3-",         f"第二次应带着断点续传，实际 {seen[1]!r}（说明 .part 没被用上）"


def test_stale_part_file_is_not_mixed_in_when_range_is_ignored(ums, tmp_path,
                                                              monkeypatch):
    """服务端忽略 Range（返回 200）时，旧的半截 .part 必须被丢弃重下。

    场景：上次跑到一半留下的 .part，这次服务端不支持续传。
    若不当心，会把新内容**追加**在旧的半截后面，得到一个坏包。
    """
    monkeypatch.setattr(ums.time, "sleep", lambda *_: None)
    payload = b"ABCDEFGHIJ"

    def fake_urlopen(req, timeout=120):
        class R:
            status = 200                     # 忽略 Range
            headers = {"Content-Length": str(len(payload))}

            def read(self, n=-1):
                nonlocal payload
                out, payload = payload[:n], payload[n:]
                return out

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        return R()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    dest = tmp_path / "snap.tar"
    # 先放一个假的半截文件
    (tmp_path / "snap.part").write_bytes(b"XXXX")
    ums.download("https://example.test/x.tar", dest)
    assert dest.read_bytes() == b"ABCDEFGHIJ", "没从头重下，混进了旧的半截内容"
