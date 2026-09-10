# -*- coding: utf-8 -*-
"""strategy_v2 paper-live recommendation (research only, spec §48/§49).

Flow: frozen S3 production model predictions at the paper-live date ->
top-K candidates -> the v2 allocation method (PIT covariance/vols at the
date) -> target weights -> lot-rounded BUY/SELL/HOLD against the previous
paper-live state -> estimated shares / cash / turnover / fees.

Capital 500,000 (spec §48). Writes
reports/paper_live/latest_recommendation_v2.csv and updates
experiments/portfolio/paper_live_state.parquet. NO REAL TRADING.

    python scripts/portfolio/generate_v2_recommendation.py
    python scripts/portfolio/generate_v2_recommendation.py --date 2026-09-04 --capital 500000
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = PROJECT_ROOT / "experiments" / "portfolio"
STATE_PATH = EXP_DIR / "paper_live_state.parquet"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-09-04")
    ap.add_argument("--capital", type=float, default=500_000.0)
    args = ap.parse_args()

    import yaml

    base_cfg = yaml.safe_load((PROJECT_ROOT / "config" / "strategy_v1.yaml")
                              .read_text(encoding="utf-8"))
    v2 = yaml.safe_load((PROJECT_ROOT / "config" / "strategy_v2.yaml")
                        .read_text(encoding="utf-8"))
    p = v2["portfolio"]
    signal_date = pd.Timestamp(args.date)

    from personal_quant.strategy.costs import TransactionCostModel
    from personal_quant.strategy.features import compute_features, \
        flatten_columns
    from personal_quant.strategy.model import AlphaModel
    from personal_quant.strategy.qlib_provider import init_qlib_with_canonical
    from personal_quant.strategy.universe import build_universe

    init_qlib_with_canonical()
    base_cfg["universe"]["st_filter"]["enabled"] = True   # paper live only
    universe = build_universe(signal_date, base_cfg)
    symbols = universe["symbol"].tolist()
    feats = compute_features(symbols, [signal_date], cache=False)
    f = feats.get(signal_date)
    if f is None or f.empty:
        print("ERROR: no features for the date")
        return 1
    f = flatten_columns(f)

    from factors.base import load_factor_data
    from factors.normalization import fill_missing, normalize_panel
    from factors.registry import FACTOR_REGISTRY, FACTORS

    step4_pack = json.loads((PROJECT_ROOT / "experiments" / "factors"
                             / "factor_run_001" / "factor_pack_v1.json")
                            .read_text(encoding="utf-8"))
    news_pack = json.loads((PROJECT_ROOT / "experiments" / "news"
                            / "news_factor_run_001"
                            / "factor_pack_news_v1.json")
                           .read_text(encoding="utf-8"))
    custom_features = step4_pack["selected"] + news_pack["selected"]
    data = load_factor_data("2014-06-01", args.date)
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

    model_path = (PROJECT_ROOT / "experiments" / "news" / "strategy"
                  / "model.txt")
    model = AlphaModel.load(model_path, dict(base_cfg["model"]["params"]),
                            seed=base_cfg["model"]["seed"])
    m = f.dropna(how="all")
    preds = pd.Series(model.predict(m[model.feature_columns]),
                      index=m.index).sort_values(ascending=False)
    cand = preds.head(p["top_k"])
    print(f"universe: {len(symbols)}; candidates: {len(cand)}")

    # ---- v2 allocation at the date (PIT) ----------------------------------
    from portfolio.allocator import AllocationInput, allocate
    from portfolio.backtest import lot_floor
    from portfolio.constraints import PortfolioConstraints
    from portfolio.covariance import estimate_covariance

    cons = PortfolioConstraints.from_dict(p["constraints"])
    covres = estimate_covariance(data.close_raw, cand.index, signal_date,
                                 p["risk"]["window"], p["risk"]["covariance"],
                                 p["risk"].get("ewma_halflife"))
    cand_df = pd.DataFrame({"prediction": cand,
                            "raw_rank": range(1, len(cand) + 1)})
    cand_df["vol"] = covres.vols.reindex(cand_df.index)
    cand_df["industry"] = data.industries.reindex(cand_df.index)
    liq_cap = None
    if cons.liquidity_frac:
        amt = data.amount_cny.loc[:signal_date, cand.index].tail(20).mean()
        liq_cap = (cons.liquidity_frac * amt / args.capital).clip(
            upper=cons.max_weight)
        cand_df["liq_cap"] = liq_cap
    else:
        cand_df["liq_cap"] = np.nan

    prev_w = pd.Series(dtype=float)
    prev_shares = pd.Series(dtype=int)
    if STATE_PATH.exists():
        st = pd.read_parquet(STATE_PATH)
        if len(st) and "symbol" in st.columns:
            prev_w = st.set_index("symbol")["weight"]
            if "shares" in st.columns:
                prev_shares = st.set_index("symbol")["shares"]
    inp = AllocationInput(
        date=signal_date, candidates=cand_df, cov=covres,
        prev_weights=prev_w, constraints=cons,
        cost_model=TransactionCostModel.from_config(base_cfg),
        method=p["allocation_method"], params=p["method_params"])
    alloc = allocate(inp)
    target = alloc.weights
    print(f"allocator: {p['allocation_method']} "
          f"status={alloc.optimizer_status}")

    # ---- paper-live sizing: target weights -> shares -> BUY/SELL/HOLD -----
    cost = TransactionCostModel.from_config(base_cfg)
    px = data.close_raw.loc[:signal_date, target.index].ffill().iloc[-1]
    rows = []
    traded = 0.0
    fees_total = 0.0
    state_rows = []
    for sym, w in target.items():
        p0 = px.get(sym)
        if p0 is None or not np.isfinite(p0):
            continue
        target_value = args.capital * w
        target_shares = lot_floor(target_value, p0, cons.lot_size)
        cur_shares = int(prev_shares.get(sym, 0))
        delta = target_shares - cur_shares
        if delta > 0:
            action = "BUY"
            fee = cost.buy_cost(delta * p0)
        elif delta < 0:
            action = "SELL"
            fee = cost.sell_cost(-delta * p0)
        elif target_shares == 0 and cur_shares == 0:
            # target value below one lot at this price: not tradable
            action = "SKIP(below_1_lot)"
            fee = 0.0
        else:
            action = "HOLD"
            fee = 0.0
        traded += abs(delta) * p0
        fees_total += fee
        exec_w = target_shares * p0 / args.capital
        state_rows.append({"symbol": sym, "weight": exec_w,
                           "shares": target_shares, "date": signal_date})
        rows.append({
            "date": signal_date, "symbol": sym, "action": action,
            "prediction": float(cand[sym]), "raw_rank":
                int(cand_df.loc[sym, "raw_rank"]),
            "volatility": float(cand_df.loc[sym, "vol"]),
            "target_weight": float(w),
            "target_value": round(target_value, 2),
            "price": float(p0), "shares": target_shares,
            "delta_shares": delta, "exec_weight": exec_w,
            "estimated_fee": round(fee, 2),
            "industry": cand_df.loc[sym, "industry"],
            "optimizer_status": alloc.optimizer_status,
        })
    # holdings dropped from the new top-K: full SELL
    for sym in prev_shares.index:
        if sym in target.index or prev_shares.get(sym, 0) <= 0:
            continue
        p0 = data.close_raw.loc[:signal_date, sym].ffill().iloc[-1]
        if p0 is None or not np.isfinite(p0):
            continue
        sell_shares = int(prev_shares[sym])
        fee = cost.sell_cost(sell_shares * p0)
        traded += sell_shares * p0
        fees_total += fee
        rows.append({
            "date": signal_date, "symbol": sym, "action": "SELL",
            "prediction": None, "raw_rank": None, "volatility": None,
            "target_weight": 0.0, "target_value": 0.0, "price": float(p0),
            "shares": 0, "delta_shares": -sell_shares, "exec_weight": 0.0,
            "estimated_fee": round(fee, 2), "industry": None,
            "optimizer_status": alloc.optimizer_status,
        })
    df = pd.DataFrame(rows)
    invested = float((df["shares"] * df["price"]).sum())
    turnover = traded / (2.0 * args.capital)
    out_dir = PROJECT_ROOT / "reports" / "paper_live"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "latest_recommendation_v2.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    pd.DataFrame(state_rows).to_parquet(STATE_PATH, index=False)
    print(f"\n===== PAPER LIVE strategy_v2 {signal_date.date()} "
          f"(capital {args.capital:,.0f}, research only) =====")
    print(df[["symbol", "action", "shares", "target_weight", "prediction",
              "industry"]].to_string(index=False))
    n_skip = int((df["action"].str.startswith("SKIP")).sum())
    print(f"\ninvested (actual lots): {invested:,.0f} "
          f"({invested/args.capital:.1%}); estimated turnover: "
          f"{turnover:.3f}; estimated fees: {fees_total:,.0f}; residual "
          f"cash: {args.capital - invested:,.0f}"
          + (f"; skipped (below 1 lot): {n_skip}" if n_skip else ""))
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
