# -*- coding: utf-8 -*-
"""Wealth tests run against a TEMPORARY SQLite file — never the real
data/wealth/wealth.db (personal financial records must not be touched by
tests, and tests must be reproducible on a clean machine)."""

import pytest

from wealth import db as wdb


@pytest.fixture
def conn(tmp_path):
    c = wdb.connect(tmp_path / "wealth_test.db")
    yield c
    c.close()


@pytest.fixture
def seeded(conn):
    from wealth import seed

    seed.seed(conn)
    return conn


@pytest.fixture
def basic(seeded):
    """One platform + account + a fund product and a stock product."""
    from wealth import repository as repo

    platforms = {p["name"]: p["platform_id"]
                 for p in repo.list_platforms(seeded)}
    pt = platforms["天天盈"]
    acct = repo.list_accounts(seeded, pt)[0]["account_id"]
    fund = repo.create_product(seeded, acct, "债券基金 A", "bond_fund")
    stock_acct = repo.list_accounts(
        seeded, platforms["券商"])[0]["account_id"]
    stock = repo.create_product(seeded, stock_acct, "贵州茅台", "stock",
                                ticker="600519.SH", market="SH")
    mm = repo.create_product(seeded, acct, "现金管理 B", "money_fund")
    return {"conn": seeded, "fund": fund, "stock": stock, "mm": mm,
            "acct": acct, "stock_acct": stock_acct, "platforms": platforms}
