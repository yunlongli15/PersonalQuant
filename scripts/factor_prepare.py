# -*- coding: utf-8 -*-
"""STEP 4 factor-research data preparation (one-time DuckDB bursts).

Produces DB-free DERIVED caches under data/derived/factors/ so the research
scripts can run while other processes (financial fetcher) hold the DuckDB
lock:

  calendar.parquet           official trading calendar
  industries.parquet         symbol -> CSRC industry (current)
  labels.parquet             forward returns: date, horizon, symbol, label
                             (adjusted_close[t+h]/adjusted_close[t]-1,
                             calendar shift — same definition as
                             strategy_v1's label)
  universes.parquet          date, symbol, universe ('full'|'financial')
  financial_metrics.parquet  snapshot of the PIT financial_metrics table

The research universe follows the strategy_v1 rules with ONE documented
deviation: liquidity uses the calibrated amount (amount_cny; see
docs/step4_market_data_quality.md) instead of raw source units, because
the raw amount is not comparable across stocks. strategy_v1 itself is
frozen and untouched.

    python scripts/factor_prepare.py
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from personal_quant import db
from personal_quant.strategy.rebalance import rebalance_dates

from factors.base import (DERIVED, FactorData, load_factor_data)

HORIZONS = [1, 5, 10, 20, 40, 60]


def prepare_calendar() -> None:
    conn = db.connect()
    days = conn.execute(
        "SELECT trade_date FROM trading_calendar WHERE is_open ORDER BY trade_date"
    ).fetch_df()
    days.to_parquet(DERIVED / "calendar.parquet", index=False)
    print(f"calendar: {len(days)} days")


def prepare_industries() -> None:
    conn = db.connect()
    df = conn.execute(
        "SELECT symbol, industry_name FROM industry_membership "
        "WHERE classification='csrc' AND industry_name IS NOT NULL"
    ).fetch_df()
    df = df.groupby("symbol")["industry_name"].last().reset_index()
    df.to_parquet(DERIVED / "industries.parquet", index=False)
    print(f"industries: {len(df)} symbols")


def prepare_labels(data: FactorData, dates) -> None:
    """Forward returns per (date, horizon, symbol)."""
    adj = data.adj_close
    rows = []
    for h in HORIZONS:
        fwd = adj.shift(-h) / adj - 1.0
        sub = fwd.reindex(pd.DatetimeIndex(dates))
        long = sub.reset_index().melt(id_vars="index")
        long.columns = ["date", "symbol", "label"]
        long["horizon"] = h
        rows.append(long.dropna(subset=["label"]))
    out = pd.concat(rows, ignore_index=True)
    out.to_parquet(DERIVED / "labels.parquet", index=False)
    print(f"labels: {len(out):,} rows "
          f"({len(dates)} dates x {len(HORIZONS)} horizons)")


def prepare_universes(data: FactorData, dates, config: dict,
                      top_n_financial: int) -> None:
    """Per-date research universe + financial sub-universe.

    Same rules as strategy_v1 (exchanges, listing age via list_date with
    first-bar proxy, delist date, suspension window, liquidity), with two
    documented deviations: liquidity uses the calibrated amount_cny
    (cross-stock comparable; strategy_v1's raw amount is not) over a
    20-trading-day window (strategy_v1 uses a 40-calendar-day window —
    same intent). strategy_v1 itself stays frozen.
    """
    cfg = config["factor_research"]["universe"]
    conn = db.connect()
    sec = conn.execute(
        "SELECT symbol, exchange, list_date, delist_date FROM securities"
    ).fetch_df()
    sec["list_date"] = pd.to_datetime(sec["list_date"])
    sec["delist_date"] = pd.to_datetime(sec["delist_date"])
    # index pseudo-instruments share stock code ranges in the qlib source —
    # exclude them explicitly (documented in the config)
    sec = sec[~sec["symbol"].isin(cfg.get("index_exclude", []))]

    fin_list = pd.DataFrame()
    top = conn.execute(
        "SELECT symbol FROM daily_valuation WHERE trade_date = "
        "(SELECT MAX(trade_date) FROM daily_valuation) "
        "ORDER BY total_market_cap DESC "
        f"LIMIT {int(top_n_financial)}"
    ).fetch_df()
    if len(top):
        top_set = set(top["symbol"])
        fin_list = pd.DataFrame({"symbol": sorted(top_set)})
    print(f"financial universe anchor: top-{len(fin_list)} by current "
          f"market cap")

    # per-symbol eligibility constants
    min_days = int(cfg["min_listing_days"])
    age_cutoff = pd.Timedelta(days=float(min_days) * 1.5)
    sec = sec[sec["exchange"].isin(cfg["exchanges"])]
    eligible = {}
    for _, r in sec.iterrows():
        if pd.notna(r["list_date"]):
            eligible[r["symbol"]] = r["list_date"] + age_cutoff
    no_list = sec[sec["list_date"].isna()]["symbol"]
    if len(no_list):
        first = data.bars.groupby("symbol")["trade_date"].min()
        for s in no_list:
            if s in first.index:
                eligible[s] = first[s] + age_cutoff
    delist = sec.set_index("symbol")["delist_date"].to_dict()

    has_bar = data.adj_close.notna()
    # suspension rule (strategy_v1): last trade within max_absent_days*1.5
    # calendar days
    absent = int(cfg["suspension"]["max_absent_days"])
    traded_ok = has_bar.rolling(max(1, int(absent * 1.5)), min_periods=1
                                ).max().fillna(False).astype(bool)

    if cfg["liquidity"]["enabled"]:
        win = int(cfg["liquidity"]["window_days"])
        thr = float(cfg["liquidity"]["min_amount_cny"])
        liq_ok = data.amount_cny.rolling(win).mean() >= thr
        if not data.scale_available:
            print("WARNING: market_scale.parquet missing — liquidity uses "
                  "UNcalibrated amount (results not comparable across "
                  "stocks); run scripts/calibrate_market_scale.py first")
    else:
        liq_ok = has_bar.copy()
        liq_ok[:] = True

    elig_s = pd.Series(eligible)
    delist_s = sec.set_index("symbol")["delist_date"]
    rows = []
    for d in pd.DatetimeIndex(dates):
        cols = has_bar.columns
        alive = pd.isna(delist_s.reindex(cols)) | (delist_s.reindex(cols) > d)
        old = elig_s.reindex(cols).fillna(pd.Timestamp.max) <= d
        keep = cols[alive.values & old.values
                    & traded_ok.loc[d, cols].values
                    & liq_ok.loc[d, cols].values]
        if not len(keep):
            continue
        rows.append(pd.DataFrame({"date": d, "symbol": keep,
                                  "universe": "full"}))
        if len(fin_list):
            fin_cols = [s for s in keep if s in set(fin_list["symbol"])]
            if fin_cols:
                rows.append(pd.DataFrame({"date": d, "symbol": fin_cols,
                                          "universe": "financial"}))
    out = pd.concat(rows, ignore_index=True)
    out.to_parquet(DERIVED / "universes.parquet", index=False)
    n_full = out[out["universe"] == "full"].groupby("date")["symbol"].count()
    n_fin = out[out["universe"] == "financial"].groupby("date")["symbol"].count()
    print(f"universes: {len(out):,} rows; full per date "
          f"{n_full.min()}-{n_full.max()} (median {n_full.median():.0f}); "
          f"financial per date {n_fin.min()}-{n_fin.max()}")


def prepare_financial_snapshot() -> None:
    conn = db.connect()
    df = conn.execute(
        "SELECT symbol, fiscal_year, fiscal_period, availability_date, "
        "availability_date_unknown, metric_name, metric_value "
        "FROM financial_metrics"
    ).fetch_df()
    df.to_parquet(DERIVED / "financial_metrics.parquet", index=False)
    print(f"financial snapshot: {len(df)} metric rows")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2017-01-01",
                    help="bars load start (labels/universe window)")
    ap.add_argument("--end", default="2026-12-31")
    args = ap.parse_args()

    import yaml

    cfg = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "config"
         / "factor_research.yaml").read_text(encoding="utf-8")
    )
    ts = cfg["factor_research"]["time_split"]
    dates = rebalance_dates(args.start, args.end)

    DERIVED.mkdir(parents=True, exist_ok=True)
    prepare_calendar()
    prepare_industries()
    data = load_factor_data(args.start, args.end, use_cache=False)
    print(f"bars loaded: {len(data.bars):,} rows, "
          f"{data.calendar[0].date()}..{data.calendar[-1].date()}, "
          f"scale_available={data.scale_available}")
    prepare_labels(data, dates)
    prepare_universes(data, dates, cfg,
                      int(cfg["factor_research"]["universe"]
                          ["financial_universe"]
                          ["top_n_by_current_market_cap"]))
    prepare_financial_snapshot()
    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
