# -*- coding: utf-8 -*-
"""Forward 观测指标（spec §14 / §16 / §18 / §19 / §39）。

三条纪律
--------
1. **不足周期就是 NA，绝不填 0**（§18）：某信号日的 60 日前瞻收益还没走完，
   那一格只能是 NaN，不能当成 0 收益参与统计。
2. **事实与解释分开**（§27）：本模块只产出事实（收益/IC/换手/回撤），
   不下"模型失效"这类判断。判断留给报告，且必须有统计证据。
3. **只观察，不反馈**（§17）：短期 IC 下降不触发任何参数改动。
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

HORIZONS = (1, 5, 20, 60)


# ---------------------------------------------------------------------------
# 前瞻收益
# ---------------------------------------------------------------------------

def realized_returns(predictions: pd.DataFrame,
                     labels: Dict[int, pd.DataFrame],
                     calendar: Optional[pd.DatetimeIndex] = None,
                     horizons: Sequence[int] = HORIZONS) -> pd.DataFrame:
    """给每条预测补上 realized_return_{h}d。

    labels: {horizon: DataFrame(date × symbol)}。窗口未走完的格子保持 NA。
    """
    if predictions.empty:
        return predictions.assign(**{f"realized_return_{h}d": [] for h in horizons})
    out = predictions.copy()
    for h in horizons:
        lab = labels.get(h)
        col = f"realized_return_{h}d"
        if lab is None:
            out[col] = np.nan
            continue
        idx = pd.MultiIndex.from_arrays(
            [pd.to_datetime(out["signal_date"]), out["symbol"]])
        flat = lab.stack(dropna=False)
        flat.index = flat.index.set_names(["date", "symbol"])
        out[col] = flat.reindex(idx).to_numpy()
    return out


def incomplete_window_mask(signal_dates: Sequence[pd.Timestamp],
                           calendar: pd.DatetimeIndex,
                           horizon: int) -> pd.Series:
    """哪些信号日的 h 日前瞻窗口还没走完（= 必须记 NA）。"""
    cal = pd.DatetimeIndex(calendar)
    pos = {d: i for i, d in enumerate(cal)}
    last = cal[-1] if len(cal) else None
    out = {}
    for d in signal_dates:
        d = pd.Timestamp(d)
        i = pos.get(d)
        out[d] = bool(last is None or i is None or i + horizon >= len(cal))
    return pd.Series(out)


# ---------------------------------------------------------------------------
# 预测质量
# ---------------------------------------------------------------------------

def ic_table(predictions: pd.DataFrame, label: pd.DataFrame,
             min_stocks: int = 30) -> pd.DataFrame:
    """逐信号日的 IC / RankIC。predictions 需含 date, symbol, prediction。

    label: date × symbol 的前瞻收益（与预测**日期对齐**）。
    """
    if predictions.empty:
        return pd.DataFrame(columns=["date", "n", "ic", "rank_ic"])
    rows = []
    dates = pd.to_datetime(predictions["signal_date"]
                           if "signal_date" in predictions else
                           predictions["date"])
    work = predictions.assign(_d=dates)
    for d, g in work.groupby("_d"):
        if d not in label.index:
            continue
        y = label.loc[d].reindex(g["symbol"])
        m = pd.concat([g.set_index("symbol")["prediction"], y.rename("y")],
                      axis=1).dropna()
        if len(m) < min_stocks or m["y"].std() == 0 or \
                m["prediction"].std() == 0:
            continue
        rows.append({"date": d, "n": len(m),
                     "ic": m["prediction"].corr(m["y"]),
                     "rank_ic": m["prediction"].corr(m["y"],
                                                     method="spearman")})
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True) \
        if rows else pd.DataFrame(columns=["date", "n", "ic", "rank_ic"])


def summarize_ic(tab: pd.DataFrame) -> dict:
    if tab.empty:
        return {"n_dates": 0, "ic_mean": np.nan, "rank_ic_mean": np.nan,
                "icir": np.nan, "positive_ratio": np.nan}
    sd = tab["ic"].std(ddof=0)
    return {
        "n_dates": int(len(tab)),
        "ic_mean": float(tab["ic"].mean()),
        "rank_ic_mean": float(tab["rank_ic"].mean()),
        "icir": float(tab["ic"].mean() / sd) if sd > 0 else np.nan,
        "positive_ratio": float((tab["ic"] > 0).mean()),
    }


def rolling_ic(tab: pd.DataFrame, window: int = 20) -> pd.Series:
    if tab.empty:
        return pd.Series(dtype=float)
    s = tab.set_index("date")["ic"]
    return s.rolling(min_periods=max(2, window // 2), window=window).mean()


def rolling_rank_ic(tab: pd.DataFrame, window: int = 20) -> pd.Series:
    if tab.empty:
        return pd.Series(dtype=float)
    return tab.set_index("date")["rank_ic"].rolling(
        min_periods=max(2, window // 2), window=window).mean()


def topk_realized(predictions: pd.DataFrame, label: pd.DataFrame,
                  k: int = 20) -> pd.DataFrame:
    """每个信号日 Top-K 的实际前瞻收益（组合真正吃到的部分）。"""
    if predictions.empty:
        return pd.DataFrame(columns=["date", "topk_return", "n"])
    work = predictions.copy()
    work["date"] = pd.to_datetime(
        work["signal_date"] if "signal_date" in work else work["date"])
    rows = []
    for d, g in work.groupby("date"):
        if d not in label.index:
            continue
        y = label.loc[d].reindex(g["symbol"])
        m = pd.concat([g.set_index("symbol")["prediction"], y.rename("y")],
                      axis=1).dropna()
        if len(m) < k:
            continue
        rows.append({"date": d,
                     "topk_return": float(m.nlargest(k, "prediction")["y"].mean()),
                     "n": len(m)})
    return pd.DataFrame(rows)


def quantile_returns(predictions: pd.DataFrame, label: pd.DataFrame,
                     n_q: int = 5) -> pd.DataFrame:
    """逐日分位收益（Q1..Qn），用来对照历史研究期的分布。"""
    if predictions.empty:
        return pd.DataFrame(columns=["date"] + [f"Q{i+1}" for i in range(n_q)])
    work = predictions.copy()
    work["date"] = pd.to_datetime(
        work["signal_date"] if "signal_date" in work else work["date"])
    rows = []
    for d, g in work.groupby("date"):
        if d not in label.index:
            continue
        y = label.loc[d].reindex(g["symbol"])
        m = pd.concat([g.set_index("symbol")["prediction"], y.rename("y")],
                      axis=1).dropna()
        if len(m) < n_q * 10:
            continue
        q = pd.qcut(m["prediction"].rank(method="first"), n_q, labels=False)
        means = m.groupby(q)["y"].mean()
        rows.append({"date": d, **{f"Q{i+1}": float(means.get(i, np.nan))
                                   for i in range(n_q)}})
    return pd.DataFrame(rows)


def prediction_stats(predictions: pd.DataFrame) -> pd.DataFrame:
    """预测分布与集中度（§21 / §31）。逐日一行。"""
    if predictions.empty:
        return pd.DataFrame(columns=["date", "n", "score_mean", "score_std",
                                     "dispersion", "top1_z", "top1"])
    work = predictions.copy()
    work["date"] = pd.to_datetime(
        work["signal_date"] if "signal_date" in work else work["date"])
    rows = []
    for d, g in work.groupby("date"):
        s = g["prediction"].dropna()
        if len(s) < 10 or s.std() == 0:
            continue
        top1 = float(s.max())
        rows.append({
            "date": d, "n": int(len(s)),
            "score_mean": float(s.mean()), "score_std": float(s.std()),
            "dispersion": float(s.std() / abs(s.mean()))
            if s.mean() != 0 else np.nan,
            "top1_z": float((top1 - s.mean()) / s.std()),
            "top1": top1,
        })
    return pd.DataFrame(rows)


def rank_stability(prev: pd.DataFrame, cur: pd.DataFrame,
                   k: int = 20) -> float:
    """两期 Top-K 名单的重合度（1 = 完全没变）。"""
    if prev.empty or cur.empty:
        return np.nan
    a = set(prev.nlargest(k, "prediction")["symbol"])
    b = set(cur.nlargest(k, "prediction")["symbol"])
    if not a or not b:
        return np.nan
    return len(a & b) / len(a | b)


# ---------------------------------------------------------------------------
# 组合业绩
# ---------------------------------------------------------------------------

def drawdown(nav: pd.Series) -> pd.Series:
    if nav.empty:
        return nav
    return nav / nav.cummax() - 1.0


def performance(nav: pd.Series, benchmarks: Optional[Dict[str, pd.Series]] = None,
                turnover: Optional[pd.Series] = None,
                costs: Optional[pd.Series] = None) -> dict:
    """forward 业绩事实（不下结论）。"""
    from personal_quant.strategy import metrics as mt

    out = {"n_days": int(len(nav))}
    if nav.empty:
        return out
    ret = mt.daily_returns(nav)
    out.update({
        "cumulative_return": float(nav.iloc[-1] / nav.iloc[0] - 1.0),
        "max_drawdown": float(mt.max_drawdown(nav)),
        "volatility": float(mt.annualized_volatility(nav)),
        "worst_day": float(ret.min()) if len(ret) else np.nan,
        "best_day": float(ret.max()) if len(ret) else np.nan,
        "positive_day_ratio": float((ret > 0).mean()) if len(ret) else np.nan,
    })
    # 样本不足时不给 Sharpe / 年化——短样本年化是误导（§41）
    if len(nav) >= 60:
        out["annualized_return"] = float(mt.annualized_return(nav))
        out["sharpe"] = float(mt.sharpe_ratio(nav))
    else:
        out["annualized_return"] = np.nan
        out["sharpe"] = np.nan
        out["note"] = f"样本 {len(nav)} 天 < 60，不年化、不算 Sharpe"
    for name, b in (benchmarks or {}).items():
        b = b.reindex(nav.index).ffill()
        if b.dropna().empty:
            continue
        out[f"{name}_cumulative"] = float(b.iloc[-1] / b.iloc[0] - 1.0)
        out[f"{name}_active"] = out["cumulative_return"] - \
            out[f"{name}_cumulative"]
    if turnover is not None and len(turnover):
        out["avg_turnover"] = float(turnover.mean())
        out["total_turnover"] = float(turnover.sum())
    if costs is not None and len(costs):
        out["total_cost"] = float(costs.sum())
        out["cost_bps_of_nav"] = float(costs.sum() / nav.mean() * 1e4) \
            if nav.mean() else np.nan
    return out


def distribution_shift(forward: pd.Series, historical: pd.Series) -> dict:
    """forward 分布 vs 历史分布（§32 / §39）。只描述，不触发任何调整。"""
    f = pd.Series(forward).dropna()
    h = pd.Series(historical).dropna()
    if f.empty or h.empty:
        return {"n_forward": len(f), "n_historical": len(h),
                "mean_forward": np.nan, "mean_historical": np.nan,
                "shift_z": np.nan}
    sd = h.std(ddof=0)
    return {
        "n_forward": int(len(f)), "n_historical": int(len(h)),
        "mean_forward": float(f.mean()), "mean_historical": float(h.mean()),
        "std_forward": float(f.std(ddof=0)), "std_historical": float(sd),
        "shift_z": float((f.mean() - h.mean()) / sd) if sd > 0 else np.nan,
    }
