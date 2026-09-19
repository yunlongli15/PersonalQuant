# -*- coding: utf-8 -*-
"""§12：CSV 导入 —— 幂等、不猜、dry-run 与真实导入判定一致。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from wealth import engine, importer, repository as repo

HEADER = "date,symbol,side,quantity,price,fees,account"


def _write(tmp_path, lines):
    p = tmp_path / "t.csv"
    p.write_text("\n".join([HEADER] + lines), encoding="utf-8")
    return p


def test_standard_buy_import(conn, tmp_path):
    f = _write(tmp_path, ["2026-09-01,600519.SH,BUY,100,1680.5,5.2,券商"])
    res = importer.import_transactions_csv(conn, f)
    assert res.n_errors == 0 and len(res.imported) == 1
    h = engine.holdings_from_ledger(repo.list_transactions(conn))
    assert h.units == 100


def test_chinese_headers_and_sides(conn, tmp_path):
    p = tmp_path / "cn.csv"
    p.write_text("日期,代码,方向,数量,价格,手续费,账户\n"
                 "2026-09-01,600519.SH,买入,100,1680.5,5.2,券商\n",
                 encoding="utf-8")
    res = importer.import_transactions_csv(conn, p)
    assert res.n_errors == 0 and len(res.imported) == 1


def test_reimport_is_idempotent(conn, tmp_path):
    f = _write(tmp_path, ["2026-09-01,600519.SH,BUY,100,10.0,0,券商"])
    importer.import_transactions_csv(conn, f)
    second = importer.import_transactions_csv(conn, f)
    assert len(second.skipped) == 1 and len(second.imported) == 0


def test_duplicate_rows_inside_one_file_are_skipped(conn, tmp_path):
    f = _write(tmp_path, ["2026-09-01,600519.SH,BUY,100,10.0,0,券商",
                          "2026-09-01,600519.SH,BUY,100,10.0,0,券商"])
    res = importer.import_transactions_csv(conn, f)
    assert len(res.imported) == 1 and len(res.skipped) == 1


def test_dry_run_writes_nothing(conn, tmp_path):
    f = _write(tmp_path, ["2026-09-01,600519.SH,BUY,100,10.0,0,券商"])
    res = importer.import_transactions_csv(conn, f, dry_run=True)
    assert res.dry_run and len(res.imported) == 1
    assert repo.list_transactions(conn) == []


def test_unknown_side_is_an_error_not_a_guess(conn, tmp_path):
    f = _write(tmp_path, ["2026-09-01,600519.SH,WAT,100,10.0,0,券商"])
    res = importer.import_transactions_csv(conn, f)
    assert res.n_errors == 1 and "方向" in res.errors[0].detail


def test_missing_required_columns_fails_loudly(conn, tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("foo,bar\n1,2\n", encoding="utf-8")
    res = importer.import_transactions_csv(conn, p)
    assert res.n_errors >= 1 and "缺少必需列" in res.errors[0].detail


def test_cash_flow_uses_quantity_when_price_is_absent(conn, tmp_path):
    """转入没有价格：quantity 就是金额（曾经错用 qty×price 恒为 0）。"""
    f = _write(tmp_path, ["2026-09-01,,DEPOSIT,50000,0,0,券商"])
    res = importer.import_transactions_csv(conn, f)
    assert res.n_errors == 0
    assert engine.cash_balance(conn)["implied"] == pytest.approx(50000.0)


def test_dry_run_and_real_run_agree_on_errors(conn, tmp_path):
    f = _write(tmp_path, ["2026-09-01,,DEPOSIT,0,0,0,券商"])
    dry = importer.import_transactions_csv(conn, f, dry_run=True)
    real = importer.import_transactions_csv(conn, f)
    assert dry.n_errors == real.n_errors == 1


def test_import_is_audited(conn, tmp_path):
    f = _write(tmp_path, ["2026-09-01,600519.SH,BUY,100,10.0,0,券商"])
    importer.import_transactions_csv(conn, f)
    logs = repo.list_audit(conn, limit=50)
    assert any(l["action"] == "import_csv" for l in logs)


def test_bad_date_is_reported_with_line_number(conn, tmp_path):
    f = _write(tmp_path, ["not-a-date,600519.SH,BUY,100,10.0,0,券商"])
    res = importer.import_transactions_csv(conn, f)
    assert res.n_errors == 1 and res.errors[0].line == 2
