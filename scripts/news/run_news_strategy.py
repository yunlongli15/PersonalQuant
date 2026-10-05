# -*- coding: utf-8 -*-
"""strategy_v1_news backtest (STEP 5 strategy experiment).

    python scripts/news/run_news_strategy.py

Same engine / split / params / costs / Top-20 / T+1 as strategy_v1; the
only change is the feature set: Alpha158 + factor_pack_v1 + the selected
news factors (config/strategy_v1_news.yaml). strategy_v1 itself is never
overwritten.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

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
OUT_DIR = PROJECT_ROOT / "experiments" / "news" / "strategy"


def load_configs():
    import yaml

    base = yaml.safe_load((PROJECT_ROOT / "config" / "strategy_v1.yaml")
                          .read_text(encoding="utf-8"))
    news_cfg = yaml.safe_load((PROJECT_ROOT / "config" / "strategy_v1_news.yaml")
                              .read_text(encoding="utf-8"))
    return base, news_cfg


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--news-version", default="v1", choices=["v1", "v2"],
                    help="读哪一版新闻数据：v1=原始（SSE 只含定期报告），"
                         "v2=修复 SSE 采集后的重建集")
    ap.add_argument("--out-dir", default=None,
                    help="输出目录（默认写死的那一个；S3_v2 必须另指一个，"
                         "绝不能覆盖冻结的生产模型）")
    ap.add_argument("--strategy-name", default="strategy_v1_news",
                    help="写进 manifest 的策略名")
    args = ap.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else OUT_DIR
    if args.news_version == "v2":
        from factors.base import set_news_version, news_version
        set_news_version("v2")
        print(f"[news] 使用 news_{news_version()}（修复 SSE 采集后的公告集）")
    if out_dir == OUT_DIR and args.news_version != "v1":
        raise SystemExit(
            "拒绝执行：用 news_v2 训练却要写进默认目录，会覆盖冻结的生产模型"
            f"（{OUT_DIR}）。请用 --out-dir 另指一个。")

    config, news_cfg = load_configs()
    ts = config["time_split"]
    cost_model = TransactionCostModel.from_config(config)
    init_qlib_with_canonical()

    step4_pack = json.loads((PROJECT_ROOT / "experiments" / "factors"
                             / "factor_run_001" / "factor_pack_v1.json")
                            .read_text(encoding="utf-8"))
    news_pack = json.loads((PROJECT_ROOT / "experiments" / "news"
                            / "news_factor_run_001"
                            / "factor_pack_news_v1.json")
                           .read_text(encoding="utf-8"))
    features = (step4_pack["selected"] + news_pack["selected"])
    print(f"{args.strategy_name} features: {features}")

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

    data = load_factor_data("2014-06-01", ts["test"][1])
    custom = {}
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
                m = m.join(cc, how="left")
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
    fit = model.fit(train_df.drop(columns=["label", "date", "symbol"]),
                    train_df["label"],
                    valid_df.drop(columns=["label", "date", "symbol"]),
                    valid_df["label"])
    out_dir.mkdir(parents=True, exist_ok=True)
    model.save(out_dir / "model.txt")

    pred_frames = []
    for d in valid_dates + test_dates:
        f = feats.get(d)
        if f is None or f.empty:
            continue
        m = flatten_columns(f).copy()
        cc = custom.get(d)
        if cc is not None and not cc.empty:
            m = m.join(cc, how="left")
        lab = labels.get(d)
        if lab is None:
            continue
        m["label"] = lab
        m = m.dropna(subset=["label"])
        m["prediction"] = model.predict(m[model.feature_columns])
        m["date"] = d
        pred_frames.append(m.reset_index()[["date", "symbol", "prediction",
                                           "label"]])
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
            m = m.join(cc, how="left")
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
                 model_version=args.strategy_name)
    res.nav.to_frame("nav").to_parquet(out_dir / "nav.parquet")
    res.turnover.to_frame("turnover").to_parquet(out_dir / "turnover.parquet")
    res.predictions.to_parquet(out_dir / "monthly_predictions.parquet")

    summary = {
        "strategy": args.strategy_name,
        "created": datetime.now().isoformat(timespec="seconds"),
        "features": features,
        "strategy_metrics": mt.summarize(res.nav, None, res.turnover,
                                         len(res.trades),
                                         args.strategy_name),
        "ic": ic_by_period,
        "quantile_summary": quantile_summary(qa).to_dict("records"),
        "top_bottom_spread": top_bottom_spread(qa),
        "fit": fit,
    }
    with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    save_manifest(build_manifest(config, args.strategy_name, extra={
        "features": features}), out_dir)
    s = summary["strategy_metrics"]
    print(f"{args.strategy_name} test: ann={s['annualized_return']:.4f} "
          f"sharpe={s['sharpe']:.3f} mdd={s['max_drawdown']:.4f} "
          f"IC={ic_by_period['test']['ic_mean']:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
