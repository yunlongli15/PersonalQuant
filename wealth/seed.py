# -*- coding: utf-8 -*-
"""Default platforms / asset categories / benchmarks (STEP 7A).

Idempotent: running twice changes nothing.
"""

from __future__ import annotations

from typing import Optional

from . import repository as repo

DEFAULT_PLATFORMS = [
    ("天天盈", "fund_platform"),
    ("支付宝", "fund_platform"),
    ("微信理财", "fund_platform"),
    ("银行", "bank"),
    ("南方基金", "fund_platform"),
    ("券商", "broker"),
    ("现金", "cash"),
]

#: 资产大类（spec §26 的 Dashboard 分组）
DEFAULT_CATEGORIES = [
    ("Cash", 10, "cash,money_fund"),
    ("Funds", 20, "bond_fund,index_fund,qdii,other"),
    ("Bond Funds", 30, "bond_fund"),
    ("Index Funds", 40, "index_fund,qdii"),
    ("Stocks", 50, "stock,etf"),
    ("Gold", 60, "gold"),
    ("Other", 90, "other"),
]

DEFAULT_BENCHMARKS = ["CSI300"]


def seed(conn, with_benchmarks: bool = True) -> dict:
    created = {"platforms": 0, "accounts": 0, "categories": 0}
    for name, kind in DEFAULT_PLATFORMS:
        row = conn.execute("SELECT platform_id FROM platforms WHERE name=?",
                           (name,)).fetchone()
        if row is None:
            pid = repo.create_platform(conn, name, kind)
            # 每个平台自动建一个默认账户，Daily Update 直接挂产品
            repo.create_account(conn, pid, f"{name} 默认账户")
            created["platforms"] += 1
            created["accounts"] += 1
    for name, order, applies in DEFAULT_CATEGORIES:
        row = conn.execute(
            "SELECT category_id FROM wealth_categories WHERE name=?",
            (name,)).fetchone()
        if row is None:
            repo.add_category(conn, name, order, applies)
            created["categories"] += 1
    if with_benchmarks:
        created["benchmarks"] = list(repo.list_benchmarks(conn) and
                                     {r["benchmark"]
                                      for r in repo.list_benchmarks(conn)}
                                     or set())
    return created
