# -*- coding: utf-8 -*-
"""建立漂移监控的基线（一次性；换基线时才重跑）。

    python scripts/paper_live/init_drift_baselines.py [--date 2026-09-30]

为什么需要单独一步：`paper_live/engine.py` 的每日运行**只读**基线。若让它在
运行中顺手建档，"第一次跑"与"第二次跑"会产出不同的漂移结果，而 observation
是 append-only 的（store 会正确地拒绝覆盖同一天的记录），每日运行就不再幂等。

监控上膛之前，每日报告里 news / data 两行是 `NO_BASELINE` —— 那是实话：
这条监控还没生效，不等于"没有漂移"。

基线内容：
- news：2018-01-31..2025-12-31 历史因子快照的每因子 mean/std。必须用历史才
  有效 —— 只拿一天当基线的话 std=0，"位移超过 3σ"永远不触发。
- data：参考日当天的完整性指标（n_symbols / 缺失率 / 覆盖率，容差 30%）。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None,
                    help="data 基线的参考信号日（默认取最早一期 observation）")
    ap.add_argument("--only", default=None, choices=["news", "data"],
                    help="只建其中一份")
    args = ap.parse_args()

    from paper_live import drift as D
    from scripts.paper_live import _runner

    cfg, store, provider = _runner.build()
    state_dir = store.root / "state"

    ref = args.date
    if ref is None:
        obs = sorted((store.root / "observations").glob("*.json"))
        ref = obs[0].stem if obs else None

    if args.only != "news" and ref is None:
        print("没有 observation 可以当参考日；data 基线请显式给 --date")
        return 1

    out = D.init_baselines(
        state_dir,
        provider=None if args.only == "news" else provider,
        reference_date=ref)

    if args.only:
        out = {k: v for k, v in out.items() if k.startswith(args.only)}

    if not out:
        print("没有写出任何基线 —— 历史新闻快照不存在？参考日取不到？")
        return 1
    for k, v in sorted(out.items()):
        print(f"  {k}: {v}")
    print(f"\n基线目录: {state_dir}")
    print("基线一旦定下就**不要**随手重建 —— 换了基线，漂移的含义就变了。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
