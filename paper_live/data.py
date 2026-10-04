# -*- coding: utf-8 -*-
"""数据接入层（唯一与行情/因子/模型的接触面）。

之所以做成对象而不是散落的函数调用：forward 引擎必须能在**不碰数据库**的
情况下被测试（tests/forward/ 用假 provider 跑完整流程），也必须在真实运行时
只读 signal_date 之前的数据。把这条边界收在一个类里，PIT 才有地方可审。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class ProviderStats:
    """一次运行消费了哪些数据（写进 manifest，供日后复盘 §7）。"""
    latest_trading_day: Optional[str] = None
    latest_bar_date: Optional[str] = None
    n_universe: int = 0
    n_features: int = 0
    n_custom_factors: int = 0
    feature_source: str = ""
    news_latest: Optional[str] = None
    financial_latest: Optional[str] = None
    data_snapshot_id: str = ""
    consumed_factors: List[str] = field(default_factory=list)


class LiveDataProvider:
    """真实数据源：canonical parquet + DuckDB + 冻结模型。"""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.p = cfg["paper_live"]
        self.stats = ProviderStats()
        self._model = None
        self._factor_data = None

    # ------------------------------------------------------------- 交易日
    def latest_trading_day(self, on_or_before=None) -> Optional[pd.Timestamp]:
        from factors.base import load_calendar
        cal = load_calendar()
        if on_or_before is None:
            return pd.Timestamp(cal[-1]) if len(cal) else None
        sub = cal[cal <= pd.Timestamp(on_or_before)]
        return pd.Timestamp(sub[-1]) if len(sub) else None

    def latest_bar_date(self, symbols: Optional[List[str]] = None,
                        on_or_before: Optional[pd.Timestamp] = None
                        ) -> Optional[pd.Timestamp]:
        """默认给库里最新的一天；给 on_or_before 则给**该日及之前**的最新一天。

        审计必须用后者：历史回放时库里有更新的数据，但那不等于我们消费了它。
        """
        from personal_quant import db
        q = "SELECT MAX(trade_date) AS d FROM daily_bars"
        cond, params = [], []
        if symbols:
            marks = ",".join("?" * len(symbols))
            cond.append(f"symbol IN ({marks})")
            params += list(symbols)
        if on_or_before is not None:
            cond.append("trade_date <= ?")
            params.append(str(pd.Timestamp(on_or_before).date()))
        if cond:
            q += " WHERE " + " AND ".join(cond)
        row = db.connect().execute(q, params).fetch_df()
        d = row["d"].iloc[0]
        return pd.Timestamp(d) if pd.notna(d) else None

    def trading_calendar(self) -> pd.DatetimeIndex:
        from factors.base import load_calendar
        return load_calendar()

    # ------------------------------------------------------------- 股票池
    def universe(self, date: pd.Timestamp) -> List[str]:
        import yaml
        from personal_quant.strategy.universe import build_universe
        base = yaml.safe_load(
            (PROJECT_ROOT / self.p["paths"]["universe_config"]).read_text(
                encoding="utf-8"))
        u = self.p["universe"]
        base["universe"]["st_filter"]["enabled"] = bool(u.get("st_filter",
                                                              True))
        base["universe"]["min_listing_days"] = int(u["min_listing_days"])
        base["universe"]["suspension"]["max_absent_days"] = int(
            u["suspension_max_absent_days"])
        base["universe"]["liquidity"]["min_amount"] = float(
            u["liquidity_min_amount"])
        syms = build_universe(pd.Timestamp(date), base)["symbol"].tolist()
        self.stats.n_universe = len(syms)
        return syms

    # ------------------------------------------------------------- 特征
    def feature_matrix(self, date: pd.Timestamp,
                       symbols: List[str]) -> pd.DataFrame:
        """Alpha158（与 strategy_v1 同一 handler），只用到 date 为止的数据。"""
        from personal_quant.strategy.features import (compute_features,
                                                      flatten_columns)
        feats = compute_features(symbols, [pd.Timestamp(date)], cache=True)
        f = feats.get(pd.Timestamp(date))
        if f is None or f.empty:
            raise RuntimeError(f"{pd.Timestamp(date).date()} 没有可用特征")
        f = flatten_columns(f).reindex(symbols)
        self.stats.n_features = int(f.shape[1])
        self.stats.feature_source = "data/derived/features"
        return f

    # ------------------------------------------------------------- 自定义因子
    def custom_factors(self, date: pd.Timestamp,
                       symbols: List[str]) -> pd.DataFrame:
        from factors.base import load_factor_data
        from factors.normalization import fill_missing, normalize_panel
        from factors.registry import FACTOR_REGISTRY, FACTORS

        packs = []
        for rel in self.p["alpha"]["feature_packs"]:
            packs += json.loads(
                (PROJECT_ROOT / rel).read_text(encoding="utf-8"))["selected"]
        seen, names = set(), []
        for n in packs:
            if n not in seen:
                seen.add(n)
                names.append(n)

        data = load_factor_data("2014-06-01", str(pd.Timestamp(date).date()))
        cols = []
        for name in names:
            panel = FACTORS[name](data, dates=[pd.Timestamp(date)])
            panel = panel.reindex(pd.DatetimeIndex([pd.Timestamp(date)]))
            if FACTOR_REGISTRY[name]["category"] == "news":
                panel = fill_missing(normalize_panel(panel, "rank"), "drop",
                                     data.industries)
            else:
                panel = fill_missing(normalize_panel(panel, "rank"),
                                     "sector_median", data.industries)
            cols.append(panel.loc[pd.Timestamp(date)].reindex(symbols)
                        .rename(name))
        out = pd.concat(cols, axis=1)
        self.stats.n_custom_factors = int(out.shape[1])
        self.stats.consumed_factors = names
        return out

    # ------------------------------------------------------------- 模型
    def model(self):
        if self._model is None:
            import yaml
            from personal_quant.strategy.model import AlphaModel
            base = yaml.safe_load(
                (PROJECT_ROOT / self.p["paths"]["model_params"]).read_text(
                    encoding="utf-8"))
            self._model = AlphaModel.load(
                PROJECT_ROOT / self.p["alpha"]["model"],
                dict(base["model"]["params"]), seed=base["model"]["seed"])
        return self._model

    def predict(self, features: pd.DataFrame,
                custom: pd.DataFrame) -> pd.Series:
        f = features.join(custom, how="left")
        m = f.dropna(how="all")
        model = self.model()
        missing = [c for c in model.feature_columns if c not in m.columns]
        if missing:
            raise RuntimeError(f"模型需要的特征缺失 {len(missing)} 列："
                               f"{missing[:5]}")
        return pd.Series(model.predict(m[model.feature_columns]), index=m.index)

    # ------------------------------------------------------------- 行情
    def prices(self, symbols: List[str],
               date: pd.Timestamp) -> pd.Series:
        from personal_quant import db
        if not symbols:
            return pd.Series(dtype=float)
        marks = ",".join("?" * len(symbols))
        df = db.connect().execute(
            f"SELECT symbol, close FROM daily_bars WHERE trade_date = ? "
            f"AND symbol IN ({marks})",
            [str(pd.Timestamp(date).date())] + list(symbols)).fetch_df()
        return df.set_index("symbol")["close"].astype(float)

    def names(self, symbols: List[str]) -> Dict[str, str]:
        from personal_quant import db
        if not symbols:
            return {}
        marks = ",".join("?" * len(symbols))
        df = db.connect().execute(
            f"SELECT symbol, name FROM securities WHERE symbol IN ({marks})",
            list(symbols)).fetch_df()
        return dict(zip(df["symbol"], df["name"]))

    def close_panel(self, symbols: List[str], start, end) -> pd.DataFrame:
        from personal_quant import db
        marks = ",".join("?" * len(symbols))
        df = db.connect().execute(
            f"SELECT trade_date, symbol, close FROM daily_bars "
            f"WHERE trade_date BETWEEN ? AND ? AND symbol IN ({marks})",
            [str(pd.Timestamp(start).date()), str(pd.Timestamp(end).date())]
            + list(symbols)).fetch_df()
        if df.empty:
            return pd.DataFrame()
        return df.pivot(index="trade_date", columns="symbol", values="close")

    def execute(self, symbol: str, signal_date: pd.Timestamp, side: str,
                shares: int, limit_threshold: float):
        from personal_quant.strategy.execution import execute_order
        return execute_order(symbol, pd.Timestamp(signal_date), side, shares,
                             limit_threshold)

    # ------------------------------------------------------------- 基准
    def benchmark_nav(self, symbol: str, start, end) -> pd.Series:
        from personal_quant.strategy.benchmarks import (equal_weight_market_nav,
                                                        index_nav)
        if symbol == "EW_MARKET":
            return equal_weight_market_nav(str(start), str(end))
        return index_nav(symbol, str(start), str(end))

    # ------------------------------------------------------------- 新鲜度
    def news_latest(self) -> Optional[pd.Timestamp]:
        from pipeline.freshness import news_latest
        return news_latest()

    def financial_latest(self) -> Optional[pd.Timestamp]:
        from pipeline.freshness import financial_latest
        return financial_latest()

    def bars(self, symbols: List[str], start, end) -> pd.DataFrame:
        """open/high/low/close/volume —— 供执行与审计使用。"""
        from personal_quant import db
        if not symbols:
            return pd.DataFrame()
        marks = ",".join("?" * len(symbols))
        return db.connect().execute(
            f"SELECT trade_date, symbol, open, high, low, close, volume "
            f"FROM daily_bars WHERE trade_date BETWEEN ? AND ? "
            f"AND symbol IN ({marks})",
            [str(pd.Timestamp(start).date()), str(pd.Timestamp(end).date())]
            + list(symbols)).fetch_df()

    def financial_availability(self, symbols: List[str]) -> pd.DataFrame:
        from personal_quant import db
        if not symbols:
            return pd.DataFrame(columns=["symbol", "availability_date"])
        marks = ",".join("?" * len(symbols))
        return db.connect().execute(
            f"SELECT DISTINCT symbol, availability_date FROM "
            f"financial_metrics WHERE symbol IN ({marks})",
            list(symbols)).fetch_df()

    def news_availability(self, symbols: List[str],
                          on_or_before: Optional[pd.Timestamp] = None
                          ) -> pd.DataFrame:
        """**截至 on_or_before 可用**的新闻发布时间（per symbol）。

        不能直接 `MAX(published_at)` 全表扫——那问的是"库里有啥"，
        历史回放时必然返回 2026 年的文档，把正常的回放误判成 PIT 违规。

        盘后(>15:00)→次日的规则在 derived 因子层执行
        （docs/步骤5-新闻时点规则.md），由 tests/news/test_news_pit.py 与因子
        投毒测试覆盖；这里只回答"信号日为止有没有新闻、有多新"。
        """
        from personal_quant import db
        if not symbols:
            return pd.DataFrame(columns=["symbol", "published_at"])
        marks = ",".join("?" * len(symbols))
        cond, params = [f"symbol IN ({marks})"], list(symbols)
        if on_or_before is not None:
            cond.append("published_at <= ?")
            params.append(str(pd.Timestamp(on_or_before).date()) + " 23:59:59")
        try:
            return db.connect().execute(
                f"SELECT symbol, MAX(published_at) AS published_at "
                f"FROM news_documents WHERE {' AND '.join(cond)} "
                f"GROUP BY symbol", params).fetch_df()
        except Exception:
            return pd.DataFrame(columns=["symbol", "published_at"])
