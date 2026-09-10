# -*- coding: utf-8 -*-
"""STEP 6 portfolio studies (spec §31-§34).

**Selection protocol — PRE-SPECIFIED before any result was seen**
（写死在本文件里，先于所有实验结果；禁止看结果后改规则）:

  stage 1 (top_k  ∈ {10, 20, 30, 50}, P0): 选 research Sharpe 最大的 K，
          且 valid Sharpe >= 0.8 x research Sharpe（稳定性门）；并列按
          valid Sharpe。
  stage 2 (cash   ∈ {5%, 10%, 15%}, P0@K*): 同 stage 1 规则。
  stage 3 (methods P0-P6 @K*/cash*): 选 research Sharpe 最大的方法，且：
          (a) valid Sharpe >= 0.8 x research Sharpe；
          (b) 平均单边换手 <= 1.0；
          (c) research MDD >= P0 research MDD - 0.05。
          无方法通过 -> 保持 P0（如实记录）。
  stage 4 (frequency: monthly vs quarterly, stage-3 前 3 名):
          只有 chosen 方法 research 与 valid 的 quarterly Sharpe 都
          >= 0.9 x 对应 monthly Sharpe 时采用 quarterly，否则 monthly。
  stage 5 (frozen test 2024-2025): 7 方法 x 最终参数单次评估（只记录，
          绝不用于选择）。
  stage 6 (signals s1/s2/s3 x stage-3 选定方法): research+valid 对比 +
          test 单次（S3 已在 STEP 5 增量检查中冻结；本阶段只是记录）。

所有运行：同引擎/同执行/同成本；每阶段只变化该阶段列出的参数。
选择只用 research 2018-2021 + valid 2022-2023；2024-2025 冻结。

    python scripts/portfolio/run_portfolio_study.py --stage 1
    python scripts/portfolio/run_portfolio_study.py --stage all
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from research_portfolio import EXP_DIR, load_yaml, run_one

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SELECTION = EXP_DIR / "selection.json"
METHODS = ["equal_weight", "score_weight", "inverse_vol", "gmv", "mvo",
           "risk_parity", "turnover_aware"]
PERIODS = ("research", "valid")


def load_selection() -> dict:
    if SELECTION.exists():
        return json.loads(SELECTION.read_text(encoding="utf-8"))
    return {}


def save_selection(sel: dict):
    SELECTION.write_text(json.dumps(sel, indent=2, ensure_ascii=False,
                                    default=str), encoding="utf-8")


def row(result, signal, period, method, top_k, cash, sector_cap, quarterly,
        cov):
    m = result.metrics
    return {
        "signal": signal, "period": period, "method": method, "top_k": top_k,
        "cash_buffer": cash, "sector_cap": sector_cap,
        "quarterly": bool(quarterly), "cov": cov,
        "ann": m["annualized_return"], "sharpe": m["sharpe"],
        "mdd": m["max_drawdown"], "calmar": m["calmar"],
        "vol": m["annualized_volatility"], "turnover_avg": m["avg"],
        "fees": m["total_fees"], "avg_holdings": m["avg_holdings"],
        "eff_n": m["avg_effective_n"], "hhi": m["avg_hhi"],
        "ind_conc": m.get("avg_industry_concentration", float("nan")),
        "n_trades": m.get("n_trades", float("nan")),
    }


def run_pair(method, signal, top_k, cash, sector_cap, quarterly=False,
             cov="sample", method_params=None, verbose=True):
    """One method over research + valid; returns a list of metric rows.
    Existing artifacts (same parameters) are reused — reruns are cheap."""
    rows = []
    for period in PERIODS:
        rid = f"{signal}_{period}_{method}_k{top_k}_c{int(cash*100)}" \
              + ("_q" if quarterly else "")
        mpath = EXP_DIR / rid / "metrics.json"
        if mpath.exists():
            with open(mpath, encoding="utf-8") as f:
                m = json.load(f)
            rows.append(dict(row_from_metrics(m), signal=signal,
                             period=period, method=method, top_k=top_k,
                             cash_buffer=cash, sector_cap=sector_cap,
                             quarterly=bool(quarterly), cov=cov))
            continue
        res = run_one(method, period, signal, top_k=top_k,
                      cash_buffer=cash, sector_cap=sector_cap,
                      quarterly=quarterly, cov=cov, run_id=rid,
                      out_dir=EXP_DIR / rid, method_params=method_params)
        rows.append(row(res, signal, period, method, top_k, cash,
                        sector_cap, quarterly, cov))
    return rows


def row_from_metrics(m):
    return {
        "ann": m["annualized_return"], "sharpe": m["sharpe"],
        "mdd": m["max_drawdown"], "calmar": m["calmar"],
        "vol": m["annualized_volatility"], "turnover_avg": m["avg"],
        "fees": m["total_fees"], "avg_holdings": m["avg_holdings"],
        "eff_n": m["avg_effective_n"], "hhi": m["avg_hhi"],
        "ind_conc": m.get("avg_industry_concentration", float("nan")),
        "n_trades": m.get("n_trades", float("nan")),
    }


def gate_ok(r, v):
    return v["sharpe"] >= 0.8 * r["sharpe"]


def stage1(sel, portfolio_cfg):
    """top_k study on P0."""
    print("\n===== stage 1: top_k (P0, research+valid) =====", flush=True)
    cfg = portfolio_cfg["portfolio"]
    rows = []
    for k in cfg["studies"]["top_k_candidates"]:
        rows += run_pair("equal_weight", cfg["signal"], k,
                         cfg["constraints"]["cash_buffer"],
                         cfg["constraints"]["sector_cap"])
    df = pd.DataFrame(rows)
    df.to_csv(EXP_DIR / "study_1_topk.csv", index=False)
    r = df[df["period"] == "research"].set_index("top_k")
    v = df[df["period"] == "valid"].set_index("top_k")
    cands = [(k, r.loc[k, "sharpe"], v.loc[k, "sharpe"])
             for k in df["top_k"].unique() if gate_ok(r.loc[k], v.loc[k])]
    if cands:
        chosen = max(cands, key=lambda x: (x[1], x[2]))[0]
        rule = "argmax research sharpe, gate valid>=0.8*research"
    else:
        chosen = max(df["top_k"].unique(),
                     key=lambda k: r.loc[k, "sharpe"])
        rule = ("no K passes the stability gate -> research-sharpe max "
                "(gate violated, recorded honestly)")
    print(df.pivot_table(index="top_k", columns="period",
                         values=["sharpe", "ann", "mdd", "turnover_avg"])
          .round(4))
    print(f"stage1 chosen top_k={chosen} ({rule})")
    sel["stage1"] = {"chosen_top_k": int(chosen), "rule": rule,
                     "table": df.to_dict("records")}
    save_selection(sel)
    return chosen


def stage2(sel, portfolio_cfg, top_k):
    """cash buffer study on P0 @K*."""
    print("\n===== stage 2: cash buffer (P0 @K*) =====", flush=True)
    cfg = portfolio_cfg["portfolio"]
    rows = []
    for c in cfg["studies"]["cash_buffers"]:
        rows += run_pair("equal_weight", cfg["signal"], top_k, c,
                         cfg["constraints"]["sector_cap"])
    df = pd.DataFrame(rows)
    df.to_csv(EXP_DIR / "study_2_cash.csv", index=False)
    r = df[df["period"] == "research"].set_index("cash_buffer")
    v = df[df["period"] == "valid"].set_index("cash_buffer")
    cands = [(c, r.loc[c, "sharpe"], v.loc[c, "sharpe"])
             for c in df["cash_buffer"].unique() if gate_ok(r.loc[c], v.loc[c])]
    if cands:
        chosen = max(cands, key=lambda x: (x[1], x[2]))[0]
        rule = "argmax research sharpe, gate valid>=0.8*research"
    else:
        chosen = max(df["cash_buffer"].unique(),
                     key=lambda c: r.loc[c, "sharpe"])
        rule = ("no cash level passes the gate -> research-sharpe max "
                "(recorded honestly)")
    print(df.pivot_table(index="cash_buffer", columns="period",
                         values=["sharpe", "ann", "mdd", "turnover_avg"])
          .round(4))
    print(f"stage2 chosen cash={chosen} ({rule})")
    sel["stage2"] = {"chosen_cash": float(chosen), "rule": rule,
                     "table": df.to_dict("records")}
    save_selection(sel)
    return chosen


def stage3(sel, portfolio_cfg, top_k, cash):
    """method comparison (research+valid) @K*/cash*."""
    print("\n===== stage 3: methods (research+valid @K*/cash*) =====",
          flush=True)
    cfg = portfolio_cfg["portfolio"]
    rows = []
    for m in METHODS:
        params = dict(cfg["methods"].get(m, {}))
        rows += run_pair(m, cfg["signal"], top_k, cash,
                         cfg["constraints"]["sector_cap"],
                         method_params=params)
    df = pd.DataFrame(rows)
    df.to_csv(EXP_DIR / "study_3_methods.csv", index=False)
    r = df[df["period"] == "research"].set_index("method")
    v = df[df["period"] == "valid"].set_index("method")
    p0 = r.loc["equal_weight"]
    cands = [(m, r.loc[m, "sharpe"], v.loc[m, "sharpe"])
             for m in METHODS
             if gate_ok(r.loc[m], v.loc[m])
             and r.loc[m, "turnover_avg"] <= 1.0
             and r.loc[m, "mdd"] >= p0["mdd"] - 0.05]
    if cands:
        chosen = max(cands, key=lambda x: (x[1], x[2]))[0]
        rule = ("argmax research sharpe, gates: valid>=0.8x, "
                "turnover<=1.0, mdd>=P0-0.05")
    else:
        chosen = "equal_weight"
        rule = ("no method passes all gates -> P0 kept (recorded "
                "honestly)")
    print(df.pivot_table(index="method", columns="period",
                         values=["sharpe", "ann", "mdd", "turnover_avg"])
          .round(4))
    print(f"stage3 chosen method={chosen} ({rule})")
    sel["stage3"] = {"chosen_method": chosen, "rule": rule,
                     "table": df.to_dict("records")}
    save_selection(sel)
    return chosen


def stage4(sel, portfolio_cfg, top_k, cash):
    """monthly vs quarterly for the stage-3 top-3 methods."""
    print("\n===== stage 4: frequency (monthly vs quarterly) =====",
          flush=True)
    cfg = portfolio_cfg["portfolio"]
    study3 = pd.DataFrame(sel["stage3"]["table"])
    r3 = study3[(study3["period"] == "research") &
                (study3["method"] != "equal_weight")]
    top3 = r3.nlargest(3, "sharpe")["method"].tolist()
    if not top3:
        top3 = ["equal_weight"]
    rows = []
    for m in top3:
        params = dict(cfg["methods"].get(m, {}))
        rows += run_pair(m, cfg["signal"], top_k, cash,
                         cfg["constraints"]["sector_cap"], quarterly=True,
                         method_params=params)
    df = pd.DataFrame(rows)
    df.to_csv(EXP_DIR / "study_4_frequency.csv", index=False)
    chosen_freq = "monthly"
    notes = []
    for m in top3:
        mm = sel["stage3"]["table"]
        base = {p: next(x for x in mm
                        if x["method"] == m and x["period"] == p)
                for p in PERIODS}
        q = {p: next(x for x in df.to_dict("records")
                     if x["method"] == m and x["period"] == p)
             for p in PERIODS}
        ok = (q["research"]["sharpe"] >= 0.9 * base["research"]["sharpe"]
              and q["valid"]["sharpe"] >= 0.9 * base["valid"]["sharpe"])
        notes.append({"method": m, "quarterly_ok": ok,
                      "m_research_sharpe": base["research"]["sharpe"],
                      "q_research_sharpe": q["research"]["sharpe"],
                      "m_valid_sharpe": base["valid"]["sharpe"],
                      "q_valid_sharpe": q["valid"]["sharpe"]})
    if notes and all(n["quarterly_ok"] for n in notes):
        chosen_freq = "quarterly"
    print(df.pivot_table(index="method", columns="period",
                         values=["sharpe", "ann", "mdd", "turnover_avg"])
          .round(4))
    print(f"stage4 chosen frequency={chosen_freq}")
    sel["stage4"] = {"chosen_frequency": chosen_freq, "notes": notes,
                     "rule": ("quarterly iff all top-3 methods keep "
                              "research+valid sharpe >= 0.9x monthly"),
                     "table": df.to_dict("records")}
    save_selection(sel)
    return chosen_freq


def stage5(sel, portfolio_cfg, top_k, cash, freq):
    """Frozen test: single final evaluation of all 7 methods."""
    print("\n===== stage 5: frozen test single eval (2024-2025) =====",
          flush=True)
    cfg = portfolio_cfg["portfolio"]
    quarterly = freq == "quarterly"
    rows = []
    for m in METHODS:
        params = dict(cfg["methods"].get(m, {}))
        rid = f"s3_test_{m}_k{top_k}_c{int(cash*100)}"
        rid += "_q" if quarterly else ""
        res = run_one(m, "test", cfg["signal"], top_k=top_k,
                      cash_buffer=cash,
                      sector_cap=cfg["constraints"]["sector_cap"],
                      quarterly=quarterly, run_id=rid,
                      out_dir=EXP_DIR / rid, method_params=params)
        rows.append(row(res, cfg["signal"], "test", m, top_k, cash,
                        cfg["constraints"]["sector_cap"], quarterly,
                        cfg["risk"]["covariance"]))
    df = pd.DataFrame(rows)
    df.to_csv(EXP_DIR / "study_5_frozen_test.csv", index=False)
    print(df[["method", "ann", "sharpe", "mdd", "calmar", "turnover_avg",
              "eff_n", "ind_conc"]].round(4).to_string(index=False))
    sel["stage5"] = {"table": df.to_dict("records"),
                     "note": "single final evaluation — never used for "
                             "selection"}
    save_selection(sel)
    return df


def stage6(sel, portfolio_cfg, top_k, cash, freq):
    """Signal comparison s1/s2/s3 x the stage-3 chosen method."""
    print("\n===== stage 6: signal comparison =====", flush=True)
    cfg = portfolio_cfg["portfolio"]
    method = sel["stage3"]["chosen_method"]
    params = dict(cfg["methods"].get(method, {}))
    quarterly = freq == "quarterly"
    rows = []
    for s in ("s1", "s2", "s3"):
        for period in PERIODS + ("test",):
            rid = f"{s}_{period}_{method}_k{top_k}_c{int(cash*100)}"
            rid += "_q" if quarterly else ""
            res = run_one(method, period, s, top_k=top_k,
                          cash_buffer=cash,
                          sector_cap=cfg["constraints"]["sector_cap"],
                          quarterly=quarterly, run_id=rid,
                          out_dir=EXP_DIR / rid, method_params=params)
            rows.append(row(res, s, period, method, top_k, cash,
                            cfg["constraints"]["sector_cap"], quarterly,
                            cfg["risk"]["covariance"]))
    df = pd.DataFrame(rows)
    df.to_csv(EXP_DIR / "study_6_signals.csv", index=False)
    print(df.pivot_table(index="signal", columns="period",
                         values=["sharpe", "ann", "mdd"]).round(4))
    sel["stage6"] = {"table": df.to_dict("records"),
                     "note": "S3 frozen by the STEP 5 incremental check; "
                             "this stage records, never re-selects"}
    save_selection(sel)
    return df


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all",
                    help="1|2|3|4|5|6|all")
    args = ap.parse_args()

    portfolio_cfg = load_yaml(PROJECT_ROOT / "config" / "portfolio_v1.yaml")
    sel = load_selection()
    if not sel.get("protocol"):
        sel["protocol"] = (
            "PRE-SPECIFIED (scripts/portfolio/run_portfolio_study.py "
            "docstring): top_k/cash/method by research Sharpe with the "
            "valid>=0.8x gate (method also turnover<=1.0 and mdd>=P0-0.05); "
            "quarterly iff research+valid >= 0.9x monthly for the top-3 "
            "methods; test 2024-2025 evaluated once, never for selection.")
    save_selection(sel)

    want = set(args.stage.split(",")) if args.stage != "all" else \
        {"1", "2", "3", "4", "5", "6"}

    if "1" in want:
        k = stage1(sel, portfolio_cfg)
        sel = load_selection()
    else:
        k = sel.get("stage1", {}).get("chosen_top_k")
        if not k:
            print("ERROR: run stage 1 first"); return 1
    if "2" in want:
        c = stage2(sel, portfolio_cfg, k)
        sel = load_selection()
    else:
        c = sel.get("stage2", {}).get("chosen_cash")
        if not c:
            print("ERROR: run stage 2 first"); return 1
    if "3" in want:
        m = stage3(sel, portfolio_cfg, k, c)
        sel = load_selection()
    else:
        m = sel.get("stage3", {}).get("chosen_method")
        if not m:
            print("ERROR: run stage 3 first"); return 1
    if "4" in want:
        f = stage4(sel, portfolio_cfg, k, c)
        sel = load_selection()
    else:
        f = sel.get("stage4", {}).get("chosen_frequency")
        if not f:
            print("ERROR: run stage 4 first"); return 1
    if "5" in want:
        stage5(sel, portfolio_cfg, k, c, f)
    if "6" in want:
        stage6(sel, portfolio_cfg, k, c, f)
    print(f"\nselection so far: top_k={k} cash={c} method={m} "
          f"frequency={f}\n{SELECTION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
