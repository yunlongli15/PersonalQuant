# -*- coding: utf-8 -*-
"""§9 / §13：持仓由流水重建；市值 = 数量 × 现价（不是成本）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from wealth import engine, repository as repo


def _buy(conn, pid, d, units, price, fee=0.0):
    return repo.create_transaction(conn, d, pid, "buy", units=units,
                                   price=price, amount=units * price, fee=fee)


def _sell(conn, pid, d, units, price, fee=0.0):
    return repo.create_transaction(conn, d, pid, "sell", units=units,
                                   price=price, amount=units * price, fee=fee)


def test_units_accumulate_and_average_cost_includes_fees(conn, make_product):
    pid = make_product()
    _buy(conn, pid, "2026-09-01", 100, 10.0, fee=5.0)
    _buy(conn, pid, "2026-09-02", 100, 20.0, fee=5.0)
    h = engine.holdings_from_ledger(repo.list_transactions(conn))
    assert h.units == 200
    assert h.avg_cost == pytest.approx((1000 + 5 + 2000 + 5) / 200)


def test_market_value_uses_price_not_cost(conn, make_product):
    pid = make_product()
    _buy(conn, pid, "2026-09-01", 100, 10.0)
    h = engine.holdings_from_ledger(repo.list_transactions(conn))
    assert h.market_value(25.0) == pytest.approx(2500.0)     # 不是 1000
    assert h.unrealized_pnl(25.0) == pytest.approx(1500.0)


def test_sell_reduces_units_and_realizes_pnl(conn, make_product):
    pid = make_product()
    _buy(conn, pid, "2026-09-01", 200, 10.0)
    _sell(conn, pid, "2026-09-02", 100, 12.0)
    h = engine.holdings_from_ledger(repo.list_transactions(conn))
    assert h.units == 100
    assert h.realized_pnl == pytest.approx(200.0)


def test_selling_everything_leaves_zero_units(conn, make_product):
    pid = make_product()
    _buy(conn, pid, "2026-09-01", 100, 10.0)
    _sell(conn, pid, "2026-09-02", 100, 11.0)
    h = engine.holdings_from_ledger(repo.list_transactions(conn))
    assert h.units == 0


def test_value_positions_reports_missing_prices(conn, make_product):
    pid = make_product()
    _buy(conn, pid, "2026-09-01", 100, 10.0)
    v = engine.value_positions(conn, prices={})       # 没有现价
    assert v["missing_price"] == ["600519.SH"]
    # 缺价时按成本计价，绝不当作 0
    assert v["market_value"] == pytest.approx(1000.0)


def test_value_positions_uses_supplied_price(conn, make_product):
    pid = make_product()
    _buy(conn, pid, "2026-09-01", 100, 10.0)
    v = engine.value_positions(conn, prices={"600519.SH": 12.5})
    assert v["holdings"][0]["market_value"] == pytest.approx(1250.0)
    assert v["missing_price"] == []


def test_positions_materialisation_matches_ledger(conn, make_product):
    pid = make_product()
    _buy(conn, pid, "2026-09-01", 100, 10.0)
    engine.write_positions(conn, "2026-09-01", {pid: 12.0})
    rows = engine.position_consistency(conn)
    assert all(r["status"] in ("ok", "not_materialised") for r in rows)
