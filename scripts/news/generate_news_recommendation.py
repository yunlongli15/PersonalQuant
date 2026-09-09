# -*- coding: utf-8 -*-
"""strategy_v1_news paper-live recommendation (research only).

    python scripts/news/generate_news_recommendation.py --date 2026-09-04

Same flow as strategy_v1's paper live, with the news feature set (Alpha158
+ factor_pack_v1 + news factors). Writes
reports/paper_live/latest_recommendation_news.csv.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "experiments" / "news" / "strategy"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--capital", type=float, default=500_000.0)
    args = ap.parse_args()

    import yaml

    config = yaml.safe_load((PROJECT_ROOT / "config" / "strategy_v1.yaml")
                            .read_text(encoding="utf-8"))
    news_cfg = yaml.safe_load((PROJECT_ROOT / "config"
                               / "strategy_v1_news.yaml")
                              .read_text(encoding="utf-8"))
    from personal_quant.strategy.qlib_provider import init_qlib_with_canonical

    init_qlib_with_canonical()
    signal_date = pd.Timestamp(args.date)

    model_path = OUT_DIR / "model.txt"
    if not model_path.exists():
        print("ERROR: no news strategy model — run run_news_strategy.py")
        return 1

    from personal_quant.strategy.features import compute_features, flatten_columns
    from personal_quant.strategy.model import AlphaModel
    from personal_quant.strategy.recommendation import generate_recommendation
    from personal_quant.strategy.universe import build_universe

    config["universe"]["st_filter"]["enabled"] = True
    universe = build_universe(signal_date, config)
    feats = compute_features(universe["symbol"].tolist(), [signal_date],
                             cache=False)
    f = feats.get(signal_date)
    if f is None or f.empty:
        print("ERROR: no features for the date")
        return 1
    f = flatten_columns(f)

    import json

    from factors.base import load_factor_data
    from factors.normalization import fill_missing, normalize_panel
    from factors.registry import FACTOR_REGISTRY, FACTORS

    # the feature set is the FROZEN packs (same as the trained model)
    step4_pack = json.loads((PROJECT_ROOT / "experiments" / "factors"
                             / "factor_run_001" / "factor_pack_v1.json")
                            .read_text(encoding="utf-8"))
    news_pack = json.loads((PROJECT_ROOT / "experiments" / "news"
                            / "news_factor_run_001"
                            / "factor_pack_news_v1.json")
                           .read_text(encoding="utf-8"))
    custom_features = step4_pack["selected"] + news_pack["selected"]
    data = load_factor_data("2014-06-01", "2026-12-31")
    for name in custom_features:
        panel = FACTORS[name](data, dates=[signal_date])
        panel = panel.reindex(pd.DatetimeIndex([signal_date]))
        if FACTOR_REGISTRY[name]["category"] == "news":
            panel = fill_missing(normalize_panel(panel, "rank"), "drop",
                                 data.industries)
        else:
            panel = fill_missing(normalize_panel(panel, "rank"),
                                 "sector_median", data.industries)
        f = f.join(panel.loc[signal_date].rename(name), how="left")

    model = AlphaModel.load(model_path, dict(config["model"]["params"]),
                            seed=config["model"]["seed"])

    def predictor(date, symbols):
        sub = f.reindex(symbols).dropna(how="all")
        if sub.empty:
            return pd.Series(dtype=float)
        return model.predict_series(sub[model.feature_columns], sub.index)

    rec = generate_recommendation(
        signal_date, config, predictor, args.capital,
        model_version="strategy_v1_news",
    )
    out_dir = PROJECT_ROOT / "reports" / "paper_live"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "latest_recommendation_news.csv"
    rec.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"\n===== PAPER LIVE (strategy_v1_news, research only) =====")
    print(rec.to_string(index=False))
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
