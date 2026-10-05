# -*- coding: utf-8 -*-
"""news_v2 的表必须是**事件** schema，不能是文档 schema。

2026-10-05 踩过：`replace_events(table="news_events_v2")` 里把同一个表名
既当文档表又当事件表传给 ensure_tables()，于是先按**文档** schema 建出了
news_events_v2，紧接着事件表的 `CREATE TABLE IF NOT EXISTS` 静默跳过 ——
表建出来了、名字也对，schema 是错的，一直要到 INSERT 时才炸：

    BinderException: Table "news_events_v2" does not have a column
    named "event_id". Did you mean: "content_hash"

这正是"IF NOT EXISTS 把错误藏起来"那一族问题。下面的断言直接盯 schema。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from personal_quant import db
from news.storage import EVENT_COLS, ensure_tables

TABLE = "news_events_schema_probe"

EVENT_ONLY = ["event_id", "direction", "risk", "availability_time",
              "extraction_version"]
DOCUMENT_ONLY = ["content_hash", "raw_hash", "org_id", "source_count"]


@pytest.fixture
def probe():
    conn = db.connect()
    conn.execute(f"DROP TABLE IF EXISTS {TABLE}")
    try:
        yield conn
    finally:
        conn.execute(f"DROP TABLE IF EXISTS {TABLE}")


def _cols(conn):
    return [r["column_name"] for r in db.query(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name=?", [TABLE])]


def test_versioned_events_table_gets_the_event_schema(probe):
    ensure_tables(extra_events_table=TABLE)
    cols = _cols(probe)
    assert cols, "表没建出来"
    for c in EVENT_ONLY:
        assert c in cols, f"缺事件列 {c}；实际列：{cols}"
    assert set(cols) == set(EVENT_COLS), f"列集合不对：{cols}"


def test_versioned_events_table_is_not_the_document_schema(probe):
    """这条是那次事故的直接回归：文档列一个都不该出现。"""
    ensure_tables(extra_events_table=TABLE)
    cols = _cols(probe)
    for c in DOCUMENT_ONLY:
        assert c not in cols, f"表被建成了文档 schema（多出 {c}）"


def test_calling_both_extra_args_does_not_corrupt_the_events_table(probe):
    """两个参数给同一张表时必须只按事件 schema 建 —— 后建的那个 IF NOT EXISTS
    会被前一个悄悄吃掉。ensure_tables 现在由调用方保证只传一个，
    这里钉住"只传事件表"这一条路径。"""
    ensure_tables(extra_events_table=TABLE)
    ensure_tables(extra_events_table=TABLE)      # 幂等
    cols = _cols(probe)
    assert set(cols) == set(EVENT_COLS), f"重复建表后 schema 变了：{cols}"
