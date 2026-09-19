# -*- coding: utf-8 -*-
"""CSV 导入（STEP 11, spec §12）。

    date, symbol, side, quantity, price, fees, account
    2026-09-18, 600519.SH, BUY, 100, 1680.5, 5.2, 券商

设计原则
--------
1. **不用猜**。列名支持中英双语与常见别名，但**认不出来就报错**，
   绝不静默把某一列当成别的东西。
2. **幂等**。重复导入同一份 CSV 不会重复记账：与已有流水"同日/同产品/
   同类型/同数量/同金额"的行会被跳过并计入 skipped。
3. **走正规入口**。每一条都经 `repository.create_transaction`，
   因此自动带 audit_log、自动校验外部流/内部流不变量。
4. **先预览后落库**。`dry_run=True` 只解析和校验，不写任何东西。
5. **不连券商**。这是手工/导出文件的导入，不是券商 API（spec §11）。
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

COLUMN_ALIASES = {
    "date": ("date", "trade_date", "日期", "交易日期", "成交日期"),
    "symbol": ("symbol", "ticker", "code", "代码", "证券代码", "股票代码"),
    "name": ("name", "名称", "证券名称", "股票名称"),
    "side": ("side", "action", "type", "方向", "买卖", "业务名称", "交易类型"),
    "quantity": ("quantity", "qty", "shares", "units", "数量", "股数", "成交数量"),
    "price": ("price", "成交价", "价格", "成交价格", "成交均价"),
    "fees": ("fees", "fee", "commission", "费用", "手续费", "佣金"),
    "account": ("account", "账户", "资金账户", "平台"),
    "amount": ("amount", "金额", "成交金额", "发生金额"),
    "note": ("note", "备注", "摘要"),
}

# 方向别名 → 账本 txn_type。认不出就报错。
SIDE_MAP = {
    "buy": "buy", "b": "buy", "买入": "buy", "证券买入": "buy",
    "sell": "sell", "s": "sell", "卖出": "sell", "证券卖出": "sell",
    "dividend": "dividend", "分红": "dividend", "红利入账": "dividend",
    "deposit": "deposit", "转入": "deposit", "银证转入": "deposit",
    "withdrawal": "withdrawal", "withdraw": "withdrawal", "转出": "withdrawal",
    "银证转出": "withdrawal",
    "transfer_in": "transfer_in", "transfer_out": "transfer_out",
    "fee": "fee", "费用": "fee",
    "split": "split", "拆股": "split", "送股": "split",
}
# 没有 symbol 也合法（纯资金流水）的类型
CASH_ONLY_TYPES = ("deposit", "withdrawal", "transfer_in", "transfer_out")
CASH_PRODUCT_NAME = "现金"


@dataclass
class ImportRow:
    line: int
    raw: dict
    status: str = "pending"          # ok | skipped | error
    detail: str = ""
    txn_id: Optional[int] = None
    txn_type: Optional[str] = None
    symbol: Optional[str] = None


@dataclass
class ImportResult:
    path: str
    n_rows: int = 0
    imported: List[ImportRow] = field(default_factory=list)
    skipped: List[ImportRow] = field(default_factory=list)
    errors: List[ImportRow] = field(default_factory=list)
    created: Dict[str, List[str]] = field(default_factory=dict)
    dry_run: bool = False

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def n_imported(self) -> int:
        return len(self.imported)

    @property
    def n_skipped(self) -> int:
        return len(self.skipped)

    @property
    def n_errors(self) -> int:
        return len(self.errors)

    def as_dict(self) -> dict:
        return {
            "path": self.path, "dry_run": self.dry_run,
            "n_rows": self.n_rows,
            "n_imported": len(self.imported),
            "n_skipped": len(self.skipped),
            "n_errors": len(self.errors),
            "created": self.created,
            "errors": [{"line": r.line, "detail": r.detail} for r in self.errors],
            "skipped": [{"line": r.line, "detail": r.detail}
                        for r in self.skipped[:20]],
        }


def _norm(s: str) -> str:
    return str(s or "").strip().lower().replace(" ", "").replace("_", "")


def detect_columns(headers: Sequence[str]) -> Dict[str, str]:
    """把文件表头映射到标准字段；认不出的列原样保留但不使用。"""
    out: Dict[str, str] = {}
    norm = {_norm(h): h for h in headers}
    for std, aliases in COLUMN_ALIASES.items():
        for a in aliases:
            if _norm(a) in norm:
                out[std] = norm[_norm(a)]
                break
    return out


def _to_float(v, default: float = 0.0) -> float:
    if v is None or str(v).strip() == "":
        return default
    return float(str(v).replace(",", "").replace("¥", "").strip())


def _parse_date(v: str) -> str:
    import pandas as pd

    s = str(v).strip()
    for fmt in (None, "%Y/%m/%d", "%Y%m%d", "%d/%m/%Y"):
        try:
            return str(pd.Timestamp(s).date()) if fmt is None else \
                str(pd.to_datetime(s, format=fmt).date())
        except Exception:
            continue
    raise ValueError(f"无法解析日期：{v!r}")


def _dedup_key(row: dict) -> tuple:
    return (str(row["txn_date"]), int(row["product_id"]), str(row["txn_type"]),
            round(float(row["units"]), 6), round(float(row["amount"]), 2))


def import_transactions_csv(conn, path, account_id: Optional[int] = None,
                            default_platform: str = "导入",
                            default_account: str = "默认账户",
                            dry_run: bool = False,
                            note_prefix: str = "CSV 导入") -> ImportResult:
    """把一份交易 CSV 导入账本。返回 ImportResult（含逐行状态）。"""
    from . import repository as repo

    p = Path(path)
    res = ImportResult(path=str(p), dry_run=dry_run)
    if not p.exists():
        r = ImportRow(0, {}, "error", f"文件不存在：{p}")
        res.errors.append(r)
        return res

    text = p.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(text.splitlines())
    headers = reader.fieldnames or []
    cols = detect_columns(headers)
    missing = [k for k in ("date", "side") if k not in cols]
    if missing:
        res.errors.append(ImportRow(0, {}, "error",
                                    f"缺少必需列 {missing}（表头：{headers}）"))
        return res

    # 账户解析（可指定，否则用 default_platform/default_account 建/找）
    acct = account_id or _ensure_account(conn, repo, default_platform,
                                         default_account, res, dry_run)
    existing = {_dedup_key(dict(r)) for r in conn.execute(
        "SELECT txn_date, product_id, txn_type, units, amount "
        "FROM transactions").fetchall()}
    seen_in_file = set()

    for i, raw in enumerate(reader, start=2):
        res.n_rows += 1
        row = ImportRow(i, dict(raw))
        try:
            side_raw = str(raw.get(cols["side"], "")).strip()
            ttype = SIDE_MAP.get(_norm(side_raw))
            if ttype is None:
                raise ValueError(f"无法识别的方向：{side_raw!r}")
            row.txn_type = ttype

            symbol = str(raw.get(cols.get("symbol", ""), "") or "").strip()
            row.symbol = symbol or None
            if not symbol and ttype not in CASH_ONLY_TYPES:
                raise ValueError(f"{ttype} 需要 symbol")

            txn_date = _parse_date(raw[cols["date"]])
            qty = _to_float(raw.get(cols.get("quantity", ""), 0))
            price = _to_float(raw.get(cols.get("price", ""), 0))
            fees = _to_float(raw.get(cols.get("fees", ""), 0))
            explicit_amount = raw.get(cols.get("amount", ""), None)
            amount = _to_float(explicit_amount, 0.0) if explicit_amount \
                not in (None, "") else qty * price

            pid = _ensure_product(conn, repo, acct, symbol,
                                  str(raw.get(cols.get("name", ""), "")
                                      or "").strip(),
                                  ttype, res, dry_run)
            if pid is None:
                raise ValueError("无法解析产品")

            # 外部流：cash_flow 必须非零且带符号（入库层也会强校验）。
            # 这里提前校验一次，好让 dry-run 与真实导入给出同样的判定。
            cash_flow = 0.0
            if ttype in CASH_ONLY_TYPES:
                # 纯资金流水没有价格：金额优先取 amount 列，否则取 quantity
                # （券商导出的"发生金额"就是这一笔的钱）。**不能**用
                # qty × price —— 那对转入/转出恒等于 0。
                if amount == 0:
                    amount = qty
                if amount == 0:
                    raise ValueError(f"{ttype} 需要金额（amount 或 quantity 列）")
                sign = 1.0 if ttype in ("deposit", "transfer_in") else -1.0
                cash_flow = sign * abs(amount)
            elif ttype == "dividend":
                # 分红通常没有价格：quantity 列放的就是红利金额
                if amount == 0:
                    amount = qty
                if amount == 0:
                    raise ValueError("分红需要金额（amount 或 quantity 列）")
            elif ttype in ("buy", "sell") and amount == 0:
                raise ValueError(f"{ttype} 需要金额（或 数量×价格）")

            payload = {
                "txn_date": txn_date, "product_id": pid, "txn_type": ttype,
                "units": qty, "price": price or None, "amount": amount,
                "fee": fees, "cash_flow": cash_flow,
                "note": str(raw.get(cols.get("note", ""), "") or "")
                        or f"{note_prefix} 第 {i} 行",
                "source": "csv_import",
            }
            key = _dedup_key(payload)
            if key in existing or key in seen_in_file:
                row.status, row.detail = "skipped", "重复行（已存在）"
                res.skipped.append(row)
                continue
            if dry_run:
                row.status, row.detail = "ok", "dry-run（未写入）"
                res.imported.append(row)
                seen_in_file.add(key)
                continue

            row.txn_id = repo.create_transaction(conn, **payload)
            row.status = "ok"
            res.imported.append(row)
            seen_in_file.add(key)
        except Exception as e:                                # noqa: BLE001
            row.status, row.detail = "error", f"{type(e).__name__}: {e}"
            res.errors.append(row)

    if not dry_run:
        from .db import audit
        audit(conn, "import_csv", "transactions", object_id=str(p),
              new_value={"imported": len(res.imported),
                         "skipped": len(res.skipped),
                         "errors": len(res.errors)},
              reason=f"CSV 导入 {p.name}")
    return res


def _ensure_account(conn, repo, platform_name: str, account_name: str,
                    res: ImportResult, dry_run: bool) -> int:
    row = conn.execute(
        """SELECT a.account_id FROM accounts a
           JOIN platforms p ON p.platform_id = a.platform_id
           WHERE p.name = ? AND a.name = ?""",
        (platform_name, account_name)).fetchone()
    if row:
        return int(row["account_id"])
    if dry_run:
        res.created.setdefault("accounts", []).append(
            f"{platform_name}/{account_name}")
        return -1
    pid = None
    r = conn.execute("SELECT platform_id FROM platforms WHERE name = ?",
                     (platform_name,)).fetchone()
    if r:
        pid = int(r["platform_id"])
    else:
        pid = repo.create_platform(conn, platform_name, kind="other")
        res.created.setdefault("platforms", []).append(platform_name)
    aid = repo.create_account(conn, pid, account_name)
    res.created.setdefault("accounts", []).append(f"{platform_name}/{account_name}")
    return aid


def _ensure_product(conn, repo, account_id: int, symbol: Optional[str],
                    name: str, ttype: str, res: ImportResult,
                    dry_run: bool) -> Optional[int]:
    """按 ticker 找产品；没有就按类型建一个。"""
    if account_id == -1:                                     # dry-run 无账户
        return -1
    if not symbol:
        symbol = CASH_PRODUCT_NAME
        ptype = "cash"
    else:
        ptype = _infer_type(symbol)

    r = conn.execute(
        "SELECT product_id FROM products WHERE account_id = ? AND ticker = ?",
        (account_id, symbol)).fetchone()
    if r:
        return int(r["product_id"])
    if dry_run:
        res.created.setdefault("products", []).append(symbol)
        return -1
    pid = repo.create_product(conn, account_id, name or symbol, ptype,
                              ticker=symbol,
                              market=_market_of(symbol))
    res.created.setdefault("products", []).append(f"{symbol}({ptype})")
    return pid


def _market_of(symbol: str) -> Optional[str]:
    if symbol.endswith(".SH"):
        return "SH"
    if symbol.endswith(".SZ"):
        return "SZ"
    if symbol.endswith(".BJ"):
        return "BJ"
    return None


def _infer_type(symbol: str) -> str:
    """按代码段推断资产类别（与 trade_plan/boards.py 的口径一致）。"""
    s = symbol.upper()
    if s == CASH_PRODUCT_NAME:
        return "cash"
    num = s.split(".")[0]
    if s.endswith(".BJ"):
        return "stock"
    if num.startswith(("51", "56", "58", "15", "16", "18")):
        return "etf"
    if num.startswith(("688", "300", "301", "600", "601", "603", "605",
                       "000", "001", "002", "003")):
        return "stock"
    return "other"
