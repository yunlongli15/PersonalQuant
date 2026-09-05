# -*- coding: utf-8 -*-
"""STEP 2 cross-validation of the canonical data layer vs Qlib.

Part A - conversion integrity: canonical daily_bars (Parquet, ingested from
         the Qlib baseline .bin files) vs a direct Qlib D.features read of
         the same 20 stocks x 2 years. Expects EXACT equality (same source).
Part B - independent source: 10 stocks x recent 2 years from EastMoney
         (akshare, unadjusted) vs the canonical layer (Yahoo-sourced
         baseline). Differences are EXPECTED (vendor, suspension handling);
         this part reports them honestly rather than forcing equality.
Part C - trading calendar: canonical calendar (Qlib baseline) vs Sina's
         trade-date list (2020-2026 overlap).

Usage: python scripts/crosscheck_qlib.py [--offline]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from personal_quant import config, db

PART_A_STOCKS = [
    "600519", "000001", "600036", "601318", "000651", "600000", "600030",
    "000333", "601988", "600887", "002415", "600028", "601857", "000002",
    "600276", "300750", "601012", "603288", "000858", "600809",
]
PART_A_YEARS = (2019, 2020)
PART_B_STOCKS = ["600519", "000001", "600036", "601318", "000651",
                 "600000", "000333", "601988", "300750", "600887"]
PART_B_YEARS = (2023, 2024)


def part_a() -> dict:
    from personal_quant.providers.qlib_baseline import load_bars

    qlib_symbols = [f"{'SH' if c.startswith(('6', '68')) else 'SZ'}{c}"
                    for c in PART_A_STOCKS]
    ref = load_bars(qlib_symbols, f"{PART_A_YEARS[0]}-01-01",
                    f"{PART_A_YEARS[1]}-12-31").reset_index()
    ref = ref.rename(columns={c: c for c in ref.columns})
    # canonical stores raw prices (source values / factor); apply the same
    # transformation to the reference side so the comparison is raw-vs-raw
    for c in ["open", "high", "low", "close", "vwap"]:
        ref[c] = ref[c] / ref["factor"]
    syms = [f"{s}.SH" if s.startswith(("6", "68")) else f"{s}.SZ"
            for s in PART_A_STOCKS]
    conn = db.connect()
    got = conn.execute(
        "SELECT symbol, trade_date, close, volume, amount, vwap FROM daily_bars "
        "WHERE trade_date BETWEEN ? AND ? AND symbol IN (SELECT unnest(?::VARCHAR[]))",
        [f"{PART_A_YEARS[0]}-01-01", f"{PART_A_YEARS[1]}-12-31", syms],
    ).fetch_df()
    got["qlib_symbol"] = got["symbol"].str.split(".").str[::-1].str.join("")
    m = ref.merge(got, on=["qlib_symbol", "trade_date"], how="inner",
                  suffixes=("_ref", "_got"))
    fields = ["close", "volume", "amount", "vwap"]
    out = {"n_rows": int(len(m)), "n_ref": int(len(ref)), "n_got": int(len(got))}
    for f in fields:
        a, b = m[f"{f}_ref"], m[f"{f}_got"]
        diff = (a - b).abs()
        out[f"{f}_exact_match"] = float((diff == 0).mean())
        out[f"{f}_max_abs_diff"] = float(diff.max())
    return out


def part_b() -> dict:
    from personal_quant.providers.akshare_market import AkShareMarketProvider

    provider = AkShareMarketProvider()
    conn = db.connect()
    rows = []
    for code in PART_B_STOCKS:
        sym = f"{code}.SH" if code.startswith(("6", "68")) else f"{code}.SZ"
        try:
            em = provider.fetch_daily_history(
                sym, f"{PART_B_YEARS[0]}-01-01", f"{PART_B_YEARS[1]}-12-31"
            )
        except Exception as e:
            rows.append({"symbol": sym, "n_days": 0, "error": str(e)[:80]})
            continue
        base = conn.execute(
            "SELECT trade_date, close FROM daily_bars WHERE symbol=? "
            "AND trade_date BETWEEN ? AND ? ORDER BY trade_date",
            [sym, f"{PART_B_YEARS[0]}-01-01", f"{PART_B_YEARS[1]}-12-31"],
        ).fetch_df()
        m = em.merge(base, on="trade_date", suffixes=("_em", "_canon"))
        if m.empty:
            rows.append({"symbol": sym, "n_days": 0, "error": "no overlap"})
            continue
        rel = ((m["close_em"] - m["close_canon"]).abs() / m["close_canon"])
        rows.append(
            {
                "symbol": sym,
                "n_days": int(len(m)),
                "close_match_exact_share": float((m["close_em"] == m["close_canon"]).mean()),
                "close_mean_abs_rel_diff": float(rel.mean()),
                "close_max_abs_rel_diff": float(rel.max()),
            }
        )
    return {"rows": rows}


def part_c() -> dict:
    from personal_quant.providers.akshare_market import AkShareMarketProvider

    provider = AkShareMarketProvider()
    sina = provider.fetch_calendar_crosscheck()
    conn = db.connect()
    cal = conn.execute(
        "SELECT DISTINCT trade_date FROM trading_calendar "
        "WHERE trade_date BETWEEN '2020-01-01' AND '2026-12-31'"
    ).fetch_df()["trade_date"]
    lo, hi = pd.Timestamp("2020-01-01"), pd.Timestamp("2026-12-31")
    sina_days = set(
        d for d in pd.to_datetime(sina["trade_date"]).dt.normalize()
        if lo <= d <= hi
    )
    cal_days = set(pd.to_datetime(cal).dt.normalize())
    only_cal = sorted(cal_days - sina_days)
    only_sina = sorted(sina_days - cal_days)
    return {
        "window": "2020-01-01..2026-12-31",
        "n_calendar": int(len(cal_days)),
        "n_sina": int(len(sina_days)),
        "intersection": int(len(cal_days & sina_days)),
        "only_in_canonical": [str(d.date()) for d in only_cal][:10],
        "n_only_in_canonical": int(len(only_cal)),
        "n_only_in_sina": int(len(only_sina)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()
    if args.offline:
        import os

        os.environ["PQ_MODE"] = "offline"
        config.MODE = "offline"

    print("Part A: canonical vs Qlib direct read (conversion integrity)")
    a = part_a()
    for k, v in a.items():
        print(f"  {k}: {v}")

    print("Part B: canonical vs EastMoney (independent source, expected diffs)")
    b = part_b()
    for r in b["rows"]:
        print(f"  {r}")

    print("Part C: trading calendar vs Sina")
    c = part_c()
    for k, v in c.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
