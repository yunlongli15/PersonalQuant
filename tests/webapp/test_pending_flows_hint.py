# -*- coding: utf-8 -*-
"""流水记了、金额没更新时，界面必须说出来（2026-09-21 用户反馈）。

背景：`transactions`（发生了什么）和 `daily_snapshots`（账户里有多少钱）
是两个东西，分开是设计 —— 系统不替用户推算余额。但两者之间那段空档
以前完全不显示，用户看到"上次金额"是旧的，会以为数据没刷新。
用临时财富库，绝不碰真实数据。
"""

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


def _new_product(conn, platform="天天盈", name="测试货币"):
    from wealth import repository as repo

    plat = [p for p in repo.list_platforms(conn) if p["name"] == platform][0]
    acct = repo.list_accounts(conn, plat["platform_id"])[0]["account_id"]
    return repo.create_product(conn, acct, name, "money_fund")


def test_pending_flow_is_listed_on_daily_update(client):
    """上次录入之后的资金流 → 在「每日录入」显式列出来。"""
    from wealth import db as wdb
    from wealth import repository as repo

    conn = wdb.connect()
    pid = _new_product(conn)
    repo.upsert_snapshot(conn, "2026-09-19", pid, units=1000,
                         market_value=1000.0)
    repo.create_transaction(conn, "2026-09-21", pid, "transfer_out",
                            amount=500.0, cash_flow=-500.0, source="user")

    h = client.get("/wealth/daily-update").text
    assert "还没有反映到「金额」里" in h
    assert "-500.00" in h
    # 必须说清楚下一步，而不是只说"有变化"
    assert "实际金额" in h


def test_flows_already_reflected_are_not_listed(client):
    """流水日期不晚于最后一次录入 → 已经反映了，不再提示。"""
    from wealth import db as wdb
    from wealth import repository as repo

    conn = wdb.connect()
    pid = _new_product(conn)
    repo.create_transaction(conn, "2026-09-18", pid, "deposit",
                            amount=1000.0, cash_flow=1000.0, source="user")
    repo.upsert_snapshot(conn, "2026-09-19", pid, units=1000,
                         market_value=1000.0)

    h = client.get("/wealth/daily-update").text
    assert "还没有反映到「金额」里" not in h


def test_internal_buy_is_not_a_pending_flow(client):
    """买卖是组合内部变化，cash_flow=0，不该被当成待处理资金流。"""
    from wealth import db as wdb
    from wealth import repository as repo

    conn = wdb.connect()
    pid = _new_product(conn)
    repo.upsert_snapshot(conn, "2026-09-19", pid, units=100, nav=10.0,
                         market_value=1000.0)
    repo.create_transaction(conn, "2026-09-21", pid, "buy", units=10,
                            price=10.0, amount=100.0, cash_flow=0.0,
                            source="user")

    h = client.get("/wealth/daily-update").text
    assert "还没有反映到「金额」里" not in h


def test_transaction_message_points_to_daily_update(client):
    """记完流水必须告诉用户：金额还没变，去「每日录入」更新。"""
    from wealth import db as wdb

    pid = _new_product(wdb.connect())
    r = client.post("/wealth/transaction", data={
        "txn_date": "2026-09-21", "txn_type": "transfer_out",
        "product_id": str(pid), "amount": "500"}, follow_redirects=True)

    assert r.status_code == 200
    assert "每日录入" in r.text
    assert "已从该产品的收益计算中剔除" in r.text


def test_transfer_labels_do_not_contradict_the_flow_model(client):
    """transfer_* 在 P&L 口径上是**外部**流；标签不能写"内部"，
    也不能和"从银行卡转入"混为一谈。"""
    from webapp.app import TXN_LABEL

    assert "内部" not in TXN_LABEL["transfer_in"]
    assert "内部" not in TXN_LABEL["transfer_out"]
    assert TXN_LABEL["transfer_in"] != TXN_LABEL["deposit"]
    assert TXN_LABEL["transfer_out"] != TXN_LABEL["withdrawal"]
