# -*- coding: utf-8 -*-
"""Benchmark context for the strategy_v2 gate failures (spec §56).

The pre-specified gates include an ABSOLUTE-return validation gate
(ann > 0, Sharpe > 0). It fails for strategy_v2 on 2022-2023. To keep the
failure interpretable — and without touching the gate definition — this
script records, for the same periods, the CSI300 buy-and-hold benchmark
and the equal-weight market benchmark from canonical data (same raw
prices, same calendar):

  absolute return        strategy and benchmarks, separately
  benchmark-relative     strategy minus CSI300 buy-and-hold (daily IR)
  equal-weight benchmark reported separately (never mixed)

Definitions are recorded with the numbers; nothing is selected here.

    python scripts/portfolio/add_benchmark_context.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from research_portfolio import EXP_DIR
from personal_quant.strategy import metrics as mt

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PERIODS = {"research": ("2018-01-01", "2021-12-31"),
           "valid": ("2022-01-01", "2023-12-31"),
           "test": ("2024-01-01", "2025-12-31")}
IDX = "000300.SH"


def main() -> int:
    from factors.base import load_factor_data

    sel = json.loads((EXP_DIR / "selection.json").read_text(
        encoding="utf-8"))
    k = int(sel["stage1"]["chosen_top_k"])
    cash = float(sel["stage2"]["chosen_cash"])
    method = sel["stage3"]["chosen_method"]

    out = {"index": IDX, "benchmark_definitions": {
        "csi300_buy_hold": "index close (canonical raw) buy-and-hold, "
                           "no costs, no rebalancing",
        "equal_weight_market": "all investable symbols, equal weight, "
                               "daily rebalanced, no costs",
        "relative": "strategy daily return - CSI300 daily return -> "
                    "annualized IR (personal_quant.strategy.metrics)",
    }, "periods": {}}

    lo = pd.Timestamp(PERIODS["research"][0]) - pd.Timedelta(days=10)
    data = load_factor_data(lo, PERIODS["test"][1])
    close = data.close_raw

    for period, (s, e) in PERIODS.items():
        s, e = pd.Timestamp(s), pd.Timestamp(e)
        nav_path = EXP_DIR / \
            f"s3_{period}_{method}_k{k}_c{int(cash*100)}" / "nav.parquet"
        entry = {}
        if nav_path.exists():
            nav = pd.read_parquet(nav_path)["nav"]
            nav.index = pd.to_datetime(nav.index)
            entry["strategy"] = mt.summarize(nav, None, None, None, method)
        # CSI300 buy-and-hold
        bench = close[IDX].loc[s:e].dropna()
        if len(bench) > 5:
            nav_b = bench / bench.iloc[0]
            entry["csi300_buy_hold"] = mt.summarize(nav_b, None, None, None,
                                                    "csi300")
            if nav_path.exists():
                entry["relative_ir_vs_csi300"] = mt.information_ratio(
                    pd.read_parquet(nav_path)["nav"], nav_b)
                a, b = mt.alpha_beta(pd.read_parquet(nav_path)["nav"], nav_b)
                entry["alpha_annualized"] = a
                entry["beta"] = b
        # equal-weight market (investable universe approximation: all
        # symbols with a price on both ends of the period)
        sub = close.loc[s:e]
        ok = sub.notna().mean() > 0.9
        if ok.any():
            eq = sub.loc[:, ok].ffill().pct_change().mean(axis=1).fillna(0.0)
            nav_eq = (1 + eq).cumprod()
            entry["equal_weight_market"] = mt.summarize(nav_eq, None, None,
                                                        None, "eq_market")
        out["periods"][period] = entry

    path = EXP_DIR / "benchmark_context.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False,
                               default=str), encoding="utf-8")
    for period, e in out["periods"].items():
        st = e.get("strategy", {})
        cb = e.get("csi300_buy_hold", {})
        ew = e.get("equal_weight_market", {})
        print(f"{period}: strategy ann={st.get('annualized_return', float('nan')):.4f} "
              f"sharpe={st.get('sharpe', float('nan')):.3f} | csi300 ann="
              f"{cb.get('annualized_return', float('nan')):.4f} sharpe="
              f"{cb.get('sharpe', float('nan')):.3f} | eq_market ann="
              f"{ew.get('annualized_return', float('nan')):.4f} sharpe="
              f"{ew.get('sharpe', float('nan')):.3f} | IR vs csi300="
              f"{e.get('relative_ir_vs_csi300', float('nan')):.3f}")
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
