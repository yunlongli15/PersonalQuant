# -*- coding: utf-8 -*-
"""行情与数据新鲜度（spec §17 / §62）。"""

from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

from ._common import PROJECT_ROOT, read_json, safe, unavailable

BENCHMARKS = {"CSI300": "000300.SH", "CSI500": "000905.SH",
              "CSI1000": "000852.SH", "SSE": "000001.SH"}


def latest_prices(symbols: Optional[List[str]] = None) -> Dict[str, float]:
    """最新收盘价：优先当日实时价（live_prices.json），否则用 canonical。

    只读。找不到就**不返回该 symbol**，由调用方决定怎么处理缺价
    （绝不当成 0）。
    """
    from personal_quant import db

    out: Dict[str, float] = {}
    live = read_json(PROJECT_ROOT / "data" / "quant" / "live_prices.json")
    if live and live.get("prices"):
        for sym, rec in live["prices"].items():
            try:
                out[sym] = float(rec["close"])
            except Exception:                                  # noqa: BLE001
                continue
    try:
        conn = db.connect()
        if symbols:
            marks = ",".join("?" * len(symbols))
            df = conn.execute(
                f"""SELECT symbol, close FROM daily_bars
                    WHERE trade_date = (SELECT MAX(trade_date) FROM daily_bars)
                      AND symbol IN ({marks})""", list(symbols)).fetch_df()
        else:
            df = conn.execute(
                "SELECT symbol, close FROM daily_bars WHERE trade_date = "
                "(SELECT MAX(trade_date) FROM daily_bars)").fetch_df()
        for _, r in df.iterrows():
            out.setdefault(r["symbol"], float(r["close"]))
    except Exception:                                          # noqa: BLE001
        pass
    return out


def price_date() -> Optional[str]:
    """行情数据的最新日期（§62：让用户知道数据不是实时的）。"""
    live = read_json(PROJECT_ROOT / "data" / "quant" / "live_prices.json")
    if live and live.get("price_date"):
        return str(live["price_date"])
    try:
        from personal_quant import db
        r = db.connect().execute(
            "SELECT MAX(trade_date) AS d FROM daily_bars").fetch_df()
        return str(r["d"].iloc[0]) if not r.empty else None
    except Exception:                                          # noqa: BLE001
        return None


def price_history(symbol: str, days: int = 250) -> List[dict]:
    """单只标的的历史收盘。"""
    from personal_quant import db

    try:
        df = db.connect().execute(
            """SELECT trade_date, close FROM daily_bars
               WHERE symbol = ? ORDER BY trade_date DESC LIMIT ?""",
            [symbol, int(days)]).fetch_df()
    except Exception:                                          # noqa: BLE001
        return []
    if df.empty:
        return []
    df = df.sort_values("trade_date")
    return [{"date": str(pd.Timestamp(r["trade_date"]).date()),
             "close": float(r["close"])} for _, r in df.iterrows()]


@safe(label="基准")
def benchmark_nav(label: str, start: str, end: str) -> dict:
    from personal_quant.strategy.benchmarks import (equal_weight_market_nav,
                                                    index_nav)
    if label == "EW_MARKET":
        s = equal_weight_market_nav(str(start), str(end))
        conv = "等权全市场（每日再平衡、流动性过滤）"
    else:
        sym = BENCHMARKS.get(label, label)
        s = index_nav(sym, str(start), str(end))
        conv = f"买入持有指数 {sym}"
    if s is None or len(s) < 2:
        return unavailable(f"{label} 无数据")
    return {"available": True, "label": label, "convention": conv,
            "series": [{"date": str(pd.Timestamp(i).date()), "value": float(v)}
                       for i, v in s.items()]}


@safe(label="数据新鲜度")
def data_status() -> dict:
    from pipeline.freshness import data_status as _ds
    rows = [f.as_dict() for f in _ds()]
    return {"available": True, "rows": rows,
            "any_stale": any(r.get("status") == "STALE" for r in rows)}
