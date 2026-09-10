# -*- coding: utf-8 -*-
"""Portfolio optimizer playground CLI (STEP 6 spec §30).

    python scripts/research_portfolio.py --method gmv --period test
    python scripts/research_portfolio.py --method equal_weight --period research
    python scripts/research_portfolio.py --method mvo --period valid --mvo-lambda small
    python scripts/research_portfolio.py --method turnover_aware --period test --quarterly

冻结 alpha 信号（spec §4）：默认 s3 = Alpha158 + factor_pack_v1 + news
（STEP 5 增量检查结论）；s1/s2 用于信号对比。valid/test 预测来自冻结的
生产模型产物（experiments/news/strategy + ablation variants）；research
期预测来自独立 OOS 模型（scripts/portfolio/build_alpha_predictions.py，
train 2015-2016 / early-stop 2017 —— 绝不用 2018-2021 自身训练数据）。

同一引擎（portfolio/backtest.py：T+1 开盘、涨跌停/停牌 NO_TRADE、100 股
手数、共享 TransactionCostModel）下换 allocation 方法。等权 + Top20 +
5% 现金的运行必须复现 strategy_v1_news（--check-anchor）。
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXP_DIR = PROJECT_ROOT / "experiments" / "portfolio"
S3_VALID_TEST = (PROJECT_ROOT / "experiments" / "news" / "strategy"
                 / "predictions.parquet")
SIGNAL_FILES = {
    "s1": PROJECT_ROOT / "experiments" / "news" / "ablation"
          / "variant_A" / "predictions.parquet",
    "s2": PROJECT_ROOT / "experiments" / "news" / "ablation"
          / "variant_B" / "predictions.parquet",
    "s3": S3_VALID_TEST,
}
SIGNAL_MODELS = {
    "s1": PROJECT_ROOT / "experiments" / "news" / "ablation"
          / "variant_A" / "model.txt",
    "s2": PROJECT_ROOT / "experiments" / "news" / "ablation"
          / "variant_B" / "model.txt",
    "s3": PROJECT_ROOT / "experiments" / "news" / "strategy" / "model.txt",
}
ANCHOR_S3 = (0.2812, 1.022, -0.2351)   # strategy_v1_news frozen anchors


def load_yaml(path):
    import yaml

    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load_predictions(signal: str, period: str) -> pd.DataFrame:
    """Frozen valid/test predictions (rebuilt through the exact frozen
    predictor path), or the OOS research-period panel."""
    if period == "research":
        p = PROJECT_ROOT / "experiments" / "news" / "strategy" / \
            f"research_predictions_{signal}.parquet"
        if not p.exists():
            raise FileNotFoundError(
                f"{p} missing — run scripts/portfolio/build_alpha_predictions.py")
        df = pd.read_parquet(p)
        df["date"] = pd.to_datetime(df["date"])
        return df[["date", "symbol", "prediction"]]
    raise ValueError("valid/test predictions go through filtered_predictions")


def custom_names_for_signal(signal: str) -> list:
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


def build_predictor(strategy_cfg, signal, dates, model_path):
    """Rebuild the frozen predictor — identical to the STEP 3/5 strategy
    scripts (feature cache + custom factor columns joined, then
    dropna(how='all') + predict_series at prediction time). This is what
    makes the candidate sets bit-identical to the frozen backtests."""
    from factors.base import load_factor_data
    from factors.normalization import fill_missing, normalize_panel
    from factors.registry import FACTOR_REGISTRY, FACTORS
    from personal_quant.strategy.features import compute_features, \
        flatten_columns
    from personal_quant.strategy.model import AlphaModel
    from personal_quant.strategy.qlib_provider import init_qlib_with_canonical
    from personal_quant.strategy.universe import build_universe

    init_qlib_with_canonical()
    names = custom_names_for_signal(signal)
    dates = list(pd.DatetimeIndex(dates))
    instruments = sorted({s for d in dates
                          for s in build_universe(d, strategy_cfg)["symbol"]})
    feats = compute_features(instruments, dates, cache=True)
    data = load_factor_data("2014-06-01", str(dates[-1]))
    custom = {}
    for name in names:
        panel = FACTORS[name](data, dates=dates)
        panel = panel.reindex(pd.DatetimeIndex(dates))
        if FACTOR_REGISTRY[name]["category"] == "news":
            panel = fill_missing(normalize_panel(panel, "rank"), "drop",
                                 data.industries)
        else:
            panel = fill_missing(normalize_panel(panel, "rank"),
                                 "sector_median", data.industries)
        for d in dates:
            custom.setdefault(d, []).append(panel.loc[d].rename(name))
    custom = {d: pd.concat(cols, axis=1) for d, cols in custom.items()}
    feat_cache = {}
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
        feat_cache[d] = m
    model = AlphaModel.load(model_path, dict(strategy_cfg["model"]["params"]),
                            seed=strategy_cfg["model"]["seed"])

    def predictor(date, symbols):
        sub = feat_cache.get(date)
        if sub is None or sub.empty:
            return pd.Series(dtype=float)
        m = sub.reindex(symbols).dropna(how="all")
        if m.empty:
            return pd.Series(dtype=float)
        return model.predict_series(m[model.feature_columns], m.index)

    return predictor


def filtered_predictions(strategy_cfg, signal, period, ts) -> pd.DataFrame:
    """Predictions for valid/test rebuilt through the frozen predictor
    (dropna(how='all') semantics included), cached per (signal, period).

    Equivalence vs the frozen parquet is asserted on the overlapping rows
    (the frozen parquet additionally contains all-NaN-feature rows that
    the frozen backtests never used — those are excluded here)."""
    cache = EXP_DIR / f"preds_{signal}_{period}.parquet"
    if cache.exists():
        df = pd.read_parquet(cache)
        df["date"] = pd.to_datetime(df["date"])
        return df[["date", "symbol", "prediction"]]
    start, end = (pd.Timestamp(ts[period][0]), pd.Timestamp(ts[period][1]))
    from personal_quant.strategy.universe import build_universe, \
        load_securities
    from portfolio.rebalance import rebalance_dates as rb_dates

    dates = rb_dates(start, end)
    predictor = build_predictor(strategy_cfg, signal, dates,
                                SIGNAL_MODELS[signal])
    sec = load_securities()
    rows = []
    for d in dates:
        univ = build_universe(d, strategy_cfg, sec)["symbol"].tolist()
        s = predictor(d, univ)
        rows += [{"date": d, "symbol": sym, "prediction": float(v)}
                 for sym, v in s.items()]
    df = pd.DataFrame(rows)

    frozen = pd.read_parquet(SIGNAL_FILES[signal])
    frozen["date"] = pd.to_datetime(frozen["date"])
    fz = frozen[(frozen["date"] >= start) & (frozen["date"] <= end)]
    merged = df.merge(fz, on=["date", "symbol"], suffixes=("", "_frozen"))
    if merged.empty:
        print("WARNING: no overlap with the frozen predictions parquet")
    else:
        maxdiff = (merged["prediction"]
                   - merged["prediction_frozen"]).abs().max()
        excluded = len(fz) - len(merged)
        print(f"predictor vs frozen: {len(merged):,} overlap rows, "
              f"max|diff|={maxdiff:.2e}, {excluded} rows excluded "
              f"(all-NaN features, never used by the frozen backtests)")
        if maxdiff > 1e-9:
            raise RuntimeError("prediction mismatch vs frozen parquet")
    EXP_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache, index=False)
    print(f"wrote {cache} ({len(df):,} rows, {len(dates)} dates)")
    return df


def build_allocation_cfg(args, portfolio_cfg, strategy_cfg) -> dict:
    pc = portfolio_cfg["portfolio"]
    constraints = dict(pc["constraints"])
    constraints["cash_buffer"] = args.cash_buffer or constraints["cash_buffer"]
    constraints["max_weight"] = args.max_weight or constraints["max_weight"]
    constraints["sector_cap"] = args.sector_cap or constraints["sector_cap"]
    if getattr(args, "liquidity_frac", None) is not None:
        constraints["liquidity_frac"] = args.liquidity_frac
    from portfolio.constraints import PortfolioConstraints

    cons = PortfolioConstraints.from_dict(constraints)
    method_params = dict(pc["methods"].get(args.method, {}))
    if getattr(args, "method_params", None):
        method_params.update(args.method_params)
    if args.mvo_lambda and args.method == "mvo":
        method_params["lambda_tier"] = args.mvo_lambda
    if args.score_variant and args.method == "score_weight":
        method_params["variant"] = args.score_variant
    if args.lambda_turn and args.method == "turnover_aware":
        method_params["lambda_turn"] = args.lambda_turn
    return {
        "method": args.method,
        "params": method_params,
        "top_k": args.top_k or pc["top_k"],
        "frequency": "quarterly" if args.quarterly else pc["rebalance"][
            "frequency"],
        "constraints": cons,
        "risk_window": args.risk_window or pc["risk"]["window"],
        "cov_method": args.cov or pc["risk"]["covariance"],
        "ewma_halflife": pc["risk"]["ewma_halflife"],
    }


def run_dir_id(signal, period, method, top_k, cash, quarterly=False) -> str:
    rid = f"{signal}_{period}_{method}_k{top_k}_c{int(cash*100)}"
    return rid + ("_q" if quarterly else "")


def run_one(method, period, signal="s3", top_k=None, cash_buffer=None,
            max_weight=None, sector_cap=None, risk_window=None, cov=None,
            mvo_lambda=None, score_variant=None, lambda_turn=None,
            quarterly=False, run_id=None, out_dir=None, check_anchor=False,
            method_params=None, liquidity_frac=None, verbose=True):
    """One (signal, period, method) portfolio backtest — shared by the
    CLI and the study drivers."""
    from types import SimpleNamespace

    args = SimpleNamespace(
        method=method, period=period, signal=signal, top_k=top_k,
        cash_buffer=cash_buffer, max_weight=max_weight,
        sector_cap=sector_cap, risk_window=risk_window, cov=cov,
        mvo_lambda=mvo_lambda, score_variant=score_variant,
        lambda_turn=lambda_turn, quarterly=quarterly, run_id=run_id,
        check_anchor=check_anchor, method_params=method_params,
        liquidity_frac=liquidity_frac)
    strategy_cfg = load_yaml(PROJECT_ROOT / "config" / "strategy_v1.yaml")
    portfolio_cfg = load_yaml(PROJECT_ROOT / "config" / "portfolio_v1.yaml")
    ts = portfolio_cfg["time_split"]
    if out_dir is None:
        out_dir = EXP_DIR / (run_id or (f"{signal}_{period}_{method}"
                                        + ("_q" if quarterly else "")))
    return run_experiment(args, strategy_cfg, portfolio_cfg, ts, out_dir,
                          verbose=verbose)


def run_experiment(args, strategy_cfg, portfolio_cfg, ts, out_dir,
                   verbose=True):
    """Run one (signal, period, method) portfolio backtest; returns the
    PortfolioBacktestResult and saves artifacts to out_dir."""
    from factors.base import load_factor_data
    from personal_quant.strategy.costs import TransactionCostModel
    from personal_quant.strategy.reproducibility import (build_manifest,
                                                         save_manifest)
    from portfolio.backtest import PortfolioBacktest
    from portfolio import portfolio_metrics as pm

    start, end = (pd.Timestamp(ts[args.period][0]),
                  pd.Timestamp(ts[args.period][1]))
    cost_model = TransactionCostModel.from_config(strategy_cfg)
    alloc_cfg = build_allocation_cfg(args, portfolio_cfg, strategy_cfg)

    if args.period == "research":
        preds = load_predictions(args.signal, args.period)
    else:
        preds = filtered_predictions(strategy_cfg, args.signal, args.period,
                                     ts)
    preds = preds[(preds["date"] >= start) & (preds["date"] <= end)]
    if preds.empty:
        raise ValueError(f"no predictions for {args.period}")

    # load_factor_data trims to its own `start`; pad 400 calendar days so
    # the covariance lookback (60/120 trading days) has warm-up history
    data = load_factor_data(pd.Timestamp(start) - pd.Timedelta(days=400), end)
    bench = None
    if "000300.SH" in data.close_raw.columns:
        bench = data.close_raw["000300.SH"].ffill()
        bench = bench[(bench.index >= start) & (bench.index <= end)]

    bt = PortfolioBacktest(strategy_cfg, cost_model, alloc_cfg,
                           portfolio_cfg["experiment"]["initial_capital"])
    res = bt.run(start, end, preds, data, bench_nav=bench, verbose=verbose)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    res.nav.to_frame("nav").to_parquet(out_dir / "nav.parquet")
    res.daily_weights.to_parquet(out_dir / "daily_weights.parquet")
    res.weights.to_parquet(out_dir / "weights.parquet")
    res.audit.to_parquet(out_dir / "audit.parquet")
    res.trades.to_parquet(out_dir / "trades.parquet")
    res.turnover.to_frame("turnover").to_parquet(out_dir / "turnover.parquet")
    res.turnover_full.to_frame("turnover_full").to_parquet(
        out_dir / "turnover_full.parquet")
    with open(out_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(res.metrics, f, indent=2, default=str)
    save_manifest(build_manifest(strategy_cfg, f"portfolio_{args.method}", extra={
        "signal": args.signal, "period": args.period,
        "allocation": alloc_cfg,
        "constraints": alloc_cfg["constraints"].to_dict(),
    }), out_dir)
    return res


def _anchor_check(res) -> bool:
    m = res.metrics
    drift = (abs(m["annualized_return"] - ANCHOR_S3[0]),
             abs(m["sharpe"] - ANCHOR_S3[1]),
             abs(m["max_drawdown"] - ANCHOR_S3[2]))
    ok = drift[0] < 0.002 and drift[1] < 0.02 and drift[2] < 0.005
    print(f"anchor s3: ann {m['annualized_return']:.4f} vs {ANCHOR_S3[0]} "
          f"(drift {drift[0]:.4f}), sharpe {m['sharpe']:.3f} vs "
          f"{ANCHOR_S3[1]} (drift {drift[1]:.3f}), mdd "
          f"{m['max_drawdown']:.4f} vs {ANCHOR_S3[2]} (drift {drift[2]:.4f}) "
          f"-> {'CONSISTENT' if ok else 'DRIFT — investigate'}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True, choices=[
        "equal_weight", "score_weight", "inverse_vol", "gmv", "mvo",
        "risk_parity", "turnover_aware"])
    ap.add_argument("--period", default="test",
                    choices=["research", "valid", "test"])
    ap.add_argument("--signal", default="s3", choices=["s1", "s2", "s3"])
    ap.add_argument("--top-k", type=int, default=None)
    ap.add_argument("--cash-buffer", type=float, default=None)
    ap.add_argument("--max-weight", type=float, default=None)
    ap.add_argument("--sector-cap", type=float, default=None)
    ap.add_argument("--risk-window", type=int, default=None)
    ap.add_argument("--cov", choices=["sample", "ewma"], default=None)
    ap.add_argument("--mvo-lambda", choices=["small", "medium", "large"],
                    default=None)
    ap.add_argument("--score-variant",
                    choices=["rank", "raw_positive", "softmax"],
                    default=None)
    ap.add_argument("--lambda-turn", type=float, default=None)
    ap.add_argument("--liquidity-frac", type=float, default=None)
    ap.add_argument("--quarterly", action="store_true")
    ap.add_argument("--check-anchor", action="store_true")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()

    run_id = args.run_id or (f"{args.signal}_{args.period}_{args.method}"
                             + ("_q" if args.quarterly else ""))
    res = run_one(args.method, args.period, args.signal, args.top_k,
                  args.cash_buffer, args.max_weight, args.sector_cap,
                  args.risk_window, args.cov, args.mvo_lambda,
                  args.score_variant, args.lambda_turn, args.quarterly,
                  run_id, EXP_DIR / run_id, args.check_anchor)
    m = res.metrics
    portfolio_cfg = load_yaml(PROJECT_ROOT / "config" / "portfolio_v1.yaml")
    print(f"\n===== {args.signal} {args.period} {args.method} "
          f"(top_k={args.top_k or portfolio_cfg['portfolio']['top_k']}) =====")
    print(f"ann={m['annualized_return']:.4f} sharpe={m['sharpe']:.3f} "
          f"mdd={m['max_drawdown']:.4f} calmar={m['calmar']:.3f} "
          f"vol={m['annualized_volatility']:.4f}")
    print(f"turnover(avg)={m['avg']:.3f} fees={m['total_fees']:.0f} "
          f"avg_holdings={m['avg_holdings']:.1f} eff_n="
          f"{m['avg_effective_n']:.1f} HHI={m['avg_hhi']:.3f} "
          f"ind_conc={m.get('avg_industry_concentration', float('nan')):.3f}")
    print(f"worst_day={m['worst_day']:.4f} worst_month="
          f"{m['worst_month']:.4f} VaR60={m['var_60d']:.4f} "
          f"CVaR60={m['cvar_60d']:.4f}")
    print(f"artifacts: {EXP_DIR / run_id}")
    if args.check_anchor:
        return 0 if _anchor_check(res) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
