# -*- coding: utf-8 -*-
"""Daily Update 流程（用户要求重做）：日期 + 渠道（选已有或新建）+ 今日金额
+ 今日收益。用临时财富库，绝不碰真实数据。"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """GUI backed by a throwaway wealth DB."""
    from wealth import db as wdb

    test_db = tmp_path / "wealth_test.db"
    monkeypatch.setattr(wdb, "WEALTH_DB", test_db)
    wdb.reset()
    from wealth import seed

    seed.seed(wdb.connect())
    import webapp.app as webapp_app

    c = TestClient(webapp_app.app)
    yield c
    wdb.reset()


def test_page_has_date_platform_income_fields(client):
    h = client.get("/wealth/daily-update").text
    assert 'type="date"' in h                      # 日期
    assert "new_platform" in h                     # 渠道（下拉）
    assert "new_platform_name" in h                # 渠道（新建）
    assert "今日收益" in h                          # 今日收益
    assert "今日金额" in h                          # 今日金额
    assert "新建产品" in h                          # 没有就新建


def test_create_channel_and_product_then_record(client):
    r = client.post("/wealth/daily-update", data={
        "as_of": "2026-09-17",
        "new_platform_name": "天天盈",
        "new_product_name": "债券基金A",
        "new_product_type": "bond_fund",
        "new_amount": "10000",
        "new_income": "3.21",
    }, follow_redirects=True)
    assert r.status_code == 200 and "已保存" in r.text

    from wealth import db as wdb
    from wealth import repository as repo

    conn = wdb.connect()
    prods = repo.list_products(conn, include_inactive=True)
    assert any(p["name"] == "债券基金A" for p in prods)
    inc = repo.list_income(conn)
    assert len(inc) == 1
    assert inc[0]["daily_income"] == pytest.approx(3.21)
    assert inc[0]["calculation_method"] == "reported"   # 用户填的，不是推导
    assert inc[0]["source"] == "user"


def test_new_channel_is_created(client):
    client.post("/wealth/daily-update", data={
        "as_of": "2026-09-17", "new_platform_name": "某新平台",
        "new_product_name": "货币A", "new_product_type": "money_fund",
        "new_amount": "5000"}, follow_redirects=True)
    from wealth import db as wdb
    from wealth import repository as repo

    names = [p["name"] for p in repo.list_platforms(wdb.connect())]
    assert "某新平台" in names


def test_existing_product_row_accepts_amount_and_income(client):
    from wealth import db as wdb
    from wealth import repository as repo

    conn = wdb.connect()
    plat = [p for p in repo.list_platforms(conn)
            if p["name"] == "天天盈"][0]
    acct = repo.list_accounts(conn, plat["platform_id"])[0]["account_id"]
    pid = repo.create_product(conn, acct, "已有的债券基金", "bond_fund")

    r = client.post("/wealth/daily-update", data={
        "as_of": "2026-09-17",
        f"amount_{pid}": "20000",
        f"income_{pid}": "5.5",
    }, follow_redirects=True)
    assert r.status_code == 200 and "已保存" in r.text
    snaps = repo.list_snapshots(conn, product_id=pid)
    assert snaps[-1]["market_value"] == pytest.approx(20000)
    inc = repo.list_income(conn, pid)
    assert inc[-1]["daily_income"] == pytest.approx(5.5)


def test_income_mismatch_is_flagged_not_overwritten(client):
    """用户填的收益与系统推导差太多 → 提示，但按用户填的记。"""
    from wealth import db as wdb
    from wealth import repository as repo

    conn = wdb.connect()
    plat = [p for p in repo.list_platforms(conn)
            if p["name"] == "银行"][0]
    acct = repo.list_accounts(conn, plat["platform_id"])[0]["account_id"]
    pid = repo.create_product(conn, acct, "测试货币", "money_fund")
    repo.upsert_snapshot(conn, "2026-09-16", pid, units=10000,
                         market_value=10000.0)

    r = client.post("/wealth/daily-update", data={
        "as_of": "2026-09-17", f"amount_{pid}": "10050",
        f"income_{pid}": "3.0"},     # 系统推导应为 50
        follow_redirects=True)
    assert "相差" in r.text
    inc = repo.list_income(conn, pid)[-1]
    assert inc["daily_income"] == pytest.approx(3.0)   # 用户填的优先


def test_blank_submit_is_rejected(client):
    r = client.post("/wealth/daily-update", data={"as_of": "2026-09-17"},
                    follow_redirects=True)
    assert "没有填写任何金额" in r.text


def test_junk_number_is_reported(client):
    r = client.post("/wealth/daily-update", data={
        "as_of": "2026-09-17", "new_platform_name": "天天盈",
        "new_product_name": "X", "new_product_type": "cash",
        "new_amount": "abc"}, follow_redirects=True)
    assert "不是数字" in r.text or "没有填写" in r.text
