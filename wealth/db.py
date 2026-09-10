# -*- coding: utf-8 -*-
"""Wealth SQLite database (data/wealth/wealth.db).

Single-user, local-only operational database for REAL personal assets.
Strictly separate from the research DuckDB/Parquet layer (spec §4):
research data is regenerable and read-only, wealth data is irreplaceable
personal state — therefore:

  - SQLite (single file, transactional, easy to back up);
  - every write goes through repository.py and is audit-logged;
  - the file lives under data/ (git-ignored) and is NEVER mixed into
    backtests or reports of the research system.

Design notes
------------
- `cash_flows` / `fees` / `dividends` are VIEWS over `transactions`
  rather than separate tables: one ledger, one source of truth, no
  double-entry reconciliation problem.
- `positions` is a TABLE written by the calculation engine (7B) from
  transactions + snapshots, so the GUI reads holdings without recomputing.
- `money-market income` gets its own table (`income_records`) because the
  “万份收益” convention is not a NAV-based return (spec §8).
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEALTH_DIR = PROJECT_ROOT / "data" / "wealth"
WEALTH_DB = WEALTH_DIR / "wealth.db"

_local = threading.local()
_lock = threading.Lock()

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS platforms (
    platform_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    kind        TEXT NOT NULL,
    note        TEXT,
    status      TEXT NOT NULL DEFAULT 'active',
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    platform_id INTEGER NOT NULL REFERENCES platforms(platform_id),
    name        TEXT NOT NULL,
    currency    TEXT NOT NULL DEFAULT 'CNY',
    note        TEXT,
    status      TEXT NOT NULL DEFAULT 'active',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (platform_id, name)
);

CREATE TABLE IF NOT EXISTS products (
    product_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id   INTEGER NOT NULL REFERENCES accounts(account_id),
    name         TEXT NOT NULL,
    product_type TEXT NOT NULL,
    ticker       TEXT,
    currency     TEXT NOT NULL DEFAULT 'CNY',
    market       TEXT,
    unit         TEXT NOT NULL DEFAULT 'CNY',
    status       TEXT NOT NULL DEFAULT 'active',
    note         TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (account_id, name)
);

CREATE TABLE IF NOT EXISTS transactions (
    txn_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    txn_date    TEXT NOT NULL,
    product_id  INTEGER NOT NULL REFERENCES products(product_id),
    txn_type    TEXT NOT NULL,
    units       REAL NOT NULL DEFAULT 0,
    price       REAL,
    amount      REAL NOT NULL DEFAULT 0,
    fee         REAL NOT NULL DEFAULT 0,
    cash_flow   REAL NOT NULL DEFAULT 0,
    note        TEXT,
    source      TEXT NOT NULL DEFAULT 'manual',
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_txn_date ON transactions(txn_date);
CREATE INDEX IF NOT EXISTS idx_txn_product ON transactions(product_id, txn_date);

CREATE TABLE IF NOT EXISTS daily_snapshots (
    snapshot_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    snap_date    TEXT NOT NULL,
    product_id   INTEGER NOT NULL REFERENCES products(product_id),
    units        REAL NOT NULL DEFAULT 0,
    nav          REAL,
    market_value REAL NOT NULL DEFAULT 0,
    cash_flow    REAL NOT NULL DEFAULT 0,
    note         TEXT,
    source       TEXT NOT NULL DEFAULT 'manual',
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (snap_date, product_id)
);
CREATE INDEX IF NOT EXISTS idx_snap_date ON daily_snapshots(snap_date);

CREATE TABLE IF NOT EXISTS positions (
    position_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    as_of        TEXT NOT NULL,
    product_id   INTEGER NOT NULL REFERENCES products(product_id),
    units        REAL NOT NULL DEFAULT 0,
    avg_cost     REAL,
    market_value REAL NOT NULL DEFAULT 0,
    realized_pnl REAL NOT NULL DEFAULT 0,
    unrealized_pnl REAL NOT NULL DEFAULT 0,
    source       TEXT NOT NULL DEFAULT 'system',
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (as_of, product_id)
);

CREATE TABLE IF NOT EXISTS income_records (
    income_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    income_date        TEXT NOT NULL,
    product_id         INTEGER NOT NULL REFERENCES products(product_id),
    beginning_units    REAL NOT NULL DEFAULT 0,
    ending_units       REAL NOT NULL DEFAULT 0,
    beginning_value    REAL NOT NULL DEFAULT 0,
    ending_value       REAL NOT NULL DEFAULT 0,
    cash_flow          REAL NOT NULL DEFAULT 0,
    daily_income       REAL NOT NULL DEFAULT 0,
    income_per_10000   REAL NOT NULL DEFAULT 0,
    annualized_yield   REAL,
    calculation_method TEXT NOT NULL DEFAULT 'exact',
    source             TEXT NOT NULL DEFAULT 'system',
    created_at         TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (income_date, product_id)
);
CREATE INDEX IF NOT EXISTS idx_income_date ON income_records(income_date);

CREATE TABLE IF NOT EXISTS benchmark_records (
    benchmark_id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_date  TEXT NOT NULL,
    benchmark    TEXT NOT NULL,
    close        REAL NOT NULL,
    source       TEXT NOT NULL DEFAULT 'canonical',
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (record_date, benchmark)
);

CREATE TABLE IF NOT EXISTS wealth_categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    applies_to  TEXT
);

-- recommendation / decision / execution trail (spec §33/§34/§36):
-- the model recommends, the user decides, reality records what happened.
CREATE TABLE IF NOT EXISTS recommendations (
    recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    as_of        TEXT NOT NULL,
    symbol       TEXT NOT NULL,
    name         TEXT,
    action       TEXT NOT NULL,
    rec_price    REAL,
    entry_low    REAL,
    entry_high   REAL,
    shares       INTEGER NOT NULL DEFAULT 0,
    target_price REAL,
    stop_loss    REAL,
    expected_return REAL,
    signal_rank  INTEGER,
    source       TEXT NOT NULL DEFAULT 'trade_plan',
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (as_of, symbol, source)
);

CREATE TABLE IF NOT EXISTS decisions (
    decision_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    recommendation_id INTEGER NOT NULL
        REFERENCES recommendations(recommendation_id),
    decision          TEXT NOT NULL,     -- accept | modify | reject
    decided_at        TEXT NOT NULL DEFAULT (datetime('now')),
    modified_price    REAL,
    modified_shares   INTEGER,
    note              TEXT
);

CREATE TABLE IF NOT EXISTS executions (
    execution_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    recommendation_id INTEGER REFERENCES recommendations(recommendation_id),
    executed_at       TEXT NOT NULL,
    price             REAL NOT NULL,
    shares            INTEGER NOT NULL,
    fees              REAL NOT NULL DEFAULT 0,
    note              TEXT
);
CREATE INDEX IF NOT EXISTS idx_rec_asof ON recommendations(as_of);
CREATE INDEX IF NOT EXISTS idx_exec_rec ON executions(recommendation_id);

CREATE TABLE IF NOT EXISTS audit_log (
    audit_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL DEFAULT (datetime('now')),
    action      TEXT NOT NULL,
    actor       TEXT NOT NULL DEFAULT 'local_user',
    object_type TEXT NOT NULL,
    object_id   TEXT,
    old_value   TEXT,
    new_value   TEXT,
    reason      TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(timestamp);

-- One ledger: cash flows / fees / dividends are views, never tables.
CREATE VIEW IF NOT EXISTS cash_flows AS
    SELECT txn_id, txn_date, product_id, txn_type,
           cash_flow, note, source
    FROM transactions
    WHERE txn_type IN ('deposit', 'withdrawal', 'transfer_in',
                       'transfer_out');

CREATE VIEW IF NOT EXISTS fees AS
    SELECT txn_id, txn_date, product_id, fee, note, source
    FROM transactions
    WHERE fee > 0;

CREATE VIEW IF NOT EXISTS dividends AS
    SELECT txn_id, txn_date, product_id, units, amount, note, source
    FROM transactions
    WHERE txn_type = 'dividend';

-- Net worth by category (latest snapshot per product).
CREATE VIEW IF NOT EXISTS v_latest_values AS
    SELECT p.product_id, p.account_id, p.name, p.product_type,
           s.snap_date AS as_of, s.units, s.nav, s.market_value
    FROM products p
    JOIN daily_snapshots s ON s.product_id = p.product_id
    WHERE s.snap_date = (SELECT MAX(s2.snap_date) FROM daily_snapshots s2
                         WHERE s2.product_id = p.product_id);
"""


def db_path() -> Path:
    return WEALTH_DB


def connect(path: Optional[Path] = None) -> sqlite3.Connection:
    """Thread-local SQLite connection with the schema applied.

    `check_same_thread=False` is safe here because connections are
    thread-local (each thread gets its own).
    """
    p = Path(path) if path else WEALTH_DB
    if path is None:
        conn = getattr(_local, "conn", None)
        if conn is not None:
            return conn
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    if path is None:
        _local.conn = conn
    return conn


def reset(path: Optional[Path] = None) -> None:
    """Drop the cached connection (tests / after backup-restore)."""
    conn = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
        _local.conn = None


def close() -> None:
    reset()


def table_names(conn: sqlite3.Connection) -> list:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view') "
        "ORDER BY name").fetchall()
    return [r["name"] for r in rows]


def audit(conn: sqlite3.Connection, action: str, object_type: str,
          object_id=None, old_value=None, new_value=None, reason=None,
          actor: str = "local_user") -> None:
    """Append-only audit trail (spec §39) — call for every mutation."""
    import json

    def _s(v):
        if v is None or isinstance(v, str):
            return v
        return json.dumps(v, ensure_ascii=False, default=str)

    conn.execute(
        "INSERT INTO audit_log (action, actor, object_type, object_id, "
        "old_value, new_value, reason) VALUES (?,?,?,?,?,?,?)",
        (action, actor, object_type, None if object_id is None
         else str(object_id), _s(old_value), _s(new_value), reason))
    conn.commit()


def backup(dest_dir: Optional[Path] = None,
           conn: Optional[sqlite3.Connection] = None) -> Path:
    """One-click SQLite backup -> backup/wealth_YYYYMMDD.db (spec §40)."""
    from datetime import datetime

    c = conn or connect()
    out_dir = Path(dest_dir) if dest_dir else PROJECT_ROOT / "backup"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"wealth_{datetime.now():%Y%m%d_%H%M%S}.db"
    import sqlite3 as _s

    dest = _s.connect(str(target))
    with dest:
        c.backup(dest)
    dest.close()
    return target
