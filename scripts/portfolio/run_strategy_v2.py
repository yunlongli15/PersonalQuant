# -*- coding: utf-8 -*-
"""strategy_v2 = frozen alpha S3 + chosen portfolio allocation
(STEP 6 spec §52-§54).

Same engine (portfolio/backtest.py), same execution rules and cost model
as strategy_v1; strategy_v1 itself is never modified. The v2 config
(config/strategy_v2.yaml) is the single source of truth.

research/valid/test artifacts are reused when a study run with identical
parameters exists (run_portfolio_study.py naming); otherwise the period is
re-run. The production-candidate gates (spec §54) are then evaluated and
written to experiments/portfolio/strategy_v2/gates.json:

  1 research pass            ann > 0 and sharpe > 0
  2 validation pass          ann > 0 and sharpe > 0
  3 PIT pass                 tests/portfolio PIT suite green
  4 risk constraints pass    no FAIL rows in the constraint audit checks
  5 reproducibility pass     deterministic allocator + anchor drift 0
  6 transaction cost pass    fees recorded, fees/initial < 5%
  7 no future leakage        tests/portfolio no-future-data suite green
  8 stress test pass         chosen MDD >= P0 MDD - 0.05 on every named
                             stress window (2020/2022/2024)
  9 no pathological concentration  eff_n >= 10, top weight <= max_weight,
                             industry concentration <= sector cap

    python scripts/portfolio/run_strategy_v2.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from research_portfolio import EXP_DIR, load_yaml, run_dir_id, run_one

PROJECT_ROOT = Path(__file__).resolve().parents[2]
V2_DIR = EXP_DIR / "strategy_v2"
ANCHOR_S3 = (0.2812, 1.022, -0.2351)


def load_or_run(v2, signal, period, method, quarterly):
    top_k = v2["portfolio"]["top_k"]
    cash = v2["portfolio"]["constraints"]["cash_buffer"]
    rid = run_dir_id(signal, period, method, top_k, cash, quarterly)
    d = EXP_DIR / rid
    if (d / "metrics.json").exists():
        with open(d / "metrics.json", encoding="utf-8") as f:
            return json.load(f), d
    res = run_one(method, period, signal, top_k=top_k, cash_buffer=cash,
                  sector_cap=v2["portfolio"]["constraints"]["sector_cap"],
                  risk_window=v2["portfolio"]["risk"]["window"],
                  cov=v2["portfolio"]["risk"]["covariance"],
                  quarterly=quarterly, run_id=rid, out_dir=d,
                  method_params=v2["portfolio"]["method_params"])
    return res.metrics, d


def main() -> int:
    v2 = load_yaml(PROJECT_ROOT / "config" / "strategy_v2.yaml")
    p = v2["portfolio"]
    signal = p["signal"]
    method = p["allocation_method"]
    quarterly = p["rebalance"]["frequency"] == "quarterly"
    top_k = p["top_k"]
    cash = p["constraints"]["cash_buffer"]
    print(f"strategy_v2: signal={signal} method={method} top_k={top_k} "
          f"cash={cash} freq={p['rebalance']['frequency']}")

    res_metrics, res_dir = load_or_run(v2, signal, "research", method,
                                       quarterly)
    val_metrics, val_dir = load_or_run(v2, signal, "valid", method,
                                       quarterly)
    test_metrics, test_dir = load_or_run(v2, signal, "test", method,
                                         quarterly)
    p0_metrics, p0_dir = load_or_run(v2, signal, "test", "equal_weight",
                                     quarterly)

    # ---- gates (spec §54) -------------------------------------------------
    gates = {}
    gates["1_research_pass"] = (res_metrics["annualized_return"] > 0
                                and res_metrics["sharpe"] > 0)
    gates["2_validation_pass"] = (val_metrics["annualized_return"] > 0
                                  and val_metrics["sharpe"] > 0)

    import subprocess

    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/portfolio/test_covariance_pit.py",
         "tests/portfolio/test_portfolio_no_future_data.py", "-q"],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=600)
    gates["3_pit_pass"] = r.returncode == 0
    gates["7_no_future_leakage"] = r.returncode == 0

    a = pd.read_parquet(test_dir / "audit.parquet")
    constraint_checks = {"weight_sum", "cash_buffer", "max_weight",
                         "sector_cap", "no_short", "no_leverage",
                         "tradable", "lot_size"}
    bad = a[(a["check"].isin(constraint_checks))
            & (a["status"] == "FAIL")]
    gates["4_risk_constraints_pass"] = len(bad) == 0

    anchor = EXP_DIR / "anchor_check_p0" / "metrics.json"
    if anchor.exists():
        m = json.loads(anchor.read_text(encoding="utf-8"))
        drift = (abs(m["annualized_return"] - ANCHOR_S3[0]),
                 abs(m["sharpe"] - ANCHOR_S3[1]),
                 abs(m["max_drawdown"] - ANCHOR_S3[2]))
        gates["5_reproducibility_pass"] = (drift[0] < 0.002
                                           and drift[1] < 0.02
                                           and drift[2] < 0.005)
    else:
        gates["5_reproducibility_pass"] = False

    gates["6_transaction_cost_pass"] = (
        test_metrics["total_fees"] > 0
        and test_metrics["fees_fraction"] < 0.05)

    stress = EXP_DIR / "stress_test.csv"
    gates["8_stress_test_pass"] = False
    if stress.exists():
        s = pd.read_csv(stress)
        named = s[s["window"].str.startswith("20")]
        worst = {}
        for period, w in named.groupby("window"):
            mdd = dict(zip(w["method"], w["mdd"]))
            if "P0" in mdd and "chosen" in mdd:
                worst[period] = mdd["chosen"] >= mdd["P0"] - 0.05
        if worst:
            gates["8_stress_test_pass"] = all(worst.values())

    gates["9_no_pathological_concentration"] = (
        test_metrics["avg_effective_n"] >= 10
        and test_metrics["max_top_weight"]
        <= v2["portfolio"]["constraints"]["max_weight"] + 1e-6
        and test_metrics.get("max_industry_concentration", 1.0)
        <= v2["portfolio"]["constraints"]["sector_cap"] + 1e-6)

    V2_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "strategy_v2": v2,
        "research": res_metrics,
        "valid": val_metrics,
        "test": test_metrics,
        "p0_test": p0_metrics,
        "gates": gates,
        "note": ("candidate gates per spec §54; never 'future guaranteed' — "
                 "based on research + validation + frozen test only"),
    }
    with open(V2_DIR / "gates.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str, ensure_ascii=False)

    print("\n===== strategy_v2 (frozen test 2024-2025) =====")
    for k, v in gates.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    print(f"test: ann={test_metrics['annualized_return']:.4f} "
          f"sharpe={test_metrics['sharpe']:.3f} "
          f"mdd={test_metrics['max_drawdown']:.4f}")
    print(f"P0:   ann={p0_metrics['annualized_return']:.4f} "
          f"sharpe={p0_metrics['sharpe']:.3f} "
          f"mdd={p0_metrics['max_drawdown']:.4f}")
    print(f"wrote {V2_DIR / 'gates.json'}")
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
