# -*- coding: utf-8 -*-
"""生成演示账户（spec §69）。

    python scripts/make_demo_account.py
    PQ_WEALTH_DB=data/wealth/demo.db python scripts/run_app.py

为什么用**独立的演示库**而不是往真实库里塞数据：
真实财富库是"不可再生的个人状态"，一条演示流水混进去就再也分不清真假。
演示库放 `data/wealth/demo.db`，两个库物理隔离，随时可删可重建。
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

DEMO_DB = PROJECT_ROOT / "data" / "wealth" / "demo.db"

# 一批手写的示例流水（不是真实持仓，也不构成任何建议）
TRADES = [
    # (日期, 代码, 名称, 类型, 数量, 价格, 费用, 流水类型)
    ("2026-06-02", "", "现金", "cash", 0, 0, 0, "deposit"),
    ("2026-06-03", "600519.SH", "贵州茅台", "stock", 100, 1520.0, 5.2, "buy"),
    ("2026-06-03", "510300.SH", "沪深300ETF", "etf", 2000, 3.92, 5.0, "buy"),
    ("2026-06-15", "000001.SZ", "平安银行", "stock", 1000, 11.35, 5.0, "buy"),
    ("2026-07-08", "600519.SH", "贵州茅台", "stock", 0, 0, 0, "dividend"),
    ("2026-08-03", "000001.SZ", "平安银行", "stock", 500, 12.10, 5.3, "sell"),
]
DIVIDEND_AMOUNT = 1800.0        # 茅台分红（示例）
DEPOSIT_AMOUNT = 300000.0       # 初始入金（示例）
SNAP_VALUES = {                 # 现金产品的每日余额（示例）
    "2026-06-02": 300000.0, "2026-06-03": 144000.0,
    "2026-06-15": 132000.0, "2026-08-03": 138000.0,
}
# 各标的的示例收盘价（仅演示；不是行情，也不是建议）
PRICE_PATH = {
    "2026-06-03": {"600519.SH": 1520.0, "510300.SH": 3.92},
    "2026-06-15": {"600519.SH": 1545.0, "510300.SH": 3.98,
                   "000001.SZ": 11.35},
    "2026-08-03": {"600519.SH": 1580.0, "510300.SH": 4.05,
                   "000001.SZ": 12.10},
}


def _units_held(conn, product_id, as_of: str) -> float:
    """该产品截至 as_of 的持仓股数（由流水重建）。"""
    from wealth import engine

    txns = [dict(r) for r in conn.execute(
        "SELECT * FROM transactions WHERE product_id = ? AND txn_date <= ?",
        (product_id, as_of))]
    return engine.holdings_from_ledger(txns).units


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DEMO_DB))
    ap.add_argument("--force", action="store_true", help="覆盖已有演示库")
    args = ap.parse_args()

    target = Path(args.db)
    if target.exists():
        if not args.force:
            print(f"演示库已存在：{target}\n（加 --force 覆盖重建）")
            return 0
        target.unlink()
    target.parent.mkdir(parents=True, exist_ok=True)

    os.environ["PQ_WEALTH_DB"] = str(target)
    from wealth import db, engine, repository as repo

    conn = db.connect()
    pid = repo.create_platform(conn, "演示券商", kind="broker",
                               note="仅用于界面演示")
    aid = repo.create_account(conn, pid, "演示账户")

    created = {}
    for _, ticker, name, ptype, _, _, _, _ in TRADES:
        key = ticker or "现金"
        if key in created:
            continue
        created[key] = repo.create_product(
            conn, aid, name, ptype, ticker=ticker or None,
            market=(ticker[-2:] if ticker else None))

    for d, ticker, name, ptype, units, price, fee, ttype in TRADES:
        prod = created[ticker or "现金"]
        if ttype == "deposit":
            repo.create_transaction(conn, d, prod, "deposit",
                                    amount=DEPOSIT_AMOUNT,
                                    cash_flow=DEPOSIT_AMOUNT,
                                    note="演示初始入金", source="demo")
        elif ttype == "dividend":
            repo.create_transaction(conn, d, prod, "dividend",
                                    amount=DIVIDEND_AMOUNT, source="demo")
        else:
            repo.create_transaction(conn, d, prod, ttype, units=units,
                                    price=price, amount=units * price,
                                    fee=fee, source="demo")

    # 每日快照：现金余额 + 各标的市值。
    # 只给现金写快照的话，净值序列就只剩现金，存入 30 万再买入会显示成
    # 巨额回撤（看起来像 -50%），完全误导。
    cash = created["现金"]
    for d, v in SNAP_VALUES.items():
        # 入金当天的快照必须带 cash_flow，否则 value_series 会把 30 万入金
        # 算成当日"收益"（P&L 铁律：外部流要从收益里剔除）。
        flow = DEPOSIT_AMOUNT if d == "2026-06-02" else 0.0
        repo.upsert_snapshot(conn, d, cash, units=v, nav=1.0, market_value=v,
                             cash_flow=flow, source="demo")
    for d, prices in PRICE_PATH.items():
        for ticker, px in prices.items():
            prod = created.get(ticker)
            if prod is None:
                continue
            held = _units_held(conn, prod, d)
            if held <= 0:
                continue
            repo.upsert_snapshot(conn, d, prod, units=held, nav=px,
                                 market_value=held * px, source="demo")

    v = engine.value_positions(conn, prices={"600519.SH": 1580.0,
                                             "510300.SH": 4.05,
                                             "000001.SZ": 11.90})
    print(f"演示库已生成：{target}")
    print(f"  账户：演示券商 / 演示账户")
    print(f"  持仓 {v['n_positions']} 只，市值 {v['market_value']:,.0f}，"
          f"现金 {v['cash_recorded']:,.0f}")
    print("\n用演示库启动界面：")
    print(f"  PQ_WEALTH_DB={target} python scripts/run_app.py")
    print("（**不会**影响 data/wealth/wealth.db 里的真实数据）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
