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
NEWS_PACKS = {
    "v1": (PROJECT_ROOT / "experiments" / "news" / "news_factor_run_001"
           / "factor_pack_news_v1.json"),
    "v2": (PROJECT_ROOT / "experiments" / "news" / "news_factor_run_002"
           / "factor_pack_news_v2.json"),
}
NEWS_PACK = NEWS_PACKS["v1"]        # 向后兼容的别名

#: 策略注册表。切换生产策略 = 改 PRODUCTION_STRATEGY 这一行，
#: 不要散落着改模型路径。
#:
#:   production_clean_v1 = **当前生产**。Alpha158 only，无自定义特征、
#:                         **不使用任何新闻因子**（PHASE 7 选定）
#:   S3_v1               = 旧生产基线。新闻特征选自带残缺的语料，
#:                         标记 CONTAMINATED，仅作历史参照
#:   S3_v2               = 修复新闻后重训，回测严重退化，已否决
#:
#: `custom_features` 省略（None）= 按 news_version 从 factor_pack 推；
#: 显式给列表 = 以它为准。生产策略必须显式写死，不能靠推导 ——
#: 推导链一旦改动，生产特征集会跟着悄悄变。
STRATEGIES = {
    "production_clean_v1": {
        "model": "experiments/clean/clean_A/model.txt",
        "custom_features": [],
        "news_version": "v1",          # 不读新闻；取值只为让口径确定
        "feature_version": "alpha158",
        "uses_news": False,
        "features_label": "Alpha158",
    },
    "S3_v1": {
        "model": "experiments/news/strategy/model.txt",
        "custom_features": None,
        "news_version": "v1",
        "feature_version": "alpha158+factor_pack_v1+factor_pack_news_v1",
        "uses_news": True,
        "features_label": "Alpha158 + factor_pack_v1 + 新闻 v1",
    },
    "S3_v2": {
        "model": "experiments/news/strategy_s3_v2/model.txt",
        "custom_features": None,
        "news_version": "v2",
        "feature_version": "alpha158+factor_pack_v1+factor_pack_news_v2",
        "uses_news": True,
        "features_label": "Alpha158 + factor_pack_v1 + 新闻 v2",
    },
}

#: 生产默认策略（PHASE 7 §十二/§二十三）。
PRODUCTION_STRATEGY = "production_clean_v1"


def strategy_spec(name: Optional[str] = None) -> dict:
    name = name or PRODUCTION_STRATEGY
    if name not in STRATEGIES:
        raise ValueError(f"未知策略 {name!r}；可选 {sorted(STRATEGIES)}")
    spec = dict(STRATEGIES[name])
    spec["name"] = name
    spec["model_path"] = PROJECT_ROOT / spec["model"]
    return spec


def signal_path(as_of: str, strategy: Optional[str] = None) -> Path:
    """信号的**版本化**路径。

    钉版消费者（daily_exit_paper_v1）读这一份，所以生产策略切到 S3_v2
    时，正在跑的实验读到的信号逐位不变。
    """
    name = strategy or PRODUCTION_STRATEGY
    return QUANT_DIR / f"signals_{name}_{as_of}.parquet"


def _feature_names(strategy: Optional[str] = None) -> list:
    """该策略要算的自定义特征。

    - `custom_features` 显式给了列表 -> 用它（生产策略走这条）；
    - 给了空列表 -> 没有自定义特征（production_clean_v1 就是这种，
      只用 Alpha158）；
    - 为 None -> 按 news_version 从 STEP4 pack + 新闻 pack 推。

    **必须跟着 strategy 走**：写死 v1 的话，S3_v2 会在只有
    `regulatory_event_count_20d` 的模型上喂进 v1 的三个新闻因子，
    模型要么 KeyError，要么拿到错的列 —— 这正是"切换策略"最容易
    悄悄出错的地方。
    """
    spec = strategy_spec(strategy)
    explicit = spec.get("custom_features")
    if explicit is not None:
        return list(explicit)
    step4 = json.loads(STEP4_PACK.read_text(encoding="utf-8"))
    news = json.loads(NEWS_PACKS[spec["news_version"]].read_text(encoding="utf-8"))
    return step4["selected"] + news["selected"]


def _symbol_names() -> pd.Series:
    """symbol -> name from the canonical securities parquet (read-only,
    DB-free; the frozen universe query does not select names)."""
    import pyarrow.parquet as pq

    p = PROJECT_ROOT / "data" / "parquet" / "securities"
    if not p.exists():
        return pd.Series(dtype=object)
    try:
        df = pq.read_table(str(p), columns=["symbol", "name"]).to_pandas()
        return df.dropna(subset=["name"]).drop_duplicates("symbol") \
            .set_index("symbol")["name"]
    except Exception:
        return pd.Series(dtype=object)


def compute_signals(signal_date: str, top_k: int = 20,
                    universe_config: Optional[dict] = None,
                    strategy: Optional[str] = None) -> pd.DataFrame:
    """S3 predictions for every universe symbol at `signal_date`.

    Columns: symbol, prediction, raw_rank, name.
    Strictly PIT: features/labels/factors only use data <= signal_date
    (the STEP 3-6 machinery guarantees it; this function adds no data).

    strategy 默认取 PRODUCTION_STRATEGY；同时决定读哪一版新闻数据。
    """
    import yaml

    from factors.base import load_factor_data, set_news_version

    set_news_version(strategy_spec(strategy)["news_version"])
    from personal_quant.strategy.features import (compute_features,
                                                  flatten_columns)
    from personal_quant.strategy.model import AlphaModel
    from personal_quant.strategy.universe import build_universe

    cfg = yaml.safe_load((PROJECT_ROOT / "config" / "strategy_v1.yaml")
                         .read_text(encoding="utf-8"))
    if universe_config:
        cfg.update(universe_config)
    cfg["universe"]["st_filter"]["enabled"] = True     # live view only
    d = pd.Timestamp(signal_date)

    # NOTE: do NOT call init_qlib_with_canonical() in THIS process.
    # compute_features() below spawns per-quarter worker subprocesses that
    # initialise qlib themselves; if the parent has already brought qlib
    # (and its joblib pool) up on Windows, the worker deadlocks and the
    # run times out after 30 minutes with no error (reproduced 2026-09-17,
    # and the reason features.py uses subprocesses at all). The universe
    # comes from DuckDB and the model from LightGBM — neither needs qlib
    # here.
    universe = build_universe(d, cfg)
    symbols = universe["symbol"].tolist()
    feats = compute_features(symbols, [d], cache=False)
    f = feats.get(d)
    if f is None or f.empty:
        raise RuntimeError(f"no features for {signal_date}")
    f = flatten_columns(f)

    # 自定义特征。没有的话**不加载因子数据** —— load_factor_data 要把
    # 事件快照和行情面板全读进来（几十秒、数 GB），
    # production_clean_v1 只用 Alpha158，白读一遍纯属浪费。
    names = _feature_names(strategy)
    if names:
        from factors.normalization import fill_missing, normalize_panel
        from factors.registry import FACTOR_REGISTRY, FACTORS

        data = load_factor_data("2014-06-01", signal_date)
        for name in names:
            panel = FACTORS[name](data, dates=[d]).reindex(pd.DatetimeIndex([d]))
            if FACTOR_REGISTRY[name]["category"] == "news":
                panel = fill_missing(normalize_panel(panel, "rank"), "drop",
                                     data.industries)
            else:
                panel = fill_missing(normalize_panel(panel, "rank"),
                                     "sector_median", data.industries)
            f = f.join(panel.loc[d].rename(name), how="left")

    _spec = strategy_spec(strategy)
    if not _spec["model_path"].exists():
        raise FileNotFoundError(
            f"策略 {_spec['name']} 的模型不存在：{_spec['model']}")
    model = AlphaModel.load(_spec["model_path"], dict(cfg["model"]["params"]),
                            seed=cfg["model"]["seed"])
    m = f.dropna(how="all")
    preds = pd.Series(model.predict(m[model.feature_columns]), index=m.index)
    out = preds.sort_values(ascending=False).rename("prediction").to_frame()
    out.index.name = "symbol"
    out = out.reset_index()
    out["signal_date"] = d
    out["raw_rank"] = range(1, len(out) + 1)
    names = universe.set_index("symbol")["name"] \
        if "name" in universe.columns else _symbol_names()
    out["name"] = out["symbol"].map(names)
    out["is_top"] = out["raw_rank"] <= top_k
    return out


def save_signals(df: pd.DataFrame, as_of: Optional[str] = None,
                 strategy: Optional[str] = None) -> Path:
    QUANT_DIR.mkdir(parents=True, exist_ok=True)
    spec = strategy_spec(strategy)
    d = str(as_of or pd.Timestamp(df["signal_date"].iloc[0]).date())
    p = QUANT_DIR / f"signals_{d}.parquet"
    df.to_parquet(p, index=False)
    df.to_parquet(SIGNALS_LATEST, index=False)
    # 版本化副本：钉版消费者（daily_exit_paper_v1）读它。
    # 没有这一份的话，生产策略一切换，正在跑的实验每天读到的信号就变了。
    df.to_parquet(signal_path(d, spec["name"]), index=False)
    state = {
        "as_of": d,
        "computed_at": datetime.now().isoformat(timespec="seconds"),
        "n_symbols": int(len(df)),
        "model": str(spec["model"]),
        "model_version": f"strategy_v2/{spec['name']}",
        "feature_version": spec["feature_version"],
        "strategy": spec["name"],
        "news_version": spec["news_version"],
        "uses_news": spec.get("uses_news", True),
        "features_label": spec.get("features_label", spec["feature_version"]),
        "custom_features": list(_feature_names(spec["name"])),
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
                    top_k: int = 20,
                    strategy: Optional[str] = None) -> dict:
    """Job entry point: compute + persist the signal snapshot.

    strategy 默认 = PRODUCTION_STRATEGY。传别的名字只改这一次刷新的口径，
    **不改生产默认** —— 回退/对比实验（例如 `--strategy S3_v1`）不需要
    动代码，也不会让日常刷新跟着变。
    """
    if signal_date is None:
        from pipeline.freshness import last_trading_day

        ltd = last_trading_day()
        if ltd is None:
            raise RuntimeError("trading calendar is empty")
        signal_date = str(ltd.date())
    df = compute_signals(signal_date, top_k=top_k, strategy=strategy)
    p = save_signals(df, signal_date, strategy=strategy)
    return {"as_of": signal_date, "n_symbols": len(df), "path": str(p),
            "strategy": strategy_spec(strategy)["name"]}


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
    """Build the trade plan with EXPLICIT sizing and stamp the state file.

    这里的 500_000 / 20 是**回测口径**。面向用户的每日计划不要用这些
    默认值 —— 它不知道账户资金、套用小资金 K 规则、也不做实时价覆盖。
    刷新链的 portfolio_refresh 已经改走 `write_recommendation_note`
    （账户口径）；直接调用本函数时请显式传 capital/top_k。
    """
    from trade_plan.plan import build_trade_plan, save_plan

    plan = build_trade_plan(capital=capital, top_k=top_k, **kwargs)
    save_plan(plan)
    save_portfolio_state(plan["as_of"], plan)
    return {"as_of": plan["as_of"], "n_positions": len(plan["rows"]),
            "invested": plan["total_buy_value"]}
