# -*- coding: utf-8 -*-
"""STEP 4 market data continuity audit (offline, read-only).

Detects and characterizes data-quality issues in canonical daily_bars:

  A. spurious adjustment-factor discontinuities (repair_factors pattern)
  B. day-over-day jump census per field (close/volume/amount/vwap/factor)
     for |ratio-1| > 1.0 / 2.0 / 5.0  (i.e. +/-100/200/500%)
  C. volume/amount scaling shifts: sustained level changes without a price
     move (Yahoo adjusted-volume artifacts)
  D. amount/(close*volume) consistency ("k ratio"): per-stock median,
     spread, within-stock variation, level shifts — a volume-vs-amount unit
     mismatch shows up as k far from 1
  E. vwap bounds: vwap within [low, high] (+0.5% tolerance)
  F. basic sanity: amount>0 iff volume>0; low<=open/close<=high; close>0

Read-only over the daily_bars view; results are written to
data/derived/audit/market_continuity.json and printed.

    python scripts/audit_market_data.py [--start 2015-01-01] [--end 2026-12-31]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from personal_quant import db

OUT = Path(__file__).resolve().parents[1] / "data" / "derived" / "audit"


def _q(conn, sql, params=None):
    return conn.execute(sql, params or []).fetch_df()


def audit_factor_jumps(conn, start, end):
    """A. factor/prev_factor > 2 with |close move| < 15% (spurious)."""
    row = _q(conn, f"""
        WITH px AS (
          SELECT symbol, trade_date, close, factor,
                 LAG(close) OVER w prev_close,
                 LAG(factor) OVER w prev_factor
          FROM daily_bars WHERE trade_date >= '{start}' AND trade_date <= '{end}'
          WINDOW w AS (PARTITION BY symbol ORDER BY trade_date)
        )
        SELECT COUNT(*) n_events, COUNT(DISTINCT symbol) n_symbols
        FROM px
        WHERE prev_factor > 0 AND factor/prev_factor > 2.0
          AND prev_close > 0 AND abs(close/prev_close - 1) < 0.15
    """)
    return {c: int(row[c].iloc[0]) for c in ("n_events", "n_symbols")}


def audit_jump_census(conn, start, end):
    """B. day-over-day |ratio-1| census per field."""
    fields = ["close", "volume", "amount", "vwap", "factor"]
    out = {}
    for f in fields:
        row = _q(conn, f"""
            WITH px AS (
              SELECT symbol, close, volume, amount, vwap, factor,
                     LAG({f}) OVER (PARTITION BY symbol ORDER BY trade_date) prev
              FROM daily_bars
              WHERE trade_date >= '{start}' AND trade_date <= '{end}'
            )
            SELECT
              COUNT(*) FILTER (WHERE prev > 0 AND abs({f}/prev - 1) > 1.0) g100,
              COUNT(*) FILTER (WHERE prev > 0 AND abs({f}/prev - 1) > 2.0) g200,
              COUNT(*) FILTER (WHERE prev > 0 AND abs({f}/prev - 1) > 5.0) g500
            FROM px
        """)
        out[f] = {c: int(row[c].iloc[0]) for c in ("g100", "g200", "g500")}
    return out


def audit_scale_shifts(conn, start, end):
    """C. volume/amount scaling shifts without a price move.

    vol20 = mean volume over the trailing 20 rows; a shift event = the
    20-row mean changes >3x across a 20-row gap while close moved <15%.
    """
    row = _q(conn, f"""
        WITH px AS (
          SELECT symbol, trade_date, close, volume, amount,
                 AVG(volume) OVER (PARTITION BY symbol ORDER BY trade_date
                                   ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) vol20,
                 AVG(amount) OVER (PARTITION BY symbol ORDER BY trade_date
                                   ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) amt20
          FROM daily_bars
          WHERE trade_date >= '{start}' AND trade_date <= '{end}'
        ),
        lagged AS (
          SELECT *, LAG(vol20, 20) OVER (PARTITION BY symbol ORDER BY trade_date) prev_vol20,
                    LAG(amt20, 20) OVER (PARTITION BY symbol ORDER BY trade_date) prev_amt20,
                    LAG(close, 20) OVER (PARTITION BY symbol ORDER BY trade_date) prev_close
          FROM px
        )
        SELECT
          COUNT(*) FILTER (WHERE prev_vol20 > 0 AND vol20/prev_vol20 > 3.0
                           AND prev_close > 0 AND abs(close/prev_close - 1) < 0.15) vol_up,
          COUNT(*) FILTER (WHERE prev_vol20 > 0 AND prev_vol20/vol20 > 3.0
                           AND prev_close > 0 AND abs(close/prev_close - 1) < 0.15) vol_dn,
          COUNT(*) FILTER (WHERE prev_amt20 > 0 AND amt20/prev_amt20 > 3.0
                           AND prev_close > 0 AND abs(close/prev_close - 1) < 0.15) amt_up,
          COUNT(*) FILTER (WHERE prev_amt20 > 0 AND prev_amt20/amt20 > 3.0
                           AND prev_close > 0 AND abs(close/prev_close - 1) < 0.15) amt_dn
        FROM lagged
    """)
    return {c: int(row[c].iloc[0]) for c in ("vol_up", "vol_dn", "amt_up", "amt_dn")}


def audit_k_ratio(conn, start, end):
    """D. k = amount/(close*volume): median per stock + histogram + CV."""
    med = _q(conn, f"""
        SELECT symbol, MEDIAN(k) med_k, AVG(k) mean_k, STDDEV(k) std_k,
               COUNT(*) n, COUNT(k) n_k
        FROM (SELECT symbol, amount/(close*volume) k
              FROM daily_bars
              WHERE trade_date >= '{start}' AND trade_date <= '{end}'
                AND close > 0 AND volume > 0 AND amount > 0)
        GROUP BY symbol HAVING COUNT(*) >= 30
    """)
    med["cv"] = med["std_k"] / med["mean_k"]
    hist = _q(conn, f"""
        WITH k AS (
          SELECT symbol, MEDIAN(amount/(close*volume)) med_k
          FROM daily_bars
          WHERE trade_date >= '{start}' AND trade_date <= '{end}'
            AND close > 0 AND volume > 0 AND amount > 0
          GROUP BY symbol HAVING COUNT(*) >= 30
        )
        SELECT ROUND(log10(med_k), 1) log10k, COUNT(*) n
        FROM k GROUP BY 1 ORDER BY 1
    """)
    return {
        "n_symbols": int(len(med)),
        "median_k": float(med["med_k"].median()),
        "p10_k": float(med["med_k"].quantile(0.10)),
        "p90_k": float(med["med_k"].quantile(0.90)),
        "p01_k": float(med["med_k"].quantile(0.01)),
        "p99_k": float(med["med_k"].quantile(0.99)),
        "frac_k_in_0p1_10": float(((med["med_k"] > 0.1) & (med["med_k"] < 10)).mean()),
        "median_cv": float(med["cv"].median()),
        "frac_cv_lt_1": float((med["cv"] < 1.0).mean()),
        "log10_histogram": {str(r["log10k"]): int(r["n"]) for _, r in hist.iterrows()},
    }


def audit_vwap_bounds(conn, start, end):
    """E. vwap within [low, high] (+0.5% tolerance)."""
    row = _q(conn, f"""
        SELECT COUNT(*) n,
               COUNT(*) FILTER (WHERE vwap < low*0.995 OR vwap > high*1.005) bad
        FROM daily_bars
        WHERE trade_date >= '{start}' AND trade_date <= '{end}'
          AND vwap IS NOT NULL AND low IS NOT NULL AND high IS NOT NULL
    """)
    return {"n": int(row["n"].iloc[0]), "violations": int(row["bad"].iloc[0])}


def audit_basic_sanity(conn, start, end):
    """F. amount/volume sign consistency + OHLC ordering."""
    row = _q(conn, f"""
        SELECT COUNT(*) n,
          COUNT(*) FILTER (WHERE volume <= 0) vol_bad,
          COUNT(*) FILTER (WHERE amount <= 0 AND volume > 0) amt_zero_with_vol,
          COUNT(*) FILTER (WHERE close <= 0) close_bad,
          COUNT(*) FILTER (WHERE low > open OR low > close OR high < open OR high < close) ohlc_bad
        FROM daily_bars
        WHERE trade_date >= '{start}' AND trade_date <= '{end}'
    """)
    return {c: int(row[c].iloc[0]) for c in
            ("n", "vol_bad", "amt_zero_with_vol", "close_bad", "ohlc_bad")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2015-01-01")
    ap.add_argument("--end", default="2026-12-31")
    args = ap.parse_args()

    conn = db.connect()
    report = {
        "window": [args.start, args.end],
        "factor_jumps": audit_factor_jumps(conn, args.start, args.end),
        "jump_census": audit_jump_census(conn, args.start, args.end),
        "scale_shifts": audit_scale_shifts(conn, args.start, args.end),
        "k_ratio": audit_k_ratio(conn, args.start, args.end),
        "vwap_bounds": audit_vwap_bounds(conn, args.start, args.end),
        "basic_sanity": audit_basic_sanity(conn, args.start, args.end),
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "market_continuity.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"wrote {OUT / 'market_continuity.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
