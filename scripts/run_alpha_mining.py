# -*- coding: utf-8 -*-
"""Alpha mining run: shallow expression search over factor_pack_v1 atoms.

    python scripts/run_alpha_mining.py [--run-id mining_run_001]

Leakage contract (enforced):
- search + scoring: RESEARCH dates only (2018-2021)
- validation ranking: VALID dates only (2022-2023)
- test (2024-2025): evaluated exactly once at the end, reported only
- AlphaMiner.period_end = valid end — any attempt to score on later dates
  raises (tested in tests/factors/test_mining_leakage.py)
- snooping diagnostics record the number of candidates tested

Output: experiments/factors/<run-id>/ (beam.json, candidates.json,
snooping.json) + reports/mined_factors/<expr>.md with TRAIN/VALIDATION/TEST
sections. Mined candidates are research candidates (factor_pack_v2 pool),
never a production strategy.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from factors.base import DERIVED, load_factor_data
from factors.evaluator import ic_series
from factors.mining import AlphaMiner, parse
from factors.normalization import fill_missing, normalize_panel
from factors.registry import FACTOR_REGISTRY, FACTORS

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXP = PROJECT_ROOT / "experiments" / "factors"


def load_labels():
    labels = pd.read_parquet(DERIVED / "labels.parquet")
    return {int(h): g.pivot(index="date", columns="symbol", values="label")
            for h, g in labels.groupby("horizon")}


def load_universes():
    univ = pd.read_parquet(DERIVED / "universes.parquet")
    univ["date"] = pd.to_datetime(univ["date"])
    return {kind: {pd.Timestamp(d): sorted(s) for d, s in
                   univ[univ["universe"] == kind].groupby("date")["symbol"]}
            for kind in ("full", "financial")}


def mask_universe(panel: pd.DataFrame, universe: dict) -> pd.DataFrame:
    out = panel.copy()
    for d, syms in universe.items():
        if d in out.index:
            out.loc[d, out.columns.difference(syms)] = np.nan
    return out


def period_dates(cfg, period):
    from factors.base import cached_rebalance_dates

    ts = cfg["time_split"]
    lo, hi = ts[period]
    return cached_rebalance_dates(lo, hi)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="mining_run_001")
    ap.add_argument("--pack", default="factor_run_001",
                    help="experiment dir holding factor_pack_v1.json")
    args = ap.parse_args()

    import yaml

    cfg = yaml.safe_load(
        (PROJECT_ROOT / "config" / "factor_research.yaml").read_text(
            encoding="utf-8")
    )["factor_research"]
    pack_file = EXP / args.pack / "factor_pack_v1.json"
    if not pack_file.exists():
        print(f"ERROR: {pack_file} not found — run research_all_factors.py "
              f"first")
        return 1
    pack_names = json.loads(pack_file.read_text(encoding="utf-8"))["selected"]
    print(f"atom pool (factor_pack_v1): {pack_names}")

    labels = load_labels()
    universes = load_universes()
    r_dates = pd.DatetimeIndex(period_dates(cfg, "research"))
    v_dates = pd.DatetimeIndex(period_dates(cfg, "valid"))
    t_dates = pd.DatetimeIndex(period_dates(cfg, "test"))

    data = load_factor_data("2017-01-01", "2025-12-31")

    def atom_panel(name, dates):
        raw = FACTORS[name](data, dates=list(pd.DatetimeIndex(dates)))
        raw = raw.reindex(pd.DatetimeIndex(dates))
        return mask_universe(raw, universes["full"])

    # atom panels on research+valid (mining never sees test)
    atoms = {n: atom_panel(n, r_dates.union(v_dates)) for n in pack_names}
    pack_panels = {n: fill_missing(normalize_panel(
        atom_panel(n, r_dates), "rank"), "drop", data.industries)
        for n in pack_names}

    cfg_eff = dict(cfg)
    cfg_eff["missing"] = {"method": "drop"}
    miner = AlphaMiner(
        cfg_eff, atoms, r_dates,
        {h: labels[h] for h in cfg["labels"]["horizons"]},
        universe=universes["full"], industries=data.industries,
        period_end=pd.Timestamp(cfg["time_split"]["valid"][1]),
    )

    print(f"search: {miner.max_per_gen} candidates/generation, "
          f"beam {miner.beam_size}, depth <= {miner.depth_max}, "
          f"period_end {miner.period_end.date()}", flush=True)
    res = miner.search(pack_names, pack_panels)
    print(f"generation 1+2 tested {miner.n_candidates_tested} candidates; "
          f"best research score {res['best_research_score']:.3f} "
          f"(ICIR {res['best_research_icir']:.3f})", flush=True)

    ranked = miner.validate(res["beam"], v_dates,
                            {h: labels[h] for h in cfg["labels"]["horizons"]})
    gated = miner.gate(ranked, pack_panels, set(pack_names))
    print(f"validation-ranked: {len(ranked)}, gate-passed: {len(gated)}")
    top = (gated or ranked)[:miner.top_candidates]

    # ---- frozen test: single final evaluation (report only) ---------------
    for c in top:
        expr = parse(c["expr"], miner.depth_max)
        atom_t = {n: atom_panel(n, t_dates) for n in expr.atoms()}
        from factors.mining import eval_expr

        pt = eval_expr(expr, atom_t).reindex(t_dates)
        ic = ic_series(pt, labels[20].reindex(t_dates), min_stocks=30)
        s = ic["rank_ic"]
        c["test_icir"] = float(s.mean() / s.std(ddof=0)) if len(s) and \
            s.std(ddof=0) > 0 else None
        c["test_ic_mean"] = float(s.mean()) if len(s) else None
        c["test_n"] = int(len(s))
        c["test_turnover"] = None

    snooping = {
        "n_candidates_tested": miner.n_candidates_tested,
        "best_research_score": res["best_research_score"],
        "best_research_icir": res["best_research_icir"],
        "best_validation_icir": ranked[0]["valid_icir"] if ranked else None,
        "n_gate_passed": len(gated),
        "top_candidates": [{k: c.get(k) for k in
                            ("expr", "icir", "valid_icir", "test_icir",
                             "test_ic_mean", "coverage", "turnover",
                             "gate_reasons")}
                           for c in top],
    }
    run_dir = EXP / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "snooping.json").write_text(
        json.dumps(snooping, indent=2, ensure_ascii=False), encoding="utf-8")
    (run_dir / "beam.json").write_text(
        json.dumps(miner.score_log, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8")
    (run_dir / "candidates.json").write_text(
        json.dumps({c["expr"]: {k: c.get(k) for k in
                                ("icir", "valid_icir", "test_icir",
                                 "test_ic_mean", "coverage", "turnover",
                                 "stability", "gate_reasons")}
                    for c in top},
                   indent=2, ensure_ascii=False, default=str),
        encoding="utf-8")

    out_dir = PROJECT_ROOT / "reports" / "mined_factors"
    out_dir.mkdir(parents=True, exist_ok=True)
    for c in top:
        md = [f"# mined factor: `{c['expr']}`", "",
              f"run: {args.run_id} · {datetime.now().isoformat(timespec='seconds')}",
              "", "| period | rank-IC mean | rank-ICIR |",
              "| --- | --- | --- |",
              f"| TRAIN (2018-2021, search) | — | {c.get('icir')} |",
              f"| VALIDATION (2022-2023) | — | {c.get('valid_icir')} |",
              f"| TEST (2024-2025, frozen, single pass) | "
              f"{c.get('test_ic_mean')} | {c.get('test_icir')} |",
              "", f"coverage: {c.get('coverage')}  ·  "
              f"turnover: {c.get('turnover')}",
              "", "Status: RESEARCH CANDIDATE (factor_pack_v2 pool) — "
              "not a production strategy."]
        safe = c["expr"].replace("/", "_div_").replace("*", "_mul_")
        (out_dir / f"mined_{safe}.md").write_text("\n".join(md),
                                                  encoding="utf-8")
    print(f"wrote {run_dir} and {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
