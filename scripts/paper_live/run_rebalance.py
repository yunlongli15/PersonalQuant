# -*- coding: utf-8 -*-
"""Paper live 调仓日运行（spec §12 / §42）。

    python scripts/paper_live/run_rebalance.py --date 2026-09-30

与 run_daily 走**同一条引擎路径**，只是强制按调仓日处理，并输出
reports/paper_live/recommendations/<date>.csv（买卖清单）。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import _runner
from paper_live.alerts import check_alerts
from paper_live.engine import run_day

REC_COLS = ["symbol", "name", "rank", "predicted_return", "current_weight",
            "target_weight", "current_value", "target_value", "delta_value",
            "estimated_shares", "estimated_trade_value", "action",
            "estimated_fee", "execution_rule", "status", "reason"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="调仓信号日")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--validation", action="store_true")
    args = ap.parse_args()

    cfg, store, provider = _runner.build(validation=args.validation)
    d = pd.Timestamp(args.date)
    try:
        result = run_day(d, cfg, store, provider, dry_run=args.dry_run,
                         force_rebalance=True, alerts_fn=check_alerts)
    except (PermissionError, ValueError) as e:
        print(f"[REFUSED] {e}")
        return 2
    _runner.emit(result)

    if not result.is_rebalance:
        print("警告：该日未被判定为调仓日")
    # 推荐清单
    if not args.dry_run:
        trades = store.read_frame("trades", d)
        if trades is not None and not trades.empty:
            outdir = (_runner.PROJECT_ROOT /
                      cfg["paper_live"]["paths"]["root"] / "recommendations")
            outdir.mkdir(parents=True, exist_ok=True)
            p = outdir / f"{d.date()}.csv"
            cols = [c for c in REC_COLS if c in trades.columns]
            trades[cols].to_csv(p, index=False, encoding="utf-8-sig")
            print(f"推荐清单 -> {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
