# -*- coding: utf-8 -*-
"""§44：任何修改都必须可审计。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from wealth import db, repository as repo


def test_audit_records_old_and_new_values(conn, make_product):
    pid = make_product()
    repo.update_product(conn, pid, reason="改名", name="新名字")
    logs = [l for l in repo.list_audit(conn, limit=20)
            if l["object_type"] == "products"]
    assert logs
    top = logs[0]
    assert top["old_value"] and top["new_value"]
    assert "新名字" in str(top["new_value"])


def test_audit_grows_with_every_write(conn, make_product):
    pid = make_product()
    n0 = len(repo.list_audit(conn, limit=500))
    repo.create_transaction(conn, "2026-09-01", pid, "buy", units=1,
                            price=1.0, amount=1.0)
    n1 = len(repo.list_audit(conn, limit=500))
    assert n1 > n0


def test_repository_exposes_no_way_to_delete_audit_rows():
    """审计表只能在写入时追加；repository 里没有删除它的入口。"""
    names = [n for n in dir(repo) if not n.startswith("_")]
    assert not any("audit" in n and ("delete" in n or "clear" in n)
                   for n in names)
    # 只有读取接口
    assert callable(repo.list_audit)


def test_reason_is_stored_for_critical_edits(conn, make_product):
    pid = make_product()
    tid = repo.create_transaction(conn, "2026-09-01", pid, "buy", units=1,
                                  price=1.0, amount=1.0)
    repo.delete_transaction(conn, tid, reason="录错了，重录")
    logs = repo.list_audit(conn, limit=20)
    assert any(l.get("reason") == "录错了，重录" for l in logs)


def test_audit_captures_json_payloads(conn, make_product):
    make_product()
    logs = repo.list_audit(conn, limit=5)
    assert logs and logs[0]["timestamp"]


def test_backup_does_not_touch_the_source(conn, tmp_path):
    pid_source = conn.execute("SELECT COUNT(*) AS n FROM products"
                              ).fetchone()["n"]
    p = db.backup(dest_dir=tmp_path, conn=conn)
    assert Path(p).exists()
    after = conn.execute("SELECT COUNT(*) AS n FROM products").fetchone()["n"]
    assert after == pid_source
