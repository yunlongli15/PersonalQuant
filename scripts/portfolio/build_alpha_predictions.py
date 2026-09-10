# -*- coding: utf-8 -*-
"""Research-period (2018-2021) OOS alpha predictions for the portfolio study.

The frozen alpha signal (S3 = Alpha158 + factor_pack_v1 + news) has
valid/test predictions from the production model (trained 2015-2021,
experiments/news/strategy/predictions.parquet). For portfolio METHOD
selection on the RESEARCH period (2018-2021) those predictions would be
in-sample, so this script produces OOS research predictions via ANNUAL
WALK-FORWARD (mirroring the STEP 3 quarterly-retrain precedent):

    predict year Y  ->  train on 2015..Y-2, early stopping on Y-1

The valid/test production models are NOT retouched — this only adds OOS
research-period predictions.

Honest limitation (recorded in the fit JSONs): news coverage starts 2018,
so models predicting 2018-2019 saw no news in their training windows and
cannot split on news columns (LightGBM ignores all-NaN training columns).
Models predicting 2020-2021 train on data that includes news. The
production model (trained 2015-2021) is unaffected.

S1/S2 research models are built the same way for the signal comparison
(spec §33). All-NaN-feature rows are excluded from the saved predictions
(same filter the frozen predictor applies at backtest time).

Outputs (experiments/news/strategy/):
  research_model_{signal}_{year}.txt
  research_predictions_{signal}.parquet
  research_fit_{signal}.json

    python scripts/portfolio/build_alpha_predictions.py
    python scripts/portfolio/build_alpha_predictions.py --signals s3
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

from personal_quant.strategy.features import compute_features, compute_labels
from personal_quant.strategy.features import flatten_columns
from personal_quant.strategy.model import AlphaModel
from personal_quant.strategy.qlib_provider import init_qlib_with_canonical
from personal_quant.strategy.rebalance import rebalance_dates
from personal_quant.strategy.universe import build_universe

from factors.base import load_factor_data
from factors.normalization import fill_missing, normalize_panel
from factors.registry import FACTOR_REGISTRY, FACTORS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT = PROJECT_ROOT / "experiments" / "news" / "strategy"

RESEARCH_YEARS = [2018, 2019, 2020, 2021]   # OOS research predictions
TRAIN_FROM = "2015-01-01"                   # rolling window start


def custom_names(signal: str) -> list:
    step4 = json.loads((PROJECT_ROOT / "experiments" / "factors"
                        / "factor_run_001" / "factor_pack_v1.json")
                       .read_text(encoding="utf-8"))
    news = json.loads((PROJECT_ROOT / "experiments" / "news"
                       / "news_factor_run_001" / "factor_pack_news_v1.json")
                      .read_text(encoding="utf-8"))
    if signal == "s1":
        return []
    if signal == "s2":
        return step4["selected"]
    return step4["selected"] + news["selected"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--signals", default="s1,s2,s3")
    args = ap.parse_args()

    import yaml

    config = yaml.safe_load((PROJECT_ROOT / "config" / "strategy_v1.yaml")
                            .read_text(encoding="utf-8"))
    init_qlib_with_canonical()

    year_dates = {y: (rebalance_dates(f"{y}-01-01", f"{y}-12-31"))
                  for y in RESEARCH_YEARS}
    train_dates = {y: rebalance_dates(TRAIN_FROM, f"{y-2}-12-31")
                   for y in RESEARCH_YEARS}
    es_dates = {y: rebalance_dates(f"{y-1}-01-01", f"{y-1}-12-31")
                for y in RESEARCH_YEARS}
    all_dates = sorted({d for y in RESEARCH_YEARS
                        for d in (train_dates[y] + es_dates[y]
                                  + year_dates[y])})
    instruments = sorted({s for d in all_dates
                          for s in build_universe(d, config)["symbol"]})
    date_universes = {d: build_universe(d, config)["symbol"].tolist()
                      for d in all_dates}
    print(f"{len(all_dates)} dates; {len(instruments)} instruments",
          flush=True)
    feats = compute_features(instruments, all_dates, cache=True)
    labels = compute_labels(instruments, all_dates, 20)

    data = load_factor_data("2014-06-01", f"{RESEARCH_YEARS[-1]}-12-31")
    signals = [s.strip() for s in args.signals.split(",")]
    for signal in signals:
        names = custom_names(signal)
        print(f"\n===== signal {signal}: {names} =====", flush=True)
        custom = {}
        for name in names:
            panel = FACTORS[name](data, dates=list(pd.DatetimeIndex(all_dates)))
            panel = panel.reindex(pd.DatetimeIndex(all_dates))
            if FACTOR_REGISTRY[name]["category"] == "news":
                panel = fill_missing(normalize_panel(panel, "rank"), "drop",
                                     data.industries)
            else:
                panel = fill_missing(normalize_panel(panel, "rank"),
                                     "sector_median", data.industries)
            for d in all_dates:
                custom.setdefault(d, []).append(panel.loc[d].rename(name))
        custom = {d: pd.concat(cols, axis=1) for d, cols in custom.items()}

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

        fits = {}
        pred_frames = []
        for y in RESEARCH_YEARS:
            train_df = build(train_dates[y])
            es_df = build(es_dates[y])
            model = AlphaModel(dict(config["model"]["params"]),
                               seed=config["model"]["seed"])
            fit = model.fit(train_df.drop(columns=["label", "date", "symbol"]),
                            train_df["label"],
                            es_df.drop(columns=["label", "date", "symbol"]),
                            es_df["label"])
            model.save(OUT / f"research_model_{signal}_{y}.txt")
            fits[str(y)] = {
                "train": [str(train_dates[y][0]), str(train_dates[y][-1])],
                "es": [str(es_dates[y][0]), str(es_dates[y][-1])],
                "fit": fit,
                "news_blind": bool("news" in signal
                                   and y <= RESEARCH_YEARS[0] + 1),
            }
            print(f"  [{signal}/{y}] valid_rmse={fit['valid_rmse']:.5f}"
                  f"{' (news-blind: no news in training window)'
                     if fits[str(y)]['news_blind'] else ''}",
                  flush=True)

            for d in year_dates[y]:
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
                m = m[~m[model.feature_columns].isna().all(axis=1)]
                m["prediction"] = model.predict(m[model.feature_columns])
                m["date"] = d
                pred_frames.append(m.reset_index()[["date", "symbol",
                                                   "prediction", "label"]])
        with open(OUT / f"research_fit_{signal}.json", "w",
                  encoding="utf-8") as f:
            json.dump({"signal": signal, "walk_forward_years": RESEARCH_YEARS,
                       "created": datetime.now().isoformat(timespec="seconds"),
                       "note": ("annual walk-forward: train 2015..Y-2, "
                                "early-stop Y-1, predict Y; models for "
                                "2018-2019 are news-blind (coverage starts "
                                "2018) — honest limitation"),
                       "fits": fits}, f, indent=2, default=str)
        preds = pd.concat(pred_frames, ignore_index=True)
        out_path = OUT / f"research_predictions_{signal}.parquet"
        preds.to_parquet(out_path)
        print(f"  wrote {out_path}: {len(preds):,} rows, "
              f"{preds['date'].nunique()} dates", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
