# -*- coding: utf-8 -*-
"""Portfolio-level metrics (STEP 6 spec §35/§36/§38/§39/§56).

Core return/risk numbers reuse the frozen strategy metrics module
(personal_quant.strategy.metrics) so every portfolio method is scored
with the SAME formulas as strategy_v1 (fair comparison). On top of that:

  - historical VaR / CVaR on 60d and 120d trailing windows (spec §36);
  - tail stats (worst day / worst month / best month);
  - weight concentration: HHI, effective N, top holding, holdings count
    (spec §38) — from the ACTUAL execution weights (lot-rounded), not the
    theoretical targets;
  - industry concentration per day (spec §39);
  - cumulative transaction cost from the trade log (spec §26);
  - monthly / yearly return tables and a NAV correlation table (spec §37).

Benchmark convention (spec §56): absolute returns are always reported;
relative numbers use CSI300 buy-and-hold as the benchmark, and the
equal-weight benchmark is reported separately — never mixed (definitions
recorded in the reports).
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd

from personal_quant.strategy import metrics as mt

TRADING_DAYS = 252


def _last_var_cvar(returns: pd.Series, window: int, q: float = 0.05
                   ) -> tuple[float, float]:
    r = returns.tail(window)
    if len(r) < 2:
        return float("nan"), float("nan")
    var = float(r.quantile(q))
    tail = r[r <= var]
    cvar = float(tail.mean()) if len(tail) else var
    return var, cvar


def extend_summary(
    nav: pd.Series,
    bench_nav: Optional[pd.Series] = None,
    turnover: Optional[pd.Series] = None,
    n_trades: Optional[int] = None,
    label: str = "portfolio",
) -> dict:
    s = mt.summarize(nav, bench_nav, turnover, n_trades, label)
    r = mt.daily_returns(nav)
    s["var_60d"], s["cvar_60d"] = _last_var_cvar(r, 60)
    s["var_120d"], s["cvar_120d"] = _last_var_cvar(r, 120)
    s["worst_day"] = float(r.min()) if len(r) else float("nan")
    mr = mt.monthly_returns(nav)
    s["worst_month"] = float(mr.min()) if len(mr) else float("nan")
    s["best_month"] = float(mr.max()) if len(mr) else float("nan")
    return s


def weight_metrics(
    daily_weights: pd.DataFrame,
    industries: Optional[pd.Series] = None,
) -> dict:
    """Concentration stats from ACTUAL daily execution weights
    (date x symbol; sums <= 1 with cash)."""
    w = daily_weights
    hhi = (w ** 2).sum(axis=1)
    eff_n = 1.0 / hhi.replace(0, np.nan)
    out = {
        "avg_holdings": float((w > 0).sum(axis=1).mean()),
        "avg_hhi": float(hhi.mean()),
        "avg_effective_n": float(eff_n.mean()),
        "avg_top_weight": float(w.max(axis=1).mean()),
        "max_top_weight": float(w.max(axis=1).max()),
        "hhi_series": hhi,
        "effective_n_series": eff_n,
    }
    if industries is not None and len(w):
        ind = industries.reindex(w.columns).fillna("UNKNOWN")
        conc = []
        for d, row in w.iterrows():
            s = row.groupby(ind.reindex(row.index)).sum()
            conc.append(float(s.max()) if len(s) else 0.0)
        out["avg_industry_concentration"] = float(np.mean(conc))
        out["max_industry_concentration"] = float(np.max(conc))
        out["industry_concentration_series"] = pd.Series(
            conc, index=w.index)
    return out


def fee_metrics(trades: pd.DataFrame, initial_capital: float) -> dict:
    """Cumulative transaction cost (spec §26: gross/net separation)."""
    if trades.empty:
        return {"total_fees": 0.0, "fees_fraction": 0.0, "n_trades": 0}
    fees = trades["fee"].sum()
    cum = trades.sort_values("exec_date").groupby("exec_date")[
        "fee"].sum().cumsum()
    return {
        "total_fees": float(fees),
        "fees_fraction": float(fees / initial_capital),
        "n_trades": int(len(trades)),
        "cumulative_fees": cum,
    }


def returns_tables(nav: pd.Series) -> tuple[pd.Series, pd.Series]:
    return mt.monthly_returns(nav), mt.yearly_returns(nav)


def nav_correlation(navs: Dict[str, pd.Series]) -> pd.DataFrame:
    """Daily-return correlation between portfolio methods (spec §37)."""
    r = pd.DataFrame({k: v.pct_change() for k, v in navs.items()})
    return r.corr()
