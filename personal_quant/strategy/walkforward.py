# -*- coding: utf-8 -*-
"""Walk-forward evaluation: quarterly retraining, monthly rebalancing.

Training window rolls forward quarter by quarter over the evaluation period;
every month's signal uses the model trained strictly on data before that
month. No retraining frequency is hardcoded (config
model.training_frequency).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional

import pandas as pd

from .model import AlphaModel

QUARTERLY = "quarterly"


def _eval_t_plus_h(d: pd.Timestamp, horizon: int = 20) -> Optional[pd.Timestamp]:
    """The trading day `horizon` days after d (for realized-label evaluation)."""
    from .rebalance import trading_days

    days = trading_days()
    i = next((j for j, x in enumerate(days) if x >= d), None)
    if i is None or i + horizon >= len(days):
        return None
    return days[i + horizon]


def walk_forward_periods(start: str, end: str, frequency: str = QUARTERLY):
    """Yield (train_start, train_end, period_start, period_end) tuples.

    Rolling training window ends at the period start; the window length is
    kept fixed (the config train span) once enough history exists.
    """
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    window_years = 7  # fixed rolling window (config train span analogue)
    period_start = start_ts
    while period_start <= end_ts:
        if frequency == QUARTERLY:
            period_end = (period_start + pd.tseries.offsets.QuarterEnd(0)) + pd.Timedelta(days=1)
            period_end = period_end - pd.Timedelta(days=1)
        else:
            raise ValueError(f"unsupported frequency {frequency}")
        if period_end > end_ts:
            period_end = end_ts
        train_start = period_start - pd.DateOffset(years=window_years)
        yield (
            str(train_start.date()),
            str((period_start - pd.Timedelta(days=1)).date()),
            str(period_start.date()),
            str(period_end.date()),
        )
        period_start = period_end + pd.Timedelta(days=1)


def run_walk_forward(
    eval_start: str,
    eval_end: str,
    date_loader: Callable[[str, str], List[pd.Timestamp]],
    data_builder: Callable[[List[pd.Timestamp]], pd.DataFrame],
    config: dict,
    out_dir: Path,
) -> pd.DataFrame:
    """Quarterly retrain + monthly predict over [eval_start, eval_end].

    data_builder(dates) -> training rows (date x symbol features + label) for
    those dates; date_loader returns the rebalance dates of a period.
    Returns the full prediction frame (date, symbol, prediction, label).
    """
    params = dict(config["model"]["params"])
    seed = config["model"]["seed"]
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    periods = list(walk_forward_periods(eval_start, eval_end, QUARTERLY))
    for i, (tr_s, tr_e, pe_s, pe_e) in enumerate(periods):
        train_dates = date_loader(tr_s, tr_e)
        period_dates = date_loader(pe_s, pe_e)
        if not period_dates:
            continue
        # training rows strictly before the period (labels only from rows
        # whose horizon completes within the training span)
        train_df = data_builder(train_dates)
        X = train_df.drop(columns=["label", "date", "symbol"])
        y = train_df["label"]
        model = AlphaModel(params, seed)
        model.fit(X, y)
        # predict the period's dates; the label column (realized future
        # returns) is attached ONLY for evaluation, never as a model input
        feat_dates = data_builder(period_dates, labels=False)
        labels = {}
        from .. import db as _db

        for d in period_dates:
            f = feat_dates[feat_dates["date"] == d]
            if f.empty:
                continue
            conn = _db.connect()
            base = conn.execute(
                "SELECT symbol, close * factor AS adj FROM daily_bars "
                "WHERE trade_date = ? AND symbol IN (SELECT unnest(?::VARCHAR[]))",
                [d, list(f["symbol"])],
            ).fetch_df().set_index("symbol")["adj"]
            fwd = conn.execute(
                "SELECT symbol, close * factor AS adj FROM daily_bars "
                "WHERE trade_date = ? AND symbol IN (SELECT unnest(?::VARCHAR[]))",
                [_eval_t_plus_h(d, horizon=20), list(f["symbol"])],
            ).fetch_df().set_index("symbol")["adj"]
            labels[d] = (fwd / base - 1.0).dropna()
        preds = []
        for d in period_dates:
            sub = feat_dates[feat_dates["date"] == d]
            if sub.empty:
                continue
            p = model.predict(sub.drop(columns=["date", "symbol", "label"],
                                        errors="ignore"))
            lab = labels.get(d)
            preds.append(
                pd.DataFrame(
                    {"date": d, "symbol": sub["symbol"],
                     "prediction": p,
                     "label": sub["symbol"].map(lab) if lab is not None else pd.NA}
                )
            )
        if preds:
            frames.append(pd.concat(preds))
        model.save(out_dir / f"model_q{i}.txt")
    if not frames:
        return pd.DataFrame(columns=["date", "symbol", "prediction", "label"])
    return pd.concat(frames, ignore_index=True)
