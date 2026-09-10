# -*- coding: utf-8 -*-
"""One-click data update (spec §20) + data status (spec §21).

    python scripts/quant/refresh_all.py --status        # freshness panel
    python scripts/quant/refresh_all.py --dry-run       # what would run
    python scripts/quant/refresh_all.py                 # run everything
    python scripts/quant/refresh_all.py --only factor_refresh,signal_refresh
    PQ_MODE=offline python scripts/quant/refresh_all.py # skip network jobs

Order: market -> news -> financial -> valuation -> factors -> signals ->
forecast -> portfolio. A network job in offline mode is recorded SKIPPED
(never reported as success). A real failure stops the chain unless
--continue-on-error, so recommendations can never silently ride on stale
inputs.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true",
                    help="print the data freshness panel and exit")
    ap.add_argument("--dry-run", action="store_true",
                    help="list the jobs and their offline state, run none")
    ap.add_argument("--only", default=None,
                    help="comma-separated subset of job names")
    ap.add_argument("--continue-on-error", action="store_true")
    ap.add_argument("--capital", type=float, default=500_000.0)
    ap.add_argument("--top-k", type=int, default=20)
    args = ap.parse_args()

    from pipeline import freshness, jobs, refresh

    if args.status:
        print(freshness.render_status_table())
        return 0

    if args.dry_run:
        only = args.only.split(",") if args.only else None
        print(json.dumps({"offline": refresh._is_offline(),
                          "jobs": refresh.JOB_NAMES,
                          "selected": only or refresh.JOB_NAMES},
                         ensure_ascii=False, indent=2))
        return 0

    only = args.only.split(",") if args.only else None
    results = refresh.run_all(
        only=only, continue_on_error=args.continue_on_error,
        jobs={n: f for n, f in refresh.REFRESH_JOBS
              if not only or n in only})
    print("\n===== refresh results =====")
    for r in results:
        mark = {"SUCCESS": "OK", "SKIPPED": "skipped",
                "SKIPPED_OFFLINE": "offline (skipped)",
                "FAILED": "FAILED"}.get(r["status"], r["status"])
        print(f"  [{mark:>18}] {r['job']}"
              + (f" — {r['detail']}" if r.get("detail") else "")
              + (f" — {r['error']}" if r.get("error") else ""))
    failed = [r for r in results if r["status"] == "FAILED"]
    print("\n===== data status after refresh =====")
    print(freshness.render_status_table())
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
