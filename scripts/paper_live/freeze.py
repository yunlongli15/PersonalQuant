# -*- coding: utf-8 -*-
"""冻结 paper-live 策略（spec §4）。

    python scripts/paper_live/freeze.py            # 写入 freeze 哈希
    python scripts/paper_live/freeze.py --check    # 只校验，不写

冻结后 config/paper_live.yaml 的 freeze 块记录 model / feature pack /
config 的 sha256；之后任何一处改动都会被 drift 检查发现。
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _runner
from paper_live.config import verify_freeze, write_freeze


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    cfg, _, _ = _runner.build()
    if args.check:
        print(json.dumps(verify_freeze(cfg), ensure_ascii=False, indent=2))
        return 0

    before = verify_freeze(cfg)
    if before.get("is_frozen") and before.get("drift"):
        print("警告：当前工件与已冻结哈希不一致：")
        print(json.dumps({"mismatches": before["mismatches"]},
                         ensure_ascii=False, indent=2))
        print("拒绝重新冻结 —— 冻结只做一次。若确需变更，请新开 "
              "strategy_version 与新的 forward holdout，并在报告中记录。")
        return 2

    hashes = write_freeze()
    print("已冻结：")
    for k, v in hashes.items():
        print(f"  {k:20s} {v[:16]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
