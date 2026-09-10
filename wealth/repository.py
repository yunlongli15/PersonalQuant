# -*- coding: utf-8 -*-
"""CRUD for the wealth database (STEP 7A).

Every mutation funnels through here so that audit logging (spec §39) is
impossible to forget: create/update/delete all write an audit_log row
with old/new values. Reads never mutate.
"""

from __future__ import annotations

import sqlite3
from typing import List, Optional, Sequence

from . import db
from .models import (BENCHMARKS, PLATFORM_KINDS, PRODUCT_TYPES, TXN_TYPES,
                     Account, BenchmarkRecord, DailySnapshot, IncomeRecord,
                     Platform, Product, Transaction)


class ValidationError(ValueError):
    """Rejected input (bad enum, negative amount, unknown reference)."""


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _dict(row) -> dict:
    return dict(row) if row is not None else {}


def _check_enum(value: str, allowed: Sequence[str], field: str) -> str:
    if value not in allowed:
        raise ValidationError(f"{field}={value!r} not in {list(allowed)}")
    return value


def _require(conn, table: str, key: str, value) -> None:
    if value is None or not conn.execute(
            f"SELECT 1 FROM {table} WHERE {key}=? LIMIT 1", (value,)).fetchone():
        raise ValidationError(f"{table}.{key}={value!r} does not exist")


def _insert(conn, table: str, cols: List[str], vals: List, audit_action: str,
            reason: Optional[str] = None) -> int:
    sql = (f"INSERT INTO {table} ({', '.join(cols)}) "
           f"VALUES ({', '.join('?' * len(cols))})")
    cur = conn.execute(sql, vals)
    conn.commit()
    new_id = int(cur.lastrowid)
    db.audit(conn, audit_action, table, new_id,
             new_value=dict(zip(cols, vals)), reason=reason)
    return new_id


def _update(conn, table: str, key: str, key_val, fields: dict,
            reason: Optional[str] = None) -> None:
    old = _dict(conn.execute(f"SELECT * FROM {table} WHERE {key}=?",
                             (key_val,)).fetchone())
    if not old:
        raise ValidationError(f"{table}.{key}={key_val!r} does not exist")
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    conn.execute(f"UPDATE {table} SET {sets} WHERE {key}=?",
                 list(fields.values()) + [key_val])
    conn.commit()
    db.audit(conn, "update", table, key_val, old_value=old,
             new_value=fields, reason=reason)


def _delete(conn, table: str, key: str, key_val,
            reason: Optional[str] = None) -> None:
    old = _dict(conn.execute(f"SELECT * FROM {table} WHERE {key}=?",
                             (key_val,)).fetchone())
    if not old:
        raise ValidationError(f"{table}.{key}={key_val!r} does not exist")
    conn.execute(f"DELETE FROM {table} WHERE {key}=?", (key_val,))
    conn.commit()
    db.audit(conn, "delete", table, key_val, old_value=old, reason=reason)


# ---------------------------------------------------------------------------
# platforms / accounts / products
# ---------------------------------------------------------------------------

def create_platform(conn, name: str, kind: str = "other",
                    note: Optional[str] = None) -> int:
    _check_enum(kind, PLATFORM_KINDS, "kind")
    return _insert(conn, "platforms", ["name", "kind", "note"],
                   [name, kind, note], "create")


def update_platform(conn, platform_id: int, reason: Optional[str] = None,
                    **fields) -> None:
    if "kind" in fields:
        _check_enum(fields["kind"], PLATFORM_KINDS, "kind")
    _update(conn, "platforms", "platform_id", platform_id, fields, reason)


def list_platforms(conn, status: Optional[str] = None) -> List[dict]:
    sql = "SELECT * FROM platforms"
    params: List = []
    if status:
        sql += " WHERE status=?"
        params.append(status)
    return [_dict(r) for r in conn.execute(sql + " ORDER BY platform_id",
                                           params).fetchall()]


def create_account(conn, platform_id: int, name: str, currency: str = "CNY",
                   note: Optional[str] = None) -> int:
    _require(conn, "platforms", "platform_id", platform_id)
    return _insert(conn, "accounts",
                   ["platform_id", "name", "currency", "note"],
                   [platform_id, name, currency, note], "create")


def update_account(conn, account_id: int, reason: Optional[str] = None,
                   **fields) -> None:
    if "platform_id" in fields:
        _require(conn, "platforms", "platform_id", fields["platform_id"])
    _update(conn, "accounts", "account_id", account_id, fields, reason)


def list_accounts(conn, platform_id: Optional[int] = None) -> List[dict]:
    if platform_id is None:
        rows = conn.execute("SELECT * FROM accounts ORDER BY account_id")
    else:
        rows = conn.execute(
            "SELECT * FROM accounts WHERE platform_id=? ORDER BY account_id",
            (platform_id,))
    return [_dict(r) for r in rows.fetchall()]


def create_product(conn, account_id: int, name: str, product_type: str,
                   ticker: Optional[str] = None, currency: str = "CNY",
                   market: Optional[str] = None,
                   unit: str = "CNY") -> int:
    _check_enum(product_type, PRODUCT_TYPES, "product_type")
    _require(conn, "accounts", "account_id", account_id)
    return _insert(conn, "products",
                   ["account_id", "name", "product_type", "ticker",
                    "currency", "market", "unit"],
                   [account_id, name, product_type, ticker, currency,
                    market, unit], "create")


def update_product(conn, product_id: int, reason: Optional[str] = None,
                   **fields) -> None:
    if "product_type" in fields:
        _check_enum(fields["product_type"], PRODUCT_TYPES, "product_type")
    _update(conn, "products", "product_id", product_id, fields, reason)


def list_products(conn, account_id: Optional[int] = None,
                  product_type: Optional[str] = None,
                  include_inactive: bool = False) -> List[dict]:
    sql = "SELECT * FROM products WHERE 1=1"
    params: List = []
    if account_id is not None:
        sql += " AND account_id=?"
        params.append(account_id)
    if product_type is not None:
        sql += " AND product_type=?"
        params.append(product_type)
    if not include_inactive:
        sql += " AND status='active'"
    return [_dict(r) for r in conn.execute(
        sql + " ORDER BY product_id", params).fetchall()]


def get_product(conn, product_id: int) -> dict:
    d = _dict(conn.execute("SELECT * FROM products WHERE product_id=?",
                           (product_id,)).fetchone())
    if not d:
        raise ValidationError(f"product {product_id} does not exist")
    return d


# ---------------------------------------------------------------------------
# transactions (the ledger)
# ---------------------------------------------------------------------------

def create_transaction(conn, txn_date: str, product_id: int, txn_type: str,
                       units: float = 0.0, price: Optional[float] = None,
                       amount: float = 0.0, fee: float = 0.0,
                       cash_flow: float = 0.0, note: Optional[str] = None,
                       source: str = "manual") -> int:
    """One ledger row.

    `cash_flow` is the EXTERNAL flow (spec §7): deposit/withdrawal and
    transfers are signed; buy/sell are internal and must pass 0 (a
    non-zero value here would silently corrupt the P&L calculation).
    The invariant is enforced, not merely documented.
    """
    _check_enum(txn_type, TXN_TYPES, "txn_type")
    _require(conn, "products", "product_id", product_id)
    from .models import EXTERNAL_FLOW_TYPES

    if txn_type in EXTERNAL_FLOW_TYPES:
        if cash_flow == 0:
            raise ValidationError(
                f"{txn_type} requires a non-zero cash_flow (signed: "
                f"in=+, out=-)")
    elif cash_flow != 0:
        raise ValidationError(
            f"{txn_type} is an internal flow: cash_flow must be 0 "
            f"(got {cash_flow}) — external flows only via "
            f"deposit/withdrawal/transfer_*")
    if amount < 0 or fee < 0 or units < 0:
        raise ValidationError("units/amount/fee must be non-negative")
    return _insert(conn, "transactions",
                   ["txn_date", "product_id", "txn_type", "units", "price",
                    "amount", "fee", "cash_flow", "note", "source"],
                   [txn_date, product_id, txn_type, units, price, amount,
                    fee, cash_flow, note, source], "create")


def update_transaction(conn, txn_id: int, reason: str, **fields) -> None:
    """Corrections REQUIRE a reason (spec §39: 交易记录修改必须可追溯)."""
    if not reason:
        raise ValidationError("transaction corrections require a reason")
    if "txn_type" in fields:
        _check_enum(fields["txn_type"], TXN_TYPES, "txn_type")
    _update(conn, "transactions", "txn_id", txn_id, fields, reason)


def delete_transaction(conn, txn_id: int, reason: str) -> None:
    if not reason:
        raise ValidationError("transaction deletions require a reason")
    _delete(conn, "transactions", "txn_id", txn_id, reason)


def list_transactions(conn, product_id: Optional[int] = None,
                      start: Optional[str] = None, end: Optional[str] = None,
                      txn_type: Optional[str] = None) -> List[dict]:
    sql = "SELECT * FROM transactions WHERE 1=1"
    params: List = []
    if product_id is not None:
        sql += " AND product_id=?"
        params.append(product_id)
    if start:
        sql += " AND txn_date >= ?"
        params.append(start)
    if end:
        sql += " AND txn_date <= ?"
        params.append(end)
    if txn_type:
        sql += " AND txn_type=?"
        params.append(txn_type)
    return [_dict(r) for r in conn.execute(
        sql + " ORDER BY txn_date, txn_id", params).fetchall()]


# ---------------------------------------------------------------------------
# snapshots / income / positions
# ---------------------------------------------------------------------------

def upsert_snapshot(conn, snap_date: str, product_id: int, units: float = 0.0,
                    nav: Optional[float] = None,
                    market_value: float = 0.0, cash_flow: float = 0.0,
                    note: Optional[str] = None,
                    source: str = "manual") -> int:
    """Daily entry (idempotent): the same (date, product) overwrites."""
    _require(conn, "products", "product_id", product_id)
    old = _dict(conn.execute(
        "SELECT * FROM daily_snapshots WHERE snap_date=? AND product_id=?",
        (snap_date, product_id)).fetchone())
    if old:
        _update(conn, "daily_snapshots", "snapshot_id", old["snapshot_id"],
                {"units": units, "nav": nav, "market_value": market_value,
                 "cash_flow": cash_flow, "note": note, "source": source},
                reason="daily update (same date overwrite)")
        return int(old["snapshot_id"])
    return _insert(conn, "daily_snapshots",
                   ["snap_date", "product_id", "units", "nav",
                    "market_value", "cash_flow", "note", "source"],
                   [snap_date, product_id, units, nav, market_value,
                    cash_flow, note, source], "create")


def list_snapshots(conn, product_id: Optional[int] = None,
                   start: Optional[str] = None,
                   end: Optional[str] = None) -> List[dict]:
    sql = "SELECT * FROM daily_snapshots WHERE 1=1"
    params: List = []
    if product_id is not None:
        sql += " AND product_id=?"
        params.append(product_id)
    if start:
        sql += " AND snap_date >= ?"
        params.append(start)
    if end:
        sql += " AND snap_date <= ?"
        params.append(end)
    return [_dict(r) for r in conn.execute(
        sql + " ORDER BY snap_date, product_id", params).fetchall()]


def upsert_income(conn, income_date: str, product_id: int, **fields) -> int:
    """万份收益记录（spec §8）: idempotent per (date, product)."""
    _require(conn, "products", "product_id", product_id)
    allowed = ["beginning_units", "ending_units", "beginning_value",
               "ending_value", "cash_flow", "daily_income",
               "income_per_10000", "annualized_yield",
               "calculation_method", "source"]
    vals = {k: fields[k] for k in allowed if k in fields}
    old = _dict(conn.execute(
        "SELECT * FROM income_records WHERE income_date=? AND product_id=?",
        (income_date, product_id)).fetchone())
    if old:
        _update(conn, "income_records", "income_id", old["income_id"], vals,
                reason="income recomputation (same date overwrite)")
        return int(old["income_id"])
    cols = ["income_date", "product_id"] + list(vals)
    return _insert(conn, "income_records", cols,
                   [income_date, product_id] + list(vals.values()), "create")


def list_income(conn, product_id: Optional[int] = None,
                start: Optional[str] = None,
                end: Optional[str] = None) -> List[dict]:
    sql = "SELECT * FROM income_records WHERE 1=1"
    params: List = []
    if product_id is not None:
        sql += " AND product_id=?"
        params.append(product_id)
    if start:
        sql += " AND income_date >= ?"
        params.append(start)
    if end:
        sql += " AND income_date <= ?"
        params.append(end)
    return [_dict(r) for r in conn.execute(
        sql + " ORDER BY income_date, product_id", params).fetchall()]


def replace_positions(conn, as_of: str, rows: List[dict]) -> int:
    """Write the engine-computed positions for one date (idempotent)."""
    conn.execute("DELETE FROM positions WHERE as_of=?", (as_of,))
    n = 0
    for r in rows:
        conn.execute(
            "INSERT INTO positions (as_of, product_id, units, avg_cost, "
            "market_value, realized_pnl, unrealized_pnl, source) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (as_of, r["product_id"], r.get("units", 0.0),
             r.get("avg_cost"), r.get("market_value", 0.0),
             r.get("realized_pnl", 0.0), r.get("unrealized_pnl", 0.0),
             r.get("source", "system")))
        n += 1
    conn.commit()
    return n


def list_positions(conn, as_of: Optional[str] = None) -> List[dict]:
    if as_of is None:
        row = conn.execute("SELECT MAX(as_of) d FROM positions").fetchone()
        as_of = row["d"] if row and row["d"] else None
    if as_of is None:
        return []
    return [_dict(r) for r in conn.execute(
        "SELECT * FROM positions WHERE as_of=? ORDER BY product_id",
        (as_of,)).fetchall()]


# ---------------------------------------------------------------------------
# benchmarks / categories / audit
# ---------------------------------------------------------------------------

def upsert_benchmark(conn, record_date: str, benchmark: str, close: float,
                     source: str = "canonical") -> None:
    if benchmark not in BENCHMARKS and not benchmark.startswith("custom:"):
        raise ValidationError(
            f"benchmark={benchmark!r} not in {BENCHMARKS} (custom ones "
            f"must be named 'custom:<name>')")
    conn.execute(
        "INSERT INTO benchmark_records (record_date, benchmark, close, "
        "source) VALUES (?,?,?,?) ON CONFLICT(record_date, benchmark) "
        "DO UPDATE SET close=excluded.close, source=excluded.source",
        (record_date, benchmark, close, source))
    conn.commit()


def list_benchmarks(conn, benchmark: Optional[str] = None) -> List[dict]:
    if benchmark:
        rows = conn.execute(
            "SELECT * FROM benchmark_records WHERE benchmark=? "
            "ORDER BY record_date", (benchmark,))
    else:
        rows = conn.execute(
            "SELECT * FROM benchmark_records ORDER BY record_date")
    return [_dict(r) for r in rows.fetchall()]


def add_category(conn, name: str, sort_order: int = 0,
                 applies_to: Optional[str] = None) -> int:
    return _insert(conn, "wealth_categories", ["name", "sort_order",
                                               "applies_to"],
                   [name, sort_order, applies_to], "create")


def list_categories(conn) -> List[dict]:
    return [_dict(r) for r in conn.execute(
        "SELECT * FROM wealth_categories ORDER BY sort_order, category_id"
    ).fetchall()]


def list_audit(conn, limit: int = 100, object_type: Optional[str] = None
               ) -> List[dict]:
    if object_type:
        rows = conn.execute(
            "SELECT * FROM audit_log WHERE object_type=? "
            "ORDER BY audit_id DESC LIMIT ?", (object_type, limit))
    else:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY audit_id DESC LIMIT ?",
            (limit,))
    return [_dict(r) for r in rows.fetchall()]


# ---------------------------------------------------------------------------
# exports (spec §40)
# ---------------------------------------------------------------------------

EXPORTABLE = ("platforms", "accounts", "products", "transactions",
              "daily_snapshots", "positions", "income_records",
              "benchmark_records", "wealth_categories", "audit_log")


def export_csv(conn, dest_dir, tables: Optional[Sequence[str]] = None
               ) -> dict:
    import csv
    from pathlib import Path

    out = Path(dest_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = {}
    for t in (tables or EXPORTABLE):
        rows = conn.execute(f"SELECT * FROM {t}").fetchall()
        p = out / f"{t}.csv"
        with open(p, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            if rows:
                w.writerow(rows[0].keys())
                w.writerows([tuple(r) for r in rows])
        written[t] = len(rows)
    return written


def export_json(conn, path, tables: Optional[Sequence[str]] = None) -> dict:
    import json
    from pathlib import Path

    data = {}
    for t in (tables or EXPORTABLE):
        data[t] = [_dict(r) for r in conn.execute(f"SELECT * FROM {t}")]
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2,
                            default=str), encoding="utf-8")
    return {t: len(v) for t, v in data.items()}
