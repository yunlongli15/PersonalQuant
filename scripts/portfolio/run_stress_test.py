# -*- coding: utf-8 -*-
"""Historical stress tests (STEP 6 spec §46).

Periods: 2020 (research nav), 2022 (valid nav), 2024 (test nav), plus the
largest-drawdown window of each period. For each window: max drawdown,
recovery time (peak -> recovery to the same peak), annualized volatility,
and the same for the equal-weight baseline (P0) for comparison.

Reads the study artifacts (navs already computed by
run_portfolio_study.py) — nothing is re-backtested here.

    python scripts/portfolio/run_stress_test.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from research_portfolio import EXP_DIR

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PERIOD_WINDOWS = {"research": ("2020-01-01", "2020-12-31"),
                  "valid": ("2022-01-01", "2022-12-31"),
                  "test": ("2024-01-01", "2024-12-31")}


def nav_path(signal, period, method, top_k, cash, quarterly):
    rid = f"{signal}_{period}_{method}_k{top_k}_c{int(cash*100)}"
    rid += "_q" if quarterly else ""
    p = EXP_DIR / rid / "nav.parquet"
    return p if p.exists() else None


def load_nav(p):
    s = pd.read_parquet(p)["nav"]
    s.index = pd.to_datetime(s.index)
    return s


def dd_window_stats(nav, lo, hi):
    sub = nav[(nav.index >= lo) & (nav.index <= hi)]
    if len(sub) < 5:
        return None
    peak = sub.cummax()
    dd = sub / peak - 1.0
    trough_i = int(dd.idxmin().tolist() if hasattr(dd.idxmin(), "tolist")
                   else dd.argmin())
    # recovery: first day after the trough where nav >= the trough's peak
    trough_peak = peak.iloc[:trough_i + 1].max()
    after = sub.iloc[trough_i:]
    recovered = after[after >= trough_peak]
    recovery_days = (int((recovered.index[0] - sub.index[trough_i]).days)
                     if len(recovered) else None)
    ret = sub.pct_change().dropna()
    return {
        "mdd": float(dd.min()),
        "trough_date": str(sub.index[trough_i].date()),
        "recovery_days": recovery_days,
        "ann_vol": float(ret.std(ddof=1) * np.sqrt(252)),
        "n_days": len(sub),
    }


def largest_dd_window(nav):
    peak = nav.cummax()
    dd = nav / peak - 1.0
    trough = dd.idxmin()
    # window: from the trough's peak to recovery
    peak_date = nav.loc[:trough].idxmax()
    after = nav.loc[trough:]
    recovered = after[after >= nav.loc[peak_date]]
    end = recovered.index[0] if len(recovered) else nav.index[-1]
    return peak_date, end


def main() -> int:
    sel_path = EXP_DIR / "selection.json"
    if not sel_path.exists():
        print("ERROR: selection.json missing — run the study first")
        return 1
    sel = json.loads(sel_path.read_text(encoding="utf-8"))
    k = sel["stage1"]["chosen_top_k"]
    cash = sel["stage2"]["chosen_cash"]
    method = sel["stage3"]["chosen_method"]
    freq = sel["stage4"]["chosen_frequency"]
    quarterly = freq == "quarterly"
    print(f"chosen: top_k={k} cash={cash} method={method} "
          f"frequency={freq}")

    rows = []
    for period, (lo, hi) in PERIOD_WINDOWS.items():
        for label, m in (("P0", "equal_weight"), ("chosen", method)):
            p = nav_path("s3", period, m, k, cash, quarterly)
            if p is None:
                print(f"WARNING: no nav for {period}/{m}")
                continue
            nav = load_nav(p)
            s = dd_window_stats(nav, lo, hi)
            if s:
                rows.append({"period": period, "window": f"{lo}..{hi}",
                             "method": label, **s})
            # largest drawdown window of the period
            lo2, hi2 = largest_dd_window(nav)
            s2 = dd_window_stats(nav, lo2, hi2)
            if s2:
                rows.append({"period": period,
                             "window": f"largest DD {str(lo2.date())}.."
                                       f"{str(hi2.date())}",
                             "method": label, **s2})
    df = pd.DataFrame(rows)
    out = EXP_DIR / "stress_test.csv"
    df.to_csv(out, index=False)
    print(df.round(3).to_string(index=False))
    print(f"\nwrote {out}")

    # headline comparison: chosen vs P0 on each named stress window
    print("\n===== stress headline: chosen vs P0 =====")
    for period, (lo, hi) in PERIOD_WINDOWS.items():
        pair = {}
        for label, m in (("P0", "equal_weight"), ("chosen", method)):
            p = nav_path("s3", period, m, k, cash, quarterly)
            if p is None:
                continue
            pair[label] = dd_window_stats(load_nav(p), lo, hi)
        if len(pair) == 2:
            print(f"{lo}..{hi}: P0 mdd={pair['P0']['mdd']:.3f} -> chosen "
                  f"mdd={pair['chosen']['mdd']:.3f} | recovery P0="
                  f"{pair['P0']['recovery_days']}d chosen="
                  f"{pair['chosen']['recovery_days']}d")
    return 0


if __name__ == "__main__":
    sys.exit(main())
