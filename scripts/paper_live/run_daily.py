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
from paper_live.engine import rebalance_signal_date, run_day


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
    # 今天是不是调仓日，今天**答不出来**（日历里只有已经发生的交易日）。
    # 等到下个周期第一个交易日，上一个交易日才被确认 —— 那时以它为信号日
    # 补做这次调仓，执行正好落在今天开盘。见 paper_live.engine。
    sig = rebalance_signal_date(d, cfg, provider.trading_calendar())
    try:
        result = run_day(d, cfg, store, provider, dry_run=args.dry_run,
                         signal_date=sig, alerts_fn=check_alerts)
    except (PermissionError, ValueError) as e:
        print(f"[REFUSED] {e}")
        return 2
    _runner.emit(result)
    return 0 if result.status != "INVALID" else 1


if __name__ == "__main__":
    sys.exit(main())
