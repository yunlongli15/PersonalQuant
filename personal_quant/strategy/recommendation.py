# -*- coding: utf-8 -*-
"""Paper-live recommendation generation (research only, no trading)."""

from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional

import pandas as pd

from .. import db
from .universe import build_universe

LOT = 100


def generate_recommendation(
    date: pd.Timestamp,
    config: dict,
    predictor: Callable[[pd.Timestamp, List[str]], pd.Series],
    capital: float,
    current_positions: Optional[Dict[str, int]] = None,
    model_version: str = "strategy_v1",
    dataset_version: str = "canonical",
    feature_version: str = "alpha158",
) -> pd.DataFrame:
    """Produce the paper-live target portfolio for `date`.

    current_positions: {symbol: shares} (default empty).
    Output columns: symbol, name, rank, predicted_return, target_weight,
    target_value, current_weight, current_value, action, estimated_shares.
    """
    current_positions = current_positions or {}
    cfg = config
    universe = build_universe(date, cfg)
    if universe.empty:
        raise RuntimeError(f"empty universe at {date.date()}")
    scores = predictor(date, universe["symbol"].tolist())
    scores = scores.dropna().sort_values(ascending=False)
    picks = scores.head(cfg["portfolio"]["top_k"])
    w_stock = (1.0 - cfg["portfolio"]["cash_buffer"]) / cfg["portfolio"]["top_k"]

    names = db.connect().execute(
        "SELECT symbol, name FROM securities WHERE symbol IN (SELECT unnest(?::VARCHAR[]))",
        [list(picks.index)],
    ).fetch_df().set_index("symbol")["name"].to_dict()

    rows = []
    for i, sym in enumerate(picks.index):
        px_row = db.connect().execute(
            "SELECT close FROM daily_bars WHERE symbol=? AND trade_date<=? "
            "ORDER BY trade_date DESC LIMIT 1", [sym, date]
        ).fetch_df()
        px = float(px_row["close"].iloc[0]) if not px_row.empty else None
        if px is None:
            continue
        target_value = capital * w_stock
        cur_shares = current_positions.get(sym, 0)
        cur_value = cur_shares * px
        delta = target_value - cur_value
        action = "HOLD"
        est_shares = cur_shares
        if delta > 0 and math.floor(delta / px / LOT) * LOT >= LOT:
            action = "BUY"
            est_shares = cur_shares + math.floor(delta / px / LOT) * LOT
        elif delta < 0:
            sell = min(int(math.ceil(abs(delta) / px)), cur_shares)
            if sell > 0:
                action = "SELL"
                est_shares = cur_shares - sell
        rows.append(
            {
                "symbol": sym,
                "name": names.get(sym),
                "rank": i + 1,
                "predicted_return": float(picks[sym]),
                "target_weight": w_stock,
                "target_value": round(target_value, 2),
                "current_weight": cur_value / capital if capital else 0.0,
                "current_value": round(cur_value, 2),
                "action": action,
                "estimated_shares": int(est_shares),
                "last_price": px,
            }
        )
    return pd.DataFrame(rows)
