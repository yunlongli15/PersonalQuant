# -*- coding: utf-8 -*-
"""Dashboard 数据层（spec §28 / §47）。

    python scripts/paper_live/build_dashboard.py

只产出 forward_dashboard.parquet + .json，本阶段**不做 GUI**。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import _runner
from paper_live.report import build_dashboard, save_dashboard


def main() -> int:
    cfg, store, provider = _runner.build()
    benchmarks = {}
    df, payload = build_dashboard(store, cfg, benchmarks)
    paths = save_dashboard(store, cfg, df, payload)
    print(f"dashboard: {len(df)} 行")
    print(f"  {paths['parquet']}")
    print(f"  {paths['json']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
