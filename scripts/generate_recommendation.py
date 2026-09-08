# -*- coding: utf-8 -*-
"""Paper-live recommendation (research only — no real trading).

    python scripts/generate_recommendation.py --date 2026-09-04 --capital 500000

Uses the strategy_v1 model trained on the fixed train/valid split (the same
model as the run_001 backtest). Outputs reports/paper_live/
latest_recommendation.csv + a human-readable summary.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_config():
    import yaml

    return yaml.safe_load(
        (PROJECT_ROOT / "config" / "strategy_v1.yaml").read_text(encoding="utf-8")
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="signal date (latest trading day)")
    ap.add_argument("--capital", type=float, default=500_000.0)
    ap.add_argument("--model", default=None,
                    help="path to model.txt (default: latest experiment model)")
    args = ap.parse_args()

    config = load_config()
    from personal_quant.strategy.qlib_provider import init_qlib_with_canonical

    init_qlib_with_canonical()
    signal_date = pd.Timestamp(args.date)

    # locate the latest experiment model
    exp_dir = PROJECT_ROOT / "experiments" / "strategy_v1"
    model_path = Path(args.model) if args.model else None
    if model_path is None:
        candidates = sorted(exp_dir.glob("run_*/model.txt"))
        if not candidates:
            print("ERROR: no trained model found; run scripts/backtest_strategy.py first")
            return 1
        model_path = candidates[-1]
    print(f"using model: {model_path}")

    from personal_quant.strategy.features import compute_features
    from personal_quant.strategy.model import AlphaModel
    from personal_quant.strategy.recommendation import generate_recommendation
    from personal_quant.strategy.universe import build_universe

    # paper live applies the current-snapshot ST filter (documented in the
    # config note: the filter is off for historical backtests because no
    # historical ST series exists, but the current snapshot is trustworthy)
    config["universe"]["st_filter"]["enabled"] = True
    universe = build_universe(signal_date, config)
    print(f"universe at {signal_date.date()}: {len(universe)} stocks "
          f"(ST filter ON, current snapshot)")

    feats = compute_features(universe["symbol"].tolist(), [signal_date], cache=False)
    f = feats.get(signal_date)
    if f is None or f.empty:
        print("ERROR: no features available for the date")
        return 1
    from personal_quant.strategy.features import flatten_columns

    f = flatten_columns(f)
    model = AlphaModel.load(model_path, dict(config["model"]["params"]),
                            seed=config["model"]["seed"])

    def predictor(date, symbols):
        sub = f.reindex(symbols).dropna(how="all")
        if sub.empty:
            return pd.Series(dtype=float)
        return model.predict_series(sub[model.feature_columns], sub.index)

    rec = generate_recommendation(
        signal_date, config, predictor, args.capital,
        model_version=config["strategy"]["version"],
    )
    out_dir = PROJECT_ROOT / "reports" / "paper_live"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "latest_recommendation.csv"
    rec.to_csv(path, index=False, encoding="utf-8-sig")

    print("\n===== PAPER LIVE PORTFOLIO (research only) =====")
    print(f"signal date: {signal_date.date()}  capital: {args.capital:,.0f}")
    print(rec.to_string(index=False))
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
