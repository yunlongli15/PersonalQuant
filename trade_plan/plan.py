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

from .boards import eligibility

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
    board: str = "UNKNOWN"                  # STAR/CHINEXT/BSE/MAIN/FUND
    board_name: str = ""                    # 板块中文名
    capital_required: float = 0.0           # 开通该板块所需日均资产
    experience_months: int = 0
    can_buy: bool = True                    # 账户当前是否满足门槛
    restriction_reason: str = ""            # 不满足时的原因


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


def _cost_rates(strategy_cfg: dict) -> tuple:  # noqa: D401
    """(buy unit rate, sell unit rate, round-trip rate) — used only for
    sizing and for the coarse ordering of candidates. Per-position fees
    that the user sees are computed with the full model (see
    `_position_fees`) because the unit rates ignore the minimum
    commission."""
    from personal_quant.strategy.costs import TransactionCostModel
    from portfolio.transaction_cost import round_trip_rate, unit_buy_rate, \
        unit_sell_rate

    model = TransactionCostModel.from_config(strategy_cfg)
    return (unit_buy_rate(model), unit_sell_rate(model),
            round_trip_rate(model))


def _position_fees(strategy_cfg: dict, buy_value: float,
                   exit_value: float) -> tuple:
    """(buy fee, sell fee) for one position using the REAL cost model.

    Why not value x unit_rate: the broker charges a minimum commission
    (5 CNY), which binds for every position a small account can afford
    (~9,500 CNY -> 2.4 CNY of commission, floored to 5). The unit rates
    ignore the floor, understating the round trip by ~0.055% of the
    position — small, but it is the user's money, so the plan reports the
    floored, real number.
    """
    from personal_quant.strategy.costs import TransactionCostModel

    m = TransactionCostModel.from_config(strategy_cfg)
    return m.buy_cost(buy_value), m.sell_cost(exit_value)


def account_profile() -> dict:
    """Account capital + board permissions (config/account_profile.yaml).

    Defaults to auto-detecting capital from the wealth database on top of
    the configured starting capital, so the permission flags follow the
    real account rather than a guess.
    """
    import yaml

    p = PROJECT_ROOT / "config" / "account_profile.yaml"
    cfg = {"capital": 100_000.0,
           "experience_months": None,     # None = unknown (warn, not block)
           "auto_detect_capital": True}
    if p.exists():
        cfg.update(yaml.safe_load(p.read_text(encoding="utf-8")) or {})
    if cfg.get("auto_detect_capital"):
        try:
            from wealth import db as wdb
            from wealth import service

            s = service.latest_summary(wdb.connect())
            if s.get("net_worth"):
                cfg["capital"] = max(float(cfg["capital"]),
                                     float(s["net_worth"]))
        except Exception:                                    # noqa: BLE001
            pass
    return cfg


def _effective_max_weight(top_k: int, invest_target: float,
                          requested: float) -> float:
    """Smallest single-name cap that still allows the target to be met.

    K names each capped at `max_weight` can hold at most K x max_weight,
    so with few names a 10% cap makes the problem infeasible (K=5 ->
    50% < 95%). The cap therefore rises only when it must: the configured
    10% is kept for K>=20 (so the STEP 6 behaviour and its anchor are
    untouched) and lifted to invest_target/K x 1.05 for smaller books.
    """
    need = invest_target / max(top_k, 1) * 1.05
    return round(max(requested, need), 4)


def build_trade_plan(capital: float = 500_000.0,
                     top_k: int = 20,
                     risk_profile: str = "balanced",
                     max_weight: float = 0.10,
                     sector_cap: float = 0.20,
                     cash_buffer: float = 0.05,
                     allocation_method: Optional[str] = None,
                     signal_date: Optional[str] = None,
                     frequency: str = "monthly",
                     account_capital: Optional[float] = None,
                     experience_months: Optional[int] = None,
                     exclude_restricted: bool = True,
                     horizon: int = 20,
                     holdings: Optional[Dict[str, int]] = None,
                     price_overrides: Optional[Dict[str, float]] = None
                     ) -> dict:
    """Full pipeline: frozen signal -> allocation -> lot-sized plan.

    `account_capital` drives the BOARD PERMISSION check (科创板 50万 /
    创业板 10万), which is independent of the backtest capital: a user
    with 10万元 cannot buy 科创板 regardless of the simulated size.
    """
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

    prof = account_profile()
    if account_capital is None:
        account_capital = float(prof["capital"])
    if experience_months is None:
        experience_months = prof.get("experience_months")

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
    # A recommendation the account cannot act on is not a recommendation:
    # by default the board filter runs BEFORE Top-K, so the K positions
    # are the best K the account can actually buy. Restricted names are
    # still reported (plan["excluded_restricted"]) so nothing is hidden.
    excluded_restricted: List[dict] = []
    if exclude_restricted:
        ranked = sig.sort_values("prediction", ascending=False)
        for sym in ranked["symbol"]:
            e = eligibility(sym, account_capital, experience_months)
            if not e.can_buy:
                row = ranked[ranked["symbol"] == sym].iloc[0]
                excluded_restricted.append({
                    "symbol": sym, "name": row.get("name"),
                    "raw_rank": int(row["raw_rank"]),
                    "board": e.board, "board_name": e.board_name,
                    "capital_required": e.capital_required,
                    "reason": e.reason})
            if len(excluded_restricted) >= 50:
                break
        blocked = {d["symbol"] for d in excluded_restricted}
        sig = sig[~sig["symbol"].isin(blocked)]
    top = sig.sort_values("prediction", ascending=False).head(top_k)
    symbols = top["symbol"].tolist()

    fdata = load_factor_data(pd.Timestamp(as_of) - pd.Timedelta(days=400),
                             as_of)
    prices = fdata.close_raw.loc[:pd.Timestamp(as_of), symbols].ffill()
    last = prices.iloc[-1]
    vols = prices.pct_change().tail(60).std()

    # Live-price override: when the trading day has closed but the
    # upstream snapshot has not published it yet, prices can be fetched
    # per symbol. The SIGNAL stays at `as_of` (its ranking is unchanged);
    # only the price inputs move, so the entry band / target / stop are
    # actionable for the next session. Recorded in the plan so the mixed
    # vintage is visible.
    live_symbols = []
    if price_overrides:
        for sym, px in price_overrides.items():
            if sym in last.index and px and np.isfinite(px):
                last[sym] = float(px)
                live_symbols.append(sym)

    cov = estimate_covariance(fdata.close_raw, symbols, as_of,
                              window=60, method="sample")
    max_weight = _effective_max_weight(top_k, 1.0 - cash_buffer, max_weight)
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
    # Forecast horizon drives targets/stops/time-stop. 20 trading days is
    # the FROZEN strategy's horizon (monthly rebalance); 5 days is the
    # weekly variant the user asked for — the same frozen signal, but a
    # shorter, explicitly non-validated holding period.
    if horizon not in (1, 5, 20):
        raise ValueError(f"horizon must be 1, 5 or 20 (got {horizon})")
    fc = load_forecasts()
    if fc.empty or (fc["signal_date"].iloc[0] if len(fc) else None) != as_of:
        fc = forecast_for_date(as_of, symbols=symbols)
    fch = fc[fc["horizon"] == horizon].set_index("symbol") if len(fc) else \
        pd.DataFrame()

    # Holdings-aware mode (weekly rebalancing): with the user's actual
    # positions the plan becomes a DELTA list — what to add, trim, exit —
    # instead of a from-scratch shopping list. Without holdings it is the
    # initial build (every row BUY/SKIP).
    held = {k: int(v) for k, v in (holdings or {}).items() if v}
    exiting: List[dict] = []

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
        fh = fch.loc[sym] if len(fch) and sym in fch.index else None
        exp_ret = float(fh["expected_return"]) if fh is not None and \
            pd.notna(fh["expected_return"]) else np.nan
        tgt = target_and_stop(px, plan_px, exp_ret, vol, risk_profile,
                              horizon=horizon)
        # real round-trip cost for THIS position size (minima included),
        # expressed as a rate on the buy value
        if value > 0:
            exit_value = value * (1.0 + (exp_ret if np.isfinite(exp_ret)
                                         else 0.0))
            buy_fee, sell_fee = _position_fees(strategy_cfg, value,
                                               exit_value)
            fee_rate = (buy_fee + sell_fee) / value
        else:
            buy_fee = sell_fee = 0.0
            fee_rate = rt_rate
        net_ret = exp_ret - fee_rate if np.isfinite(exp_ret) else np.nan
        elig = eligibility(sym, account_capital, experience_months)
        reasons = []
        if shares == 0:
            reasons.append("SKIP: target value below one 100-share lot")
        if elig.restricted:
            reasons.append(f"权限受限（{elig.board_name}）：{elig.reason}")
        cur = held.get(sym, 0)
        if cur and shares:
            if shares > cur:
                action, reasons = "ADD", [f"加仓：现持 {cur} → 目标 "
                                          f"{shares} 股"]
            elif shares < cur:
                action, reasons = "REDUCE", [f"减仓：现持 {cur} → 目标 "
                                             f"{shares} 股"]
            else:
                action, reasons = "HOLD", [f"维持 {cur} 股"]
        elif cur and not shares:
            action, reasons = "SELL", [f"清仓 {cur} 股（已不在目标组合）"]
        elif elig.restricted:
            action = "BUY_RESTRICTED"
        else:
            action = "BUY" if shares else "SKIP"
        rows.append(TradePlanRow(
            symbol=sym, name=top.set_index("symbol")["name"].get(sym),
            action=action,
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
            forecast=({f"expected_return_{horizon}d": float(exp_ret),
                       f"p_up_{horizon}d": float(fh["p_up"])
                       if fh is not None else None,
                       "q05": float(fh["q05"]) if fh is not None else None,
                       "q95": float(fh["q95"]) if fh is not None else None,
                       "trend": str(fh["trend"]) if fh is not None
                       else None} if fh is not None else {}),
            risk={"vol_60d": round(vol, 4),
                  "risk_share": float(alloc.extras.get("risk_share", pd.Series(
                      dtype=float)).get(sym, np.nan))
                  if alloc.extras.get("risk_share") is not None else None},
            reasons=reasons,
            raw_rank=int(top.set_index("symbol")["raw_rank"].get(sym, 0)),
            signal_prediction=float(
                top.set_index("symbol")["prediction"].get(sym, np.nan)),
            board=elig.board, board_name=elig.board_name,
            capital_required=elig.capital_required,
            experience_months=elig.experience_months,
            can_buy=elig.can_buy, restriction_reason=elig.reason,
        ))
        planned_value += value

    # held names that fell out of the target set: full exit
    for sym, sh in held.items():
        if sym in weights.index or sh <= 0:
            continue
        col = fdata.close_raw[sym] if sym in fdata.close_raw.columns else None
        px = float(col.loc[:pd.Timestamp(as_of)].ffill().iloc[-1]) \
            if col is not None and len(col.loc[:pd.Timestamp(as_of)]) else np.nan
        e = eligibility(sym, account_capital, experience_months)
        rows.append(TradePlanRow(
            symbol=sym, name=None, action="SELL",
            current_price=round(px, 3) if np.isfinite(px) else 0.0,
            recommended_entry_price=round(px, 3) if np.isfinite(px) else 0.0,
            entry_low=0.0, entry_high=0.0,
            entry_rationale="exit: no longer in the target portfolio",
            shares=0, lot_size=LOT, buy_value=0.0, weight=0.0,
            target_weight=0.0, target_price=None, expected_return=None,
            expected_net_return=None, expected_holding_days=0,
            stop_loss=None, time_stop_days=0,
            reasons=[f"清仓 {sh} 股：已不在目标组合（卖出理由见下）"],
            board=e.board, board_name=e.board_name, can_buy=e.can_buy))

    df = pd.DataFrame([r.__dict__ for r in rows])
    if not df.empty:
        df = df.sort_values("target_weight", ascending=False).reset_index(
            drop=True)
    if len(df):
        fees_est = float(sum(
            _position_fees(strategy_cfg, v, v)[0]
            for v in df["buy_value"] if v > 0))
    else:
        fees_est = 0.0
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
        "top_k": top_k, "horizon": horizon,
        "horizon_validated": horizon == 20,
        "max_weight": max_weight,
        "max_weight_derived": (max_weight > 0.10 + 1e-9),
        "account_capital": account_capital,
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
        "exclude_restricted": exclude_restricted,
        "excluded_restricted": excluded_restricted,
        "signal_version": "strategy_v2/S3",
        "price_source": ("live fetch" if live_symbols
                         else "canonical, same date as the signal"),
        "live_prices": {s: float(last[s]) for s in live_symbols},
        "forecast_version": (fc["forecast_version"].iloc[0]
                             if len(fc) else None),
        "cost_model": {"unit_buy_rate": buy_rate, "unit_sell_rate": sell_rate,
                       "round_trip_rate": rt_rate},
        "rows": df.to_dict("records") if len(df) else [],
    }
    return plan


#: 小资金适配规则（先于结果写死，与 alpha 选择无关，纯粹是资金/手数可行性）
SMALL_CAPITAL_MIN_HOLDINGS = 5      # 分散底线
SMALL_CAPITAL_MIN_INVESTED = 0.60   # 最小投入率（其余是现金拖累）
SMALL_CAPITAL_K_CANDIDATES = (3, 4, 5, 6, 7, 8, 10)


def suggest_top_k(capital: float, risk_profile: str = "balanced",
                  candidates=SMALL_CAPITAL_K_CANDIDATES) -> dict:
    """Largest K whose plan still clears the small-capital floors.

    A 100-share lot is 4,750 CNY of a 100,000 CNY book at K=20, so most
    A-share names are simply unbuyable and the portfolio ends up half in
    cash. This rule picks K from the price/lot arithmetic ALONE — no
    return, IC or backtest number enters the decision, so it cannot
    snoop on results.

    Rule: the largest K with holdings >= 5 and invested >= 60%; if none
    qualifies, the K with the highest invested fraction among those with
    holdings >= 5.
    """
    scans = []
    for k in candidates:
        try:
            p = build_trade_plan(capital=capital, top_k=k,
                                 risk_profile=risk_profile,
                                 exclude_restricted=True)
        except Exception:                                    # noqa: BLE001
            continue
        inv = p["total_buy_value"] / p["capital"]
        scans.append({"top_k": k, "invested": inv,
                      "n_positions": p["n_positions"],
                      "expected_net_return_pct": p["expected_net_return_pct"]})
    ok = [s for s in scans
          if s["n_positions"] >= SMALL_CAPITAL_MIN_HOLDINGS
          and s["invested"] >= SMALL_CAPITAL_MIN_INVESTED]
    if ok:
        chosen = max(ok, key=lambda s: s["top_k"])
        rule = (f"largest K with holdings>={SMALL_CAPITAL_MIN_HOLDINGS} and "
                f"invested>={SMALL_CAPITAL_MIN_INVESTED:.0%}")
    else:
        pool = [s for s in scans
                if s["n_positions"] >= SMALL_CAPITAL_MIN_HOLDINGS] or scans
        chosen = max(pool, key=lambda s: s["invested"]) if pool else None
        rule = "no K clears both floors -> highest invested fraction"
    return {"chosen_top_k": chosen["top_k"] if chosen else None,
            "rule": rule, "scans": scans, "capital": capital}


def plan_summary_by_board(plan: dict) -> List[dict]:
    """Per-board totals, split by whether the account can actually buy
    (spec ask: 科创板需 50 万，账户不具备 → 必须标注)."""
    rows = plan.get("rows", [])
    out: Dict[str, dict] = {}
    for r in rows:
        b = r.get("board", "UNKNOWN")
        d = out.setdefault(b, {
            "board": b, "board_name": r.get("board_name", b),
            "capital_required": r.get("capital_required", 0.0),
            "n": 0, "n_buyable": 0, "value": 0.0, "value_buyable": 0.0,
            "restricted_symbols": []})
        v = float(r.get("buy_value") or 0.0)
        d["n"] += 1
        d["value"] += v
        if r.get("can_buy"):
            d["n_buyable"] += 1
            d["value_buyable"] += v
        else:
            d["restricted_symbols"].append(r["symbol"])
    return sorted(out.values(), key=lambda d: -d["value"])


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
