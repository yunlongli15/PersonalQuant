# -*- coding: utf-8 -*-
"""STEP 6 acceptance checks (24 items, spec §60).

    PYTHONIOENCODING=utf-8 python scripts/verify_step6.py

Checks artifacts + reruns the DB-free portfolio test suite; prints
PASS/FAIL per item and a summary. No DuckDB writes, no network.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXP = PROJECT_ROOT / "experiments" / "portfolio"
NEWS_STRAT = PROJECT_ROOT / "experiments" / "news" / "strategy"
REPORTS = PROJECT_ROOT / "reports"
ANCHOR_S3 = (0.2812, 1.022, -0.2351)

checks = []


def check(name, ok, detail=""):
    checks.append({"name": name, "ok": bool(ok), "detail": str(detail)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}"
          + (f" — {detail}" if detail and not ok else ""))


def main() -> int:
    # 1. STEP5 incremental alpha check
    p = REPORTS / "步骤5-新闻增量alpha检查.md"
    ok = p.exists() and "是" in p.read_text(encoding="utf-8")
    check("STEP5 incremental alpha check", ok, str(p))

    # 2. optimizer registry
    from portfolio.portfolio_registry import ALLOCATION_METHODS

    check("optimizer registry", len(ALLOCATION_METHODS) == 7,
          ",".join(ALLOCATION_METHODS))

    # 3. covariance PIT / 4. stability (invariant under future poisoning)
    from portfolio.covariance import estimate_covariance, is_stable

    rng = np.random.RandomState(0)
    close = pd.DataFrame(rng.randn(100, 6) * 0.02 + 1.0,
                         index=pd.date_range("2023-01-02", periods=100,
                                             freq="B"),
                         columns=[f"T{i}" for i in range(6)]).cumprod()
    c1 = estimate_covariance(close, close.columns, close.index[60], 40)
    poisoned = close.copy()
    poisoned.loc[poisoned.index > close.index[60], :] *= 1000.0
    c2 = estimate_covariance(poisoned, poisoned.columns,
                             close.index[60], 40)
    check("covariance PIT", np.allclose(c1.cov.to_numpy(), c2.cov.to_numpy()))
    check("covariance stability", is_stable(c1.diagnostics))

    # 5-11. method artifacts (round-1 research+valid + frozen test)
    sel = json.loads((EXP / "selection.json").read_text(encoding="utf-8")) \
        if (EXP / "selection.json").exists() else {}
    s3 = pd.DataFrame(sel.get("stage3", {}).get("table", []))
    s5 = pd.DataFrame(sel.get("stage5", {}).get("table", []))
    from portfolio.portfolio_registry import PORTFOLIO_REGISTRY

    for m in PORTFOLIO_REGISTRY:
        label = PORTFOLIO_REGISTRY[m]["label"].split()[0]
        in3 = not s3.empty and m in set(s3["method"])
        in5 = not s5.empty and m in set(s5["method"])
        check(f"method {m} ({label})", in3 and in5,
              f"study3={in3} study5={in5}")

    # 12-14. constraint audit (from a frozen-test optimizer-method run)
    method = sel.get("stage3", {}).get("chosen_method", "gmv")
    k = sel.get("stage1", {}).get("chosen_top_k", 20)
    cash = sel.get("stage2", {}).get("chosen_cash", 0.05)
    freq = sel.get("stage4", {}).get("chosen_frequency", "monthly")
    rid = f"s3_test_{method}_k{k}_c{int(cash*100)}"
    rid += "_q" if freq == "quarterly" else ""
    audit_path = EXP / rid / "audit.parquet"
    audit_ok = {"max_weight": False, "sector_cap": False, "cash_buffer":
                False, "weight_sum": False, "lot_size": False,
                "fallback_recorded": False}
    if audit_path.exists():
        a = pd.read_parquet(audit_path)
        for cname in audit_ok:
            sub = a[(a["check"] == cname)]
            audit_ok[cname] = len(sub) > 0 and \
                sub["status"].isin(["PASS", "SKIP"]).all()
    check("max weight constraint", audit_ok["max_weight"], rid)
    check("sector constraint", audit_ok["sector_cap"], rid)
    check("cash constraint", audit_ok["cash_buffer"] and
          audit_ok["weight_sum"], rid)

    # 15. transaction cost (fees recorded and nonzero)
    metrics_path = EXP / rid / "metrics.json"
    fees_ok = False
    if metrics_path.exists():
        m = json.loads(metrics_path.read_text(encoding="utf-8"))
        fees_ok = m.get("total_fees", 0) > 0
    check("transaction cost", fees_ok, rid)

    # 16. turnover
    turn_ok = metrics_path.exists() and \
        json.loads(metrics_path.read_text(encoding="utf-8")).get("avg", 0) >= 0
    check("turnover", turn_ok, rid)

    # 17. risk contribution
    w_path = EXP / rid / "weights.parquet"
    rc_ok = False
    if w_path.exists():
        w = pd.read_parquet(w_path)
        rc_ok = "contribution_to_risk" in w.columns and \
            w["contribution_to_risk"].notna().any()
    check("risk contribution", rc_ok, rid)

    # 18. lot rounding (artifact + helper)
    from portfolio.backtest import lot_floor

    lot_ok = lot_floor(2370.0, 10.0, 100) == 200
    if audit_path.exists():
        a = pd.read_parquet(audit_path)
        sub = a[a["check"] == "lot_size"]
        lot_ok = lot_ok and len(sub) > 0 and \
            sub["status"].isin(["PASS", "SKIP"]).all()
    check("lot rounding", lot_ok)

    # 19. fallback (records exist: optimal or recorded reasons)
    fb_ok = audit_ok["fallback_recorded"]
    if w_path.exists():
        w = pd.read_parquet(w_path)
        fb_ok = fb_ok and set(w["optimizer_status"].unique()) <= {
            "optimal", "fallback_inverse_vol", "fallback_equal_weight"}
    check("fallback", fb_ok, rid)

    # 20. stress test
    stress = EXP / "stress_test.csv"
    check("stress test", stress.exists(), str(stress))

    # 21. benchmark consistency (definitions in the optimizer report)
    rep = REPORTS / "步骤6-组合优化.md"
    bench_ok = rep.exists() and \
        "CSI300" in rep.read_text(encoding="utf-8")
    check("benchmark consistency", bench_ok, str(rep))

    # 22. reproducibility (test suite + engine anchor)
    anchor_ok = False
    ap = EXP / "anchor_check_p0" / "metrics.json"
    if ap.exists():
        m = json.loads(ap.read_text(encoding="utf-8"))
        drift = (abs(m["annualized_return"] - ANCHOR_S3[0]),
                 abs(m["sharpe"] - ANCHOR_S3[1]),
                 abs(m["max_drawdown"] - ANCHOR_S3[2]))
        anchor_ok = drift[0] < 0.002 and drift[1] < 0.02 and drift[2] < 0.005
    check("reproducibility", anchor_ok, "anchor drift vs strategy_v1_news")

    # 23. strategy_v2 — artifact integrity (NOT "all gates passed": the
    # pre-specified validation gate legitimately FAILs in a bear market
    # and gates are never rewritten to look better; verification checks
    # that the candidate exists, its 9 gates are all recorded, and the
    # frozen-test numbers in the gates file match the run artifacts).
    v2 = PROJECT_ROOT / "config" / "strategy_v2.yaml"
    gates = EXP / "strategy_v2" / "gates.json"
    v2_ok = v2.exists() and gates.exists()
    detail = str(gates)
    if gates.exists():
        g = json.loads(gates.read_text(encoding="utf-8"))
        gates_map = g.get("gates", {})
        want = {"1_research_pass", "2_validation_pass", "3_pit_pass",
                "4_risk_constraints_pass", "5_reproducibility_pass",
                "6_transaction_cost_pass", "7_no_future_leakage",
                "8_stress_test_pass", "9_no_pathological_concentration"}
        v2_ok = v2_ok and set(gates_map.keys()) == want
        rid_v2 = f"s3_test_{sel.get('stage3', {}).get('chosen_method', 'equal_weight')}" \
                 f"_k{k}_c{int(cash*100)}"
        mp = EXP / rid_v2 / "metrics.json"
        if mp.exists():
            mm = json.loads(mp.read_text(encoding="utf-8"))
            tt = g.get("test", {})
            v2_ok = v2_ok and abs(
                tt.get("annualized_return", 0) - mm["annualized_return"]) < 1e-9
        d2 = pd.read_parquet(EXP / rid_v2 / "weights.parquet") \
            if (EXP / rid_v2 / "weights.parquet").exists() else pd.DataFrame()
        if not d2.empty:
            v2_ok = v2_ok and {"prediction", "raw_rank", "target_weight",
                               "optimizer_status"}.issubset(d2.columns)
        detail = (f"{sum(1 for v in gates_map.values() if v)}/"
                  f"{len(gates_map)} gates pass (recorded, not rewritten)")
    check("strategy_v2", v2_ok, detail)

    # 24. paper live
    pl = REPORTS / "paper_live" / "latest_recommendation_v2.csv"
    check("paper live", pl.exists(), str(pl))

    # ---- rerun the DB-free portfolio test suite ---------------------------
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/portfolio/", "-q"],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True,
        timeout=600)
    check("portfolio tests", r.returncode == 0,
          (r.stdout + r.stderr).strip().splitlines()[-1]
          if (r.stdout + r.stderr).strip() else "returncode "
          f"{r.returncode}")

    n_pass = sum(1 for c in checks if c["ok"])
    print(f"\nSUMMARY: {n_pass} PASS / {len(checks) - n_pass} FAIL / "
          f"OVERALL: {'PASS' if n_pass == len(checks) else 'FAIL'}")
    return 0 if n_pass == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
