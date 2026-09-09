# -*- coding: utf-8 -*-
"""STEP 4 model ablation: does the factor research add alpha?

    python scripts/backtest_ablation.py [--variants A,A1,A2,A3,A4,C_full,C_res,D]

Variants (identical engine / split / params / costs / Top-20 / T+1 — ONLY
the feature set changes, per the STEP 4 spec):
  A       Alpha158 only (= strategy_v1, reproducibility anchor)
  A1      Alpha158 + valuation factors
  A2      Alpha158 + technical custom factors
  A3      Alpha158 + financial PIT factors
  A4 (=B) Alpha158 + all selected non-financial factors
  C_full  Alpha158 + all selected factors on the full universe
          (financial factors sector-median filled — the documented
          missing-neutral variant)
  C_res   Alpha158 + all selected factors, financial universe only
          (restriction applied at the predictor: non-financial-universe
          names score NaN, engine untouched)
  D       C_res + gated mined factors (research candidate ONLY)

Factor sets come from factor_pack_v1 (selection used research+valid only).
LightGBM params are the FROZEN strategy_v1 params — no tuning for looks.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from personal_quant.strategy import metrics as mt
from personal_quant.strategy.analysis import (ic_summary, quantile_analysis,
                                              quantile_summary,
                                              top_bottom_spread)
from personal_quant.strategy.backtest import MonthlyBacktest
from personal_quant.strategy.costs import TransactionCostModel
from personal_quant.strategy.features import compute_features, compute_labels
from personal_quant.strategy.features import flatten_columns
from personal_quant.strategy.model import AlphaModel, compute_ic
from personal_quant.strategy.qlib_provider import init_qlib_with_canonical
from personal_quant.strategy.rebalance import rebalance_dates
from personal_quant.strategy.reproducibility import build_manifest, save_manifest
from personal_quant.strategy.universe import build_universe

from factors.base import DERIVED, load_factor_data
from factors.normalization import fill_missing, normalize_panel
from factors.registry import FACTOR_REGISTRY, FACTORS

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ABL = PROJECT_ROOT / "experiments" / "factors" / "ablation"


def load_config():
    import yaml

    return yaml.safe_load(
        (PROJECT_ROOT / "config" / "strategy_v1.yaml").read_text(encoding="utf-8")
    )


def load_factor_cfg():
    import yaml

    return yaml.safe_load(
        (PROJECT_ROOT / "config" / "factor_research.yaml").read_text(
            encoding="utf-8")
    )["factor_research"]


def load_pack(run_id: str) -> dict:
    p = PROJECT_ROOT / "experiments" / "factors" / run_id / "factor_pack_v1.json"
    return json.loads(p.read_text(encoding="utf-8"))


def load_mined(run_id: str) -> list:
    p = PROJECT_ROOT / "experiments" / "factors" / run_id / "candidates.json"
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, dict):  # {expr: {metrics}} -> list with expr key
        return [{"expr": k, **v} for k, v in data.items()]
    return data


def is_financial(name: str) -> bool:
    meta = FACTOR_REGISTRY[name]
    return meta["pit"] and meta["source"].startswith("financial")


def variant_features(pack: dict, mined: list, pack_run: str) -> dict:
    """Variant -> list of custom factor names (mined: expression strings).

    Technical custom factors = factor_pack_v1 (selected on research+valid).
    Financial/valuation factors = the candidate sets with restricted
    coverage >= 0.2 (the pack itself selected no financial factor — the
    ablation still answers 'does financial info help?' with the candidate
    set, per the spec's A1/A3 design)."""
    import json

    sel = pack["selected"]
    min_cov = 0.2
    fin_all = [n for n in FACTOR_REGISTRY if is_financial(n)]
    ok_fin = []
    for n in fin_all:
        ev = json.loads((PROJECT_ROOT / "experiments" / "factors" / pack_run
                         / "evaluations" / f"{n}.json").read_text(
            encoding="utf-8"))
        if ev.get("restricted", {}).get("coverage", 0.0) >= min_cov:
            ok_fin.append(n)
    val = [f for f in ok_fin if FACTOR_REGISTRY[f]["category"] == "valuation"]
    fin = [f for f in ok_fin if f not in val]
    tech = sel  # the pack's technical selection
    mined_exprs = [c["expr"] for c in mined[:5]]
    return {
        "A": [],
        "A1": val,
        "A2": tech,
        "A3": fin,
        "A4": tech + val,
        "C_full": tech + val + fin,
        "C_res": tech + val + fin,
        "D": tech + val + fin + mined_exprs,
    }


def custom_columns(features, data, dates, financial_fill: str):
    """date -> DataFrame(symbol x custom factor columns), rank-normalized.

    financial_fill: 'drop' (restricted runs) or the missing method
    (full-universe runs with sector-median neutral fill).
    """
    out = {d: [] for d in dates}
    from factors.mining import eval_expr, parse

    for name in features:
        panel = None
        if name in FACTORS:
            panel = FACTORS[name](data, dates=list(pd.DatetimeIndex(dates)))
            panel = panel.reindex(pd.DatetimeIndex(dates))
            method = financial_fill if is_financial(name) else "sector_median"
            panel = fill_missing(normalize_panel(panel, "rank"), method,
                                 data.industries)
        else:  # mined expression
            expr = parse(name, 3)
            atom_panels = {}
            for a in expr.atoms():
                ap = FACTORS[a](data, dates=list(pd.DatetimeIndex(dates)))
                ap = ap.reindex(pd.DatetimeIndex(dates))
                ap = fill_missing(normalize_panel(ap, "rank"), financial_fill,
                                  data.industries)
                atom_panels[a] = ap
            panel = eval_expr(expr, atom_panels)
        panel = panel.rename_axis("date")
        for d in dates:
            col = panel.loc[d].rename(name)
            out[d].append(col)
    return {d: pd.concat(cols, axis=1) for d, cols in out.items()
            if cols}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default="A,A1,A2,A3,A4,C_full,C_res,D")
    ap.add_argument("--pack-run", default="factor_run_001")
    ap.add_argument("--mining-run", default="mining_run_001")
    ap.add_argument("--test-only", action="store_true",
                    help="skip retraining A (reuse run_001 artifacts)")
    args = ap.parse_args()
    variants = [v.strip() for v in args.variants.split(",")]

    config = load_config()
    fcfg = load_factor_cfg()
    ts = config["time_split"]
    cost_model = TransactionCostModel.from_config(config)
    init_qlib_with_canonical()

    pack = load_pack(args.pack_run)
    mined = load_mined(args.mining_run)
    feat_map = variant_features(pack, mined, args.pack_run)
    print("pack selected:", pack["selected"])
    print("ablation financial set:", feat_map["A3"])
    print("ablation valuation set:", feat_map["A1"])
    print("mined candidates:", [m["expr"] for m in mined][:5])

    train_dates = rebalance_dates(ts["train"][0], ts["train"][1])
    valid_dates = rebalance_dates(ts["valid"][0], ts["valid"][1])
    test_dates = rebalance_dates(ts["test"][0], ts["test"][1])
    all_dates = sorted(set(train_dates + valid_dates + test_dates))

    # ---- Alpha158 slices (cached from strategy_v1 runs) -------------------
    instruments = sorted({s for d in all_dates
                          for s in build_universe(d, config)["symbol"]})
    print(f"[ablation] {len(all_dates)} dates, {len(instruments)} instruments")
    feats = compute_features(instruments, all_dates, cache=True)
    labels = compute_labels(instruments, all_dates, 20)
    date_universes = {d: build_universe(d, config)["symbol"].tolist()
                      for d in all_dates}

    # ---- custom factor panels (all candidate columns, once) ----------------
    data = load_factor_data("2014-06-01", ts["test"][1])
    all_custom = sorted({f for names in feat_map.values() for f in names})
    custom_drop = custom_columns(all_custom, data, all_dates, "drop")
    custom_fill = custom_columns(all_custom, data, all_dates, "sector_median")
    print(f"[ablation] custom columns: {all_custom}")

    results = {}
    for variant in variants:
        if variant not in feat_map:
            print(f"WARNING: unknown variant {variant}, skipping")
            continue
        names = feat_map[variant]
        out_dir = ABL / f"variant_{variant}"
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n===== variant {variant}: {names} =====")

        def build(dates, custom, names):
            frames = []
            for d in dates:
                f = feats.get(d)
                if f is None or f.empty:
                    continue
                m = flatten_columns(f).copy()
                cc = custom.get(d)
                if cc is not None and not cc.empty:
                    keep = [c for c in names if c in cc.columns]
                    if keep:
                        m = m.join(cc[keep], how="left")
                lab = labels.get(d)
                if lab is None:
                    continue
                m["label"] = lab
                m = m.dropna(subset=["label"])
                univ = date_universes.get(d)
                if univ:
                    m = m[m.index.isin(univ)]
                m["date"] = d
                frames.append(m.reset_index())
            return pd.concat(frames, ignore_index=True) if frames else \
                pd.DataFrame(columns=["date", "symbol", "label"])

        custom = custom_fill if variant == "C_full" else custom_drop
        train_df = build(train_dates, custom, names)
        valid_df = build(valid_dates, custom, names)
        model = AlphaModel(dict(config["model"]["params"]),
                           seed=config["model"]["seed"])
        fit = model.fit(
            train_df.drop(columns=["label", "date", "symbol"]),
            train_df["label"],
            valid_df.drop(columns=["label", "date", "symbol"]),
            valid_df["label"],
        )
        model.save(out_dir / "model.txt")
        with open(out_dir / "fit_metrics.json", "w", encoding="utf-8") as f:
            json.dump({**fit, "variant": variant,
                       "custom_features": names}, f, indent=2, default=str)
        print(f"  fit: best_iteration={fit['best_iteration']} "
              f"train_rmse={fit['train_rmse']:.5f} "
              f"valid_rmse={fit['valid_rmse']:.5f}")

        # ---- predictions / IC on valid + test ------------------------------
        pred_frames = []
        for d in valid_dates + test_dates:
            f = feats.get(d)
            if f is None or f.empty:
                continue
            m = flatten_columns(f).copy()
            cc = custom.get(d)
            if cc is not None and not cc.empty:
                keep = [c for c in names if c in cc.columns]
                if keep:
                    m = m.join(cc[keep], how="left")
            lab = labels.get(d)
            if lab is None:
                continue
            m["label"] = lab
            m = m.dropna(subset=["label"])
            m["prediction"] = model.predict(m[model.feature_columns])
            m["date"] = d
            pred_frames.append(m.reset_index()[["date", "symbol",
                                               "prediction", "label"]])
        preds = pd.concat(pred_frames, ignore_index=True)
        preds.to_parquet(out_dir / "predictions.parquet")
        ic_df = compute_ic(preds)
        ic_df.to_parquet(out_dir / "ic.parquet")
        vs, ve, ts_, te_ = (pd.Timestamp(x) for x in (
            ts["valid"][0], ts["valid"][1], ts["test"][0], ts["test"][1]))
        ic_by_period = {
            "valid": ic_summary(ic_df[(ic_df["date"] >= vs) &
                                      (ic_df["date"] <= ve)], "valid"),
            "test": ic_summary(ic_df[(ic_df["date"] >= ts_) &
                                     (ic_df["date"] <= te_)], "test"),
        }
        qa = quantile_analysis(preds[preds["date"] >= vs])
        qa.to_parquet(out_dir / "quantiles.parquet")

        # ---- backtest (engine untouched; C_res restricts via predictor) ----
        feat_cache = {}
        for d in all_dates:
            f = feats.get(d)
            if f is None or f.empty:
                continue
            m = flatten_columns(f).copy()
            cc = custom.get(d)
            if cc is not None and not cc.empty:
                keep = [c for c in names if c in cc.columns]
                if keep:
                    m = m.join(cc[keep], how="left")
            feat_cache[d] = m

        if variant == "C_res":
            univ = pd.read_parquet(DERIVED / "universes.parquet")
            univ["date"] = pd.to_datetime(univ["date"])
            fin_sets = {pd.Timestamp(d): set(g["symbol"]) for d, g in
                        univ[univ["universe"] == "financial"].groupby("date")}

            def predictor(date, symbols):
                allowed = fin_sets.get(date, set())
                sub = feat_cache.get(date)
                if sub is None or sub.empty:
                    return pd.Series(dtype=float)
                ok = [s for s in symbols if s in allowed]
                m = sub.reindex(ok).dropna(how="all")
                if m.empty:
                    return pd.Series(dtype=float)
                return model.predict_series(m[model.feature_columns], m.index)
        else:
            def predictor(date, symbols):
                sub = feat_cache.get(date)
                if sub is None or sub.empty:
                    return pd.Series(dtype=float)
                m = sub.reindex(symbols).dropna(how="all")
                if m.empty:
                    return pd.Series(dtype=float)
                return model.predict_series(m[model.feature_columns], m.index)

        bt = MonthlyBacktest(config, cost_model, 1_000_000.0)
        res = bt.run(ts["test"][0], ts["test"][1], predictor,
                     model_version=f"ablation_{variant}",
                     feature_version="alpha158+custom")
        res.nav.to_frame("nav").to_parquet(out_dir / "nav.parquet")
        res.turnover.to_frame("turnover").to_parquet(out_dir / "turnover.parquet")
        res.predictions.to_parquet(out_dir / "monthly_predictions.parquet")

        summary = {
            "variant": variant,
            "custom_features": names,
            "strategy": mt.summarize(res.nav, None, res.turnover,
                                     len(res.trades), f"ablation_{variant}"),
            "ic": ic_by_period,
            "quantile_summary": quantile_summary(qa).to_dict("records"),
            "top_bottom_spread": top_bottom_spread(qa),
            "fit": fit,
        }
        with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, default=str)
        save_manifest(build_manifest(config, f"ablation_{variant}", extra={
            "variant": variant, "custom_features": names,
        }), out_dir)
        results[variant] = summary
        s = summary["strategy"]
        print(f"  test: ann={s['annualized_return']:.4f} "
              f"sharpe={s['sharpe']:.3f} mdd={s['max_drawdown']:.4f} "
              f"IC={ic_by_period['test']['ic_mean']:.4f}")

    # ---- comparison table ------------------------------------------------
    rows = []
    for v, r in results.items():
        s = r["strategy"]
        rows.append({
            "variant": v,
            "ann_return": s["annualized_return"],
            "sharpe": s["sharpe"],
            "max_drawdown": s["max_drawdown"],
            "turnover": s.get("avg"),
            "ic_test": r["ic"]["test"]["ic_mean"],
            "rankic_test": r["ic"]["test"]["rank_ic_mean"],
            "icir_test": r["ic"]["test"]["icir"],
            "valid_rmse": r["fit"]["valid_rmse"],
            "n_features": len(r["custom_features"]) + 158,
        })
    comp = pd.DataFrame(rows)
    comp.to_csv(ABL / "comparison.csv", index=False)
    print("\n===== ablation comparison (test 2024-2025) =====")
    print(comp.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
