# -*- coding: utf-8 -*-
"""tests/portfolio_account 共用夹具：临时财富库（不碰真实 data/wealth）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest


@pytest.fixture
def conn(tmp_path):
    """每个测试一个全新的 SQLite 库。"""
    from wealth import db
    c = db.connect(tmp_path / "t.db")
    yield c
    c.close()


@pytest.fixture
def acct(conn):
    """一个平台 + 一个账户，返回 account_id。"""
    from wealth import repository as repo
    pid = repo.create_platform(conn, "券商", kind="broker")
    return repo.create_account(conn, pid, "默认账户")


@pytest.fixture
def make_product(conn, acct):
    def _make(name="贵州茅台", ptype="stock", ticker="600519.SH"):
        from wealth import repository as repo
        return repo.create_product(conn, acct, name, ptype, ticker=ticker)
    return _make
