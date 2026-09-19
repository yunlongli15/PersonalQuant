# -*- coding: utf-8 -*-
"""微结构因子消融回测（新增因子到底有没有用）。

    python scripts/portfolio/run_micro_ablation.py
    python scripts/portfolio/run_micro_ablation.py --variants S3,M

同一引擎 / 同区间 / 同参数 / 同成本 / 同 Top-20 / 同 T+1 执行，只改特征集：

  S3   Alpha158 + factor_pack_v1 + news        （冻结基线，必须复现 0.2812）
  M    Alpha158 + micro_pack（5 个新因子）      （新因子单独）
  N    Alpha158 + pack_v1 + news + micro_pack   （全组合，看增量）

纪律（与 STEP 4/5/6 一致）：
- 因子入选只用 research 2018-2021 + valid 2022-2023（由
  scripts/research_all_factors.py 的 select_factor_pack 决定）；
- frozen test 2024-2025 只做单次最终评估，绝不用于选择；
- S3 变体必须复现冻结锚点 (0.2812, 1.022, -0.2351)，否则报告 drift。
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

from personal_quant.strategy import metrics as mt
from personal_quant.strategy.analysis import (ic_summary, quantile_analysis,
                                              top_bottom_spread)
from personal_quant.strategy.backtest import MonthlyBacktest
from personal_quant.strategy.costs import TransactionCostModel
from personal_quant.strategy.features import compute_features, compute_labels
from personal_quant.strategy.features import flatten_columns
from personal_quant.strategy.model import AlphaModel, compute_ic
from personal_quant.strategy.qlib_provider import init_qlib_with_canonical
from personal_quant.strategy.rebalance import rebalance_dates
from personal_quant.strategy.universe import build_universe

from factors.base import load_factor_data
from factors.normalization import fill_missing, normalize_panel
from factors.registry import FACTOR_REGISTRY, FACTORS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT = PROJECT_ROOT / "experiments" / "factors" / "micro_ablation"
MICRO_PACK = PROJECT_ROOT / "experiments" / "factors" / "micro_run_001" / \
    "factor_pack_v1.json"
ANCHOR_S3 = (0.2812, 1.022, -0.2351)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default="S3,M,N")
    args = ap.parse_args()

    import yaml

    config = yaml.safe_load((PROJECT_ROOT / "config" / "strategy_v1.yaml")
                            .read_text(encoding="utf-8"))
    ts = config["time_split"]
    cost_model = TransactionCostModel.from_config(config)
    init_qlib_with_canonical()

    step4 = json.loads((PROJECT_ROOT / "experiments" / "factors"
                        / "factor_run_001" / "factor_pack_v1.json")
                       .read_text(encoding="utf-8"))["selected"]
    news = json.loads((PROJECT_ROOT / "experiments" / "news"
                       / "news_factor_run_001" / "factor_pack_news_v1.json")
                      .read_text(encoding="utf-8"))["selected"]
    micro = json.loads(MICRO_PACK.read_text(encoding="utf-8"))["selected"]
    print(f"pack_v1: {step4}")
    print(f"news   : {news}")
    print(f"micro  : {micro}")

    def dedup(names):
        """Keep first occurrence: the micro pack re-selects some factors
        that are already in pack_v1 (e.g. amount_20), and LightGBM refuses
        duplicate feature names."""
        out, seen = [], set()
        for n in names:
            if n not in seen:
                seen.add(n)
                out.append(n)
        return out

    variants = {
        "S3": dedup(step4 + news),
        "M": dedup(micro),
        "N": dedup(step4 + news + micro),
    }
    wanted = [v.strip() for v in args.variants.split(",")]

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
    all_custom = sorted({f for n in wanted for f in variants[n]})
    custom = {}
    for name in all_custom:
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

    def build(dates, names):
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

    results = {}
    OUT.mkdir(parents=True, exist_ok=True)
    for v in wanted:
        names = variants[v]
        out_dir = OUT / f"variant_{v}"
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n===== 变体 {v}: {len(names)} 个自定义因子 =====", flush=True)

        train_df = build(train_dates, names)
        valid_df = build(valid_dates, names)
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
                     model_version=f"micro_{v}")
        res.nav.to_frame("nav").to_parquet(out_dir / "nav.parquet")
        res.turnover.to_frame("turnover").to_parquet(
            out_dir / "turnover.parquet")
        summary = {
            "variant": v, "features": names,
            "strategy": mt.summarize(res.nav, None, res.turnover,
                                     len(res.trades), f"micro_{v}"),
            "ic": ic_by_period,
            "top_bottom_spread": top_bottom_spread(qa),
            "fit": fit,
        }
        with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, default=str)
        results[v] = summary
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
                     "n_custom": len(r["features"])})
    comp = pd.DataFrame(rows)
    comp.to_csv(OUT / "comparison.csv", index=False)
    print("\n===== 微结构因子消融（frozen test 2024-2025）=====")
    print(comp.to_string(index=False))
    if "S3" in results:
        s = results["S3"]["strategy"]
        drift = (abs(s["annualized_return"] - ANCHOR_S3[0]),
                 abs(s["sharpe"] - ANCHOR_S3[1]),
                 abs(s["max_drawdown"] - ANCHOR_S3[2]))
        print(f"\n锚点 S3: ann {s['annualized_return']:.4f} vs {ANCHOR_S3[0]} "
              f"(drift {drift[0]:.4f}), sharpe {s['sharpe']:.3f} vs "
              f"{ANCHOR_S3[1]} (drift {drift[1]:.3f}) -> "
              f"{'CONSISTENT' if drift[0] < 0.002 and drift[1] < 0.02 else 'DRIFT'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
