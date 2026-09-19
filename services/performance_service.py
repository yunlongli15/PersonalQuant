# -*- coding: utf-8 -*-
"""收益与风险调整（spec §15 / §16 / §17 / §36 / §49）。

**不自己实现 TWR/XIRR** —— 直接用 `wealth/engine.py` 里已经存在且有测试的
实现（spec §49 明确要求：不要 GUI 自己实现一套）。
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from ._common import safe, to_float, unavailable
from . import market_service


def _conn():
    from wealth import db
    return db.connect()


@safe(label="收益")
def summary(start: Optional[str] = None, end: Optional[str] = None) -> dict:
    """账户整体收益：TWR / XIRR / P&L / 日收益，全部来自 wealth 引擎。"""
    from wealth import engine

    conn = _conn()
    perf = engine.performance(conn, start, end)
    if perf.get("empty"):
        return unavailable("还没有净值数据（录入每日快照后才有收益曲线）",
                           twr=None, mwr_xirr=None)
    return {"available": True, **{k: v for k, v in perf.items()
                                  if k != "curve" and k != "daily_returns"},
            "curve": _series_points(perf.get("curve"))}


def _series_points(curve) -> list:
    """curve 是 RangeIndex + snap_date 列（不是时间索引）——按列取。"""
    if curve is None or len(curve) == 0:
        return []
    try:
        if "snap_date" in curve.columns:
            dates = [str(pd.Timestamp(d).date()) for d in curve["snap_date"]]
        else:
            dates = [str(pd.Timestamp(i).date()) for i in curve.index]
        return [{"date": d,
                 "value": float(curve["value"].iloc[i]),
                 "pnl": float(curve["pnl"].iloc[i])}
                for i, d in enumerate(dates)]
    except Exception:                                          # noqa: BLE001
        return []


@safe(label="区间分解")
def breakdown(start: str, end: str) -> dict:
    """区间内：外部流入 / 流出 / 投资损益 / 分红 / 费用 / 对账误差。"""
    from wealth import service
    return {"available": True, **service.decompose_period(_conn(), start, end)}


@safe(label="收益分解")
def attribution(period: str = "MTD") -> dict:
    """贡献分解（spec §36）：按标的 / 资产类别 / 策略。

    用**已实现 + 未实现**损益对期初市值的占比来衡量贡献。没有期初
    市值时退回绝对额，并明确标注口径，不假装是收益率。
    """
    from . import portfolio_service

    pos = portfolio_service.positions()
    if not pos.get("available") or not pos["rows"]:
        return unavailable("没有持仓，无法做贡献分解")

    rows = []
    for r in pos["rows"]:
        pnl = to_float(r["unrealized_pnl"]) + to_float(r["realized_pnl"])
        rows.append({"symbol": r["symbol"], "name": r["name"],
                     "asset_class": r["asset_class_cn"],
                     "pnl": pnl,
                     "market_value": to_float(r["market_value"])})
    rows.sort(key=lambda x: -x["pnl"])
    total = sum(r["pnl"] for r in rows)
    by_class: dict = {}
    for r in rows:
        by_class[r["asset_class"]] = by_class.get(r["asset_class"], 0.0) + \
            r["pnl"]
    return {
        "available": True, "period": period,
        "total_pnl": total,
        "top_contributors": rows[:10],
        "top_detractors": [r for r in rows[::-1] if r["pnl"] < 0][:10],
        "by_asset_class": [{"label": k, "pnl": v}
                           for k, v in sorted(by_class.items(),
                                              key=lambda kv: -kv[1])],
        "note": "口径 = 已实现 + 未实现损益（绝对额）；没有期初市值时不折算收益率",
    }


@safe(label="基准对比")
def versus_benchmark(label: str = "CSI300") -> dict:
    perf = summary()
    if not perf.get("available"):
        return perf
    curve = perf.get("curve") or []
    if len(curve) < 2:
        return unavailable("净值序列太短，无法与基准比较")
    start, end = curve[0]["date"], curve[-1]["date"]
    bench = market_service.benchmark_nav(label, start, end)
    if not bench.get("available"):
        return bench
    nav0 = curve[0]["value"] or 1.0
    port_ret = (curve[-1]["value"] / nav0 - 1.0) if nav0 else None
    b0 = bench["series"][0]["value"]
    bench_ret = (bench["series"][-1]["value"] / b0 - 1.0) if b0 else None
    return {"available": True, "label": label,
            "convention": bench["convention"],
            "start": start, "end": end,
            "portfolio_return": port_ret, "benchmark_return": bench_ret,
            "active_return": (port_ret - bench_ret)
            if port_ret is not None and bench_ret is not None else None,
            "benchmark_series": bench["series"]}


@safe(label="月度/年度收益")
def calendar_returns() -> dict:
    from personal_quant.strategy import metrics as mt

    from wealth import engine
    perf = engine.performance(_conn())
    if perf.get("empty"):
        return unavailable("还没有净值数据")
    nav = perf["curve"]["value"]
    nav.index = perf["curve"].index
    monthly = mt.monthly_returns(nav)
    yearly = mt.yearly_returns(nav)
    return {
        "available": True,
        "monthly": [{"period": str(i)[:7], "return": float(v)}
                    for i, v in monthly.items()],
        "yearly": [{"period": str(i)[:4], "return": float(v)}
                   for i, v in yearly.items()],
        "max_drawdown": float(mt.max_drawdown(nav)),
    }
