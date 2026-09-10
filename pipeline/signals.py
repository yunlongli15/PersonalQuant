# -*- coding: utf-8 -*-
"""Signal / portfolio state snapshots (STEP 7C).

The GUI must be able to show today's candidates without re-running the
model on every page load, and the freshness panel must be able to say
when they were computed. So a signal refresh writes a snapshot to

    data/quant/signals_<as_of>.parquet     (per-symbol signal rows)
    data/quant/signals_latest.parquet      (copy of the newest)
    data/quant/forecast_state.json         (freshness stamp)

and the portfolio snapshot to

    data/quant/portfolio_state.json        (freshness stamp)

The computation reuses the FROZEN production model (strategy_v2 = S3) —
this module never trains anything.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUANT_DIR = PROJECT_ROOT / "data" / "quant"
SIGNALS_LATEST = QUANT_DIR / "signals_latest.parquet"
SIGNALS_STATE = QUANT_DIR / "signals_state.json"
PORTFOLIO_STATE = QUANT_DIR / "portfolio_state.json"

MODEL_PATH = PROJECT_ROOT / "experiments" / "news" / "strategy" / "model.txt"
STEP4_PACK = (PROJECT_ROOT / "experiments" / "factors" / "factor_run_001"
              / "factor_pack_v1.json")
NEWS_PACK = (PROJECT_ROOT / "experiments" / "news" / "news_factor_run_001"
             / "factor_pack_news_v1.json")


def _feature_names() -> list:
    step4 = json.loads(STEP4_PACK.read_text(encoding="utf-8"))
    news = json.loads(NEWS_PACK.read_text(encoding="utf-8"))
    return step4["selected"] + news["selected"]


def compute_signals(signal_date: str, top_k: int = 20,
                    universe_config: Optional[dict] = None) -> pd.DataFrame:
    """Frozen S3 predictions for every universe symbol at `signal_date`.

    Columns: symbol, prediction, raw_rank, name.
    Strictly PIT: features/labels/factors only use data <= signal_date
    (the STEP 3-6 machinery guarantees it; this function adds no data).
    """
    import yaml

    from factors.base import load_factor_data
    from factors.normalization import fill_missing, normalize_panel
    from factors.registry import FACTOR_REGISTRY, FACTORS
    from personal_quant.strategy.features import (compute_features,
                                                  flatten_columns)
    from personal_quant.strategy.model import AlphaModel
    from personal_quant.strategy.qlib_provider import \
        init_qlib_with_canonical
    from personal_quant.strategy.universe import build_universe

    cfg = yaml.safe_load((PROJECT_ROOT / "config" / "strategy_v1.yaml")
                         .read_text(encoding="utf-8"))
    if universe_config:
        cfg.update(universe_config)
    cfg["universe"]["st_filter"]["enabled"] = True     # live view only
    d = pd.Timestamp(signal_date)

    init_qlib_with_canonical()
    universe = build_universe(d, cfg)
    symbols = universe["symbol"].tolist()
    feats = compute_features(symbols, [d], cache=False)
    f = feats.get(d)
    if f is None or f.empty:
        raise RuntimeError(f"no features for {signal_date}")
    f = flatten_columns(f)

    data = load_factor_data("2014-06-01", signal_date)
    for name in _feature_names():
        panel = FACTORS[name](data, dates=[d]).reindex(pd.DatetimeIndex([d]))
        if FACTOR_REGISTRY[name]["category"] == "news":
            panel = fill_missing(normalize_panel(panel, "rank"), "drop",
                                 data.industries)
        else:
            panel = fill_missing(normalize_panel(panel, "rank"),
                                 "sector_median", data.industries)
        f = f.join(panel.loc[d].rename(name), how="left")

    model = AlphaModel.load(MODEL_PATH, dict(cfg["model"]["params"]),
                            seed=cfg["model"]["seed"])
    m = f.dropna(how="all")
    preds = pd.Series(model.predict(m[model.feature_columns]), index=m.index)
    out = preds.sort_values(ascending=False).rename("prediction").to_frame()
    out.index.name = "symbol"
    out = out.reset_index()
    out["signal_date"] = d
    out["raw_rank"] = range(1, len(out) + 1)
    names = universe.set_index("symbol")["name"] \
        if "name" in universe.columns else pd.Series(dtype=object)
    out["name"] = out["symbol"].map(names)
    out["is_top"] = out["raw_rank"] <= top_k
    return out


def save_signals(df: pd.DataFrame, as_of: Optional[str] = None) -> Path:
    QUANT_DIR.mkdir(parents=True, exist_ok=True)
    d = str(as_of or pd.Timestamp(df["signal_date"].iloc[0]).date())
    p = QUANT_DIR / f"signals_{d}.parquet"
    df.to_parquet(p, index=False)
    df.to_parquet(SIGNALS_LATEST, index=False)
    state = {
        "as_of": d,
        "computed_at": datetime.now().isoformat(timespec="seconds"),
        "n_symbols": int(len(df)),
        "model": str(MODEL_PATH.relative_to(PROJECT_ROOT)),
        "model_version": "strategy_v2/S3",
        "feature_version": "alpha158+factor_pack_v1+factor_pack_news_v1",
    }
    SIGNALS_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False),
                             encoding="utf-8")
    return p


def load_signals() -> pd.DataFrame:
    if not SIGNALS_LATEST.exists():
        return pd.DataFrame(columns=["symbol", "prediction", "raw_rank",
                                     "signal_date", "name", "is_top"])
    return pd.read_parquet(SIGNALS_LATEST)


def signals_state() -> dict:
    if not SIGNALS_STATE.exists():
        return {}
    return json.loads(SIGNALS_STATE.read_text(encoding="utf-8"))


def refresh_signals(signal_date: Optional[str] = None,
                    top_k: int = 20) -> dict:
    """Job entry point: compute + persist the signal snapshot."""
    if signal_date is None:
        from pipeline.freshness import last_trading_day

        ltd = last_trading_day()
        if ltd is None:
            raise RuntimeError("trading calendar is empty")
        signal_date = str(ltd.date())
    df = compute_signals(signal_date, top_k=top_k)
    p = save_signals(df, signal_date)
    return {"as_of": signal_date, "n_symbols": len(df), "path": str(p)}


def save_portfolio_state(as_of: str, plan: dict) -> Path:
    QUANT_DIR.mkdir(parents=True, exist_ok=True)
    state = {"as_of": as_of,
             "computed_at": datetime.now().isoformat(timespec="seconds"),
             **{k: v for k, v in plan.items() if k != "rows"}}
    PORTFOLIO_STATE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8")
    return PORTFOLIO_STATE


def portfolio_state() -> dict:
    if not PORTFOLIO_STATE.exists():
        return {}
    return json.loads(PORTFOLIO_STATE.read_text(encoding="utf-8"))


def refresh_portfolio_state(capital: float = 500_000.0,
                            top_k: int = 20,
                            **kwargs) -> dict:
    """Job entry point: build the trade plan and stamp the state file."""
    from pipeline.trade_plan import build_trade_plan

    plan = build_trade_plan(capital=capital, top_k=top_k, **kwargs)
    save_portfolio_state(plan["as_of"], plan)
    return {"as_of": plan["as_of"], "n_positions": len(plan["rows"]),
            "invested": plan["total_buy_value"]}
