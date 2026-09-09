# -*- coding: utf-8 -*-
"""News ablation: does news information add alpha over Alpha158?

    python scripts/news/run_news_ablation.py

Variants (same engine / split / params / costs / Top-20 / T+1 — only the
feature set changes):
  A  Alpha158 only                    (STEP 4 anchor, must reproduce 0.2475)
  B  Alpha158 + factor_pack_v1        (STEP 4 anchor, must reproduce 0.1962)
  C  Alpha158 + news rule factors     (= N1)
  D  Alpha158 + news LLM factors      (= N2; when the LLM tier is disabled
     D degenerates to A — recorded, never faked)
  E  Alpha158 + factor_pack_v1 + news (= N3)
plus the finer news ablation (spec 45): count/sentiment/novelty/
attention/risk/event-type/llm/rule-only/combined subsets.

A/B must match the STEP 4 results (0.2475 / 0.1962) — differences beyond
floating noise are reported and explained.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

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

from factors.base import load_factor_data
from factors.normalization import fill_missing, normalize_panel
from factors.registry import FACTOR_REGISTRY, FACTORS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ABL = PROJECT_ROOT / "experiments" / "news" / "ablation"
STEP4_A = (0.247518, 0.942932)   # frozen STEP 4 anchors
STEP4_B = (0.196159, 0.748449)


def load_strategy_config():
    import yaml

    return yaml.safe_load(
        (PROJECT_ROOT / "config" / "strategy_v1.yaml").read_text(
            encoding="utf-8"))


def load_news_pack() -> dict:
    p = PROJECT_ROOT / "experiments" / "news" / "news_factor_run_001" / \
        "factor_pack_news_v1.json"
    return json.loads(p.read_text(encoding="utf-8"))


def load_step4_pack() -> dict:
    p = PROJECT_ROOT / "experiments" / "factors" / "factor_run_001" / \
        "factor_pack_v1.json"
    return json.loads(p.read_text(encoding="utf-8"))


def news_subsets(selected: list) -> dict:
    def has(n, kw):
        return any(k in n for k in kw)

    return {
        "N_count": [n for n in selected if has(n, ("_count",))],
        "N_sentiment": [n for n in selected if has(
            n, ("sentiment", "positive_negative", "event_sentiment_shock"))],
        "N_novelty": [n for n in selected if has(n, ("novel",))],
        "N_attention": [n for n in selected if has(n, ("attention", "shock"))],
        "N_risk": [n for n in selected if has(
            n, ("risk", "regulatory_event"))],
        "N_eventtype": [n for n in selected if has(
            n, ("buyback", "shareholder_change", "earnings_event",
                "major_event"))],
        "N_llm": [n for n in selected if has(n, ("llm_confidence",))],
        "N_rule_all": [n for n in selected if not has(n, ("llm_confidence",))],
        "N_combined": selected,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default="A,B,C,D,E")
    ap.add_argument("--finer", action="store_true")
    args = ap.parse_args()

    config = load_strategy_config()
    ts = config["time_split"]
    cost_model = TransactionCostModel.from_config(config)
    init_qlib_with_canonical()

    news_pack = load_news_pack()
    step4_pack = load_step4_pack()
    news_sel = news_pack["selected"]
    print("news pack selected:", news_sel)

    variants = {
        "A": [],
        "B": step4_pack["selected"],
        "C": news_sel,
        "D": [n for n in news_sel if "llm" in n],
        "E": step4_pack["selected"] + news_sel,
    }
    if args.finer:
        variants.update({k: v for k, v in news_subsets(news_sel).items()})
    wanted = [v.strip() for v in args.variants.split(",")]
    if args.finer:
        wanted = list(variants)

    train_dates = rebalance_dates(ts["train"][0], ts["train"][1])
    valid_dates = rebalance_dates(ts["valid"][0], ts["valid"][1])
    test_dates = rebalance_dates(ts["test"][0], ts["test"][1])
    all_dates = sorted(set(train_dates + valid_dates + test_dates))

    instruments = sorted({s for d in all_dates
                          for s in build_universe(d, config)["symbol"]})
    feats = compute_features(instruments, all_dates, cache=True)
    labels = compute_labels(instruments, all_dates, 20)
    date_universes = {d: build_universe(d, config)["symbol"].tolist()
                      for d in all_dates}
    print(f"[news-ablation] {len(all_dates)} dates, "
          f"{len(instruments)} instruments")

    data = load_factor_data("2014-06-01", ts["test"][1])
    all_custom = sorted({f for names in variants.values() for f in names})

    def custom_columns(features):
        out = {d: [] for d in all_dates}
        for name in features:
            panel = FACTORS[name](data, dates=list(pd.DatetimeIndex(all_dates)))
            panel = panel.reindex(pd.DatetimeIndex(all_dates))
            if FACTOR_REGISTRY[name]["category"] == "news":
                panel = fill_missing(normalize_panel(panel, "rank"), "drop",
                                     data.industries)
            else:
                panel = fill_missing(normalize_panel(panel, "rank"),
                                     "sector_median", data.industries)
            for d in all_dates:
                out[d].append(panel.loc[d].rename(name))
        return {d: pd.concat(cols, axis=1) for d, cols in out.items() if cols}

    custom = custom_columns(all_custom)

    results = {}
    for variant in wanted:
        names = variants[variant]
        out_dir = ABL / f"variant_{variant}"
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n===== variant {variant}: {names} =====", flush=True)

        def build(dates):
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

        train_df = build(train_dates)
        valid_df = build(valid_dates)
        model = AlphaModel(dict(config["model"]["params"]),
                           seed=config["model"]["seed"])
        fit = model.fit(
            train_df.drop(columns=["label", "date", "symbol"]),
            train_df["label"],
            valid_df.drop(columns=["label", "date", "symbol"]),
            valid_df["label"])
        model.save(out_dir / "model.txt")

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
                     model_version=f"news_{variant}")
        res.nav.to_frame("nav").to_parquet(out_dir / "nav.parquet")
        res.turnover.to_frame("turnover").to_parquet(out_dir / "turnover.parquet")

        summary = {
            "variant": variant,
            "custom_features": names,
            "strategy": mt.summarize(res.nav, None, res.turnover,
                                     len(res.trades), f"news_{variant}"),
            "ic": ic_by_period,
            "quantile_summary": quantile_summary(qa).to_dict("records"),
            "top_bottom_spread": top_bottom_spread(qa),
            "fit": fit,
        }
        with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, default=str)
        save_manifest(build_manifest(config, f"news_{variant}", extra={
            "variant": variant, "custom_features": names}), out_dir)
        results[variant] = summary
        s = summary["strategy"]
        print(f"  test: ann={s['annualized_return']:.4f} "
              f"sharpe={s['sharpe']:.3f} mdd={s['max_drawdown']:.4f} "
              f"IC={ic_by_period['test']['ic_mean']:.4f}", flush=True)

    rows = []
    for v, r in results.items():
        s = r["strategy"]
        rows.append({"variant": v, "ann_return": s["annualized_return"],
                     "sharpe": s["sharpe"],
                     "max_drawdown": s["max_drawdown"],
                     "turnover": s.get("avg"),
                     "ic_test": r["ic"]["test"]["ic_mean"],
                     "rankic_test": r["ic"]["test"]["rank_ic_mean"],
                     "icir_test": r["ic"]["test"]["icir"],
                     "valid_rmse": r["fit"]["valid_rmse"],
                     "n_custom": len(r["custom_features"])})
    comp = pd.DataFrame(rows)
    comp.to_csv(ABL / "comparison.csv", index=False)
    print("\n===== news ablation (frozen test 2024-2025) =====")
    print(comp.to_string(index=False))

    # A/B consistency vs the frozen STEP 4 anchors
    for v, anchor in (("A", STEP4_A), ("B", STEP4_B)):
        if v in results:
            s = results[v]["strategy"]
            drift = (abs(s["annualized_return"] - anchor[0]),
                     abs(s["sharpe"] - anchor[1]))
            ok = drift[0] < 0.002 and drift[1] < 0.02
            print(f"anchor {v}: ann {s['annualized_return']:.4f} vs "
                  f"{anchor[0]:.4f} (drift {drift[0]:.4f}), sharpe "
                  f"{s['sharpe']:.3f} vs {anchor[1]:.3f} -> "
                  f"{'CONSISTENT' if ok else 'DRIFT — see report'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
