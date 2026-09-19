# -*- coding: utf-8 -*-
"""风险指标（spec §30 / §38）。

组合波动/回撤/VaR/CVaR/beta 复用 `portfolio/portfolio_metrics.py` 与
`personal_quant/strategy/metrics.py` 的既有实现，不另写一套。
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pandas as pd

from ._common import safe, to_float, unavailable
from . import market_service, portfolio_service


def _conn():
    from wealth import db
    return db.connect()


@safe(label="风险")
def metrics(benchmark: str = "CSI300") -> dict:
    from personal_quant.strategy import metrics as mt
    from wealth import engine

    perf = engine.performance(_conn())
    pos = portfolio_service.positions()

    out: dict = {"available": True, "benchmark": benchmark}

    # --- 组合层（需要净值序列）---
    if perf.get("empty"):
        out["nav_based"] = None
        out["note"] = "还没有净值序列 —— 波动/回撤/VaR 需要先录入每日快照"
    else:
        nav = perf["curve"]["value"]
        nav.index = perf["curve"].index
        ret = mt.daily_returns(nav).dropna()
        out["nav_based"] = {
            "volatility": float(mt.annualized_volatility(nav)),
            "max_drawdown": float(mt.max_drawdown(nav)),
            "worst_day": float(ret.min()) if len(ret) else None,
            "var_95_1d": float(np.percentile(ret, 5)) if len(ret) >= 20 else None,
            "cvar_95_1d": (float(ret[ret <= np.percentile(ret, 5)].mean())
                           if len(ret) >= 20 else None),
            "n_days": int(len(ret)),
        }
        try:
            b = market_service.benchmark_nav(
                benchmark, str(nav.index[0].date()), str(nav.index[-1].date()))
            if b.get("available"):
                bs = pd.Series([p["value"] for p in b["series"]],
                               index=[pd.Timestamp(p["date"])
                                      for p in b["series"]])
                beta_alpha = mt.alpha_beta(nav, bs)
                out["nav_based"]["beta"] = float(beta_alpha[1])
                out["nav_based"]["alpha_annualized"] = float(beta_alpha[0])
                out["nav_based"]["information_ratio"] = float(
                    mt.information_ratio(nav, bs))
        except Exception:                                      # noqa: BLE001
            pass

    # --- 持仓层（无需净值）---
    if pos.get("available") and pos["rows"]:
        # 集中度必须用**已投资权重**（归一化到 1），不能用"占总资产"的权重。
        # 否则现金占 90% 时，HHI 会被现金稀释成一个无意义的极小值
        # （实测：1 只持仓 + 93% 现金 → HHI 0.0046，有效持仓数 217，
        # 完全误导）。现金单独用 cash_ratio 报告。
        mv = np.array([to_float(r["market_value"]) for r in pos["rows"]])
        invested = float(mv[mv > 0].sum())
        w = (mv[mv > 0] / invested) if invested > 0 else np.array([])
        hhi = float((w ** 2).sum()) if len(w) else None
        out["holdings_based"] = {
            "n_positions": len(pos["rows"]),
            "invested_value": invested,
            "hhi": hhi,
            "effective_n": (1.0 / hhi) if hhi else None,
            "top_weight": float(w.max()) if len(w) else None,
            "top5_weight": float(np.sort(w)[::-1][:5].sum()) if len(w) else None,
            "cash_ratio": None,
            "basis": "已投资权重（不含现金）；现金见 cash_ratio",
        }
        alloc = portfolio_service.allocation()
        if alloc.get("available"):
            out["holdings_based"]["cash_ratio"] = alloc.get("cash_ratio")
    else:
        out["holdings_based"] = None

    return out


@safe(label="行业暴露")
def sector_exposure() -> dict:
    """行业暴露（用 canonical 的 CSRC 行业分类；当前快照，已知限制）。"""
    from personal_quant import db
    pos = portfolio_service.positions()
    if not pos.get("available") or not pos["rows"]:
        return unavailable("没有持仓")
    syms = [r["symbol"] for r in pos["rows"] if r["symbol"]]
    if not syms:
        return unavailable("持仓没有可识别的代码")
    marks = ",".join("?" * len(syms))
    try:
        df = db.connect().execute(
            f"SELECT symbol, industry FROM industries WHERE symbol IN ({marks})",
            syms).fetch_df()
    except Exception as e:                                     # noqa: BLE001
        return unavailable(f"行业数据不可用：{e}")
    ind = dict(zip(df["symbol"], df["industry"])) if not df.empty else {}
    buckets: dict = {}
    total = 0.0
    unknown = 0.0
    for r in pos["rows"]:
        mv = to_float(r["market_value"])
        total += mv
        k = ind.get(r["symbol"]) or "未知"
        if k == "未知":
            unknown += mv
        buckets[k] = buckets.get(k, 0.0) + mv
    rows = [{"industry": k, "value": v,
             "weight": (v / total) if total else 0.0}
            for k, v in sorted(buckets.items(), key=lambda kv: -kv[1])]
    return {"available": True, "rows": rows, "total_value": total,
            "unknown_weight": (unknown / total) if total else 0.0,
            "note": "行业为当前 CSRC 快照（历史行业变更罕见，已知限制）"}


@safe(label="集中度告警")
def concentration_alert(threshold: float = 0.25) -> dict:
    """单只权重超过阈值 → 只提示（§38：只报警，不自动交易）。"""
    pos = portfolio_service.positions()
    if not pos.get("available"):
        return pos
    over = [{"symbol": r["symbol"], "name": r["name"],
             "weight": to_float(r["weight"])}
            for r in pos["rows"] if to_float(r["weight"]) > threshold]
    return {"available": True, "threshold": threshold, "over": over,
            "ok": not over,
            "note": "仅提示，不产生任何调整动作"}
