# -*- coding: utf-8 -*-
"""月度 forward 复盘（spec §26 / §40 / §42）。

    python scripts/paper_live/monthly_report.py --month 2026-10
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import _runner
from paper_live.report import monthly_report, nav_series, yearly_report

BENCH_LABELS = ["CSI300", "CSI500", "CSI1000"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", default=None, help="YYYY-MM")
    ap.add_argument("--year", type=int, default=None)
    ap.add_argument("--validation", action="store_true")
    args = ap.parse_args()

    cfg, store, provider = _runner.build(validation=args.validation)
    out = _runner.PROJECT_ROOT / "reports" / "forward_holdout"
    out.mkdir(parents=True, exist_ok=True)

    if args.year:
        text = yearly_report(store, cfg, args.year)
        p = out / f"{args.year}.md"
    else:
        month = args.month or str(pd.Timestamp.today().to_period("M"))
        benchmarks = {}
        nav = nav_series(store)
        if len(nav) >= 2:
            for b in cfg["paper_live"]["benchmarks"]:
                try:
                    benchmarks[b["label"]] = provider.benchmark_nav(
                        b["symbol"],
                        str(pd.Timestamp(nav.index[0]).date()),
                        str(pd.Timestamp(nav.index[-1]).date()))
                except Exception as e:
                    print(f"  [warn] 基准 {b['label']} 取数失败: {e}")
        text = monthly_report(store, cfg, month, benchmarks=benchmarks,
                              revisions=store.all_revisions())
        p = out / f"{month}.md"
    p.write_text(text, encoding="utf-8")
    print(f"月度报告 -> {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
