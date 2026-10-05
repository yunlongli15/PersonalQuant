# -*- coding: utf-8 -*-
"""训练"干净"候选模型（PHASE 7）—— 不使用任何新闻因子。

    python scripts/quant/train_clean_model.py --features alpha158
    python scripts/quant/train_clean_model.py --features factor_pack_v1

两个候选**只差特征集**，其余一切与 strategy_v1 逐项相同：
模型类型 / 超参数 / seed / label / horizon / train-valid-test 切分 /
embargo / 调仓规则 / 成本模型 / 组合构造。这不是新策略，
是同一个引擎换特征。

**为什么必须重新训练，而不是把 S3_v1 的新闻列删掉**：
S3_v1 的树已经学过新闻特征，它的分裂点是在有新闻列的前提下长出来的；
把列去掉再喂给它，模型看到的分布和训练时完全不同。
（PHASE 7 §四）

产出（每个候选一个目录）：
    experiments/clean/<name>/model.txt / summary.json / manifest.json /
    nav.parquet / turnover.parquet / predictions.parquet /
    monthly_predictions.parquet / trades.parquet
"""

import argparse
import hashlib
import json
import platform
import subprocess
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
from personal_quant.strategy.features import (compute_features, compute_labels,
                                              flatten_columns)
from personal_quant.strategy.model import AlphaModel, compute_ic
from personal_quant.strategy.qlib_provider import init_qlib_with_canonical
from personal_quant.strategy.rebalance import rebalance_dates
from personal_quant.strategy.universe import build_universe

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = PROJECT_ROOT / "experiments" / "clean"

#: 候选定义。**新闻因子一个都不在里面** —— 这是 PHASE 7 的全部要点。
CANDIDATES = {
    "clean_A": {
        "pack": None,
        "label": "Alpha158 only",
        "features": [],
    },
    "clean_B": {
        "pack": ("experiments/factors/factor_run_001/factor_pack_v1.json",
                 "selected"),
        "label": "Alpha158 + factor_pack_v1（非新闻）",
        "features": [],
    },
}
CANDIDATES["clean_B"]["features"] = None            # 运行时从 pack 读


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"],
                                       cwd=PROJECT_ROOT,
                                       text=True).strip()
    except Exception:                                          # noqa: BLE001
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", required=True,
                    choices=["alpha158", "factor_pack_v1"],
                    help="alpha158 = 候选A；factor_pack_v1 = 候选B（非新闻）")
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()

    name = "clean_A" if args.features == "alpha158" else "clean_B"
    out_dir = Path(args.out_dir) if args.out_dir else OUT_ROOT / name
    out_dir.mkdir(parents=True, exist_ok=True)

    import yaml

    cfg_path = PROJECT_ROOT / "config" / "strategy_v1.yaml"
    config = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    ts = config["time_split"]
    cost_model = TransactionCostModel.from_config(config)
    init_qlib_with_canonical()

    # ---- 特征集 ---------------------------------------------------------
    custom: list = []
    pack_info = None
    if args.features == "factor_pack_v1":
        pack_path = PROJECT_ROOT / "experiments" / "factors" / \
            "factor_run_001" / "factor_pack_v1.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        custom = list(pack["selected"])
        # 硬断言：非新闻 pack 里绝不能出现新闻因子
        news = _news_names()
        leaked = [f for f in custom if f in news]
        if leaked:
            raise SystemExit(f"拒绝训练：factor_pack_v1 里出现新闻因子 {leaked}")
        pack_info = {"path": str(pack_path.relative_to(PROJECT_ROOT)),
                     "sha256": _sha256(pack_path), "selected": custom}
    print(f"[{name}] custom features ({len(custom)}): {custom}")

    # ---- 数据 -----------------------------------------------------------
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

    custom_panels = {}
    if custom:
        from factors.base import load_factor_data, set_news_version
        from factors.normalization import fill_missing, normalize_panel
        from factors.registry import FACTORS

        set_news_version("v1")          # 不读新闻，但保持口径确定
        data = load_factor_data("2014-06-01", ts["test"][1])
        for nm in custom:
            panel = FACTORS[nm](data, dates=list(pd.DatetimeIndex(all_dates)))
            panel = panel.reindex(pd.DatetimeIndex(all_dates))
            panel = fill_missing(normalize_panel(panel, "rank"),
                                 "sector_median", data.industries)
            for d in all_dates:
                custom_panels.setdefault(d, []).append(
                    panel.loc[d].rename(nm))
        custom_panels = {d: pd.concat(cols, axis=1)
                         for d, cols in custom_panels.items()}

    def build(dates):
        frames = []
        for d in dates:
            f = feats.get(d)
            if f is None or f.empty:
                continue
            m = flatten_columns(f).copy()
            cc = custom_panels.get(d)
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
    model.save(out_dir / "model.txt")

    # ---- 预测 / 回测（与 strategy_v1 同一引擎）--------------------------
    pred_frames = []
    for d in valid_dates + test_dates:
        f = feats.get(d)
        if f is None or f.empty:
            continue
        m = flatten_columns(f).copy()
        cc = custom_panels.get(d)
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
        cc = custom_panels.get(d)
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
    res = bt.run(ts["test"][0], ts["test"][1], predictor, model_version=name)
    res.nav.to_frame("nav").to_parquet(out_dir / "nav.parquet")
    res.turnover.to_frame("turnover").to_parquet(out_dir / "turnover.parquet")
    res.predictions.to_parquet(out_dir / "monthly_predictions.parquet")
    if not res.trades.empty:
        res.trades.to_parquet(out_dir / "trades.parquet")

    strategy_metrics = mt.summarize(res.nav, None, res.turnover,
                                    len(res.trades), name)
    summary = {
        "strategy": name,
        "created": datetime.now().isoformat(timespec="seconds"),
        "features": custom,
        "uses_news": False,
        "strategy_metrics": strategy_metrics,
        "ic": ic_by_period,
        "quantile_summary": quantile_summary(qa).to_dict("records"),
        "top_bottom_spread": top_bottom_spread(qa),
        "fit": fit,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8")

    # ---- 版本化 manifest（PHASE 7 §十三）--------------------------------
    manifest = {
        "run_id": name,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "python_version": platform.python_version(),
        "base_config": str(cfg_path.relative_to(PROJECT_ROOT)),
        "base_config_sha256": _sha256(cfg_path),
        "feature_pack": pack_info,
        "feature_set": ("alpha158" if not custom
                        else "alpha158+factor_pack_v1"),
        "news_factors": "DISABLED",
        "model_params": config["model"]["params"],
        "model_seed": config["model"]["seed"],
        "time_split": config["time_split"],
        "label": config["label"],
        "execution": config["execution"],
        "transaction_costs": config["transaction_costs"],
        "rebalance": config["rebalance"],
        "portfolio": config["portfolio"],
        "universe": config["universe"],
        "n_features_total": len(model.feature_columns),
        "n_custom_features": len(custom),
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8")

    s = strategy_metrics
    print(f"{name} test: ann={s['annualized_return']:.4f} "
          f"sharpe={s['sharpe']:.3f} mdd={s['max_drawdown']:.4f} "
          f"IC={ic_by_period['test']['ic_mean']:.4f}")
    return 0


def _news_names() -> set:
    from factors.registry import FACTOR_REGISTRY

    return {n for n, m in FACTOR_REGISTRY.items() if m["category"] == "news"}


if __name__ == "__main__":
    sys.exit(main())
