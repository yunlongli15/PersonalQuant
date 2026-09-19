# -*- coding: utf-8 -*-
"""每日自动化流水线（STEP 12）。

    python scripts/run_daily.py                  # 跑最新交易日
    python scripts/run_daily.py --dry-run        # 只做检查，不写任何东西
    python scripts/run_daily.py --date 2026-09-18
    python scripts/run_daily.py --force          # 忽略"已完成"，新开一个 run
    python scripts/run_daily.py --backfill --force --date ...   # 历史模拟
    python scripts/run_daily.py --history        # 看运行历史

用户平时只需要这一条命令（或交给 Windows 计划任务）。
**不训练模型、不选因子、不调参数、不自动下单。**
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.daily import TASK_NAMES, history, run_daily


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="运行日期（默认最新交易日）")
    ap.add_argument("--dry-run", action="store_true",
                    help="只做环境/数据/冻结/数据源检查，不写任何东西")
    ap.add_argument("--force", action="store_true",
                    help="忽略幂等判断，新开一个 run（不覆盖原记录）")
    ap.add_argument("--backfill", action="store_true",
                    help="历史模拟（必须同时给 --force；绝不进入 forward 选择）")
    ap.add_argument("--only", default=None, help="只跑这些步骤（逗号分隔）")
    ap.add_argument("--with-financial", action="store_true",
                    help="同时抓取财务数据（默认按需跳过：S3 特征集不含财务因子）")
    ap.add_argument("--history", action="store_true", help="打印运行历史后退出")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if args.history:
        rows = history(limit=30)
        if not rows:
            print("还没有运行历史。")
            return 0
        print(f"{'run_id':<22}{'status':<26}{'耗时':>8}{'告警':>6}{'错误':>6}")
        for r in rows:
            print(f"{r['run_id']:<22}{r['status']:<26}"
                  f"{r['duration_s'] or 0:>7.1f}s{r['n_warnings']:>6}"
                  f"{r['n_errors']:>6}")
        return 0

    only = [s.strip() for s in args.only.split(",")] if args.only else None
    if only:
        unknown = [s for s in only if s not in TASK_NAMES]
        if unknown:
            print(f"未知步骤 {unknown}；可用：{TASK_NAMES}", file=sys.stderr)
            return 2

    run = run_daily(date=args.date, dry_run=args.dry_run, force=args.force,
                    backfill=args.backfill, verbose=args.verbose, only=only,
                    with_financial=args.with_financial)

    if args.json:
        print(json.dumps(run.as_dict(), ensure_ascii=False, indent=2,
                         default=str))
    else:
        print(f"\n=== 每日流水线 {run.run_id} ===")
        print(f"状态：{run.status}  耗时 {run.duration_s:.1f}s  "
              f"（{len(run.tasks)} 个步骤）\n")
        for t in run.tasks:
            mark = {"OK": "✓", "WARNING": "!", "FAILED": "✗",
                    "INVALID": "✗", "BLOCKED": "·",
                    "SKIPPED": "-"}.get(t.status, "?")
            print(f"  {mark} {t.name:<18}{t.status:<10}"
                  f"{(t.detail or t.error)[:64]}")
        if run.warnings:
            print("\n告警：")
            for w in run.warnings:
                print(f"  ! {w[:100]}")
        if run.errors:
            print("\n错误：")
            for e in run.errors:
                print(f"  ✗ {e[:100]}")
        if not run.dry_run and run.status not in ("ALREADY_COMPLETED",):
            print(f"\n日报：reports/daily/{run.date}.md")
            print(f"日志：logs/daily/{run.date}.log")

    if run.status in ("ALREADY_COMPLETED",):
        print("\n今天已经跑过了，且输入没有变化（用 --force 可再跑一次）。")
    return 0 if run.status in ("OK", "WARNING", "ALREADY_COMPLETED",
                               "WAITING_FOR_FORWARD_DATA") else 1


if __name__ == "__main__":
    sys.exit(main())
