# -*- coding: utf-8 -*-
"""每日告警检查（STEP 12, spec §17 / §18）。

    python scripts/check_daily_alerts.py            # 看最近一次运行产生的告警
    python scripts/check_daily_alerts.py --json

**只报警。** 本脚本没有任何修改策略/模型/组合的路径。
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.daily_alerts import CODES
from pipeline.daily_report import load_latest_summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    s = load_latest_summary()
    if not s:
        print("还没有每日运行记录（先跑 python scripts/run_daily.py）")
        return 0

    alerts = s.get("alerts") or []
    if args.json:
        print(json.dumps({"date": s.get("date"), "status": s.get("status"),
                          "alerts": alerts}, ensure_ascii=False, indent=2))
    else:
        print(f"最近一次运行：{s.get('date')}  状态 {s.get('status')}")
        if not alerts:
            print("无告警。")
        for a in alerts:
            print(f"[{a['level']:8s}] {a['code']:<18} {a['detail'][:80]}")
        print(f"\n合计 {len(alerts)} 条 ｜ 可用告警码：{', '.join(CODES)}")
        print("所有告警只报警：不调整策略、不重训模型、不改组合权重。")
    return 0 if not any(a["level"] in ("ERROR", "CRITICAL")
                        for a in alerts) else 1


if __name__ == "__main__":
    sys.exit(main())
