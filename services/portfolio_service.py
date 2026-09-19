# -*- coding: utf-8 -*-
"""账户 / 持仓 / 资产配置 / 对账（spec §6–§9 / §20 / §35 / §52 / §53）。"""

from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from ._common import safe, to_float, unavailable
from . import market_service

# spec §7 的资产分类顺序（展示用）
ASSET_CLASS_ORDER = ["stock", "etf", "fund", "bond", "money_market",
                     "cash", "other"]
ASSET_CLASS_CN = {
    "stock": "股票", "etf": "ETF", "fund": "基金", "bond": "债券",
    "money_market": "货币", "cash": "现金", "other": "其他",
    "bond_fund": "债券基金", "index_fund": "指数基金", "qdii": "QDII",
    "gold": "黄金", "money_fund": "货币基金",
}


def _conn():
    from wealth import db
    return db.connect()


def account_class(asset_class: str) -> str:
    """把 product_type 归并到 spec §7 的粗分类。"""
    m = {"stock": "stock", "etf": "etf", "index_fund": "fund",
         "bond_fund": "bond", "qdii": "fund", "gold": "other",
         "money_fund": "money_market", "cash": "cash", "other": "other",
         "fund": "fund", "bond": "bond", "money_market": "money_market"}
    return m.get(asset_class, "other")


@safe(label="账户")
def accounts() -> dict:
    from wealth import repository as repo
    rows = repo.list_accounts(_conn())
    return {"available": True, "rows": rows, "n": len(rows)}


@safe(label="持仓估值")
def valuation(account_id: Optional[int] = None) -> dict:
    """按**流水 × 最新价**估值。导入历史成交后立刻有数，不必等每日快照。"""
    from wealth import engine

    conn = _conn()
    tickers = [r["ticker"] for r in conn.execute(
        "SELECT ticker FROM products WHERE ticker IS NOT NULL AND "
        "status = 'active'").fetchall()]
    prices = market_service.latest_prices(tickers) if tickers else {}
    res = engine.value_positions(conn, prices, account_id)
    res["available"] = True
    res["price_date"] = market_service.price_date()
    return res


@safe(label="持仓明细")
def positions(account_id: Optional[int] = None) -> dict:
    v = valuation(account_id)
    if not v.get("available"):
        return v
    total = to_float(v.get("market_value")) + to_float(v.get("cash_recorded"))
    rows = []
    for h in v["holdings"]:
        mv = to_float(h["market_value"])
        rows.append({
            "symbol": h["symbol"], "name": h["name"],
            "asset_class": h["asset_class"],
            "asset_class_cn": ASSET_CLASS_CN.get(h["asset_class"],
                                                 h["asset_class"]),
            "quantity": h["units"], "avg_cost": h["avg_cost"],
            "price": h["price"], "market_value": mv,
            "weight": (mv / total) if total else 0.0,
            "unrealized_pnl": h["unrealized_pnl"],
            "realized_pnl": h["realized_pnl"],
            "return_pct": ((h["price"] / h["avg_cost"] - 1.0)
                           if h["avg_cost"] else None),
            "account": h["account"],
        })
    rows.sort(key=lambda r: -abs(to_float(r["market_value"])))
    return {"available": True, "rows": rows, "n": len(rows),
            "total_value": total, "missing_price": v["missing_price"],
            "price_date": v.get("price_date")}


@safe(label="资产配置")
def allocation(account_id: Optional[int] = None) -> dict:
    v = valuation(account_id)
    if not v.get("available"):
        return v
    buckets: Dict[str, float] = {}
    for h in v["holdings"]:
        k = account_class(h["asset_class"])
        buckets[k] = buckets.get(k, 0.0) + to_float(h["market_value"])
    if v.get("cash_recorded"):
        buckets["cash"] = buckets.get("cash", 0.0) + to_float(
            v["cash_recorded"])
    total = sum(buckets.values())
    rows = []
    for cls in ASSET_CLASS_ORDER:
        val = buckets.get(cls, 0.0)
        rows.append({"asset_class": cls,
                     "label": ASSET_CLASS_CN.get(cls, cls),
                     "value": val,
                     "weight": (val / total) if total else 0.0})
    return {"available": True, "rows": rows, "total_value": total,
            "cash_ratio": (buckets.get("cash", 0.0) / total) if total else 0.0}


@safe(label="每日快照")
def snapshots(limit: int = 400) -> dict:
    from wealth import db
    # sqlite3 的游标没有 fetch_df()（那是 DuckDB 的 API）—— 用 pandas 读
    df = pd.read_sql_query(
        """SELECT snap_date, SUM(market_value) AS total_value
           FROM daily_snapshots GROUP BY snap_date
           ORDER BY snap_date DESC LIMIT ?""", db.connect(),
        params=(int(limit),))
    if df.empty:
        return unavailable("还没有每日快照")
    df = df.sort_values("snap_date")
    return {"available": True,
            "series": [{"date": str(r["snap_date"]),
                        "value": float(r["total_value"] or 0.0)}
                       for _, r in df.iterrows()]}


@safe(label="对账")
def reconciliation() -> dict:
    from wealth import engine
    return {"available": True, **engine.reconcile(_conn())}


@safe(label="持仓一致性")
def consistency() -> dict:
    from wealth import engine
    rows = engine.position_consistency(_conn())
    bad = [r for r in rows if r["status"] == "MISMATCH"]
    return {"available": True, "rows": rows, "n_mismatch": len(bad)}


@safe(label="交易流水")
def transactions(limit: int = 500, account_id: Optional[int] = None) -> dict:
    from wealth import db
    sql = """SELECT t.*, p.name AS product_name, p.ticker, p.product_type,
                    a.name AS account
             FROM transactions t
             JOIN products p ON p.product_id = t.product_id
             JOIN accounts a ON a.account_id = p.account_id"""
    params = []
    if account_id is not None:
        sql += " WHERE p.account_id = ?"
        params.append(account_id)
    sql += " ORDER BY t.txn_date DESC, t.txn_id DESC LIMIT ?"
    params.append(int(limit))
    df = pd.read_sql_query(sql, db.connect(), params=tuple(params))
    return {"available": True,
            "rows": [dict(r) for _, r in df.iterrows()],
            "n": int(len(df))}


@safe(label="产品列表")
def products() -> dict:
    """产品列表（给录入表单用）。带账户名，页面直接显示。"""
    from wealth import db
    df = pd.read_sql_query(
        """SELECT p.product_id, p.name, p.ticker, p.product_type,
                  p.currency, p.status, a.name AS account,
                  a.account_id
           FROM products p JOIN accounts a ON a.account_id = p.account_id
           WHERE p.status = 'active'
           ORDER BY a.name, p.name""", db.connect())
    return {"available": True,
            "rows": [dict(r) for _, r in df.iterrows()], "n": int(len(df))}


@safe(label="记账")
def add_transaction(txn_date: str, product_id: int, txn_type: str,
                    units: float = 0.0, price=None, amount: float = 0.0,
                    fee: float = 0.0, note: str = "",
                    source: str = "gui") -> dict:
    """新增一笔流水。**这是记账，不是下单** —— 走 repository，自动审计。

    外部流（转入/转出）自动补符号化的 cash_flow，内部流恒为 0：
    这正是"存钱不算收益"在入库层的强制实现。
    """
    from wealth import repository as repo
    external = txn_type in ("deposit", "withdrawal", "transfer_in",
                            "transfer_out")
    amt = float(amount or 0.0) or (float(units) * float(price or 0.0))
    cash_flow = 0.0
    if external:
        if amt == 0:
            raise ValueError("转入/转出需要一个金额")
        cash_flow = amt if txn_type in ("deposit", "transfer_in") else -amt
    tid = repo.create_transaction(
        _conn(), txn_date=str(txn_date), product_id=int(product_id),
        txn_type=txn_type, units=float(units),
        price=float(price) if price else None, amount=amt, fee=float(fee),
        cash_flow=cash_flow, note=note or "界面录入", source=source)
    return {"available": True, "txn_id": tid, "amount": amt,
            "cash_flow": cash_flow}


@safe(label="备份")
def backup() -> dict:
    """备份个人财富库（只动 wealth.db，不碰市场数据库）。"""
    from wealth import db
    p = db.backup(conn=db.connect())
    return {"available": True, "path": str(p)}


@safe(label="导出")
def export_tables() -> dict:
    from wealth import db, repository as repo
    dest = PROJECT_ROOT / "data" / "wealth" / "export"
    res = repo.export_csv(db.connect(), dest)
    return {"available": True, "n_tables": len(res), "dest": str(dest)}


@safe(label="资料库状态")
def wealth_status() -> dict:
    from wealth import db
    conn = db.connect()
    n = conn.execute("SELECT COUNT(*) AS n FROM transactions").fetchone()["n"]
    return {"available": True, "n_transactions": int(n),
            "db_path": str(db.WEALTH_DB)}


@safe(label="更新数据")
def refresh_data_offline_guard() -> dict:
    """占位：页面用它来判断能不能跑刷新（真正的刷新由 pipeline 负责）。"""
    import os
    return {"available": True,
            "offline": os.environ.get("PQ_MODE", "").lower() == "offline"}


@safe(label="导入 CSV")
def import_csv(path, dry_run: bool = True) -> dict:
    """导入一份交易 CSV。走 importer（幂等 + 不猜值 + 自动审计）。"""
    from wealth import importer
    res = importer.import_transactions_csv(_conn(), path, dry_run=dry_run)
    return res.as_dict()
