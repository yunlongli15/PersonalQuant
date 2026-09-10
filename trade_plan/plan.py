# -*- coding: utf-8 -*-
"""Trade plan: signals -> allocation -> concrete orders (STEP 7E).

Objectives (spec §16), stated honestly:

    maximize expected net return
    subject to risk / position / industry / cash / lot-size / turnover
    constraints and transaction costs

The numbers reported are *model estimates*: expected gross return,
expected net return (after the shared cost model), expected volatility,
turnover, transaction cost and cash residual. Nothing is a promise
(spec §13: target prices are model targets, never "guaranteed").

Entry policy (spec §12): the recommendation is NOT "buy at the last
close". The entry band is built from the stock's own volatility
(ATR-style half-width, capped by a fraction of price) and the plan price
is the band midpoint; cash is sized for the plan price plus costs, so a
fill at the top of the band still fits the cash budget.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLAN_DIR = PROJECT_ROOT / "data" / "quant" / "trade_plans"

LOT = 100
RISK_PROFILES = {
    # risk_mode -> (entry band half-width multiplier, target vol scaling,
    #               stop multiple)
    "conservative": {"entry_band": 0.6, "target_scale": 0.8,
                     "stop_sigma": 1.5},
    "balanced": {"entry_band": 1.0, "target_scale": 1.0,
                 "stop_sigma": 2.0},
    "aggressive": {"entry_band": 1.4, "target_scale": 1.3,
                   "stop_sigma": 2.5},
}


@dataclass
class TradePlanRow:
    symbol: str
    name: Optional[str]
    action: str                  # BUY | HOLD | SELL | SKIP
    current_price: float
    recommended_entry_price: float
    entry_low: float
    entry_high: float
    entry_rationale: str
    shares: int
    lot_size: int
    buy_value: float
    weight: float
    target_weight: float
    target_price: Optional[float]
    expected_return: Optional[float]        # gross, horizon = 20d default
    expected_net_return: Optional[float]    # after round-trip cost
    expected_holding_days: int
    stop_loss: Optional[float]
    time_stop_days: int
    forecast: Dict = field(default_factory=dict)
    risk: Dict = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)
    raw_rank: Optional[int] = None
    signal_prediction: Optional[float] = None


def _atr_like(close: pd.Series, window: int = 20) -> float:
    """Mean absolute daily return over `window` (no future data)."""
    r = close.pct_change().dropna().tail(window)
    return float(r.abs().mean()) if len(r) else 0.02


def load_price_history(symbols: Sequence[str], as_of: str,
                       lookback_days: int = 400) -> pd.DataFrame:
    """Raw closes up to `as_of` (canonical, read-only, PIT)."""
    from factors.base import load_factor_data

    start = pd.Timestamp(as_of) - pd.Timedelta(days=lookback_days)
    data = load_factor_data(start, as_of)
    cols = [s for s in symbols if s in data.close_raw.columns]
    out = data.close_raw.loc[:pd.Timestamp(as_of), cols].ffill()
    return out


def entry_band(price: float, vol: float, profile: str,
               max_width: float = 0.03) -> tuple:
    """Entry band + rationale (spec §12).

    Half-width = profile multiplier x daily vol, capped at `max_width`
    (3%) so the band stays actionable for low-volatility names and does
    not become a fantasy discount for high-volatility ones.
    """
    p = RISK_PROFILES[profile]
    half = min(p["entry_band"] * vol, max_width)
    low = price * (1.0 - half)
    high = price * (1.0 + half * 0.5)      # allow a small chase above
    plan = (low + high) / 2.0
    rationale = (f"band = ±{half*100:.2f}% of last close "
                 f"({vol*100:.2f}% daily vol x {p['entry_band']} profile "
                 f"multiplier, capped at {max_width*100:.0f}%)")
    return low, plan, high, rationale


def target_and_stop(price: float, plan_price: float, expected_return: float,
                    vol: float, profile: str, horizon: int = 20) -> dict:
    """Model target + stop levels (never 'guaranteed')."""
    p = RISK_PROFILES[profile]
    exp = expected_return if np.isfinite(expected_return) else 0.0
    target = plan_price * (1.0 + exp * p["target_scale"])
    stop = plan_price * (1.0 - p["stop_sigma"] * vol * np.sqrt(horizon / 20))
    stop = max(stop, plan_price * 0.70)          # never deeper than -30%
    return {
        "target_price": round(float(target), 3),
        "stop_loss": round(float(stop), 3),
        "time_stop_days": int(horizon * 2),      # 2x the forecast horizon
        "expected_holding_days": int(horizon),
    }


def _cost_rates(strategy_cfg: dict) -> tuple:
    from personal_quant.strategy.costs import TransactionCostModel
    from portfolio.transaction_cost import round_trip_rate, unit_buy_rate, \
        unit_sell_rate

    model = TransactionCostModel.from_config(strategy_cfg)
    return (unit_buy_rate(model), unit_sell_rate(model),
            round_trip_rate(model))


def build_trade_plan(capital: float = 500_000.0,
                     top_k: int = 20,
                     risk_profile: str = "balanced",
                     max_weight: float = 0.10,
                     sector_cap: float = 0.20,
                     cash_buffer: float = 0.05,
                     allocation_method: Optional[str] = None,
                     signal_date: Optional[str] = None,
                     frequency: str = "monthly") -> dict:
    """Full pipeline: frozen signal -> allocation -> lot-sized plan."""
    import yaml

    from factors.base import load_factor_data
    from pipeline.forecast import forecast_for_date, load_forecasts
    from pipeline.signals import load_signals, signals_state
    from portfolio.allocator import AllocationInput, allocate
    from portfolio.constraints import PortfolioConstraints
    from portfolio.covariance import estimate_covariance

    if risk_profile not in RISK_PROFILES:
        raise ValueError(f"risk_profile={risk_profile!r} not in "
                         f"{list(RISK_PROFILES)}")

    strategy_cfg = yaml.safe_load(
        (PROJECT_ROOT / "config" / "strategy_v1.yaml")
        .read_text(encoding="utf-8"))
    portfolio_cfg = yaml.safe_load(
        (PROJECT_ROOT / "config" / "portfolio_v1.yaml")
        .read_text(encoding="utf-8"))

    sig = load_signals()
    if sig.empty:
        raise RuntimeError("no signal snapshot — run signal_refresh first")
    state = signals_state()
    as_of = signal_date or state.get("as_of") or \
        str(pd.Timestamp(sig["signal_date"].iloc[0]).date())
    as_of = str(pd.Timestamp(as_of).date())

    # allocation method: STEP 6 study selection unless overridden
    sel_path = PROJECT_ROOT / "experiments" / "portfolio" / "selection.json"
    method = allocation_method
    if method is None:
        if sel_path.exists():
            sel = json.loads(sel_path.read_text(encoding="utf-8"))
            method = sel.get("stage3", {}).get("chosen_method",
                                               "equal_weight")
        else:
            method = "equal_weight"

    sig = sig[~sig["symbol"].isin(_index_like())]
    top = sig.sort_values("prediction", ascending=False).head(top_k)
    symbols = top["symbol"].tolist()

    fdata = load_factor_data(pd.Timestamp(as_of) - pd.Timedelta(days=400),
                             as_of)
    prices = fdata.close_raw.loc[:pd.Timestamp(as_of), symbols].ffill()
    last = prices.iloc[-1]
    vols = prices.pct_change().tail(60).std()

    cov = estimate_covariance(fdata.close_raw, symbols, as_of,
                              window=60, method="sample")
    cons = PortfolioConstraints(max_weight=max_weight, sector_cap=sector_cap,
                                cash_buffer=cash_buffer, lot_size=LOT)
    cand = pd.DataFrame({
        "prediction": top.set_index("symbol")["prediction"],
        "raw_rank": top.set_index("symbol")["raw_rank"],
        "vol": cov.vols.reindex(symbols),
        "industry": fdata.industries.reindex(symbols),
        "liq_cap": np.nan,
    })
    alloc_in = AllocationInput(
        date=pd.Timestamp(as_of), candidates=cand, cov=cov,
        prev_weights=pd.Series(dtype=float), constraints=cons,
        cost_model=__import__("personal_quant.strategy.costs",
                              fromlist=["TransactionCostModel"])
        .TransactionCostModel.from_config(strategy_cfg),
        method=method, params=dict(portfolio_cfg["portfolio"]["methods"]
                                   .get(method, {})))
    alloc = allocate(alloc_in)
    weights = alloc.weights

    buy_rate, sell_rate, rt_rate = _cost_rates(strategy_cfg)

    # forecasts (PIT) for the display + target prices
    fc = load_forecasts()
    if fc.empty or (fc["signal_date"].iloc[0] if len(fc) else None) != as_of:
        fc = forecast_for_date(as_of, symbols=symbols)
    fc20 = fc[fc["horizon"] == 20].set_index("symbol") if len(fc) else \
        pd.DataFrame()

    rows: List[TradePlanRow] = []
    planned_value = 0.0
    for sym in weights.index:
        px = float(last.get(sym, np.nan))
        if not np.isfinite(px) or px <= 0:
            continue
        vol = float(vols.get(sym, np.nan))
        if not np.isfinite(vol) or vol <= 0:
            vol = 0.02
        low, plan_px, high, why = entry_band(px, vol, risk_profile)
        # size on the plan price AND include costs, so a fill at the band
        # top still fits the budget
        budget = capital * float(weights[sym]) / (1.0 + buy_rate)
        shares = int(np.floor(budget / plan_px / LOT)) * LOT
        value = shares * plan_px
        f20 = fc20.loc[sym] if len(fc20) and sym in fc20.index else None
        exp_ret = float(f20["expected_return"]) if f20 is not None and \
            pd.notna(f20["expected_return"]) else np.nan
        tgt = target_and_stop(px, plan_px, exp_ret, vol, risk_profile)
        net_ret = exp_ret - rt_rate if np.isfinite(exp_ret) else np.nan
        reasons = []
        if shares == 0:
            reasons.append("SKIP: target value below one 100-share lot")
        rows.append(TradePlanRow(
            symbol=sym, name=top.set_index("symbol")["name"].get(sym),
            action="BUY" if shares > 0 else "SKIP",
            current_price=round(px, 3),
            recommended_entry_price=round(plan_px, 3),
            entry_low=round(low, 3), entry_high=round(high, 3),
            entry_rationale=why, shares=shares, lot_size=LOT,
            buy_value=round(value, 2),
            weight=round(value / capital, 4),
            target_weight=round(float(weights[sym]), 4),
            target_price=tgt["target_price"], expected_return=(
                round(exp_ret, 4) if np.isfinite(exp_ret) else None),
            expected_net_return=(round(net_ret, 4)
                                 if np.isfinite(net_ret) else None),
            expected_holding_days=tgt["expected_holding_days"],
            stop_loss=tgt["stop_loss"], time_stop_days=tgt["time_stop_days"],
            forecast=({"expected_return_20d": float(exp_ret),
                       "p_up_20d": float(f20["p_up"]) if f20 is not None
                       else None,
                       "q05": float(f20["q05"]) if f20 is not None else None,
                       "q95": float(f20["q95"]) if f20 is not None else None,
                       "trend": str(f20["trend"]) if f20 is not None
                       else None} if f20 is not None else {}),
            risk={"vol_60d": round(vol, 4),
                  "risk_share": float(alloc.extras.get("risk_share", pd.Series(
                      dtype=float)).get(sym, np.nan))
                  if alloc.extras.get("risk_share") is not None else None},
            reasons=reasons,
            raw_rank=int(top.set_index("symbol")["raw_rank"].get(sym, 0)),
            signal_prediction=float(
                top.set_index("symbol")["prediction"].get(sym, np.nan)),
        ))
        planned_value += value

    df = pd.DataFrame([r.__dict__ for r in rows])
    if not df.empty:
        df = df.sort_values("target_weight", ascending=False).reset_index(
            drop=True)
    fees_est = float((df["buy_value"] * buy_rate).sum()) if len(df) else 0.0
    exp_gross = float((df["expected_return"].fillna(0)
                       * df["buy_value"]).sum()) if len(df) else 0.0
    exp_net = float((df["expected_net_return"].fillna(0)
                     * df["buy_value"]).sum()) if len(df) else 0.0
    port_vol = alloc.extras.get("portfolio_vol")
    invested = float(df["buy_value"].sum()) if len(df) else 0.0
    plan = {
        "as_of": as_of,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "capital": capital, "frequency": frequency,
        "risk_profile": risk_profile,
        "allocation_method": method,
        "optimizer_status": alloc.optimizer_status,
        "fallback_reason": alloc.fallback_reason,
        "top_k": top_k, "max_weight": max_weight,
        "sector_cap": sector_cap, "cash_buffer": cash_buffer,
        "total_buy_value": round(invested, 2),
        "estimated_fees": round(fees_est, 2),
        "remaining_cash": round(capital - invested - fees_est, 2),
        "cash_residual_pct": round((capital - invested - fees_est) / capital, 4),
        "expected_gross_return_value": round(exp_gross, 2),
        "expected_net_return_value": round(exp_net, 2),
        "expected_net_return_pct": round(exp_net / capital, 4),
        "expected_volatility": (round(float(port_vol), 4)
                                if port_vol is not None else None),
        "n_positions": int((df["shares"] > 0).sum()) if len(df) else 0,
        "signal_version": "strategy_v2/S3",
        "forecast_version": (fc["forecast_version"].iloc[0]
                             if len(fc) else None),
        "cost_model": {"unit_buy_rate": buy_rate, "unit_sell_rate": sell_rate,
                       "round_trip_rate": rt_rate},
        "rows": df.to_dict("records") if len(df) else [],
    }
    return plan


def _index_like() -> set:
    """Excluded pseudo-symbols (index quotes share the stock code space)."""
    return {"000300.SH", "000852.SH", "000905.SH", "000906.SH",
            "000985.SH", "399300.SZ"}


def sell_reasons(symbol: str, plan: dict, holding: Optional[dict] = None,
                 signal_rank: Optional[int] = None,
                 top_k: int = 20) -> List[str]:
    """Why SELL (spec §14) — never a bare 'SELL'."""
    reasons = []
    row = next((r for r in plan.get("rows", [])
                if r["symbol"] == symbol), None)
    if row is None:
        reasons.append("portfolio rebalance: not in the current target set")
    else:
        if row.get("target_price") and holding and \
                holding.get("last_price") and \
                holding["last_price"] >= row["target_price"]:
            reasons.append("forecast target reached")
    if signal_rank is not None and signal_rank > top_k:
        reasons.append(f"signal deterioration: rank {signal_rank} "
                       f"outside top {top_k}")
    if holding:
        if holding.get("stop_price") and holding.get("last_price") and \
                holding["last_price"] <= holding["stop_price"]:
            reasons.append("stop loss")
        if holding.get("days_held") and row and \
                holding["days_held"] > (row.get("time_stop_days") or 40):
            reasons.append("time stop")
        if holding.get("violates_risk_limit"):
            reasons.append("risk constraint violation")
    return reasons or ["portfolio rebalance"]


def save_plan(plan: dict) -> Dict[str, Path]:
    PLAN_DIR.mkdir(parents=True, exist_ok=True)
    d = plan["as_of"]
    rows = plan["rows"]
    csv_path = PLAN_DIR / f"trade_plan_{d}.csv"
    json_path = PLAN_DIR / f"trade_plan_{d}.json"
    pd.DataFrame(rows).to_csv(csv_path, index=False, encoding="utf-8-sig")
    json_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False,
                                    default=str), encoding="utf-8")
    return {"csv": csv_path, "json": json_path}


def load_plan(as_of: Optional[str] = None) -> dict:
    files = sorted(PLAN_DIR.glob("trade_plan_*.json"))
    if not files:
        return {}
    p = PLAN_DIR / f"trade_plan_{as_of}.json" if as_of else files[-1]
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))
