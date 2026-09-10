# -*- coding: utf-8 -*-
"""Supplementary study: liquidity constraint (STEP 6 spec §47).

NOT part of the pre-specified selection protocol (selection was already
frozen from study stages 1-4). This is an additional risk-control check
requested by the spec: cap each position's target value at
`liquidity_frac x 20-day average amount` so a position cannot exceed a
share of what the stock actually trades.

Decision rule (stated before the numbers, applied unchanged):
  ENABLE liquidity_frac in strategy_v2 iff, on research + valid with the
  selected method,
    (a) research Sharpe with the cap >= research Sharpe without - 0.02,
    (b) turnover does not increase, and
    (c) the number of rebalances where the cap actually binds is > 0
        (otherwise the constraint is cosmetic and is left disabled, with
        the reason recorded).
Otherwise DISABLE and record the numbers.

    python scripts/portfolio/run_liquidity_study.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from research_portfolio import EXP_DIR, load_yaml, run_dir_id, run_one

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run(method, period, top_k, cash, liq, sel):
    rid = (run_dir_id("s3", period, method, top_k, cash)
           + f"_liq{int(liq*100) if liq else 0}")
    res = run_one(method, period, "s3", top_k=top_k, cash_buffer=cash,
                  sector_cap=sel["stage3"]["table"][0]["sector_cap"],
                  liquidity_frac=liq, run_id=rid, out_dir=EXP_DIR / rid)
    return res, rid


def main() -> int:
    sel = json.loads((EXP_DIR / "selection.json").read_text(
        encoding="utf-8"))
    k = sel["stage1"]["chosen_top_k"]
    cash = sel["stage2"]["chosen_cash"]
    method = sel["stage3"]["chosen_method"]
    print(f"selected: method={method} top_k={k} cash={cash}")

    rows = []
    artifacts = {}
    for liq in (None, 0.05):
        for period in ("research", "valid"):
            res, rid = run(method, period, k, cash, liq, sel)
            m = res.metrics
            artifacts[(liq, period)] = rid
            binding = 0
            wpath = EXP_DIR / rid / "weights.parquet"
            if wpath.exists():
                w = pd.read_parquet(wpath)
                if "liq_cap" in w.columns:
                    binding = int((w["target_weight"]
                                   >= w["liq_cap"].fillna(1.0) - 1e-9).sum())
            rows.append({"liquidity_frac": liq, "period": period,
                         "sharpe": m["sharpe"], "ann":
                         m["annualized_return"], "mdd": m["max_drawdown"],
                         "turnover": m["avg"], "max_top_weight":
                         m["max_top_weight"], "eff_n": m["avg_effective_n"],
                         "cap_binds_obs": binding})
    df = pd.DataFrame(rows)
    df.to_csv(EXP_DIR / "study_7_liquidity.csv", index=False)
    print(df.round(4).to_string(index=False))

    r0 = df[(df["liquidity_frac"].isna()) & (df["period"] == "research")] \
        .iloc[0]
    r1 = df[(df["liquidity_frac"] == 0.05) & (df["period"] == "research")] \
        .iloc[0]
    binds = bool(df[df["liquidity_frac"] == 0.05]["cap_binds_obs"].sum() > 0)
    a = r1["sharpe"] >= r0["sharpe"] - 0.02
    b = r1["turnover"] <= r0["turnover"] + 1e-9
    c = binds
    enable = bool(a and b and c)
    decision = {
        "enable_liquidity_frac": enable,
        "liquidity_frac": 0.05 if enable else None,
        "rule": ("research sharpe >= no-cap - 0.02 AND turnover not "
                 "increased AND cap binds at least once"),
        "checks": {"sharpe_ok": bool(a), "turnover_ok": bool(b),
                   "binds": bool(c)},
        "numbers": df.to_dict("records"),
    }
    (EXP_DIR / "liquidity_decision.json").write_text(
        json.dumps(decision, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8")
    print(f"\nliquidity decision: enable={enable} "
          f"(sharpe_ok={a}, turnover_ok={b}, binds={c})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
