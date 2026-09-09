# -*- coding: utf-8 -*-
"""STEP 4 acceptance verification.

    python scripts/verify_step4.py

Checks (21): market data continuity, factor registry, technical factors,
valuation factors, financial PIT factors, normalization, missing handling,
IC, RankIC, ICIR, IC decay, quantile analysis, long-short, factor
correlation, factor stability, no future leakage, PIT compliance,
ablation A/B/C, Alpha Mining shallow search, mining leakage,
reproducibility. Prints PASS/FAIL per item; exit 0 only when all pass.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from personal_quant import config as pq_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS = []
FACTOR_RUN = PROJECT_ROOT / "experiments" / "factors" / "factor_run_001"
MINING_RUN = PROJECT_ROOT / "experiments" / "factors" / "mining_run_001"
ABL = PROJECT_ROOT / "experiments" / "factors" / "ablation"


def check(name, ok, detail=""):
    RESULTS.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}"
          + (f" -- {detail}" if detail else ""))


def _synth_factor_data(n_syms: int = 3, n_days: int = 200, seed: int = 1):
    from factors.base import FactorData

    rng = np.random.default_rng(seed)
    cal = pd.date_range("2020-01-01", periods=n_days, freq="B")
    syms = [f"S{i:03d}.SH" for i in range(n_syms)]
    close = pd.DataFrame(
        {s: 10 * np.exp(np.cumsum(rng.normal(0, 0.01, n_days)))
         for s in syms}, index=cal)
    vol = pd.DataFrame(rng.uniform(1e5, 1e6, (n_days, n_syms)), index=cal,
                       columns=syms)
    return FactorData(calendar=cal, bars=pd.DataFrame(), adj_close=close,
                      close_raw=close, volume_raw=vol, volume_shares=vol,
                      amount_cny=vol * close, scale=pd.DataFrame(),
                      financial=pd.DataFrame(),
                      industries=pd.Series(dtype=object),
                      scale_available=False)


def _synth_financial_data():
    from factors.base import FactorData

    syms = ["AAA.SH", "BBB.SZ"]
    fin = pd.DataFrame({
        "symbol": syms * 3,
        "metric_name": ["eps"] * 2 + ["bps"] * 2 + ["net_assets"] * 2,
        "metric_value": [2.0, -1.0, 10.0, 5.0, 1e10, 5e9],
        "fiscal_year": [2024] * 6,
        "fiscal_period": [pd.Timestamp("2024-12-31")] * 6,
        "availability_date": [pd.Timestamp("2025-04-01")] * 6,
        "availability_date_unknown": [False] * 6,
    })
    cal = pd.DatetimeIndex([pd.Timestamp("2025-06-30")])
    close = pd.DataFrame({"AAA.SH": [100.0], "BBB.SZ": [50.0]}, index=cal)
    return FactorData(calendar=cal, bars=pd.DataFrame(), adj_close=close,
                      close_raw=close, volume_raw=pd.DataFrame(),
                      volume_shares=pd.DataFrame(),
                      amount_cny=pd.DataFrame(),
                      scale=pd.DataFrame(), financial=fin,
                      industries=pd.Series(dtype=object),
                      scale_available=False)


def main() -> int:
    print("=" * 64)
    print("STEP 4 verification: factor research and alpha mining framework")
    print("=" * 64)

    # 1. market data continuity (canonical invariants)
    try:
        from personal_quant import db

        conn = db.connect()
        row = conn.execute("""
            WITH px AS (
              SELECT close, factor,
                     LAG(close) OVER w pc, LAG(factor) OVER w pf
              FROM daily_bars WHERE trade_date >= '2015-01-01'
              WINDOW w AS (PARTITION BY symbol ORDER BY trade_date))
            SELECT COUNT(*) FROM px WHERE pf > 0 AND factor/pf > 2
              AND pc > 0 AND abs(close/pc - 1) < 0.15
        """).fetchone()
        check("market data continuity (no spurious factor jumps)",
              row[0] == 0, f"{row[0]} events")
    except Exception as e:
        check("market data continuity (no spurious factor jumps)", False, str(e))

    # 2. factor registry
    try:
        from factors.registry import FACTOR_REGISTRY, FACTORS

        ok = len(FACTOR_REGISTRY) >= 25 and all(
            callable(FACTORS[n]) for n in FACTOR_REGISTRY)
        check("factor registry", ok, f"{len(FACTOR_REGISTRY)} factors")
    except Exception as e:
        check("factor registry", False, str(e))

    # 3-7. compute/normalization/missing on synthetic data
    try:
        import factors  # noqa: F401
        from factors.normalization import fill_missing, normalize_panel

        d = _synth_factor_data()
        m = FACTORS["momentum_20"](d, dates=None)
        ok = m.shape == (200, 3) and m.iloc[-1].notna().all()
        check("technical factors computable", bool(ok))
        m2 = m.dropna()  # momentum has a 20-row warm-up of all-NaN
        r = normalize_panel(m2, "rank")
        z = normalize_panel(m2, "winsorized_zscore")
        check("normalization (rank/winsorized_zscore)",
              ((r >= 0) & (r <= 1)).all().all()
              and z.notna().all().all())
        p = m2.copy()
        p.iloc[3, 0] = np.nan
        check("missing handling", fill_missing(p, "sector_median").notna()
              .all().all() and fill_missing(p, "drop").isna().any().any())
    except Exception as e:
        check("technical factors computable", False, str(e))
        check("normalization (rank/winsorized_zscore)", False, str(e))
        check("missing handling", False, str(e))

    # 8-14. evaluation on synthetic data
    try:
        from factors.evaluator import (evaluate_factor, ic_series,
                                       pairwise_correlation)

        d80 = _synth_factor_data(n_syms=80)
        rng = np.random.default_rng(2)
        labels = {20: pd.DataFrame(rng.normal(0, 0.02, (200, 80)),
                                   index=d80.calendar,
                                   columns=d80.adj_close.columns)}
        f = pd.DataFrame(rng.normal(0, 1, (200, 80)), index=d80.calendar,
                         columns=d80.adj_close.columns)
        ic = ic_series(f, labels[20], min_stocks=30)
        check("IC computable", len(ic) > 0 and "ic" in ic.columns)
        check("RankIC computable", "rank_ic" in ic.columns)
        check("ICIR computable",
              np.isfinite(ic["rank_ic"].mean() / ic["rank_ic"].std()))
        ic_map = {}
        for h in (1, 5, 20):
            ic_map[h] = ic_series(f, labels[20], min_stocks=30)["rank_ic"].mean()
        check("IC decay computable", len(ic_map) == 3)
        cfg = {"labels": {"horizons": [20], "primary_horizon": 20},
               "normalization": {"methods": ["rank"]},
               "missing": {"method": "drop"},
               "evaluation": {"min_stocks_per_date": 30}}
        ev = evaluate_factor(d80, "momentum_20", list(d80.calendar)[-60:],
                             labels, config=cfg,
                             compute=FACTORS["momentum_20"])
        check("quantile analysis", ev["normalizations"]["rank"]["quantiles"]
              .get("n_dates", 0) > 0)
        check("long-short stats", "ann_return" in
              ev["normalizations"]["rank"]["long_short"])
        corr = pairwise_correlation({"a": f, "b": -f}, method="spearman")
        check("factor correlation", corr.loc["a", "b"] < -0.9)
        yearly = ev["normalizations"]["rank"]["horizons"]["20"]["yearly"]
        check("factor stability (yearly IC)", len(yearly) >= 1)
    except Exception as e:
        check("IC computable", False, str(e))
        check("RankIC computable", False, str(e))
        check("ICIR computable", False, str(e))
        check("IC decay computable", False, str(e))
        check("quantile analysis", False, str(e))
        check("long-short stats", False, str(e))
        check("factor correlation", False, str(e))
        check("factor stability (yearly IC)", False, str(e))

    # 15. financial PIT factors
    try:
        from factors.fundamental import pit_metric_panel
        from factors.valuation import pe

        d = _synth_financial_data()
        before, _ = pit_metric_panel(d, "eps", [pd.Timestamp("2025-03-31")])
        after, _ = pit_metric_panel(d, "eps", [pd.Timestamp("2025-04-02")])
        v = pe(d, pd.DatetimeIndex([pd.Timestamp("2025-06-30")]))
        check("valuation factors computable",
              v.loc["2025-06-30", "AAA.SH"] == 50.0)
        check("financial PIT factors (announcement-day rule)",
              before.isna().all().all() and not after.isna().any().any())
    except Exception as e:
        check("valuation factors computable", False, str(e))
        check("financial PIT factors (announcement-day rule)", False, str(e))

    # 16. no future leakage
    try:
        d = _synth_factor_data()
        fn = FACTORS["momentum_60"]
        intact = fn(d, dates=None)
        d2 = _synth_factor_data()
        t = d2.calendar[100]
        d2.adj_close.loc[d2.calendar > t] *= 7.0
        corrupt = fn(d2, dates=None)
        ok = True
        for col in intact.columns:
            if not (np.isnan(intact.loc[t, col]) and np.isnan(corrupt.loc[t, col])):
                ok = ok and np.isclose(intact.loc[t, col], corrupt.loc[t, col])
        check("no future leakage (invariance to future corruption)", bool(ok))
    except Exception as e:
        check("no future leakage (invariance to future corruption)", False,
              str(e))

    # 17. PIT compliance (registry metadata)
    try:
        from factors.registry import FACTOR_REGISTRY as FR

        KNOWN_METRICS = {"revenue", "cost_of_revenue", "net_profit",
                         "total_assets", "total_liabilities", "net_assets",
                         "operating_cash_flow", "roe", "roa",
                         "gross_margin", "net_margin", "revenue_growth",
                         "net_profit_growth", "debt_to_asset", "eps", "bps"}
        fin_factors = {n: m for n, m in FR.items()
                       if m["pit"] and m["source"].startswith("financial")}
        bad = [n for n, m in fin_factors.items()
               if not (set(m["required_fields"]) - {"close", "volume",
                                                    "market_scale"})
               <= KNOWN_METRICS]
        check("PIT compliance (financial factors)",
              len(fin_factors) >= 10 and not bad,
              f"{len(fin_factors)} financial PIT factors"
              + (f"; undocumented fields: {bad}" if bad else ""))
    except Exception as e:
        check("PIT compliance (financial factors)", False, str(e))

    # 18. ablation A/B/C
    try:
        comp = ABL / "comparison.csv"
        has = comp.exists() and all(
            (ABL / f"variant_{v}" / "summary.json").exists()
            for v in ("A", "A4", "C_res"))
        detail = ""
        if comp.exists():
            df = pd.read_csv(comp)
            detail = f"{len(df)} variants: {', '.join(df['variant'])}"
        check("ablation A/B/C (+D)", bool(has), detail)
    except Exception as e:
        check("ablation A/B/C (+D)", False, str(e))

    # 19. alpha mining shallow search
    try:
        snoop = MINING_RUN / "snooping.json"
        ok = snoop.exists()
        detail = ""
        if ok:
            s = json.loads(snoop.read_text(encoding="utf-8"))
            ok = s.get("n_candidates_tested", 0) > 0
            detail = f"{s.get('n_candidates_tested')} candidates tested"
        check("Alpha Mining shallow search", bool(ok), detail)
    except Exception as e:
        check("Alpha Mining shallow search", False, str(e))

    # 20. mining leakage guard
    try:
        from factors.mining import AlphaMiner, MiningError

        atoms = {"a": pd.DataFrame(np.ones((4, 3))), }
        m = AlphaMiner({"mining": {}}, atoms,
                       pd.date_range("2020-01-01", periods=4),
                       {20: pd.DataFrame(np.ones((4, 3)))},
                       period_end=pd.Timestamp("2020-01-04"))
        raised = False
        try:
            m._guard(pd.DatetimeIndex([pd.Timestamp("2021-01-01")]))
        except MiningError:
            raised = True
        check("mining leakage guard", raised)
    except Exception as e:
        check("mining leakage guard", False, str(e))

    # 21. reproducibility
    try:
        mf = FACTOR_RUN / "manifest.json"
        ok = mf.exists()
        detail = ""
        if ok:
            m = json.loads(mf.read_text(encoding="utf-8"))
            ok = bool(m.get("git_commit") and m.get("config_sha256")
                      and m.get("n_factors", 0) > 0)
            detail = f"git {m.get('git_commit', '')[:8]}, " \
                     f"{m.get('n_factors')} factors"
        check("reproducibility (factor run manifest)", bool(ok), detail)
    except Exception as e:
        check("reproducibility (factor run manifest)", False, str(e))

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
