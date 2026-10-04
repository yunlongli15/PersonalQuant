# -*- coding: utf-8 -*-
"""冻结生产状态（STEP 12, spec §2）。

    python scripts/freeze_production.py           # 写入冻结记录
    python scripts/freeze_production.py --check   # 只校验

冻结后，生产策略（strategy_v2 / paper_live / forward holdout）不允许直接
修改。任何新研究都必须新建 experiment config，见 docs/V1.0冻结规则.md。
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import freeze


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if args.check:
        print(json.dumps(freeze.verify().as_dict(), ensure_ascii=False,
                         indent=2))
        return 0 if freeze.verify().ok else 1

    try:
        rec = freeze.write_freeze()
    except freeze.ProductionDrift as e:
        print(f"[REFUSED] {e}", file=sys.stderr)
        return 2
    print("生产状态已冻结：")
    for k in ("version", "freeze_date", "git_commit", "strategy_version",
              "feature_version", "news_feature_version", "model_version",
              "allocation_method", "execution_model",
              "forward_holdout_start", "top_k", "production_enabled"):
        if k in rec:
            print(f"  {k:24s} {rec[k]}")
    print("\n工件哈希：")
    for k, v in rec.get("hashes", {}).items():
        print(f"  {k:28s} {str(v)[:16]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
