# -*- coding: utf-8 -*-
"""Dynamic investment universe (point-in-time, no survivorship bias).

Every rebalance date gets its own universe computed strictly from data
available at that date:
  - listed for >= min_listing_days (list_date; delisted stocks included with
    their real trading history, listing proxied by first bar when list_date
    is unknown — documented, never fabricated)
  - active at the date (delist_date)
  - not suspended (has bars within max_absent_days before the date)
  - liquidity: 20d average amount >= threshold
  - ST filter: only for dates where a reliable ST status exists (current
    snapshot); in historical backtest it is disabled — see config note.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from .. import db
from ..symbols import normalize_symbol

BAR_FIELDS_SQL = {
    "close": "close",
    "amount": "amount",
}


def _q(sql: str, params=None) -> pd.DataFrame:
    return db.connect().execute(sql, params or []).fetch_df()


def load_securities() -> pd.DataFrame:
    return _q(
        "SELECT symbol, exchange, list_date, delist_date, is_st FROM securities"
    )


def first_bar_date(symbol: str) -> Optional[pd.Timestamp]:
    r = _q(
        "SELECT MIN(trade_date) d FROM daily_bars WHERE symbol=?", [symbol]
    )
    return r.iloc[0]["d"] if len(r) else None


def build_universe(
    date: pd.Timestamp,
    config: dict,
    securities: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Return the investable universe at `date` (symbol rows with metadata).

    `date` is the signal date (T); the universe is computed from data up to
    and including T only.
    """
    cfg = config["universe"]
    if securities is None:
        securities = load_securities()
    sec = securities[securities["exchange"].isin(cfg["exchanges"])].copy()

    # 1) delisted before/at date -> out
    sec = sec[sec["delist_date"].isna() | (sec["delist_date"] > date)]

    # 2) listing age >= min_listing_days
    min_days = cfg["min_listing_days"]
    if min_days and min_days > 0:
        cutoff = date - pd.Timedelta(days=min_days * 1.5)
        has_list = sec["list_date"].notna()
        age_ok = has_list & (sec["list_date"] <= cutoff)
        # symbols without a real list_date: use first bar date as a lower
        # bound proxy (documented approximation for delisted names) — one
        # batched query, never per-symbol
        no_list = ~has_list
        if no_list.any():
            missing = list(sec.loc[no_list, "symbol"])
            fb = _q(
                "SELECT symbol, MIN(trade_date) d FROM daily_bars "
                "WHERE symbol IN (SELECT unnest(?::VARCHAR[])) GROUP BY symbol",
                [missing],
            )
            fb_map = {r["symbol"]: pd.Timestamp(r["d"]) for _, r in fb.iterrows()}
            proxy = pd.Series(
                {s: fb_map.get(s) is not None and fb_map[s] <= cutoff
                 for s in missing}
            )
            sec = sec[age_ok | proxy.reindex(sec.index).fillna(False)]
        else:
            sec = sec[age_ok]

    # 3) suspension: must have traded within the last max_absent_days
    absent = cfg["suspension"]["max_absent_days"]
    lo = date - pd.Timedelta(days=absent * 2)  # calendar slack for the window
    bars = _q(
        "SELECT symbol, MAX(trade_date) last_trade FROM daily_bars "
        "WHERE trade_date <= ? AND trade_date >= ? GROUP BY symbol",
        [date, lo],
    )
    bars = bars.set_index("symbol")
    sec = sec[sec["symbol"].map(
        lambda s: s in bars.index
        and (date - bars.at[s, "last_trade"]).days <= absent * 1.5
    )]

    # 4) liquidity: 20d average amount >= threshold (data through date only)
    if cfg["liquidity"].get("enabled"):
        win = cfg["liquidity"]["window_days"]
        thr = cfg["liquidity"]["min_amount"]
        lo2 = date - pd.Timedelta(days=win * 2)
        liq = _q(
            "SELECT symbol, AVG(amount) avg_amount FROM daily_bars "
            "WHERE trade_date <= ? AND trade_date >= ? GROUP BY symbol",
            [date, lo2],
        )
        liq = liq[liq["avg_amount"] >= thr]
        sec = sec[sec["symbol"].isin(liq["symbol"])]

    # 5) ST filter: only when a reliable status at `date` exists
    if cfg["st_filter"].get("enabled"):
        # historical ST series not available; this branch is used in paper
        # live mode (current snapshot) only — enforced by caller
        sec = sec[~sec["is_st"].fillna(False)]

    return sec.reset_index(drop=True)


def universe_symbols(date: pd.Timestamp, config: dict) -> list:
    return build_universe(date, config)["symbol"].tolist()
