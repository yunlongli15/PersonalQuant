# -*- coding: utf-8 -*-
"""Single-factor research CLI.

    python scripts/research_factor.py --factor momentum_20
    python scripts/research_factor.py --factor roe --start 2018-01-01 --end 2023-12-31
    python scripts/research_factor.py --factor roe --universe financial

Evaluates one factor over the given window on the cached research data
(data/derived/factors/): prints the IC/RankIC/ICIR table per horizon,
quantile returns, long-short stats and writes
reports/factors/factor_report_<name>.md. Selection decisions must use
research+valid only (see config/factor_research.yaml).
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from factors.base import DERIVED, load_factor_data
from factors.evaluator import evaluate_factor, pairwise_correlation
from factors.registry import FACTOR_REGISTRY, FACTORS
from factors.reports import factor_report_md

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_shared():
    import yaml

    cfg = yaml.safe_load(
        (PROJECT_ROOT / "config" / "factor_research.yaml").read_text(
            encoding="utf-8")
    )["factor_research"]
    labels = pd.read_parquet(DERIVED / "labels.parquet")
    labels = {int(h): g.pivot(index="date", columns="symbol", values="label")
              for h, g in labels.groupby("horizon")}
    univ = pd.read_parquet(DERIVED / "universes.parquet")
    univ["date"] = pd.to_datetime(univ["date"])
    universes = {
        kind: {pd.Timestamp(d): sorted(s) for d, s in
               univ[univ["universe"] == kind].groupby("date")["symbol"]}
        for kind in ("full", "financial")
    }
    return cfg, labels, universes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--factor", required=True)
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    ap.add_argument("--universe", default="full",
                    choices=["full", "financial"])
    args = ap.parse_args()

    name = args.factor
    if name not in FACTOR_REGISTRY:
        print(f"ERROR: unknown factor {name!r}. Registered: "
              f"{sorted(FACTOR_REGISTRY)}")
        return 1

    cfg, labels, universes = load_shared()
    ts = cfg["time_split"]
    start = args.start or ts["research"][0]
    end = args.end or ts["valid"][1]

    data = load_factor_data("2017-01-01", end)
    from factors.base import cached_rebalance_dates

    dates = cached_rebalance_dates(start, end)
    universe = universes[args.universe]

    ev = evaluate_factor(data, name, dates, labels, universe, cfg)
    print(json.dumps({
        "factor": name,
        "dates": f"{dates[0].date()}..{dates[-1].date()} ({len(dates)})",
        "universe": args.universe,
        "coverage": ev["coverage"],
        "normalizations": ev["normalizations"],
    }, indent=2, ensure_ascii=False, default=str))

    (PROJECT_ROOT / "reports" / "factors").mkdir(parents=True, exist_ok=True)
    corr = {"factor": name}
    md = factor_report_md(name, {"research": ev},
                          cfg["labels"]["horizons"], corr_row=corr)
    out = PROJECT_ROOT / "reports" / "factors" / f"factor_report_{name}.md"
    out.write_text(md, encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
