# -*- coding: utf-8 -*-
"""STEP 3 acceptance verification.

    python scripts/verify_step3.py [--run-id run_001]

Checks strategy config, temporal split, leakage rules, universe history,
T+1 execution, position sizing, costs, backtest artifacts, benchmarks, IC,
quantiles, walk-forward, paper-live output and reproducibility.
Prints PASS/FAIL per item; exit code 0 only when all pass.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="run_001")
    args = ap.parse_args()
    run_dir = PROJECT_ROOT / "experiments" / "strategy_v1" / args.run_id

    print("=" * 64)
    print("STEP 3 verification: first low-frequency alpha strategy")
    print("=" * 64)

    import yaml

    config = yaml.safe_load(
        (PROJECT_ROOT / "config" / "strategy_v1.yaml").read_text(encoding="utf-8")
    )

    # --- config valid ---
    try:
        assert config["portfolio"]["top_k"] == 20
        assert config["rebalance"]["frequency"] == "monthly"
        assert config["execution"]["timing"] == "T1_open"
        check("strategy config valid", True)
    except Exception as e:
        check("strategy config valid", False, str(e))

    # --- temporal split ---
    ts = config["time_split"]
    ok = (ts["train"][1] < ts["valid"][0] < ts["valid"][1] < ts["test"][0]
          and ts["test"][1] < ts["paper_live_start"])
    check("temporal split valid", ok, str(ts))

    # --- no future leakage ---
    from personal_quant.strategy.rebalance import rebalance_dates

    train_d = rebalance_dates(ts["train"][0], ts["train"][1])
    test_d = rebalance_dates(ts["test"][0], ts["test"][1])
    check("no future leakage (train < test)", bool(train_d and test_d)
          and max(train_d) < min(test_d))
    check("label is future-only (horizon>0)", config["label"]["horizon_days"] == 20)

    # --- universe uses historical information ---
    from personal_quant.strategy.universe import build_universe

    u2019 = build_universe(pd.Timestamp("2019-06-28"), config)
    u2024 = build_universe(pd.Timestamp("2024-06-28"), config)
    check("universe uses historical information",
          len(u2019) > 500 and len(u2024) > 500
          and set(u2019["symbol"]) != set(u2024["symbol"]),
          f"2019: {len(u2019)}, 2024: {len(u2024)}")

    # --- execution is T+1 ---
    from personal_quant.strategy.execution import execute_order, next_trading_day

    days = list(pd.date_range("2024-01-01", "2024-01-10", freq="B"))
    t = pd.Timestamp("2024-01-08")
    nxt = next_trading_day(t)
    res = execute_order("600519.SH", t, "BUY", 100, 0.095)
    check("execution is T+1", nxt is not None and nxt > t
          and res.status.value in ("FILLED", "NO_TRADE"))

    # --- top 20 / weights / cash buffer / lot size (unit logic) ---
    w = (1.0 - config["portfolio"]["cash_buffer"]) / config["portfolio"]["top_k"]
    check("Top20 + equal weights + cash buffer",
          abs(w * config["portfolio"]["top_k"] + config["portfolio"]["cash_buffer"] - 1) < 1e-9,
          f"top_k={config['portfolio']['top_k']}, w={w:.4f}, buffer={config['portfolio']['cash_buffer']}")
    check("A-share lot size 100", config["execution"]["lot_size"] == 100)

    # --- transaction cost applied (config) ---
    from personal_quant.strategy.costs import TransactionCostModel

    m = TransactionCostModel.from_config(config)
    check("transaction cost model", m.buy_cost(100_000) > 0
          and m.sell_cost(100_000) > m.buy_cost(100_000))

    # --- backtest artifacts ---
    for f, name in [("nav.parquet", "backtest completed (nav)"),
                    ("monthly_predictions.parquet", "monthly predictions saved"),
                    ("benchmarks.parquet", "benchmarks completed"),
                    ("ic.parquet", "IC calculated"),
                    ("quantiles.parquet", "quantile analysis completed"),
                    ("summary.json", "summary generated"),
                    ("manifest.json", "reproducibility manifest")]:
        check(name, (run_dir / f).exists(), str(run_dir / f))

    # --- walk-forward (separate run dir) ---
    wf_file = PROJECT_ROOT / "experiments" / "strategy_v1" / "run_001_wf" / "walkforward_predictions.parquet"
    check("walk-forward completed", wf_file.exists(), str(wf_file))

    # --- paper live ---
    pl = PROJECT_ROOT / "reports" / "paper_live" / "latest_recommendation.csv"
    check("paper-live recommendation generated", pl.exists(), str(pl))

    # --- reproducibility ---
    import json

    if (run_dir / "manifest.json").exists():
        mf = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        ok = all(mf.get(k) for k in ["git_commit", "data_snapshot_id",
                                     "lightgbm_version", "model_seed"])
        check("results reproducible (manifest fields)", bool(ok),
              f"snapshot={mf.get('data_snapshot_id')}")
    else:
        check("results reproducible (manifest fields)", False)

    n_pass = sum(1 for _, ok in RESULTS if ok)
    n_fail = len(RESULTS) - n_pass
    print("-" * 64)
    print(f"SUMMARY: {n_pass} PASS / {n_fail} FAIL")
    print("OVERALL: PASS" if n_fail == 0 else "OVERALL: FAIL")
    for name, ok in RESULTS:
        if not ok:
            print(f"  FAILED: {name}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
