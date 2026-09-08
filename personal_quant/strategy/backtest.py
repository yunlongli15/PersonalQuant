# -*- coding: utf-8 -*-
"""Monthly-rebalance backtest engine with realistic T+1 execution.

Flow per month:
  T (last trading day) close: universe -> scores -> Top K -> target weights
  T+1 open: orders executed under the conservative rules (execution.py);
            cash buffer, A-share 100-share lots, transaction costs
  daily: mark-to-market at raw close -> NAV series (full calendar walk)

Every monthly prediction is stored (symbol/rank/weight/model_version/...)
for later review (audit).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd

from .. import db
from .costs import TransactionCostModel
from .execution import TradeStatus, execute_order
from .rebalance import rebalance_dates, trading_days
from .universe import build_universe

LOT = 100


@dataclass
class BacktestResult:
    nav: pd.Series                  # daily NAV (date -> value)
    cash: pd.Series                 # daily cash
    positions: pd.DataFrame         # daily positions (date x symbol, shares)
    trades: pd.DataFrame            # executed trades
    predictions: pd.DataFrame       # monthly predictions (audit)
    turnover: pd.Series             # per-rebalance one-sided turnover


class MonthlyBacktest:
    def __init__(self, config: dict, cost_model: TransactionCostModel,
                 initial_capital: float = 1_000_000.0):
        self.cfg = config
        self.cost = cost_model
        self.capital0 = initial_capital
        self.top_k = config["portfolio"]["top_k"]
        self.cash_buffer = config["portfolio"]["cash_buffer"]
        self.limit_threshold = config["execution"]["limit_threshold"]

    def _px(self, symbols, d: pd.Timestamp, field="close") -> pd.Series:
        """Last available price up to `d` per symbol (forward-fills
        suspension days, so held names never NaN the NAV)."""
        if not symbols:
            return pd.Series(dtype=float)
        df = db.connect().execute(
            f"SELECT symbol, {field} v FROM daily_bars WHERE trade_date <= ? "
            "AND symbol IN (SELECT unnest(?::VARCHAR[])) "
            "QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol "
            "ORDER BY trade_date DESC) = 1",
            [d, list(symbols)],
        ).fetch_df()
        return df.set_index("symbol")["v"]

    def _equity(self, positions: Dict[str, int], cash: float, d: pd.Timestamp) -> float:
        if not positions:
            return cash
        px = self._px(list(positions.keys()), d)
        return cash + float((px * pd.Series(positions)).sum())

    def run(
        self,
        start: str,
        end: str,
        predictor: Callable[[pd.Timestamp, List[str]], pd.Series],
        model_version: str = "strategy_v1",
        dataset_version: str = "canonical",
        feature_version: str = "alpha158",
        save_predictions: bool = True,
        verbose: bool = True,
    ) -> BacktestResult:
        """predictor(date, symbols) -> pd.Series(symbol -> score)."""
        cfg = self.cfg
        days = list(trading_days(start, end))
        if not days:
            raise ValueError("empty trading calendar for the period")
        rbs = rebalance_dates(start, end, cfg["rebalance"]["frequency"],
                              cfg["rebalance"]["rule"])

        # ---- phase 1: compute per-rebalance fills (T+1 execution) ---------
        fills_by_date: Dict[pd.Timestamp, List[dict]] = {}
        trades: List[dict] = []
        predictions: List[dict] = []
        turnover: Dict[pd.Timestamp, float] = {}
        cash = self.capital0
        positions: Dict[str, int] = {}

        for t in rbs:
            t1 = _next_day(t)
            if t1 is None or t1 > days[-1]:
                continue
            universe = build_universe(t, cfg)
            if universe.empty:
                continue
            scores = predictor(t, universe["symbol"].tolist())
            if scores is None or len(scores) == 0:
                continue
            scores = scores.dropna().sort_values(ascending=False)
            picks = scores.head(self.top_k)
            w_stock = (1.0 - self.cash_buffer) / self.top_k
            equity = self._equity(positions, cash, t)
            target_value = equity * w_stock
            if save_predictions:
                for i, sym in enumerate(picks.index):
                    predictions.append(
                        {
                            "prediction_date": t,
                            "symbol": sym,
                            "predicted_return": float(picks[sym]),
                            "rank": i + 1,
                            "target_weight": w_stock,
                            "model_version": model_version,
                            "dataset_version": dataset_version,
                            "feature_version": feature_version,
                        }
                    )
            # sell full positions that dropped out of the top-k
            for sym in [s for s in list(positions) if s not in picks.index]:
                sell = positions[sym]
                res = execute_order(sym, t, "SELL", sell, self.limit_threshold)
                if res is None or res.status != TradeStatus.FILLED:
                    continue
                value = sell * res.fill_price
                fee = self.cost.sell_cost(value)
                cash += value - fee
                del positions[sym]
                traded_value += value
                fills_by_date.setdefault(t1, []).append(
                    {"symbol": sym, "shares": -sell, "price": res.fill_price,
                     "cash_delta": value - fee}
                )
                trades.append(
                    {
                        "signal_date": t, "exec_date": t1, "symbol": sym,
                        "side": "SELL", "shares": sell, "price": res.fill_price,
                        "value": value, "fee": fee,
                    }
                )

            px_t = self._px(list(set(positions) | set(picks.index)), t)
            traded_value = 0.0
            for sym in picks.index:
                est_px = px_t.get(sym)
                if est_px is None or math.isnan(est_px):
                    continue
                cur_shares = positions.get(sym, 0)
                delta = target_value - cur_shares * est_px
                res = None
                if delta > 0:
                    raw = math.floor(delta / est_px / LOT) * LOT
                    if raw >= LOT:
                        res = execute_order(sym, t, "BUY", raw,
                                            self.limit_threshold)
                elif delta < 0:
                    sell = min(int(math.ceil(abs(delta) / est_px)), cur_shares)
                    if sell > 0:
                        res = execute_order(sym, t, "SELL", sell,
                                            self.limit_threshold)
                if res is None or res.status != TradeStatus.FILLED:
                    continue
                value = abs(res.shares) * res.fill_price
                if res.shares > 0:  # buy
                    fee = self.cost.buy_cost(value)
                    cash_delta = -value - fee
                else:               # sell
                    fee = self.cost.sell_cost(value)
                    cash_delta = value - fee
                cash += cash_delta
                positions[sym] = positions.get(sym, 0) + res.shares
                if positions[sym] == 0:
                    del positions[sym]
                traded_value += value
                fills_by_date.setdefault(t1, []).append(
                    {"symbol": sym, "shares": res.shares, "price": res.fill_price,
                     "cash_delta": cash_delta}
                )
                trades.append(
                    {
                        "signal_date": t, "exec_date": t1, "symbol": sym,
                        "side": "BUY" if res.shares > 0 else "SELL",
                        "shares": abs(res.shares), "price": res.fill_price,
                        "value": value, "fee": fee,
                    }
                )
            if equity > 0:
                turnover[t] = traded_value / (2.0 * equity)

        # ---- phase 2: daily walk for NAV / positions / cash ----------------
        nav_records: Dict[pd.Timestamp, float] = {}
        cash_records: Dict[pd.Timestamp, float] = {}
        pos_rows: List[dict] = []
        positions = {}
        cash = self.capital0
        for d in days:
            if d in fills_by_date:
                for f in fills_by_date[d]:
                    cash += f["cash_delta"]
                    positions[f["symbol"]] = positions.get(f["symbol"], 0) + f["shares"]
                    if positions[f["symbol"]] == 0:
                        del positions[f["symbol"]]
            nav_records[d] = self._equity(positions, cash, d)
            cash_records[d] = cash
            pos_rows.append({"date": d, **positions})

        pos_all = pd.DataFrame(pos_rows).set_index("date").fillna(0.0)
        return BacktestResult(
            nav=pd.Series(nav_records),
            cash=pd.Series(cash_records),
            positions=pos_all,
            trades=pd.DataFrame(trades),
            predictions=pd.DataFrame(predictions),
            turnover=pd.Series(turnover),
        )


def _next_day(d: pd.Timestamp) -> Optional[pd.Timestamp]:
    r = db.connect().execute(
        "SELECT MIN(trade_date) d FROM trading_calendar WHERE is_open AND trade_date > ?",
        [d],
    ).fetchone()
    return pd.Timestamp(r[0]) if r and r[0] is not None else None
