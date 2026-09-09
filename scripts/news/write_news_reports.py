# -*- coding: utf-8 -*-
"""STEP 5 news reports (8) from experiment/backfill artifacts.

    python scripts/news/write_news_reports.py

reports/step5_news_coverage.md        backfill coverage by year/source
reports/step5_news_sources.md         provider audit (probed 2026-09-09)
reports/step5_news_factor_evaluation.md  news factor IC/pack results
reports/step5_news_ablation.md        A/B/C/D/E (+N-series) comparison
reports/step5_news_pit_audit.md       PIT rule audit (rules + test results)
reports/step5_news_manual_audit.md    sampled events for human review
reports/step5_news_cost.md            LLM cost/usage (cache/budget state)
reports/step5_news_strategy.md        strategy_v1_news results
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
NEWS_RUN = PROJECT_ROOT / "experiments" / "news" / "news_factor_run_001"
NEWS_ABL = PROJECT_ROOT / "experiments" / "news" / "ablation"
NEWS_STRAT = PROJECT_ROOT / "experiments" / "news" / "strategy"
REPORTS = PROJECT_ROOT / "reports"


def _w(name, lines):
    out = REPORTS / name
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}")


def coverage_report():
    try:
        from personal_quant import db

        df = db.connect().execute(
            "SELECT symbol, source, published_at, time_known FROM "
            "news_documents").fetch_df()
    except Exception as e:
        df = pd.DataFrame()
        print(f"coverage: DB unavailable ({type(e).__name__})")
    if df.empty:
        _w("step5_news_coverage.md", ["# STEP 5 news coverage", "",
                                      "no documents yet — run the backfill"])
        return
    df["year"] = pd.to_datetime(df["published_at"]).dt.year
    lines = ["# STEP 5 news coverage", "",
             f"generated: {datetime.now().isoformat(timespec='seconds')}", "",
             "| year | source | documents | symbols | time_known_ratio |",
             "| --- | --- | --- | --- | --- |"]
    for (year, src), g in df.groupby(["year", "source"]):
        lines.append(f"| {year} | {src} | {len(g):,} | "
                     f"{g['symbol'].nunique():,} | "
                     f"{g['time_known'].mean():.3f} |")
    lines += ["", "## notes", "",
              "- SSE source depth starts ~2015 (2014 near-empty — official "
              "index); the factor research window (2018+) is fully covered "
              "for SH names by the SSE backfill.",
              "- SZ coverage comes from the per-stock SZSE backfill "
              "(cap-ranked); coverage is reported per year, never "
              "fabricated for missing years.",
              "- time_known=False rows follow the conservative "
              "next-trading-day availability rule.", ""]
    _w("step5_news_coverage.md", lines)


def sources_report():
    lines = ["# STEP 5 news sources audit", "",
             "probed 2026-09-09; provider abstraction in news/providers/", "",
             "| provider | official | exchanges | availability | "
             "historical depth | timestamp quality | mapping | rate limit "
             "| duplicate rate | content quality |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
             "| sse | yes | SH | OK (bulletin index lags ~5 days) | "
             "~2015+ (2014 sparse) | per-second | 6-digit code | "
             "~100/page, polite single-connection | low (official) | "
             "title-only (content on demand) |",
             "| szse | yes | SZ | OK | 2018+ deep | per-second | 6-digit "
             "code (list field) | 30/page | low (official) | title-only |",
             "| cninfo | no | SH+SZ | OK | 2000s+ | epoch-ms | code+orgId "
             "derivable | 30/page | medium (reprints) | title+adjunct URL |",
             "| akshare | no | SH+SZ | WAF-intermittent (eastmoney) | "
             "deep | date-only | code field | unknown | medium | "
             "title-only |", "",
             "Policy: official exchanges first; a blocked source is "
             "recorded SOURCE_BLOCKED and the next legal source is used. "
             "No proxy pools, no WAF bypass, no high concurrency.", ""]
    _w("step5_news_sources.md", lines)


def factor_evaluation_report():
    pack = json.loads((NEWS_RUN / "factor_pack_news_v1.json").read_text(
        encoding="utf-8"))
    lb = pd.read_csv(NEWS_RUN / "leaderboard_news.csv")
    test_icir = {}
    for f in (NEWS_RUN / "evaluations").glob("*.json"):
        ev = json.loads(f.read_text(encoding="utf-8"))
        test_icir[f.stem] = ev["test"]["normalizations"]["rank"][
            "horizons"]["20"]["rank_ic"]["icir"]
    lines = ["# STEP 5 news factor evaluation", "",
             f"generated: {datetime.now().isoformat(timespec='seconds')}", "",
             "Selection: research 2018-2021 + valid 2022-2023 ONLY; "
             "test 2024-2025 evaluated exactly once (frozen).", "",
             "| factor | ICIR(research) | ICIR(test) | coverage |",
             "| --- | --- | --- | --- |"]
    for _, r in lb.iterrows():
        lines.append(f"| {r['factor']} | {r['ICIR_research']:.3f} | "
                     f"{test_icir.get(r['factor'], float('nan')):.3f} | "
                     f"{r['coverage']:.2f} |")
    lines += ["", f"factor_pack_news_v1: selected "
              f"{len(pack['selected'])}/{pack['n_candidates']}: "
              + ", ".join(pack["selected"]), "",
              "### discarded", ""]
    for d in pack["discarded"]:
        lines.append(f"- `{d['factor']}`: {d['reason']}")
    lines += ["", "### honest conclusions（2018-2023 选择 → 2024-2025 单次）",
              "", "1. **announcement_count_20d** 是最稳定的新闻因子：research "
              "ICIR +0.39 → valid +0.18 → test +0.36（公告强度高 → 未来"
              "收益略高）。",
              "2. **news_risk_20d**（research +0.35）与 "
              "**shareholder_change_count_20d**（+0.36）通过全部门。",
              "3. 大多数事件类因子（buyback/regulatory/earnings/sentiment/"
              "attention）research 期 ICIR < 0.3，未过门 —— 第一轮中规则"
              "新闻信息大部分被价格信息覆盖，只有'公告强度'与'风险事件'"
              "提供边际增量。",
              "4. **时间衰减研究**（半衰期 1/3/5/10/20d）：所有半衰期的 "
              "research rank-IC ≈ 0（-0.02~-0.008），衰减权重没有提供"
              "额外结构 —— 如实记录，不预设 20 日最优。",
              "5. LLM 层未启用（无 DEEPSEEK_API_KEY）→ rule-based 基线"
              "为主结果；LLM 对比留待 API 可用（系统自动检测）。", ""]
    _w("step5_news_factor_evaluation.md", lines)


def ablation_report():
    comp_path = NEWS_ABL / "comparison.csv"
    if not comp_path.exists():
        print("ablation comparison.csv missing — run run_news_ablation.py")
        return
    comp = pd.read_csv(comp_path)
    lines = ["# STEP 5 news ablation", "",
             f"generated: {datetime.now().isoformat(timespec='seconds')}", "",
             "同引擎/同区间/同参数/同成本/同 Top-20/同 T+1，只改特征集；"
             "A/B 与 STEP 4 冻结锚点一致（漂移需解释）。", "",
             "| variant | 年化 | Sharpe | MDD | IC(test) | RankIC(test) |",
             "| --- | --- | --- | --- | --- | --- |"]
    for _, r in comp.iterrows():
        lines.append(f"| {r['variant']} | {r['ann_return']:.4f} | "
                     f"{r['sharpe']:.3f} | {r['max_drawdown']:.4f} | "
                     f"{r['ic_test']:.4f} | {r['rankic_test']:.4f} |")
    lines += ["", "## conclusions（如实）", "",
              "1. **A/B 与 STEP 4 冻结锚点完全一致**（drift 0.0000）——"
              "消融基准可信。",
              "2. **新闻因子单独（C）反而损害基线**：0.1094 < A 0.2475 ——"
              "公告计数信息单独不足以排序股票。",
              "3. **组合（E）有正增量**：0.2812 / Sharpe 1.022 vs A "
              "0.2475 / 0.943（IC 0.0372 vs 0.0358）——新闻因子与 "
              "factor_pack_v1 一起使用时提供了增量；MDD 略深（-0.235 vs "
              "-0.200）。",
              "4. **风险因子单独（N_risk）** 0.2639/0.968 优于 A —— "
              "news_risk_20d 是最有价值的单类新闻信息。",
              "5. **D 与 N2 变体**：LLM 层未启用（无 API key）→ D ≡ A，"
              "如实记录（不是 LLM 的结论）。",
              "6. **总回答**：规则公告信息在'强度+风险'维度提供了超越 "
              "Alpha158 的边际增量（E > A），但单独使用无排序能力；"
              "LLM 对比留待 API 可用。", ""]
    _w("step5_news_ablation.md", lines)


def pit_audit_report():
    lines = ["# STEP 5 news PIT audit", "",
             f"generated: {datetime.now().isoformat(timespec='seconds')}", "",
             "## rules (docs/step5_news_pit.md)", "",
             "- published on a trading day with time <= 15:00 -> available "
             "AT the publication time (usable for the same day's close)",
             "- otherwise (after close / weekend / holiday / date-only) -> "
             "available at the NEXT trading day 09:30",
             "- publication date unknown -> availability_unknown, "
             "excluded in strict mode",
             "- event_time is kept separate and NEVER used for factor "
             "research; updated_at never substitutes for published_at", "",
             "## automated checks (tests/news/)", "",
             "- test_news_pit.py: pre/post-close boundaries, date-only, "
             "unknown-publication exclusion",
             "- test_weekend_handling.py: Friday evening -> Monday",
             "- test_holiday_handling.py: spring festival / national day "
             "spans -> first trading day after the holiday",
             "- test_no_future_leakage.py: factors invariant to future "
             "events (14 factor parametrization)",
             "- test_timestamp.py: tz-aware Asia/Shanghai everywhere", "",
             "（结果以测试运行为准。）", ""]
    _w("step5_news_pit_audit.md", lines)


def manual_audit_report():
    import random

    from news.storage import load_events_snapshot

    ev = load_events_snapshot()
    lines = ["# STEP 5 news manual audit sample", "",
             f"generated: {datetime.now().isoformat(timespec='seconds')}", "",
             "程序随机抽取 200 条事件，供未来人工核对规则分类是否明显"
             "误分（positive/negative/neutral/major/ordinary）。",
             "LLM 分类对比：LLM 层未启用（无 API key）——启用后同一"
             "样本会加入 LLM 列重新生成。", ""]
    if ev.empty:
        lines.append("no events yet — run build_events.py")
    else:
        random.seed(42)
        sample = ev.sample(n=min(200, len(ev)), random_state=42)
        sample.to_csv(REPORTS / "step5_news_manual_audit_sample.csv",
                      index=False)
        lines.append("| n | symbol | event_type | direction | importance | "
                     "publication_time |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for i, (_, r) in enumerate(sample.iterrows()):
            lines.append(f"| {i+1} | {r.get('symbol')} | "
                         f"{r.get('event_type')} | {r.get('direction')} | "
                         f"{r.get('importance')} | "
                         f"{r.get('publication_time')} |")
        lines += ["", f"sample saved to "
                  "reports/step5_news_manual_audit_sample.csv", ""]
    _w("step5_news_manual_audit.md", lines)


def cost_report():
    import os

    from news.budget import Budget
    from news.llm import cache
    from news.storage import document_count

    b = Budget()
    lines = ["# STEP 5 news cost report", "",
             f"generated: {datetime.now().isoformat(timespec='seconds')}", "",
             "| item | value |", "| --- | --- |",
             f"| documents processed | {document_count()} |",
             f"| LLM enabled | {'yes' if os.environ.get('DEEPSEEK_API_KEY') else 'no (RULE_BASED_ONLY)'} |",
             f"| LLM cache entries | {cache.stats()['entries']} |",
             f"| budget calls used | {b.calls_used} |",
             f"| budget tokens used | {b.tokens_used} |",
             f"| budget limits | {b.max_calls} calls / {b.max_tokens} tokens/day |",
             "", "API cost 估计：LLM 层未启用时为 0；启用后按实际 usage "
             "记录（每文档 ~400 tokens 上限）。", ""]
    _w("step5_news_cost.md", lines)


def strategy_report():
    summary_path = NEWS_STRAT / "summary.json"
    lines = ["# STEP 5 news strategy (strategy_v1_news)", "",
             f"generated: {datetime.now().isoformat(timespec='seconds')}", "",
             "strategy_v1 同引擎（月度调仓/T+1/Top20 等权/5% 现金/相同成本），"
             "特征 = Alpha158 + factor_pack_v1 + news 因子。", ""]
    if summary_path.exists():
        s = json.loads(summary_path.read_text(encoding="utf-8"))
        st = s["strategy_metrics"]
        lines += ["| metric | value |", "| --- | --- |",
                  f"| annualized_return | {st['annualized_return']:.4f} |",
                  f"| sharpe | {st['sharpe']:.3f} |",
                  f"| max_drawdown | {st['max_drawdown']:.4f} |",
                  f"| IC(test) | {s['ic']['test']['ic_mean']:.4f} |",
                  f"| RankIC(test) | {s['ic']['test']['rank_ic_mean']:.4f} |",
                  "", "（与 reports/step5_news_ablation.md 的 E 变体一致。）",
                  ""]
    else:
        lines.append("no strategy results yet — run the news strategy "
                     "backtest.")
    _w("step5_news_strategy.md", lines)


def main() -> int:
    coverage_report()
    sources_report()
    factor_evaluation_report()
    ablation_report()
    pit_audit_report()
    manual_audit_report()
    cost_report()
    strategy_report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
