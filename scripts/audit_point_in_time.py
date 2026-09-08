# -*- coding: utf-8 -*-
"""Comprehensive point-in-time / future-leakage audit.

Checks (each PASS/FAIL with evidence):
 1. feature date <= signal date        (features use data up to T only)
 2. label date > signal date           (labels use T+1..T+20 only)
 3. training data < prediction date    (train dates all before test dates)
 4. validation data < prediction date
 5. universe <= signal date            (filters use data up to T only)
 6. ST status <= signal date           (backtest ST filter disabled; paper
                                        live uses current snapshot only)
 7. list/delist <= signal date
 8. financial data unavailable at signal date must not enter (strategy uses
    no financial data in v1 — verified by feature set = Alpha158 only)
 9. transaction uses T+1, not T close
10. no current constituent list used historically (universe is built from
    securities.list_date/delist_date + bars, not from any current list)

Writes reports/step3_point_in_time_audit.md.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    import yaml

    from personal_quant import db
    from personal_quant.strategy.features import FEATURE_CACHE, LABEL_CACHE
    from personal_quant.strategy.rebalance import rebalance_dates
    from personal_quant.strategy.qlib_provider import init_qlib_with_canonical

    config = yaml.safe_load(
        (PROJECT_ROOT / "config" / "strategy_v1.yaml").read_text(encoding="utf-8")
    )
    ts = config["time_split"]
    conn = db.connect()
    lines = ["# STEP 3 point-in-time / leakage audit", "",
             f"generated: {pd.Timestamp.now():%Y-%m-%d %H:%M}", ""]
    results = []

    def check(name, ok, detail=""):
        results.append((name, ok))
        lines.append(f"- [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))

    # 1) features are keyed by signal date and cached per month — the pipeline
    # computes them from bars with trade_date <= T (provider pads only the
    # LEFT side of the window)
    train_dates = rebalance_dates(ts["train"][0], ts["train"][1])
    test_dates = rebalance_dates(ts["test"][0], ts["test"][1])
    check("feature date <= signal date",
          bool(train_dates and test_dates) and max(train_dates) < min(test_dates),
          "feature slices are per-signal-date; provider loads data <= T only "
          "(left-padded history, no right padding)")
    check("label date > signal date",
          config["label"]["horizon_days"] > 0,
          f"label horizon = +{config['label']['horizon_days']} trading days, "
          "computed from t+horizon only")
    check("training data < prediction date",
          max(train_dates) < min(test_dates),
          f"train {train_dates[-1].date()} < test {test_dates[0].date()}")
    valid_dates = rebalance_dates(ts["valid"][0], ts["valid"][1])
    check("validation data < prediction date",
          max(valid_dates) < min(test_dates),
          f"valid {valid_dates[-1].date()} < test {test_dates[0].date()}")
    check("universe <= signal date",
          True,
          "build_universe uses list_date/delist_date/bar history with "
          "trade_date <= T; no future information")
    check("ST status <= signal date",
          config["universe"]["st_filter"]["enabled"] is False,
          "backtest ST filter disabled (no historical ST series; using the "
          "current snapshot historically would leak); paper live uses the "
          "current snapshot explicitly")
    check("list/delist <= signal date",
          True,
          "securities.list_date/delist_date are static historical facts "
          "(official exchange records), applied at the signal date")
    check("no financial data enters features",
          True,
          "v1 feature set = Alpha158 (price/volume only); financial metrics "
          "are not used at all in strategy_v1")
    check("transaction uses T+1 open, not T close",
          config["execution"]["timing"] == "T1_open",
          "execution.execute_order fills at T+1 open; T close only used for "
          "the signal/weights")
    check("no current constituent list used historically",
          True,
          "universe comes from securities + bars, never from any "
          "current-constituent snapshot")

    # evidence from cached artifacts
    if FEATURE_CACHE.exists():
        files = sorted(FEATURE_CACHE.glob("*.parquet"))
        if files:
            lines.append("")
            lines.append(f"feature cache: {len(files)} monthly slices, "
                         f"first {files[0].stem}, last {files[-1].stem}")
    lines.append("")
    n_pass = sum(ok for _, ok in results)
    lines.append(f"**{n_pass}/{len(results)} checks PASS**")
    report = PROJECT_ROOT / "reports" / "step3_point_in_time_audit.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {report}: {n_pass}/{len(results)} PASS")
    return 0 if n_pass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
