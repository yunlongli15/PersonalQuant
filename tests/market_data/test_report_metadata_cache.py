# -*- coding: utf-8 -*-
"""年报元数据必须只加载一次，而不是每次查询都重读整张表。

`fetch_financial_universe.py` 按 (股票, 财年) 调用 get_report_metadata ——
300 只 x 9 个财年 = 2,700 次。而 load_report_metadata() 每次都重开 SQLite、
重读 coverage 表（63,613 行）再重做一遍 merge，实测稳定 0.50 秒，
也就是一次运行烧掉约 22 分钟重算同一个 DataFrame（2026-10-04 实测：
133.6 分钟的作业里，仅"确认什么都不缺"就要 20+ 分钟）。

缓存安全的前提（已在代码里核实）：归档 SQLite 对本模块只读
（全模块 0 条 INSERT/UPDATE/DELETE），两个调用方都只读取返回的帧。
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from personal_quant import config
from personal_quant.providers.sse_reports import SSEReportsProvider

pytestmark = pytest.mark.skipif(
    not (config.SSE_ARCHIVE_DIR / "sse_reports" / "data" / "reports.db").exists(),
    reason="SSE 归档不在本地（bootstrap 后才有）",
)


@pytest.fixture
def counted(monkeypatch):
    """数一数 SQLite 到底被打开了几次。"""
    calls = {"n": 0}
    real = sqlite3.connect

    def wrapper(*a, **kw):
        calls["n"] += 1
        return real(*a, **kw)

    monkeypatch.setattr(sqlite3, "connect", wrapper)
    return calls


def test_metadata_is_loaded_once_per_instance(counted):
    p = SSEReportsProvider()
    first = p.load_report_metadata()
    for _ in range(5):
        p.load_report_metadata()
    assert counted["n"] == 1, f"重读了 {counted['n']} 次"

    # 而且拿到的是同一份内容
    second = p.load_report_metadata()
    assert first.equals(second)
    assert len(first) > 1000


def test_the_2700_lookup_pattern_only_touches_sqlite_once(counted):
    """模拟真实调用方式：同一实例上连查很多 (股票, 财年)。"""
    p = SSEReportsProvider()
    m = p.load_report_metadata()
    sample = m[["stock_code", "fiscal_year"]].head(50).values.tolist()
    hits = 0
    for code, fy in sample:
        r = p.get_report_metadata(f"{str(code).zfill(6)}.SH", int(fy),
                                  "annual_report")
        hits += r is not None
    assert hits > 0, "样本里应该至少有一条能查到"
    assert counted["n"] == 1, "缓存生效的话不该再打开 SQLite"


def test_the_cache_does_not_change_what_is_returned(counted):
    """缓存前后的结果必须逐位相同 —— 对比"不缓存"的那条路径。"""
    p = SSEReportsProvider()
    cached_first = p.load_report_metadata()
    cached_again = p.load_report_metadata()

    fresh = SSEReportsProvider()
    fresh._metadata = None                     # 强制重算一次
    recomputed = fresh.load_report_metadata()

    assert cached_first.equals(recomputed)
    assert cached_again.equals(recomputed)


def test_the_cache_is_per_instance_not_global(counted):
    """跨实例不能共用 —— 否则一个实例改了归档，另一个会读到陈旧数据。"""
    a = SSEReportsProvider()
    a.load_report_metadata()
    assert counted["n"] == 1
    b = SSEReportsProvider()
    b.load_report_metadata()
    assert counted["n"] == 2, "第二个实例应当自己加载一次"


def test_get_report_metadata_still_returns_the_same_shape(counted):
    p = SSEReportsProvider()
    m = p.load_report_metadata()
    code = str(m["stock_code"].iloc[0]).zfill(6)
    fy = int(m["fiscal_year"].iloc[0])
    sym = f"{code}.SH" if code.startswith(("6", "68")) else f"{code}.SZ"
    r = p.get_report_metadata(sym, fy, "annual_report")
    if r is None:
        pytest.skip("样本行恰好不是 annual_report")
    assert set(r) >= {"document_id", "symbol", "fiscal_year", "announcement_date"}
    assert r["fiscal_year"] == fy
