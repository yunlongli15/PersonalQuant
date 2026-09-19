# -*- coding: utf-8 -*-
"""PIT / 数据完整性审计（spec §6 / §42）。

    python scripts/paper_live/audit.py --date 2026-09-30
    python scripts/paper_live/audit.py                 # 最新交易日

只读，不写任何 forward observation。
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _runner
from paper_live import audit as audit_mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cfg, store, provider = _runner.build()
    d = _runner.resolve_signal_date(provider, args.date)
    symbols = provider.universe(d)
    features = provider.feature_matrix(d, symbols)
    custom = provider.custom_factors(d, symbols)
    res = audit_mod.pit_audit(
        provider, d, symbols, features, custom,
        consumed_factors=getattr(provider.stats, "consumed_factors", None))
    res.metrics.update(audit_mod.data_completeness(features, custom, symbols))

    if args.json:
        print(json.dumps(res.as_dict(), ensure_ascii=False, indent=2,
                         default=str))
    else:
        print(f"PIT 审计 {d.date()}  状态 {res.status}")
        for c in res.checks:
            print(f"  [{c.status:7s}] {c.name}: {c.detail}")
        print(f"  完整性: {res.metrics}")
    return 0 if res.status != "INVALID" else 1


if __name__ == "__main__":
    sys.exit(main())
