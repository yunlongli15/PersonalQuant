# -*- coding: utf-8 -*-
"""日报与运行清单（STEP 12, spec §14 / §15 / §16 / §20）。

**事实与解释分开**（§15）：

    FACT     本月/当日发生了什么（数字）
    ANALYSIS 允许怎么写（相对基准如何、样本够不够）
    禁止     从短期数字自动推断"模型有效/失效"

日报落在 `reports/daily/YYYY-MM-DD.md`，摘要落在同名 `.json`（给 GUI 读，§39）。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from pipeline import daily as _daily

# ---------------------------------------------------------------------------
# 格式化小工具
# ---------------------------------------------------------------------------

def _money(v, nd: int = 2) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    try:
        return f"{float(v):,.{nd}f}"
    except (TypeError, ValueError):
        return "—"


def _pct(v, nd: int = 2, signed: bool = False) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    try:
        return (f"{float(v) * 100:+.{nd}f}%" if signed
                else f"{float(v) * 100:.{nd}f}%")
    except (TypeError, ValueError):
        return "—"


def _num(v, nd: int = 4) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    try:
        return f"{float(v):,.{nd}f}"
    except (TypeError, ValueError):
        return "—"


# ---------------------------------------------------------------------------
# 摘要（§16，GUI 读这个）
# ---------------------------------------------------------------------------

def build_summary(ctx) -> dict:
    run = ctx.run
    sd = ctx.store_data
    paper = sd.get("paper_result")
    perf = sd.get("performance") or {}
    risk = sd.get("risk") or {}
    personal = sd.get("personal") or {}
    alerts = sd.get("alerts") or []
    from pipeline.daily_alerts import summarize as al_sum

    recommendation = {}
    try:
        from services import recommendation_service
        rec = recommendation_service.latest()
        if rec.get("available"):
            recommendation = {
                "signal_date": rec.get("signal_date"),
                "n_rows": rec.get("n_rows"),
                "total_buy_value": rec.get("total_buy_value"),
                "rows": rec.get("rows", [])[:20],
            }
    except Exception:                                          # noqa: BLE001
        pass

    return {
        "run_id": run.run_id,
        "date": run.date,
        "status": run.status,
        "generated_at": datetime.now(timezone.utc).astimezone()
        .isoformat(timespec="seconds"),
        "duration_s": round(run.duration_s, 2),
        "dry_run": run.dry_run,
        "backfill": run.backfill,
        "summary": {
            "n_tasks": len(run.tasks),
            "n_warnings": len(run.warnings),
            "n_errors": len(run.errors),
            "failed": run.failed(),
            "blocked": run.blocked(),
            "forward_observation": run.forward_observation,
        },
        "portfolio": {
            "market_value": personal.get("market_value"),
            "cash": personal.get("cash"),
            "total_value": personal.get("total"),
            "n_positions": personal.get("n_positions"),
            "cumulative_return": perf.get("cumulative_return"),
            "twr": perf.get("twr"),
            "mwr_xirr": perf.get("mwr_xirr"),
            "max_drawdown": perf.get("max_drawdown"),
        },
        "strategy": sd.get("freeze", {}).get("recorded", {}) or {},
        "paper_live": ({
            "status": getattr(paper, "status", None),
            "is_rebalance": bool(sd.get("is_rebalance")),
            "n_predictions": getattr(paper, "n_predictions", 0),
            "n_orders": getattr(paper, "n_orders", 0),
            "n_fills": getattr(paper, "n_fills", 0),
            "portfolio_value": (getattr(paper, "metrics", {}) or {})
            .get("portfolio_value"),
            "execution_date": getattr(paper, "execution_date", None),
            "pending": getattr(paper, "pending", False),
        } if paper is not None else None),
        "risk": {
            "nav_based": risk.get("nav_based"),
            "holdings_based": risk.get("holdings_based"),
        },
        "news": {
            "latest": (sd.get("market_latest")),
            "task": (run.task("news").as_dict()
                     if run.task("news") else None),
        },
        "alerts": alerts,
        "alert_summary": al_sum(alerts),
        "data": {"market_latest": sd.get("market_latest"),
                 "freshness": sd.get("freshness", [])},
        "recommendation": recommendation,
        "timestamps": {
            "started": run.started, "ended": run.ended,
            "market_latest": sd.get("market_latest"),
            "signal": (recommendation or {}).get("signal_date"),
        },
    }


# ---------------------------------------------------------------------------
# 日报 Markdown（§14，17 个板块）
# ---------------------------------------------------------------------------

def render_markdown(ctx, summary: dict) -> str:
    run = ctx.run
    sd = ctx.store_data
    s = summary
    p = s["portfolio"]
    paper = s.get("paper_live") or {}
    risk = s.get("risk") or {}

    L = [
        f"# 每日运行报告 · {s['date']}", "",
        f"> run_id `{s['run_id']}` ｜ 状态 **{s['status']}** ｜ "
        f"耗时 {s['duration_s']:.1f}s ｜ "
        f"生成于 {s['generated_at']}",
        "",
        "## 1. Pipeline 状态", "",
        f"- 任务 {s['summary']['n_tasks']} 个，"
        f"失败 {len(s['summary']['failed'])}，"
        f"跳过 {len(s['summary']['blocked'])}，"
        f"告警 {s['summary']['n_warnings']}",
        f"- 正式 forward 观测："
        f"**{'是' if s['summary']['forward_observation'] else '否'}**",
        "",
        "| 步骤 | 状态 | 耗时 | 说明 |", "|---|---|---|---|",
    ]
    for t in run.tasks:
        L.append(f"| {t.name} | {t.status} | {t.duration_s:.1f}s | "
                 f"{(t.detail or t.error)[:70]} |")

    L += [
        "", "## 2. 数据更新", "",
        f"- 行情最新：**{s['data']['market_latest'] or '—'}**",
        f"- 各域新鲜度：",
    ]
    for r in s["data"]["freshness"]:
        L.append(f"  - {r.get('domain')}: {r.get('status')} "
                 f"（最新 {r.get('latest')}）")

    L += [
        "", "## 3. Paper Live 状态", "",
    ]
    if not paper or paper.get("status") is None:
        L.append("- 本日未运行 paper live")
    else:
        L += [
            f"- 状态：**{paper['status']}** ｜ "
            f"{'调仓日' if paper['is_rebalance'] else '监控日'}",
            f"- 预测 {paper['n_predictions']} 只 ｜ 订单 {paper['n_orders']} ｜ "
            f"成交 {paper['n_fills']}",
            f"- 成交日：{paper.get('execution_date') or '—'}"
            + ("（订单挂起，等 T+1）" if paper.get("pending") else ""),
            f"- Paper 组合市值：{_money(paper.get('portfolio_value'))}",
        ]

    L += [
        "", "## 4-7. 个人账户与收益", "",
        f"- 持仓市值：{_money(p.get('market_value'))}",
        f"- 现金：{_money(p.get('cash'))}",
        f"- 总资产：**{_money(p.get('total_value'))}**",
        f"- 持仓数：{p.get('n_positions')}",
        f"- 累计收益：{_pct(p.get('cumulative_return'), signed=True)}",
        f"- TWR：{_pct(p.get('twr'), signed=True)} ｜ "
        f"XIRR：{_pct(p.get('mwr_xirr'), signed=True)}",
        f"- 最大回撤：{_pct(p.get('max_drawdown'))}",
        "",
        "> MTD / YTD 需要完整净值序列；序列不足时这里显示 — 而不是编一个数。",
        "",
        "## 8. 基准", "",
    ]
    try:
        from services import performance_service
        vb = performance_service.versus_benchmark()
        if vb.get("available"):
            L += [
                f"- 基准 `{vb['label']}`（{vb['convention']}）",
                f"- 区间 {vb['start']} ~ {vb['end']}",
                f"- 组合 {_pct(vb['portfolio_return'], signed=True)} ｜ "
                f"基准 {_pct(vb['benchmark_return'], signed=True)} ｜ "
                f"超额 {_pct(vb['active_return'], signed=True)}",
            ]
        else:
            L.append(f"- 暂不可比：{vb.get('reason')}")
    except Exception as e:                                     # noqa: BLE001
        L.append(f"- 基准不可用：{type(e).__name__}: {e}")

    L += ["", "## 9. 当前持仓", ""]
    try:
        from services import portfolio_service
        pos = portfolio_service.positions()
        if pos.get("available") and pos["rows"]:
            L += ["| 代码 | 名称 | 数量 | 成本 | 现价 | 市值 | 浮盈 |",
                  "|---|---|---|---|---|---|---|"]
            for r in pos["rows"][:20]:
                L.append(f"| {r['symbol']} | {r['name']} | "
                         f"{_num(r['quantity'], 0)} | {_num(r['avg_cost'], 3)} "
                         f"| {_num(r['price'], 3)} | "
                         f"{_money(r['market_value'])} | "
                         f"{_money(r['unrealized_pnl'])} |")
        else:
            L.append("- 暂无持仓")
    except Exception as e:                                     # noqa: BLE001
        L.append(f"- 不可用：{e}")

    L += ["", "## 10. 当前建议", ""]
    rec = s.get("recommendation") or {}
    if rec.get("rows"):
        L += [f"信号日 **{rec.get('signal_date')}**，共 {rec.get('n_rows')} 条"
              "（PAPER ONLY）", "",
              "| 代码 | 名称 | 动作 | 排名 | 目标权重 |", "|---|---|---|---|---|"]
        for r in rec["rows"][:15]:
            L.append(f"| {r.get('symbol')} | {r.get('name')} | "
                     f"{r.get('action')} | {r.get('rank')} | "
                     f"{_pct(r.get('target_weight'))} |")
    else:
        L.append("- 本日无建议（非调仓日或还没有交易计划）")

    L += ["", "## 11. 风险", ""]
    hb = risk.get("holdings_based") or {}
    nb = risk.get("nav_based") or {}
    if hb:
        L += [f"- 持仓数 {hb.get('n_positions')} ｜ HHI {_num(hb.get('hhi'))} "
              f"｜ 有效持仓 {_num(hb.get('effective_n'), 1)}",
              f"- 最大单只权重 {_pct(hb.get('top_weight'))} ｜ "
              f"现金比例 {_pct(hb.get('cash_ratio'))}"]
    if nb:
        L += [f"- 年化波动 {_pct(nb.get('volatility'))} ｜ "
              f"最大回撤 {_pct(nb.get('max_drawdown'))} ｜ "
              f"VaR95 {_pct(nb.get('var_95_1d'))}"]
    if not hb and not nb:
        L.append("- 暂无风险指标（需要持仓或净值序列）")

    L += ["", "## 12. 新闻", ""]
    try:
        from services import news_service
        nw = news_service.latest(limit=5)
        if nw.get("available"):
            for r in nw["rows"]:
                L.append(f"- {r['date']} **{r['symbol']}** "
                         f"{r['event_type']}（{r['direction_cn']}）")
        else:
            L.append(f"- {nw.get('reason')}")
    except Exception as e:                                     # noqa: BLE001
        L.append(f"- 不可用：{e}")

    L += ["", "## 13. 数据告警", ""]
    dw = [r for r in s["data"]["freshness"] if r.get("status") != "OK"]
    if dw:
        for r in dw:
            L.append(f"- {r.get('domain')}: {r.get('status')} "
                     f"（{r.get('detail') or r.get('latest')}）")
    else:
        L.append("- 无")

    L += ["", "## 14. 漂移告警", ""]
    fz = sd.get("freeze") or {}
    L.append(f"- 生产冻结：{'一致' if fz.get('ok') else fz.get('detail')}")
    if fz.get("mismatches"):
        L.append(f"- **不一致项**：{fz['mismatches']}")

    L += ["", "## 15. 版本与哈希", "",
          f"- git commit：`{s['strategy'].get('git_commit') or sd.get('git_commit') or '—'}`",
          f"- 策略版本：`{s['strategy'].get('strategy_version') or '—'}`",
          f"- 特征版本：`{s['strategy'].get('feature_version') or '—'}`",
          f"- 模型版本：`{s['strategy'].get('model_version') or '—'}`",
          f"- 输入指纹：`{sd.get('fingerprint')}`",
          "", "## 16. Forward 观测状态", ""]

    start = (s["strategy"].get("forward_holdout_start")
             or sd.get("forward_start") or "2026-09-18")
    ml = s["data"]["market_latest"]
    if ml and pd.Timestamp(ml) < pd.Timestamp(start):
        L += [f"- **WAITING_FOR_FORWARD_DATA** —— 行情最新 {ml} "
              f"< forward 起点 {start}",
              "- 这是**预期状态**，不是故障。数据到位后自动开始记录。"]
    else:
        L.append(f"- 行情 {ml} ≥ 起点 {start}，"
                 f"本日 forward 观测："
                 f"{'已记录' if s['summary']['forward_observation'] else '未记录'}")

    L += ["", "## 17. 告警", ""]
    if s["alerts"]:
        L += ["| 级别 | 代码 | 说明 |", "|---|---|---|"]
        for a in s["alerts"]:
            L.append(f"| {a['level']} | {a['code']} | {a['detail'][:80]} |")
    else:
        L.append("- 无告警")
    L.append("")
    L.append("> 所有告警**只报警**：不调整策略、不重训模型、不改组合权重。")

    # ---- 事实 / 解释分离（§15）----------------------------------------
    L += [
        "", "---", "", "## 事实与解释", "",
        "### FACT（本日实际发生了什么）", "",
        f"- Pipeline 状态：{s['status']}",
        f"- 个人账户总资产：{_money(p.get('total_value'))}",
        f"- 当日持仓数：{p.get('n_positions')}",
        f"- 行情最新：{s['data']['market_latest'] or '—'}",
        f"- 告警：{len(s['alerts'])} 条",
        "",
        "### ANALYSIS（允许怎么写）", "",
        "只允许描述相对基准的表现，以及样本量是否足以支撑结论。",
        "",
        "**不得**从单日数字推断\"模型有效\"或\"模型失效\"。"
        "长期结论只能来自历史研究报告（见 `reports/` 下的 STEP 报告）；"
        "而 forward 的长期证据需要时间累积 —— 按协议，"
        "样本不足时不做年化、不下结论。",
        "",
        "> 本报告由 `python scripts/run_daily.py` 自动生成，"
        "未进行任何模型训练、因子选择或参数调整。",
    ]
    return "\n".join(L)


# ---------------------------------------------------------------------------
# 写盘
# ---------------------------------------------------------------------------

def write_daily_report(ctx) -> dict:
    _daily.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    summary = build_summary(ctx)
    md = render_markdown(ctx, summary)
    mdp = _daily.REPORT_DIR / f"{ctx.run.date}.md"
    jsonp = _daily.REPORT_DIR / f"{ctx.run.date}.json"
    mdp.write_text(md, encoding="utf-8")
    jsonp.write_text(json.dumps(summary, ensure_ascii=False, indent=2,
                                default=str), encoding="utf-8")
    # GUI 读的"最新"指针
    (_daily.REPORT_DIR / "latest.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")
    ctx.store_data["summary"] = summary
    return {"markdown": str(mdp), "json": str(jsonp)}


def build_manifest(ctx) -> dict:
    """组装运行清单。

    **必须在写的那一刻组装** —— 之前的写法是 task_manifest 直接 dump
    ctx.run.manifest，但那个字典要等任务循环结束后才被填上
    run_id/status/tasks/…，结果是写出去一份几乎空的清单。
    """
    from pipeline import freeze as fz

    run, sd = ctx.run, ctx.store_data
    rec = (sd.get("freeze", {}) or {}).get("recorded", {}) or {}
    payload = dict(run.manifest)
    payload.update({
        "run_id": run.run_id, "date": run.date, "status": run.status,
        "start_time": run.started, "end_time": run.ended,
        "duration_s": round(run.duration_s, 2),
        "git_commit": fz.git_commit(),
        "strategy_version": rec.get("strategy_version", "strategy_v2"),
        "model_version": rec.get("model_version", "s3"),
        "feature_version": rec.get("feature_version", "alpha158+factor_pack_v1"),
        "news_version": rec.get("news_feature_version",
                                "factor_pack_news_v1"),
        "data_snapshot_id": sd.get("market_latest"),
        "is_rebalance": bool(sd.get("is_rebalance")),
        "forward_observation": run.forward_observation,
        "paper_root": sd.get("paper_root"),
        "dry_run": run.dry_run, "backfill": run.backfill,
        "tasks": [t.as_dict() for t in run.tasks],
        "warnings": run.warnings, "errors": run.errors,
        "input_fingerprint": sd.get("fingerprint"),
    })
    return payload


def write_manifest(ctx) -> str:
    _daily.MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    p = _daily.MANIFEST_DIR / f"{ctx.run.date}.json"
    payload = build_manifest(ctx)
    ctx.run.manifest = payload
    if "summary" in ctx.store_data:
        payload["daily_summary"] = {
            "status": ctx.store_data["summary"]["status"],
            "n_alerts": ctx.store_data["summary"]["alert_summary"]["n"],
        }
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2,
                            default=str), encoding="utf-8")
    (_daily.MANIFEST_DIR / "latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")
    return str(p)


def load_latest_summary() -> Optional[dict]:
    """GUI / CLI 读最新一次运行的摘要（§39）。"""
    p = _daily.REPORT_DIR / "latest.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:                                          # noqa: BLE001
        return None
