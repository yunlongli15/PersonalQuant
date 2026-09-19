# -*- coding: utf-8 -*-
"""导入个人交易流水 CSV（spec §12）。

    python scripts/import_portfolio.py data/inbox/trades.csv
    python scripts/import_portfolio.py trades.csv --dry-run     # 只预览
    python scripts/import_portfolio.py trades.csv --apply       # 真正写库

**默认是 dry-run**：先看清会导入什么、哪些行有问题，再决定写不写。
这是记账，不是下单；不连接任何券商。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

TEMPLATE = """date,symbol,side,quantity,price,fees,account
2026-09-18,600519.SH,BUY,100,1680.5,5.2,券商
2026-09-18,510300.SH,BUY,1000,3.85,5.0,券商
2026-09-21,600519.SH,DIVIDEND,1200,0,0,券商
2026-09-21,,DEPOSIT,50000,0,0,券商
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?", help="要导入的 CSV 路径")
    ap.add_argument("--apply", action="store_true",
                    help="真正写库（默认只预览）")
    ap.add_argument("--template", action="store_true",
                    help="打印一份模板并退出")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    args = ap.parse_args()

    if args.template or not args.csv:
        print(TEMPLATE)
        return 0

    from wealth import db, importer

    path = Path(args.csv)
    conn = db.connect()
    res = importer.import_transactions_csv(conn, path, dry_run=not args.apply)
    d = res.as_dict()

    if args.json:
        print(json.dumps(d, ensure_ascii=False, indent=2))
        return 0 if res.ok else 1

    mode = "写入" if args.apply else "预览（未写库）"
    print(f"[{mode}] {d['path']}")
    print(f"  可导入 {d['n_imported']} 行 ｜ 重复跳过 {d['n_skipped']} 行 ｜ "
          f"错误 {d['n_errors']} 行")
    if d["created"]:
        print(f"  将新建：{d['created']}")
    for e in d["errors"]:
        print(f"  [错误] 第 {e['line']} 行：{e['detail']}")
    if not args.apply and d["n_imported"]:
        print("\n确认无误后加 --apply 真正写入。")
    if args.apply and d["n_imported"]:
        print("\n已写入，全部经过 audit_log。")
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
