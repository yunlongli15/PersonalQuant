# -*- coding: utf-8 -*-
"""Paper live 每日运行（spec §5 / §42）。

    python scripts/paper_live/run_daily.py                  # 跑最新可用交易日
    python scripts/paper_live/run_daily.py --date 2026-09-30
    python scripts/paper_live/run_daily.py --dry-run        # 只检查，不落盘

非调仓日只产生 HOLD / monitoring snapshot；调仓日额外生成目标组合、
计算交易并模拟 T+1 开盘执行。绝不连接券商、绝不自动下单。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _runner
from paper_live.alerts import check_alerts
from paper_live.engine import run_day


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="信号日（默认最新交易日）")
    ap.add_argument("--dry-run", action="store_true",
                    help="不写正式 forward observation")
    ap.add_argument("--validation", action="store_true",
                    help="写 engine_validation root（历史引擎验证用）")
    args = ap.parse_args()

    cfg, store, provider = _runner.build(validation=args.validation)
    d = _runner.resolve_signal_date(provider, args.date)
    try:
        result = run_day(d, cfg, store, provider, dry_run=args.dry_run,
                         alerts_fn=check_alerts)
    except (PermissionError, ValueError) as e:
        print(f"[REFUSED] {e}")
        return 2
    _runner.emit(result)
    return 0 if result.status != "INVALID" else 1


if __name__ == "__main__":
    sys.exit(main())
