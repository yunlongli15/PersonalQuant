# -*- coding: utf-8 -*-
"""备份 / 导出个人资产数据（spec §54 / §68）。

    python scripts/backup_portfolio.py                 # 备份数据库
    python scripts/backup_portfolio.py --export        # 额外导出 CSV
    python scripts/backup_portfolio.py --list          # 列出已有备份
    python scripts/backup_portfolio.py --restore FILE  # 恢复（需 --confirm）

**只动个人数据**，绝不重复备份市场数据库（那有 17M 行，且可重新下载）。

恢复是不可逆操作：必须显式 `--confirm`，且默认先自动备份当前库。
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

BACKUP_DIR = PROJECT_ROOT / "backup"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", action="store_true",
                    help="额外导出各表为 CSV")
    ap.add_argument("--list", action="store_true", help="列出已有备份")
    ap.add_argument("--restore", default=None, help="从某个备份文件恢复")
    ap.add_argument("--confirm", action="store_true",
                    help="恢复必须显式确认")
    args = ap.parse_args()

    from wealth import db

    if args.list:
        files = sorted(BACKUP_DIR.glob("wealth_*.db"))
        if not files:
            print(f"还没有备份（目录：{BACKUP_DIR}）")
            return 0
        for f in files:
            print(f"  {f.name}  {f.stat().st_size/1024:.0f} KB")
        return 0

    if args.restore:
        src = Path(args.restore)
        if not src.exists():
            print(f"备份文件不存在：{src}", file=sys.stderr)
            return 1
        if not args.confirm:
            print("恢复会覆盖当前个人资产库，这是不可逆操作。\n"
                  f"  源：{src}\n  目标：{db.db_path()}\n"
                  "确认无误请加 --confirm。", file=sys.stderr)
            return 2
        # 恢复前先给当前库做一个备份 —— 后悔药
        safety = db.backup()
        print(f"已先把当前库备份到：{safety}")
        shutil.copy2(src, db.db_path())
        print(f"已从 {src.name} 恢复。")
        print("注意：**没有**触碰任何市场数据（DuckDB / Parquet 原样保留）。")
        return 0

    p = db.backup()
    print(f"已备份到：{p}")
    if args.export:
        from wealth import repository as repo
        dest = PROJECT_ROOT / "data" / "wealth" / "export"
        res = repo.export_csv(db.connect(), dest)
        print(f"已导出 {len(res)} 张表到：{dest}")
        for t, n in sorted(res.items()):
            print(f"  {t}: {n} 行")
    print("\n备份只包含个人资产数据；市场数据可从公开源重新下载，不重复备份。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
