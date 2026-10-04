# -*- coding: utf-8 -*-
"""成组写入必须原子提交 —— 2026-10-04 事故（news_events）的回归测试。

DuckDB 的 Python 客户端**每条语句自动提交**。"先清空表、再重新灌入"
是两条独立的提交，中途失败（报错 / Ctrl-C / 进程被杀）会留下**空表**，
而空表在下游和"真的没有数据"长得一模一样 —— 计数类因子 0 是合法取值，
所以没有任何一层会报警（reports/事故-20261004-新闻事件索引.md）。

这里把仓库里全部四处整表重建各钉一遍：**写入失败时旧数据必须原样还在**。
所有测试都跑在一次性 DuckDB 文件上，绝不碰 canonical 库。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import pytest

from personal_quant import db
from personal_quant import config


@pytest.fixture
def scratch(tmp_path, monkeypatch):
    """把 canonical DuckDB 指到一个临时文件；用完即弃。"""
    monkeypatch.setattr(config, "DUCKDB_PATH", tmp_path / "scratch.duckdb")
    db.close()
    try:
        yield db.connect()
    finally:
        db.close()


def _count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


# ---------------------------------------------------------------------------
# 机制本身
# ---------------------------------------------------------------------------

def _seed(conn):
    """一份"旧数据"，与下面事务里要写入的新数据在内容上可区分。

    只在行数上断言是不够的：自动提交时 DELETE 已经生效、随后那半截
    INSERT 又灌了行进去，行数照样对得上。必须比对内容。
    """
    conn.execute("CREATE TABLE t (a INTEGER PRIMARY KEY, tag VARCHAR)")
    conn.execute("INSERT INTO t VALUES (1, 'old')")


def test_transaction_commits_when_the_block_finishes(scratch):
    _seed(scratch)
    with db.transaction() as conn:
        conn.execute("DELETE FROM t")
        conn.execute("INSERT INTO t VALUES (2, 'new')")
    assert scratch.execute("SELECT a, tag FROM t").fetchall() == [(2, "new")]


def test_transaction_rolls_back_on_error(scratch):
    _seed(scratch)
    with pytest.raises(Exception):
        with db.transaction() as conn:
            conn.execute("DELETE FROM t")
            conn.execute("INSERT INTO t VALUES (2, 'new')")
            conn.execute("INSERT INTO t VALUES (2, 'dup')")   # 主键冲突
    assert scratch.execute("SELECT a, tag FROM t").fetchall() == [(1, "old")]


def test_transaction_rolls_back_on_keyboard_interrupt(scratch):
    _seed(scratch)
    with pytest.raises(KeyboardInterrupt):
        with db.transaction() as conn:
            conn.execute("DELETE FROM t")
            conn.execute("INSERT INTO t VALUES (2, 'new')")
            raise KeyboardInterrupt
    assert scratch.execute("SELECT a, tag FROM t").fetchall() == [(1, "old")]


# ---------------------------------------------------------------------------
# 四处整表重建
# ---------------------------------------------------------------------------

def test_write_table_keeps_the_old_rows_when_the_insert_fails(scratch):
    from personal_quant.storage.parquet import write_table

    good = pd.DataFrame([{c: None for c in (
        "symbol", "exchange", "name", "list_date", "delist_date", "is_active",
        "is_st", "first_seen_year", "last_seen_year", "source")}])
    good["symbol"] = ["600519.SH"]
    write_table(good, "securities")
    assert _count(scratch, "securities") == 1

    bad = pd.DataFrame({"symbol": ["000001.SZ"]})        # 列数不匹配 -> 绑定失败
    with pytest.raises(Exception):
        write_table(bad, "securities")
    assert scratch.execute("SELECT symbol FROM securities").fetchall() == [
        ("600519.SH",)]


def test_write_table_with_an_empty_df_leaves_the_table_alone(scratch):
    """空 DataFrame = "没东西可写"，不是"清空表"（原有语义，勿改）。"""
    from personal_quant.storage.parquet import write_table

    scratch.execute("INSERT INTO securities (symbol) VALUES ('600519.SH')")
    write_table(pd.DataFrame(columns=["symbol"]), "securities")
    assert _count(scratch, "securities") == 1


def test_ingest_calendar_keeps_the_old_calendar_when_the_insert_fails(
        scratch, monkeypatch):
    """日历清空 = 全系统取不到交易日，所以它必须要么全换要么不动。"""
    from personal_quant.ingest import qlib_baseline as qb

    scratch.execute(
        "INSERT INTO trading_calendar VALUES ('SSE', DATE '2026-09-30', TRUE)")
    dup = pd.DataFrame({"exchange": ["SSE", "SSE"],
                        "trade_date": [pd.Timestamp("2026-10-08")] * 2,
                        "is_open": [True, True]})         # 主键重复
    monkeypatch.setattr(qb, "load_calendar", lambda: dup)
    with pytest.raises(Exception):
        qb.ingest_calendar()
    assert scratch.execute(
        "SELECT trade_date FROM trading_calendar").fetchall() == [
            (pd.Timestamp("2026-09-30").date(),)]


class _StubProvider:
    def __init__(self, docs, lifecycle):
        self._docs, self._lc = docs, lifecycle

    def build_report_documents(self):
        return self._docs

    def load_lifecycle(self):
        return self._lc


def test_ingest_sse_reports_keeps_the_old_index_when_the_insert_fails(scratch):
    from personal_quant.ingest.sse_reports import ingest_sse_reports

    scratch.execute(
        "INSERT INTO report_documents (document_id, symbol) "
        "VALUES ('old', '600519.SH')")
    bad = _StubProvider(pd.DataFrame({"document_id": ["new"]}), None)
    with pytest.raises(Exception):
        ingest_sse_reports(bad)
    assert scratch.execute(
        "SELECT document_id FROM report_documents").fetchall() == [("old",)]


def test_ingest_lifecycle_keeps_the_old_rows_when_the_insert_fails(scratch):
    from personal_quant.ingest.sse_reports import ingest_lifecycle

    scratch.execute(
        "INSERT INTO company_lifecycle (symbol, status) "
        "VALUES ('600519.SH', 'active')")
    bad = _StubProvider(None, pd.DataFrame({"symbol": ["000001.SZ"]}))
    with pytest.raises(Exception):
        ingest_lifecycle(bad)
    assert scratch.execute(
        "SELECT symbol FROM company_lifecycle").fetchall() == [("600519.SH",)]


def test_replace_events_keeps_the_old_events_when_the_insert_fails(scratch):
    from news.schema import NewsEvent
    from news.storage import replace_events

    good = NewsEvent(event_id="e1", document_id="d1", symbol="600519.SH",
                     event_type="earnings")
    assert replace_events([good]) == 1

    bad = NewsEvent(event_id="e2", document_id="d2", symbol="600519.SH",
                    event_type="earnings")
    bad.importance = "not-a-number"                      # 绕过校验，模拟绑定失败
    with pytest.raises(Exception):
        replace_events([bad])
    assert scratch.execute("SELECT event_id FROM news_events").fetchall() == [
        ("e1",)]
