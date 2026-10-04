# -*- coding: utf-8 -*-
"""Full candidate-factor research run (factor_pack_v1 pipeline).

    python scripts/research_all_factors.py [--run-id factor_run_001]

Pipeline (the ordering enforces the no-test-set-selection rule):
1. research (2018-2021) + valid (2022-2023) evaluations for ALL factors
2. correlation matrix + clustering (research only)
3. factor_pack_v1 selection (research + valid only)
4. ONLY THEN: single frozen-test evaluation (2024-2025) for all factors
5. outputs: experiments/factors/<run-id>/ (evaluations, leaderboard, pack,
   correlation, dashboard, manifest) + reports/factors/*.md +
   reports/步骤4-财务因子覆盖率.md

2026 (paper live) never appears anywhere in this pipeline.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from factors.base import DERIVED, load_factor_data
from factors.evaluator import evaluate_factor, pairwise_correlation
from factors.registry import FACTOR_REGISTRY, FACTORS
from factors.reports import (dashboard_df, factor_report_md, leaderboard_df)
from factors.selection import select_factor_pack

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXP = PROJECT_ROOT / "experiments" / "factors"
REPORTS = PROJECT_ROOT / "reports" / "factors"


def load_shared(cfg: dict):
    labels = pd.read_parquet(DERIVED / "labels.parquet")
    labels = {int(h): g.pivot(index="date", columns="symbol", values="label")
              for h, g in labels.groupby("horizon")}
    univ = pd.read_parquet(DERIVED / "universes.parquet")
    univ["date"] = pd.to_datetime(univ["date"])
    universes = {
        kind: {pd.Timestamp(d): sorted(s) for d, s in
               univ[univ["universe"] == kind].groupby("date")["symbol"]}
        for kind in ("full", "financial")
    }
    return labels, universes


def period_dates(cfg: dict, period: str):
    from factors.base import cached_rebalance_dates

    ts = cfg["time_split"]
    if period == "research":
        lo, hi = ts["research"]
    elif period == "valid":
        lo, hi = ts["valid"]
    elif period == "test":
        lo, hi = ts["test"]
    else:
        raise ValueError(period)
    return cached_rebalance_dates(lo, hi)


def missing_method_for(cfg: dict, name: str) -> str:
    """Financial factors evaluate with drop (real values only) on the full
    universe — sector-median fill would fabricate coverage for stocks with
    no financial data. The sector-median variant is recorded separately.
    """
    meta = FACTOR_REGISTRY[name]
    if meta["pit"] and meta["source"].startswith("financial"):
        return "drop"
    return cfg["missing"]["method"]


def git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
            cwd=PROJECT_ROOT,
        ).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="factor_run_001")
    ap.add_argument("--only", default=None,
                    help="comma-separated factor subset (debugging)")
    args = ap.parse_args()

    import yaml

    cfg = yaml.safe_load(
        (PROJECT_ROOT / "config" / "factor_research.yaml").read_text(
            encoding="utf-8")
    )["factor_research"]
    labels, universes = load_shared(cfg)

    run_dir = EXP / args.run_id
    (run_dir / "evaluations").mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    names = sorted(FACTOR_REGISTRY)
    if args.only:
        names = [n for n in args.only.split(",") if n in FACTOR_REGISTRY]
    print(f"factors: {len(names)}")

    data = load_factor_data("2017-01-01", "2026-12-31")
    r_dates = period_dates(cfg, "research")
    v_dates = period_dates(cfg, "valid")
    t_dates = period_dates(cfg, "test")
    print(f"dates: research {len(r_dates)}, valid {len(v_dates)}, "
          f"test {len(t_dates)} (frozen)")

    research = {}
    valid = {}
    test = {}
    restricted = {}
    restricted_valid = {}

    # ---- 1. research + valid evaluation (selection information) ----------
    for i, name in enumerate(names):
        fn = FACTORS[name]
        meta = FACTOR_REGISTRY[name]
        mm = missing_method_for(cfg, name)
        cfg_eff = dict(cfg)
        cfg_eff["missing"] = {"method": mm}
        er = evaluate_factor(data, name, r_dates, labels,
                             universes["full"], cfg_eff, compute=fn)
        ev = evaluate_factor(data, name, v_dates, labels,
                             universes["full"], cfg_eff, compute=fn)
        research[name] = er
        valid[name] = ev
        if meta["pit"] and meta["source"].startswith("financial"):
            cfg_drop = dict(cfg)
            cfg_drop["missing"] = {"method": "drop"}
            restricted[name] = evaluate_factor(
                data, name, r_dates, labels, universes["financial"],
                cfg_drop, compute=fn)
            restricted_valid[name] = evaluate_factor(
                data, name, v_dates, labels, universes["financial"],
                cfg_drop, compute=fn)
        payload = {"research": er, "valid": ev}
        if name in restricted:
            payload["restricted"] = restricted[name]
            payload["restricted_valid"] = restricted_valid[name]
        with open(run_dir / "evaluations" / f"{name}.json", "w",
                  encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, default=str)
        print(f"[{i+1}/{len(names)}] {name}: research rank-ICIR(20d) "
              f"{er['normalizations']['rank']['horizons']['20']['rank_ic']['icir']:.3f}, "
              f"coverage {er['coverage']:.2f}", flush=True)

    # selection inputs: financial factors are selected on their RESTRICTED
    # (financial-universe) evaluations — their full-universe coverage is
    # capped at the financial-universe share by construction (~7%), so a
    # full-universe coverage gate would discard them all (documented in
    # factor_pack_v1.md); non-financial factors use the full universe
    research_sel = {n: (restricted.get(n) if n in restricted else research[n])
                    for n in names}
    valid_sel = {n: (restricted_valid.get(n) if n in restricted_valid
                     else valid[n]) for n in names}

    # ---- 2. correlation (research only) -----------------------------------
    from factors.normalization import fill_missing, normalize_panel

    panels = {}
    for n in names:
        raw = FACTORS[n](data, dates=list(pd.DatetimeIndex(r_dates)))
        raw = raw.reindex(pd.DatetimeIndex(r_dates))
        masked = raw.copy()
        for d, syms in universes["full"].items():
            if d in masked.index:
                masked.loc[d, masked.columns.difference(syms)] = np.nan
        panels[n] = fill_missing(normalize_panel(masked, "rank"), "drop",
                                 data.industries)
    corr = pairwise_correlation(panels, method="spearman")
    corr = corr.reindex(index=names, columns=names)
    corr.to_csv(run_dir / "correlation_matrix.csv")

    # ---- 3. factor_pack_v1 selection (research + valid ONLY) -------------
    # financial factors are selected on restricted-universe evaluations with
    # the restricted coverage threshold (their coverage ceiling is set by
    # data availability, not factor quality)
    cov_map = {n: float(cfg["selection"].get("min_coverage_restricted", 0.2))
               for n in restricted}
    pack = select_factor_pack(research_sel, valid_sel, corr, cfg,
                              min_coverage_map=cov_map)
    (run_dir / "factor_pack_v1.json").write_text(
        json.dumps(pack, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")
    print(f"\nfactor_pack_v1: selected {len(pack['selected'])} / "
          f"{pack['n_candidates']} candidates:")
    print("  " + ", ".join(pack["selected"]))
    for d in pack["discarded"]:
        print(f"  discarded {d['factor']}: {d['reason']}")

    # ---- 4. frozen test evaluation (single pass, never for selection) ----
    for name in names:
        mm = missing_method_for(cfg, name)
        cfg_eff = dict(cfg)
        cfg_eff["missing"] = {"method": mm}
        test[name] = evaluate_factor(data, name, t_dates, labels,
                                     universes["full"], cfg_eff,
                                     compute=FACTORS[name])
        payload = {"research": research[name], "valid": valid[name],
                   "test": test[name]}
        if name in restricted:
            payload["restricted"] = restricted[name]
            payload["restricted_valid"] = restricted_valid[name]
        with open(run_dir / "evaluations" / f"{name}.json", "w",
                  encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, default=str)

    # ---- 5. outputs --------------------------------------------------------
    lb = leaderboard_df(research, "research").merge(
        leaderboard_df(test, "test")[
            ["factor", "RankIC_test", "ICIR_test", "IC_pos_ratio_test"]],
        on="factor", how="left")
    lb = lb.sort_values("ICIR_research", ascending=False)
    lb.to_csv(run_dir / "leaderboard.csv", index=False)

    dash = dashboard_df({n: research[n] for n in names},
                        cfg["labels"]["horizons"])
    dash.to_parquet(run_dir / "factor_dashboard_data.parquet", index=False)

    for name in names:
        corr_row = corr.loc[name].drop(name).to_dict() if name in corr.index \
            else {}
        cluster = None
        for cl in pack["clusters"]:
            if name in cl:
                cluster = cl
        md = factor_report_md(name, {
            "research": research[name], "valid": valid[name],
            "test": test[name]}, cfg["labels"]["horizons"],
            corr_row=corr_row, cluster=cluster)
        (REPORTS / f"factor_report_{name}.md").write_text(md,
                                                          encoding="utf-8")

    pack_md = ["# factor_pack_v1", "",
               f"run: {args.run_id} · {datetime.now().isoformat(timespec='seconds')}",
               "", "## selected (research+valid only)", ""]
    for n in pack["selected"]:
        ric = research[n]["normalizations"]["rank"]["horizons"]["20"][
            "rank_ic"]["icir"]
        pack_md.append(f"- `{n}` ({FACTOR_REGISTRY[n]['category']}, "
                       f"research rank-ICIR {ric:.3f})")
    pack_md += ["", "## discarded", ""]
    for d in pack["discarded"]:
        pack_md.append(f"- `{d['factor']}`: {d['reason']}")
    (run_dir / "factor_pack_v1.md").write_text("\n".join(pack_md),
                                               encoding="utf-8")

    manifest = {
        "run_id": args.run_id,
        "created": datetime.now().isoformat(timespec="seconds"),
        "git_commit": git_commit(),
        "config_sha256": hashlib.sha256(
            (PROJECT_ROOT / "config" / "factor_research.yaml").read_bytes()
        ).hexdigest(),
        "scale_table": str(
            PROJECT_ROOT / "data" / "parquet" / "market" / "market_scale.parquet"),
        "scale_rows": len(data.scale),
        "scale_available": data.scale_available,
        "n_factors": len(names),
        "n_selected": len(pack["selected"]),
        "periods": {k: cfg["time_split"][k] for k in
                    ("research", "valid", "test")},
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8")

    print(f"\nwrote {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
