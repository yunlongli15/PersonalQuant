# -*- coding: utf-8 -*-
"""Forward 报告与 dashboard 数据层（spec §26 / §28 / §40 / §41）。

**事实与解释分开**（§27）：报告里先把事实列全（收益 / IC / 换手 / 回撤），
再单独给"可以怎么说"。禁止从短期数字自动推出"模型失效"。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# 读取 forward 记录
# ---------------------------------------------------------------------------

def nav_series(store) -> pd.Series:
    """由 metrics/<date>.parquet 拼出的净值序列（派生，不单独存储）。"""
    rows = []
    d = store.root / "metrics"
    for p in sorted(d.glob("*.parquet")):
        if "__rev" in p.stem:
            continue
        try:
            df = pd.read_parquet(p)
        except Exception:
            continue
        if not df.empty:
            rows.append(df)
    if not rows:
        return pd.Series(dtype=float)
    m = pd.concat(rows, ignore_index=True)
    m["signal_date"] = pd.to_datetime(m["signal_date"])
    m = m.sort_values("signal_date").drop_duplicates("signal_date", keep="last")
    return m.set_index("signal_date")["portfolio_value"].astype(float)


def metrics_frame(store) -> pd.DataFrame:
    rows = []
    for p in sorted((store.root / "metrics").glob("*.parquet")):
        if "__rev" in p.stem:
            continue
        try:
            df = pd.read_parquet(p)
        except Exception:
            continue
        if not df.empty:
            rows.append(df)
    if not rows:
        return pd.DataFrame()
    m = pd.concat(rows, ignore_index=True)
    m["signal_date"] = pd.to_datetime(m["signal_date"])
    return m.sort_values("signal_date").drop_duplicates(
        "signal_date", keep="last").reset_index(drop=True)


def predictions_frame(store) -> pd.DataFrame:
    rows = []
    for p in sorted((store.root / "predictions").glob("*.parquet")):
        if "__rev" in p.stem:
            continue
        try:
            df = pd.read_parquet(p)
        except Exception:
            continue
        if not df.empty:
            rows.append(df)
    if not rows:
        return pd.DataFrame()
    m = pd.concat(rows, ignore_index=True)
    m["signal_date"] = pd.to_datetime(m["signal_date"])
    return m


# ---------------------------------------------------------------------------
# Dashboard 数据层（§28）
# ---------------------------------------------------------------------------

def build_dashboard(store, cfg: dict, benchmarks: Optional[Dict[str, pd.Series]] = None,
                    labels: Optional[Dict[int, pd.DataFrame]] = None
                    ) -> tuple:
    """返回 (DataFrame, dict)。GUI 将来直接读这两个，不重新算。"""
    from . import metrics as pm

    met = metrics_frame(store)
    preds = predictions_frame(store)
    nav = nav_series(store)
    hist = None
    if not nav.empty:
        hist = pm.performance(nav, benchmarks)
    ic_tab = pm.ic_table(preds, labels[20]) if (labels and 20 in labels
                                                and not preds.empty) \
        else pd.DataFrame()
    rows = []
    for _, r in met.iterrows():
        rows.append({
            "date": str(pd.Timestamp(r["signal_date"]).date()),
            "portfolio_value": float(r["portfolio_value"]),
            "cash": float(r["cash"]),
            "cash_weight": float(r["cash_weight"]),
            "n_positions": int(r["n_positions"]),
            "cumulative_return": float(r["cumulative_return"]),
            "drawdown": float(r["drawdown"]),
            "turnover": float(r["turnover"]),
            "transaction_cost": float(r["transaction_cost"]),
            "is_rebalance": bool(r["is_rebalance"]),
        })
    df = pd.DataFrame(rows)
    payload = {
        "generated_from": str(store.root),
        "n_days": int(len(df)),
        "first_date": df["date"].iloc[0] if len(df) else None,
        "last_date": df["date"].iloc[-1] if len(df) else None,
        "performance": hist or {},
        "prediction_quality": pm.summarize_ic(ic_tab) if len(ic_tab) else
        {"n_dates": 0},
        "strategy_version": cfg["paper_live"]["strategy_version"],
        "forward_start_date": cfg["paper_live"]["forward_start_date"],
        "record_only": bool(cfg["paper_live"]["record_only"]),
    }
    return df, payload


def save_dashboard(store, cfg: dict, df: pd.DataFrame, payload: dict) -> dict:
    out = store.root / "dashboard"
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "forward_dashboard.parquet", index=False)
    (out / "forward_dashboard.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")
    return {"parquet": str(out / "forward_dashboard.parquet"),
            "json": str(out / "forward_dashboard.json")}


# ---------------------------------------------------------------------------
# 月度报告（§26 / §40）
# ---------------------------------------------------------------------------

def _fmt(v, pct=True, nd=4):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "NA"
    return f"{v:.2%}" if pct else f"{v:.{nd}f}"


def monthly_report(store, cfg: dict, month: str,
                   benchmarks: Optional[Dict[str, pd.Series]] = None,
                   labels: Optional[Dict[int, pd.DataFrame]] = None,
                   revisions: Optional[List[dict]] = None) -> str:
    """生成 reports/forward_holdout/<YYYY-MM>.md 的正文。"""
    from . import metrics as pm
    from .config import verify_freeze

    met = metrics_frame(store)
    preds = predictions_frame(store)
    nav = nav_series(store)
    period = pd.Period(month, freq="M")
    if not met.empty:
        in_month = met[pd.to_datetime(met["signal_date"]).dt.to_period("M")
                       == period]
    else:
        in_month = met

    nav_m = nav[pd.to_datetime(nav.index).to_period("M") == period] \
        if not nav.empty else nav
    perf = pm.performance(nav, benchmarks) if not nav.empty else {}
    month_ret = np.nan
    if len(nav_m) >= 2:
        month_ret = float(nav_m.iloc[-1] / nav_m.iloc[0] - 1.0)

    ic_tab = pm.ic_table(preds, labels[20]) if (labels and 20 in labels
                                                and not preds.empty) \
        else pd.DataFrame()
    ic_m = ic_tab[pd.to_datetime(ic_tab["date"]).dt.to_period("M") == period] \
        if not ic_tab.empty else ic_tab
    ic_sum = pm.summarize_ic(ic_m) if len(ic_m) else {"n_dates": 0}

    topk = pm.topk_realized(preds, labels[20], int(
        cfg["paper_live"]["portfolio"]["top_k"])) if (labels and 20 in labels
                                                      and not preds.empty) \
        else pd.DataFrame()
    topk_m = topk[pd.to_datetime(topk["date"]).dt.to_period("M") == period] \
        if not topk.empty else topk

    lines = [
        f"# Forward Holdout 月度报告 — {month}", "",
        f"> 策略版本 `{cfg['paper_live']['strategy_version']}`（已冻结）｜ "
        f"模式 `record_only`｜ 观测起点 "
        f"{cfg['paper_live']['forward_start_date']}", "",
        "## 1. 事实（FACT）", "",
        f"- 本月观测天数：**{len(in_month)}**",
        f"- 本月收益：**{_fmt(month_ret)}**",
        f"- 累计收益：**{_fmt(perf.get('cumulative_return'))}**",
        f"- 最大回撤：**{_fmt(perf.get('max_drawdown'))}**",
        f"- Sharpe：**{_fmt(perf.get('sharpe'), pct=False)}**"
        + ("" if np.isfinite(perf.get("sharpe", np.nan)) else
           "（样本不足 60 天，按 §41 不计算、不年化）"),
        "",
    ]
    if benchmarks:
        lines += ["## 2. Benchmark（各自 weighting convention 已声明）", "",
                  "| 基准 | 累计 | 策略相对 |", "|---|---|---|"]
        for name in benchmarks:
            lines.append(
                f"| {name} | {_fmt(perf.get(f'{name}_cumulative'))} | "
                f"{_fmt(perf.get(f'{name}_active'))} |")
        lines.append("")
    lines += [
        "## 3. 交易与成本", "",
        f"- 本月换手（合计）：**{_fmt(in_month['turnover'].sum() if not in_month.empty else np.nan, pct=False)}**",
        f"- 本月交易成本：**{_fmt(in_month['transaction_cost'].sum() if not in_month.empty else np.nan, pct=False)}**",
        f"- 本月调仓次数：**{int(in_month['is_rebalance'].sum()) if not in_month.empty else 0}**",
        f"- 期末持仓数：**{int(in_month['n_positions'].iloc[-1]) if not in_month.empty else 0}**",
        "",
        "## 4. 预测质量", "",
        f"- IC 均值：**{_fmt(ic_sum.get('ic_mean'))}**（{ic_sum.get('n_dates')} 期）",
        f"- RankIC 均值：**{_fmt(ic_sum.get('rank_ic_mean'))}**",
        f"- ICIR：**{_fmt(ic_sum.get('icir'), pct=False)}**",
        f"- IC > 0 比例：**{_fmt(ic_sum.get('positive_ratio'))}**",
        f"- Top-K 实际前瞻收益（本月均值）：**"
        f"{_fmt(topk_m['topk_return'].mean() if not topk_m.empty else np.nan)}**",
        "",
    ]
    if not met.empty:
        last = met.iloc[-1]
        lines += [
            "## 5. 组合状态", "",
            f"- 组合市值：{float(last['portfolio_value']):,.0f}",
            f"- 现金占比：{_fmt(last['cash_weight'])}",
            f"- 当前回撤：{_fmt(last['drawdown'])}",
            "",
        ]
    fr = verify_freeze(cfg)
    lines += [
        "## 6. 冻结与漂移", "",
        f"- 冻结校验：**{'一致' if fr.get('is_frozen') and not fr.get('drift') else fr.get('detail')}**",
        f"- 本月 revision 记录：**{len(revisions or [])}**"
        + ("（append-only，未覆盖任何历史结果）" if not revisions else ""),
        "",
        "## 7. 数据质量与 PIT", "",
    ]
    if not in_month.empty and "signal_date" in in_month.columns:
        obs = []
        for d0 in in_month["signal_date"]:
            o = store.read_json("observations", d0)
            if o:
                obs.append(o)
        if obs:
            from collections import Counter
            c = Counter(o["audit_status"] for o in obs)
            lines.append(f"- PIT 审计结果分布：{dict(c)}")
            lines.append(f"- 状态分布："
                         f"{dict(Counter(o['status'] for o in obs))}")
    lines += [
        "",
        "## 8. 本月未做任何模型/参数修改", "",
        "从 clean forward holdout 起点（"
        f"{cfg['paper_live']['forward_start_date']}）起，**没有**进行任何：",
        "因子选择、模型选择、参数调整、prompt 调整、新闻阈值调整、"
        "交易成本调整、top_k 调整、调仓频率调整、优化器调整、风险限制调整。",
        "冻结哈希每日校验，见上节。", "",
        "## 8.5 数据质量 / 告警 / 冻结状态（STEP 12）", "",
    ]
    try:
        from pipeline.daily_report import load_latest_summary
        ds = load_latest_summary() or {}
        alerts = ds.get("alerts") or []
        from collections import Counter
        lines += [
            f"- 最近一次每日运行：{ds.get('date')}"
            f"（状态 {ds.get('status')}）",
            f"- 该次数据新鲜度："
            + "；".join(f"{r.get('domain')}={r.get('status')}"
                        for r in (ds.get('data', {}) or {}).get('freshness', [])),
            f"- 告警 {len(alerts)} 条："
            f"{dict(Counter(a['code'] for a in alerts))}",
        ]
        fz = (ds.get("strategy") or {})
        lines.append(
            f"- 生产冻结：策略 `{fz.get('strategy_version')}` / "
            f"模型 `{fz.get('model_version')}` / "
            f"分配 `{fz.get('allocation_method')}` / "
            f"执行 `{fz.get('execution_model')}`")
    except Exception as e:                                     # noqa: BLE001
        lines.append(f"- 每日运行摘要不可用：{type(e).__name__}")
    lines += [
        "",
        "## 9. 可以怎么说（ANALYSIS）", "",
        "> 本节允许的解释仅限于：描述本月相对基准的表现、"
        "指出样本量是否足以支撑任何结论。",
        "",
        "**样本不足时不得推断策略失效。** 月度样本对年化收益的分辨力极低"
        "（参见 `reports/步骤9-独立信息研究.md`：24 个月的可检出最小"
        "年化差异约 41pp）。短期 IC 波动属于正常范围，不构成任何修改理由。",
        "",
    ]
    return "\n".join(lines)


def yearly_report(store, cfg: dict, year: int,
                  benchmarks: Optional[Dict[str, pd.Series]] = None) -> str:
    """年度报告骨架（§41）。不足一年标记 INCOMPLETE YEAR，绝不年化。"""
    met = metrics_frame(store)
    nav = nav_series(store)
    in_year = met[pd.to_datetime(met["signal_date"]).dt.year == year] \
        if not met.empty else met
    n_days = len(in_year)
    complete = n_days >= 230
    lines = [f"# Forward Holdout 年度报告 — {year}", ""]
    if not complete:
        lines += [f"**INCOMPLETE YEAR**（仅 {n_days} 个观测日 < 230）。",
                  "按 §41：**不对短样本做年化**，不给出年化收益/年化波动。", ""]
    nav_y = nav[pd.to_datetime(nav.index).year == year] if not nav.empty else nav
    if len(nav_y) >= 2:
        lines += [f"- 区间收益（未年化）：{nav_y.iloc[-1] / nav_y.iloc[0] - 1:.2%}",
                  f"- 区间最大回撤：{float((nav_y / nav_y.cummax() - 1).min()):.2%}",
                  ""]
    lines += ["详见各月报告 `reports/forward_holdout/<YYYY-MM>.md`。", ""]
    return "\n".join(lines)
