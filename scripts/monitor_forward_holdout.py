# -*- coding: utf-8 -*-
"""Forward holdout 监控（§25/§26）—— 只记录、只评估，**绝不参与选择**。

    python scripts/monitor_forward_holdout.py            # 看状态 + 登记新信号
    python scripts/monitor_forward_holdout.py --update-realized

为什么需要它：2024-2025 已经被评估过 3 次（STEP 6 终评、step8、step9），
不再是 untouched test。干净的样本外证据只能来自**此后新增的数据**。

这个脚本因此刻意做得很笨：它不训练、不选因子、不打分，
只把每个新的信号日的冻结预测登记下来，等标签窗口走完后回填已实现收益。
任何试图拿 holdout 数据去选因子的调用都会被 `assert_not_selection` 拦下。
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FORECAST_GLOB = "experiments/strategy_v1/forecasts/forecast_*.parquet"
LABELS = PROJECT_ROOT / "data/derived/factors/labels.parquet"
HORIZON = 20


def load_config() -> dict:
    return yaml.safe_load(
        (PROJECT_ROOT / "config" / "factor_selection_v2.yaml").read_text(
            encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update-realized", action="store_true",
                    help="标签窗口已走完的，回填已实现收益并算监控 IC")
    args = ap.parse_args()

    from incremental.holdout import ForwardHoldout

    cfg = load_config()
    h = ForwardHoldout.load(cfg)
    print(f"Forward holdout 起点 {h.start}（模式 {h.mode}）")
    print("约束：只记录 / 监控 / 评估，绝不参与因子选择。")

    if args.update_realized:
        if not LABELS.exists():
            print("标签缓存不存在，无法回填已实现收益")
            return 1
        lab = pd.read_parquet(LABELS)
        lab = lab[lab["horizon"] == HORIZON]
        by_date = {pd.Timestamp(d): g.set_index("symbol")["label"]
                   for d, g in lab.groupby("date")}
        n = 0
        for rec in list(h.records):
            d = pd.Timestamp(rec["date"])
            if d not in by_date:
                continue
            h.update_realized(d, by_date[d].to_dict())
            n += 1
        print(f"回填 {n} 期已实现收益")
        h.save()
        print(f"已写入 {h.registry}")
        return 0

    # ---- 登记新的信号日 ----
    files = sorted(PROJECT_ROOT.glob(FORECAST_GLOB))
    added = 0
    for f in files:
        stem = f.stem.replace("forecast_", "")
        try:
            d = pd.Timestamp(stem)
        except ValueError:
            continue
        if not h.is_holdout(d):
            continue
        if any(r["date"] == str(d.date()) for r in h.records):
            continue
        h.record_signal(d, str(f.relative_to(PROJECT_ROOT)),
                        note="自动登记冻结预测快照")
        added += 1
    if added:
        h.save()
    print(f"扫描 {len(files)} 个预测文件，新登记 {added} 期")

    s = h.summary()
    print(json.dumps(s, ensure_ascii=False, indent=2))
    if s["n_records"] == 0:
        print("\nholdout 尚无数据：干净的样本外证据需要时间累积，"
              "现在不做任何评判（§26）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
