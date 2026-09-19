# -*- coding: utf-8 -*-
"""交易流水记账（用户指出：说明书让我去「交易流水」记转入/转出，
那里却只能看不能记）。核心不变量：转入/转出是外部资金流，
绝不能被算成收益。"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    from wealth import db as wdb

    monkeypatch.setattr(wdb, "WEALTH_DB", tmp_path / "w.db")
    wdb.reset()
    from wealth import seed

    seed.seed(wdb.connect())
    import webapp.app as webapp_app

    yield TestClient(webapp_app.app)
    wdb.reset()


def _make_fund(client):
    r = client.post("/wealth/daily-update", data={
        "as_of": "2026-09-18", "new_platform_name": "天天盈",
        "new_product_name": "债券基金A", "new_product_type": "bond_fund",
        "new_amount": "10000"}, follow_redirects=True)
    assert "已保存" in r.text
    from wealth import db as wdb
    from wealth import repository as repo

    return [p for p in repo.list_products(wdb.connect())
            if p["name"] == "债券基金A"][0]["product_id"]


def test_transactions_page_has_a_form(client):
    h = client.get("/wealth/transactions").text
    assert 'action="/wealth/transaction"' in h
    assert "转入" in h and "转出" in h
    assert "name=\"amount\"" in h


def test_deposit_is_recorded_and_excluded_from_pnl(client):
    pid = _make_fund(client)
    r = client.post("/wealth/transaction", data={
        "txn_date": "2026-09-19", "product_id": str(pid),
        "txn_type": "deposit", "amount": "5000",
        "note": "从银行卡转入"}, follow_redirects=True)
    assert r.status_code == 200 and "已记录" in r.text
    assert "外部资金流" in r.text

    from wealth import db as wdb
    from wealth import engine, repository as repo

    conn = wdb.connect()
    t = [x for x in repo.list_transactions(conn, product_id=pid)
         if x["txn_type"] == "deposit"]
    assert t, "转入应写入台账"
    assert t[-1]["cash_flow"] == pytest.approx(5000.0)

    # 当天按 15,000 录快照：15,000 = 10,000 + 5,000 转入 → 收益必须是 0
    client.post("/wealth/daily-update", data={
        "as_of": "2026-09-19", f"amount_{pid}": "15000"},
        follow_redirects=True)
    perf = engine.performance(conn)
    assert perf["net_worth"] == pytest.approx(15000.0)
    assert perf["total_pnl"] == pytest.approx(0.0)      # 转入不是收益


def test_withdrawal_gets_negative_sign(client):
    pid = _make_fund(client)
    client.post("/wealth/transaction", data={
        "txn_date": "2026-09-19", "product_id": str(pid),
        "txn_type": "withdrawal", "amount": "2000"}, follow_redirects=True)
    from wealth import db as wdb
    from wealth import repository as repo

    t = [x for x in repo.list_transactions(wdb.connect(), product_id=pid)
         if x["txn_type"] == "withdrawal"][-1]
    assert t["cash_flow"] == pytest.approx(-2000.0)     # 自动取负


def test_dividend_does_not_create_external_flow(client):
    pid = _make_fund(client)
    client.post("/wealth/transaction", data={
        "txn_date": "2026-09-19", "product_id": str(pid),
        "txn_type": "dividend", "amount": "30"}, follow_redirects=True)
    from wealth import db as wdb
    from wealth import repository as repo

    t = [x for x in repo.list_transactions(wdb.connect(), product_id=pid)
         if x["txn_type"] == "dividend"][-1]
    assert t["cash_flow"] == 0.0                        # 分红是内部变动


def test_buy_requires_units_and_price(client):
    pid = _make_fund(client)
    r = client.post("/wealth/transaction", data={
        "txn_date": "2026-09-19", "product_id": str(pid),
        "txn_type": "buy", "amount": "1000"}, follow_redirects=True)
    assert "股数和价格" in r.text


def test_buy_records_units_and_no_cash_flow(client):
    pid = _make_fund(client)
    r = client.post("/wealth/transaction", data={
        "txn_date": "2026-09-19", "product_id": str(pid),
        "txn_type": "buy", "units": "100", "price": "10"},
        follow_redirects=True)
    assert "已记录" in r.text
    from wealth import db as wdb
    from wealth import repository as repo

    t = [x for x in repo.list_transactions(wdb.connect(), product_id=pid)
         if x["txn_type"] == "buy"][-1]
    assert t["units"] == pytest.approx(100)
    assert t["amount"] == pytest.approx(1000.0)
    assert t["cash_flow"] == 0.0


def test_blank_amount_is_rejected(client):
    pid = _make_fund(client)
    r = client.post("/wealth/transaction", data={
        "txn_date": "2026-09-19", "product_id": str(pid),
        "txn_type": "deposit", "amount": ""}, follow_redirects=True)
    assert "请填写金额" in r.text


def test_ledger_shows_signed_cash_flow_column(client):
    pid = _make_fund(client)
    client.post("/wealth/transaction", data={
        "txn_date": "2026-09-19", "product_id": str(pid),
        "txn_type": "deposit", "amount": "5000"}, follow_redirects=True)
    h = client.get("/wealth/transactions").text
    assert "5,000.00" in h and "资金流" in h
