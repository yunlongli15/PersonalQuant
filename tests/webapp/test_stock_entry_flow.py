# -*- coding: utf-8 -*-
"""股票/ETF 的录入口径与基金不同（用户要求）：
名称、代码、买入成本价、买入日期、股数、现价 → 市值、浮盈。"""

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


def _create_stock(client, **over):
    data = {"as_of": "2026-09-19", "new_platform_name": "君弘",
            "new_product_name": "贵州茅台", "new_product_type": "stock",
            "new_ticker": "600519.SH", "new_buy_date": "2026-09-15",
            "new_cost_price": "1250.00", "new_shares": "100",
            "new_price": "1300.00"}
    data.update(over)
    return client.post("/wealth/daily-update", data=data,
                       follow_redirects=True)


def test_stock_form_has_its_own_fields(client):
    """股票的表单要有代码/成本价/买入日期/股数/现价，而不是「金额」。"""
    h = client.get("/wealth/daily-update").text
    for field in ("new_ticker", "new_buy_date", "new_cost_price",
                  "new_shares", "new_price"):
        assert field in h, field
    assert "浮盈" in h and "成本价" in h and "买入日期" in h


def test_create_stock_records_cost_and_pnl(client):
    r = _create_stock(client)
    assert r.status_code == 200 and "已保存" in r.text

    from wealth import db as wdb
    from wealth import engine, repository as repo

    conn = wdb.connect()
    p = [x for x in repo.list_products(conn) if x["name"] == "贵州茅台"][0]
    assert p["ticker"] == "600519.SH"
    held = engine.positions_at(conn, p["product_id"], "2026-09-19")
    assert held.units == 100
    assert held.avg_cost == pytest.approx(1250.0)
    snap = repo.list_snapshots(conn, product_id=p["product_id"])[-1]
    assert snap["nav"] == pytest.approx(1300.0)
    assert snap["market_value"] == pytest.approx(130000.0)
    # 本金投入 = 成本（不是市值）→ 浮盈才是 P&L
    flows = [t for t in repo.list_transactions(conn) if t["txn_type"] == "deposit"]
    assert sum(t["cash_flow"] for t in flows) == pytest.approx(125000.0)


def test_daily_update_needs_only_price(client):
    _create_stock(client)
    from wealth import db as wdb
    from wealth import engine, repository as repo

    conn = wdb.connect()
    pid = [x for x in repo.list_products(conn)
           if x["name"] == "贵州茅台"][0]["product_id"]
    r = client.post("/wealth/daily-update",
                    data={"as_of": "2026-09-19",
                          f"stock_price_{pid}": "1315.50"},
                    follow_redirects=True)
    assert "已保存" in r.text
    snap = repo.list_snapshots(conn, product_id=pid)[-1]
    held = engine.positions_at(conn, pid, "2026-09-19")
    assert snap["market_value"] == pytest.approx(131550.0)
    assert snap["market_value"] - held.units * held.avg_cost == \
        pytest.approx(6550.0)


def test_stock_without_cost_price_warns(client):
    r = _create_stock(client, new_cost_price="")
    assert "成本价" in r.text          # 明确提示无法算浮盈


def test_stock_page_shows_position_columns(client):
    _create_stock(client)
    h = client.get("/wealth/daily-update").text
    assert "股票 / ETF 持仓" in h
    assert "600519.SH" in h
    assert "1250.000" in h            # 成本价
    assert "2026-09-15" in h          # 买入日期
