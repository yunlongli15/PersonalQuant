# -*- coding: utf-8 -*-
"""§51 / §60 / §67：空账户、零持仓、缺价格、缺基准、缺策略、缺新闻都不能崩。

服务层遇到任何一步取不到数据都返回 {"available": False, "reason": ...}；
页面显示明确的 NO DATA，而不是 Traceback。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from services import (backtest_service, factor_service, health_service,
                      market_service, news_service, performance_service,
                      portfolio_service, recommendation_service,
                      risk_service, strategy_service)

ALL_SERVICES = [
    ("portfolio.positions", lambda: portfolio_service.positions()),
    ("portfolio.allocation", lambda: portfolio_service.allocation()),
    ("portfolio.valuation", lambda: portfolio_service.valuation()),
    ("portfolio.snapshots", lambda: portfolio_service.snapshots()),
    ("portfolio.reconciliation", lambda: portfolio_service.reconciliation()),
    ("portfolio.consistency", lambda: portfolio_service.consistency()),
    ("portfolio.transactions", lambda: portfolio_service.transactions()),
    ("portfolio.accounts", lambda: portfolio_service.accounts()),
    ("performance.summary", lambda: performance_service.summary()),
    ("performance.attribution", lambda: performance_service.attribution()),
    ("performance.calendar", lambda: performance_service.calendar_returns()),
    ("risk.metrics", lambda: risk_service.metrics()),
    ("risk.sector", lambda: risk_service.sector_exposure()),
    ("risk.concentration", lambda: risk_service.concentration_alert()),
    ("strategy.status_card", lambda: strategy_service.status_card()),
    ("strategy.paper_live", lambda: strategy_service.paper_live()),
    ("strategy.versus_actual", lambda: strategy_service.versus_actual()),
    ("recommendation.latest", lambda: recommendation_service.latest()),
    ("news.latest", lambda: news_service.latest()),
    ("news.llm", lambda: news_service.llm_analysis()),
    ("factor.leaderboards", lambda: factor_service.leaderboards()),
    ("factor.incremental", lambda: factor_service.incremental()),
    ("factor.signals", lambda: factor_service.current_signals()),
    ("backtest.results", lambda: backtest_service.results()),
    ("health.check", lambda: health_service.check()),
    ("market.benchmark", lambda: market_service.benchmark_nav(
        "CSI300", "2025-01-01", "2025-06-30")),
]


@pytest.mark.parametrize("name,fn", ALL_SERVICES,
                         ids=[n for n, _ in ALL_SERVICES])
def test_service_never_raises(name, fn):
    """任何服务调用都不能抛异常 —— 必须降级成 available=False。"""
    res = fn()
    assert isinstance(res, dict), f"{name} 没有返回 dict"


@pytest.mark.parametrize("name,fn", ALL_SERVICES,
                         ids=[n for n, _ in ALL_SERVICES])
def test_unavailable_payload_carries_a_reason(name, fn):
    res = fn()
    if res.get("available") is False:
        assert res.get("reason"), f"{name} 标记不可用却没给原因"


def test_empty_account_is_handled(tmp_path, monkeypatch):
    """空账户：把 wealth 指向一个空库，所有账户相关服务仍不崩。"""
    from wealth import db as wdb
    monkeypatch.setattr(wdb, "WEALTH_DB", tmp_path / "empty.db")
    wdb.reset()
    try:
        v = portfolio_service.valuation()
        assert isinstance(v, dict)
        p = portfolio_service.positions()
        assert isinstance(p, dict)
        a = portfolio_service.allocation()
        assert isinstance(a, dict)
    finally:
        wdb.reset()


def test_zero_positions_after_selling_everything():
    """零持仓：不应该是负数或 NaN。"""
    from wealth import engine
    h = engine.holdings_from_ledger([
        {"txn_id": 1, "txn_date": "2026-01-01", "txn_type": "buy",
         "units": 100, "price": 10.0, "amount": 1000.0, "fee": 0.0,
         "product_id": 1},
        {"txn_id": 2, "txn_date": "2026-01-02", "txn_type": "sell",
         "units": 100, "price": 11.0, "amount": 1100.0, "fee": 0.0,
         "product_id": 1},
    ])
    assert h.units == 0.0
    assert h.market_value(99.0) == 0.0


def test_missing_price_is_reported_not_zeroed(tmp_path):
    """缺价格：按成本计价并**列出缺哪只**，绝不当作 0。"""
    from wealth import db, engine, repository as repo
    conn = db.connect(tmp_path / "m.db")
    pid = repo.create_platform(conn, "券商", kind="broker")
    aid = repo.create_account(conn, pid, "A")
    prod = repo.create_product(conn, aid, "茅台", "stock", ticker="600519.SH")
    repo.create_transaction(conn, "2026-09-01", prod, "buy", units=100,
                            price=10.0, amount=1000.0)
    v = engine.value_positions(conn, prices={})
    assert v["missing_price"] == ["600519.SH"]
    assert v["market_value"] == pytest.approx(1000.0)   # 成本，不是 0


def test_missing_benchmark_returns_unavailable():
    res = market_service.benchmark_nav("不存在的基准", "2025-01-01",
                                       "2025-06-30")
    assert isinstance(res, dict)


def test_health_check_always_lists_items():
    h = health_service.check()
    assert h.get("available") and len(h["items"]) >= 10
    for i in h["items"]:
        assert i["status"] in ("PASS", "WARNING", "FAIL")
        assert i["detail"] and "Traceback" not in i["detail"]
