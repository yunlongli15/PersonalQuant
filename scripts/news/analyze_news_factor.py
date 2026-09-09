# -*- coding: utf-8 -*-
"""Single news-factor analysis (reuses the STEP 4 factor engine).

    python scripts/news/analyze_news_factor.py --factor news_count_5d

Selection discipline: results shown here must be judged on research+valid
(2018-2023) only; the frozen test (2024-2025) is printed for the single
final evaluation and must not influence selection.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

from factors.base import DERIVED, load_factor_data
from factors.evaluator import evaluate_factor
from factors.registry import FACTOR_REGISTRY, FACTORS

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_shared(cfg):
    labels = pd.read_parquet(DERIVED / "labels.parquet")
    labels = {int(h): g.pivot(index="date", columns="symbol", values="label")
              for h, g in labels.groupby("horizon")}
    univ = pd.read_parquet(DERIVED / "universes.parquet")
    univ["date"] = pd.to_datetime(univ["date"])
    universes = {kind: {pd.Timestamp(d): sorted(s) for d, s in
                        univ[univ["universe"] == kind].groupby("date")["symbol"]}
                 for kind in ("full", "financial")}
    return labels, universes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--factor", required=True)
    ap.add_argument("--universe", default="full", choices=["full", "financial"])
    args = ap.parse_args()

    import yaml

    cfg = yaml.safe_load((PROJECT_ROOT / "config" / "news_v1.yaml").read_text(
        encoding="utf-8"))["news"]
    name = args.factor
    if name not in FACTOR_REGISTRY:
        print(f"ERROR: unknown factor {name!r}")
        return 1
    labels, universes = load_shared(cfg)
    ts = cfg["time_split"]
    from factors.base import cached_rebalance_dates

    r_dates = cached_rebalance_dates(ts["research"][0], ts["research"][1])
    v_dates = cached_rebalance_dates(ts["valid"][0], ts["valid"][1])
    t_dates = cached_rebalance_dates(ts["test"][0], ts["test"][1])

    data = load_factor_data("2017-01-01", ts["test"][1])
    cfg_eff = {"labels": {"horizons": [1, 5, 20, 40, 60],
                          "primary_horizon": 20},
               "normalization": {"methods": ["rank", "winsorized_zscore"]},
               "missing": {"method": "drop"},
               "evaluation": {"min_stocks_per_date": 30}}
    out = {}
    for period, dates in (("research", r_dates), ("valid", v_dates),
                          ("test", t_dates)):
        out[period] = evaluate_factor(data, name, dates, labels,
                                      universes[args.universe], cfg_eff,
                                      compute=FACTORS[name])
    for period, ev in out.items():
        ric = ev["normalizations"]["rank"]["horizons"]["20"]["rank_ic"]
        print(f"{period:10s} rank-IC {ric['mean']:+.4f}  ICIR "
              f"{ric['icir']:+.3f}  coverage {ev['coverage']:.2f}")
    out_dir = PROJECT_ROOT / "reports" / "factors"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"factor_report_{name}.md").write_text(
        json.dumps(out, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
