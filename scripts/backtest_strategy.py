# -*- coding: utf-8 -*-
"""STEP 3 strategy backtest runner.

    python scripts/backtest_strategy.py --strategy strategy_v1 \
        --start 2024-01-01 --end 2025-12-31 \
        [--walk-forward] [--capital 1000000]

Writes results to experiments/strategy_v1/run_<id>/:
  manifest.json, predictions.parquet, nav.parquet, benchmarks.parquet,
  ic.parquet, quantiles.parquet, summary.json, model.txt, figures/
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from personal_quant import db
from personal_quant.strategy import benchmarks as bm
from personal_quant.strategy import metrics as mt
from personal_quant.strategy.analysis import (
    ic_summary,
    quantile_analysis,
    quantile_summary,
    top_bottom_spread,
)
from personal_quant.strategy.backtest import MonthlyBacktest
from personal_quant.strategy.costs import TransactionCostModel
from personal_quant.strategy.features import build_training_data, compute_features
from personal_quant.strategy.model import AlphaModel, compute_ic
from personal_quant.strategy.qlib_provider import init_qlib_with_canonical
from personal_quant.strategy.rebalance import rebalance_dates
from personal_quant.strategy.reproducibility import build_manifest, save_manifest
from personal_quant.strategy.universe import build_universe

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_config():
    import yaml

    return yaml.safe_load(
        (PROJECT_ROOT / "config" / "strategy_v1.yaml").read_text(encoding="utf-8")
    )


def universe_union(start: str, end: str, config: dict) -> list:
    """Union of universes over all rebalance dates (for feature computation)."""
    dates = rebalance_dates(start, end)
    out = set()
    for d in dates:
        u = build_universe(d, config)
        out.update(u["symbol"].tolist())
    return sorted(out)


class ModelPredictor:
    def __init__(self, model: AlphaModel, feature_cache: dict):
        self.model = model
        self.feature_cache = feature_cache

    def __call__(self, date: pd.Timestamp, symbols: list) -> pd.Series:
        from personal_quant.strategy.features import flatten_columns

        f = self.feature_cache.get(date)
        if f is None or f.empty:
            return pd.Series(dtype=float)
        f = flatten_columns(f)
        sub = f.reindex(symbols).dropna(how="all")
        if sub.empty:
            return pd.Series(dtype=float)
        pred = self.model.predict_series(sub[self.model.feature_columns], sub.index)
        return pred


class MomentumPredictor:
    def __init__(self, lookback_days: int):
        self.lookback = lookback_days

    def __call__(self, date: pd.Timestamp, symbols: list) -> pd.Series:
        return bm.momentum_scores(date, symbols, self.lookback)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", default="strategy_v1")
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--walk-forward", action="store_true")
    ap.add_argument("--capital", type=float, default=1_000_000.0)
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()

    config = load_config()
    ts = config["time_split"]
    train_s, train_e = ts["train"]
    valid_s, valid_e = ts["valid"]
    test_s, test_e = ts["test"]
    cost_model = TransactionCostModel.from_config(config)

    run_id = args.run_id or f"run_{datetime.now():%Y%m%d_%H%M%S}"
    out_dir = PROJECT_ROOT / "experiments" / "strategy_v1" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(config, run_id, extra={
        "backtest_start": args.start, "backtest_end": args.end,
        "walk_forward": args.walk_forward, "capital": args.capital,
    })
    save_manifest(manifest, out_dir)

    print(f"run_id: {run_id}")
    init_qlib_with_canonical()

    # ---- features: compute slices for train+valid+test(+eval) periods -----
    print("[1/5] computing Alpha158 features ...")
    feat_dates = sorted(set(
        rebalance_dates(train_s, train_e)
        + rebalance_dates(valid_s, valid_e)
        + rebalance_dates(test_s, test_e)
    ))
    instruments = universe_union(train_s, test_e, config)
    print(f"  {len(feat_dates)} feature dates, {len(instruments)} instruments")
    feats = compute_features(instruments, feat_dates, cache=True)

    # ---- training data + model --------------------------------------------
    print("[2/5] training model ...")
    from personal_quant.strategy.features import compute_labels

    train_dates = rebalance_dates(train_s, train_e)
    valid_dates = rebalance_dates(valid_s, valid_e)
    # per-date PIT universes: training rows only from stocks investable at
    # that date (listing age, suspension, liquidity)
    date_universes = {
        d: build_universe(d, config)["symbol"].tolist()
        for d in train_dates + valid_dates
    }
    train_df = build_training_data(instruments, train_dates,
                                   date_universes=date_universes)
    valid_df = build_training_data(instruments, valid_dates,
                                   date_universes=date_universes)
    model = AlphaModel(dict(config["model"]["params"]),
                       seed=config["model"]["seed"])
    fit_metrics = model.fit(
        train_df.drop(columns=["label", "date", "symbol"]),
        train_df["label"],
        valid_df.drop(columns=["label", "date", "symbol"]),
        valid_df["label"],
    )
    print("  fit:", fit_metrics)
    model.save(out_dir / "model.txt")
    with open(out_dir / "fit_metrics.json", "w", encoding="utf-8") as f:
        json.dump(fit_metrics, f, indent=2, default=str)

    # ---- IC / quantile evaluation (valid + test) ---------------------------
    print("[3/5] IC + quantile analysis ...")
    from personal_quant.strategy.features import flatten_columns

    pred_frames = []
    for d in valid_dates + rebalance_dates(test_s, test_e):
        f = feats.get(d)
        if f is None or f.empty:
            continue
        labels = compute_labels(instruments, [d])[d]
        m = flatten_columns(f).copy()
        m["label"] = labels
        m = m.dropna(subset=["label"])
        if m.empty:
            continue
        m["prediction"] = model.predict(m[model.feature_columns])
        m["date"] = d
        pred_frames.append(m.reset_index()[["date", "symbol", "prediction", "label"]])
    preds = pd.concat(pred_frames, ignore_index=True)
    preds.to_parquet(out_dir / "predictions.parquet")
    ic_df = compute_ic(preds)
    ic_df.to_parquet(out_dir / "ic.parquet")
    _vs, _ve, _ts, _te = (pd.Timestamp(x) for x in (valid_s, valid_e, test_s, test_e))
    ic_by_period = {
        "valid": ic_summary(ic_df[(ic_df["date"] >= _vs) & (ic_df["date"] <= _ve)], "valid"),
        "test": ic_summary(ic_df[(ic_df["date"] >= _ts) & (ic_df["date"] <= _te)], "test"),
    }
    qa = quantile_analysis(preds[preds["date"] >= _vs])
    qa.to_parquet(out_dir / "quantiles.parquet")
    qsum = quantile_summary(qa)
    spread = top_bottom_spread(qa)

    bt = MonthlyBacktest(config, cost_model, args.capital)

    # ---- walk-forward mode (quarterly retrain over the eval period) --------
    if args.walk_forward:
        print("[4/5] walk-forward evaluation ...")
        from personal_quant.strategy.walkforward import run_walk_forward

        wf_dates = sorted(set(rebalance_dates(args.start, args.end)))
        # training rows for any date set come from the cached feature slices
        train_cache = {}

        from personal_quant.strategy.features import flatten_columns as _fl

        def data_builder(dates, labels=True):
            frames = []
            for d in dates:
                f = feats.get(d)
                if f is None or f.empty:
                    continue
                m = _fl(f).copy()
                if labels:
                    m["label"] = compute_labels(list(f.index), [d])[d]
                    m = m.dropna(subset=["label"])
                else:
                    m["label"] = pd.NA
                m["date"] = d
                frames.append(m.reset_index())
            if not frames:
                return pd.DataFrame(columns=["date", "symbol", "label"])
            return pd.concat(frames, ignore_index=True)

        wf_preds = run_walk_forward(
            args.start, args.end,
            lambda s, e: rebalance_dates(s, e),
            data_builder, config, out_dir / "walkforward",
        )
        wf_preds.to_parquet(out_dir / "walkforward_predictions.parquet")
        wf_ic = compute_ic(wf_preds)
        wf_ic.to_parquet(out_dir / "walkforward_ic.parquet")

        # backtest with the walk-forward model: rebuild a predictor from the
        # quarterly models (model_q*.txt) and the cached features
        from personal_quant.strategy.model import AlphaModel as AM

        from personal_quant.strategy.walkforward import walk_forward_periods

        qmodels = sorted((out_dir / "walkforward").glob("model_q*.txt"))
        model_map = {}
        for qf in qmodels:
            i = int(qf.stem.split("_q")[1])
            model_map[i] = AM.load(qf, dict(config["model"]["params"]),
                                   seed=config["model"]["seed"])
        # map each month to the model whose training window ended before it
        date_model = {}
        for i, (tr_s, tr_e, pe_s, pe_e) in enumerate(
            walk_forward_periods(args.start, args.end)
        ):
            for d in rebalance_dates(pe_s, pe_e):
                date_model[d] = i

        def wf_predictor(date, symbols):
            mi = date_model.get(date)
            if mi is None or mi not in model_map:
                return pd.Series(dtype=float)
            f = feats.get(date)
            if f is None or f.empty:
                return pd.Series(dtype=float)
            sub = _fl(f).reindex(symbols).dropna(how="all")
            if sub.empty:
                return pd.Series(dtype=float)
            m = model_map[mi]
            return m.predict_series(sub[m.feature_columns], sub.index)
        res = bt.run(args.start, args.end, wf_predictor,
                     model_version="strategy_v1_walkforward")
        print("  walk-forward predictions:", len(wf_preds),
              "| IC mean:", round(float(wf_ic['ic'].mean()), 4) if len(wf_ic) else None)
    else:
        # ---- fixed-split backtest (strategy + momentum baseline) -----------
        print("[4/5] backtesting ...")
        predictor = ModelPredictor(model, feats)
        res = bt.run(args.start, args.end, predictor)
    res.nav.to_frame("nav").to_parquet(out_dir / "nav.parquet")
    res.positions.to_parquet(out_dir / "positions.parquet")
    if not res.trades.empty:
        res.trades.to_parquet(out_dir / "trades.parquet")
    res.turnover.to_frame("turnover").to_parquet(out_dir / "turnover.parquet")
    res.predictions.to_parquet(out_dir / "monthly_predictions.parquet")

    # momentum baseline with identical engine
    if config["baselines"]["momentum"]["enabled"]:
        mom = MomentumPredictor(config["baselines"]["momentum"]["lookback_days"])
        res_mom = bt.run(args.start, args.end, mom)
        res_mom.nav.to_frame("nav").to_parquet(out_dir / "nav_momentum.parquet")
        res_mom.turnover.to_frame("turnover").to_parquet(
            out_dir / "turnover_momentum.parquet"
        )
    else:
        res_mom = None

    # ---- benchmarks + summary -------------------------------------------------
    print("[5/5] benchmarks + summary ...")
    bench = {}
    for idx in config["baselines"]["buy_and_hold_indexes"]:
        bench[idx] = bm.index_nav(idx, args.start, args.end)
    if config["baselines"].get("equal_weight_market"):
        bench["equal_weight_market"] = bm.equal_weight_market_nav(args.start, args.end)
    bench_df = pd.DataFrame({k: v for k, v in bench.items() if not v.empty})
    bench_df.to_parquet(out_dir / "benchmarks.parquet")

    summary = {
        "run_id": run_id,
        "strategy": mt.summarize(res.nav, bench.get("000300.SH"),
                                 res.turnover, len(res.trades), "strategy_v1"),
        "momentum_baseline": (mt.summarize(res_mom.nav, bench.get("000300.SH"),
                                           res_mom.turnover, len(res_mom.trades),
                                           "momentum_60d") if res_mom else None),
        "benchmarks": {k: mt.summarize(v, label=k) for k, v in bench.items()},
        "ic": ic_by_period,
        "quantile_summary": qsum.to_dict("records"),
        "top_bottom_spread": spread,
        "fit": fit_metrics,
        "yearly_returns": {
            str(y): float(r) for y, r in
            mt.yearly_returns(res.nav).items()
        },
    }
    with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    print("\n===== STRATEGY SUMMARY =====")
    for k, v in summary["strategy"].items():
        if isinstance(v, float):
            print(f"  {k:28s} {v:,.4f}")
        else:
            print(f"  {k:28s} {v}")
    print("\n===== BENCHMARKS =====")
    for k, v in summary["benchmarks"].items():
        print(f"  {k:28s} ann_ret={v['annualized_return']:,.4f} "
              f"sharpe={v['sharpe']:,.3f} mdd={v['max_drawdown']:,.4f}")
    print(f"\nresults written to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
