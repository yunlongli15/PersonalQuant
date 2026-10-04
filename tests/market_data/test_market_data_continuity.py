# -*- coding: utf-8 -*-
"""Market data continuity checks against the canonical layer.

These are the automated, permanent form of the STEP 4 market-data audit
(docs/步骤4-市场数据质量.md). Thresholds were calibrated from the
audit run (data/derived/audit/market_continuity.json).

The checks are skipped (not failed) when the DuckDB file is locked by
another process (the financial fetcher) — the full suite is re-run at
verification time.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import duckdb
import pandas as pd
import pytest

from personal_quant import config, db

START, END = "2015-01-01", "2026-12-31"


@pytest.fixture(scope="module")
def conn():
    try:
        c = db.connect()
        c.execute("SELECT COUNT(*) FROM daily_bars").fetchone()
        return c
    except duckdb.IOException:
        pytest.skip("DuckDB file is locked by another process")


def test_no_spurious_factor_jumps(conn):
    """repair_factors_v1 invariant: zero factor jumps >2x without a price
    move (fake corporate-action records)."""
    row = conn.execute(f"""
        WITH px AS (
          SELECT close, factor,
                 LAG(close) OVER w prev_close,
                 LAG(factor) OVER w prev_factor
          FROM daily_bars WHERE trade_date >= '{START}'
          WINDOW w AS (PARTITION BY symbol ORDER BY trade_date)
        )
        SELECT COUNT(*) n FROM px
        WHERE prev_factor > 0 AND factor/prev_factor > 2.0
          AND prev_close > 0 AND abs(close/prev_close - 1) < 0.15
    """).fetchone()
    assert row[0] == 0


def test_amount_close_volume_ratio_stable_within_stock(conn):
    """The per-stock amount/(close*volume) ratio is constant within a stock
    (CV < 1 for essentially every stock) — volume and amount share the same
    per-stock scaling, so a within-stock ratio factor is safe."""
    df = conn.execute(f"""
        SELECT symbol, STDDEV(k)/AVG(k) cv FROM (
          SELECT symbol, amount/(close*volume) k FROM daily_bars
          WHERE trade_date >= '{START}' AND close > 0
            AND volume > 0 AND amount > 0)
        GROUP BY symbol HAVING COUNT(*) >= 100
    """).fetch_df()
    assert len(df) > 4000
    assert (df["cv"] < 1.0).mean() >= 0.99


def test_vwap_within_high_low(conn):
    row = conn.execute(f"""
        SELECT COUNT(*) n,
               COUNT(*) FILTER (WHERE vwap < low*0.995 OR vwap > high*1.005) bad
        FROM daily_bars
        WHERE trade_date >= '{START}' AND vwap IS NOT NULL
    """).fetchone()
    assert row[1] / row[0] < 0.005


def test_basic_ohlc_sanity(conn):
    row = conn.execute(f"""
        SELECT COUNT(*) FILTER (WHERE volume <= 0 OR close <= 0) bad_sign,
               COUNT(*) FILTER (WHERE low > open OR low > close
                                OR high < open OR high < close) bad_ohlc,
               COUNT(*) n
        FROM daily_bars WHERE trade_date >= '{START}'
    """).fetchone()
    assert row[0] == 0
    assert row[1] == 0


def test_market_scale_table_integrity():
    """The STEP 4 repair product: per-stock calibration multipliers with
    stable constant-scale evidence (ratio CV < 0.3)."""
    scale_path = config.PARQUET_SUBDIRS["market"] / "market_scale.parquet"
    if not scale_path.exists():
        pytest.skip("market_scale.parquet not yet generated "
                    "(calibrate_market_scale.py)")
    df = pd.read_parquet(scale_path)
    assert {"symbol", "scale_volume", "ratio_cv", "repair_version"} <= set(df.columns)
    cal = df[df["n_overlap"] > 0]
    assert (cal["scale_volume"] > 0).all()
    ok = df[df["n_overlap"] >= 10]
    if len(ok) < 500:
        pytest.skip("market_scale calibration still running "
                    f"(only {len(ok)} stocks calibrated)")
    assert len(ok) >= 4000
    assert (ok["ratio_cv"] < 0.3).mean() >= 0.9


def test_calibration_recorded_in_source_registry(conn):
    """raw -> detection -> repair -> validation must be registered."""
    n = conn.execute(
        "SELECT COUNT(*) FROM source_registry "
        "WHERE source_name IN ('factor_repair_v1', 'market_scale_repair_v1')"
    ).fetchone()[0]
    assert n >= 1
