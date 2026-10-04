# -*- coding: utf-8 -*-
"""Generate the STEP 3 reports from an experiment run's artifacts.

    python scripts/write_reports.py [--run-id run_001]

Writes:
  reports/步骤3-策略v1.md
  reports/步骤3-模型评估.md
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def fmt(v, nd=4):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "n/a"
    return f"{v:,.{nd}f}" if isinstance(v, (int, float)) else str(v)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="run_001")
    args = ap.parse_args()
    run_dir = PROJECT_ROOT / "experiments" / "strategy_v1" / args.run_id
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    s = summary["strategy"]
    b = summary["benchmarks"]
    ic = summary["ic"]

    # ---------- strategy report ----------
    lines = ["# STEP 3 策略报告：strategy_v1", "",
             f"run: {summary['run_id']}  ·  {manifest['created_at']}", ""]
    lines += [
        "## 1. 策略定义", "",
        "- 月度调仓（每月最后一个交易日收盘生成信号），T+1 开盘执行",
        "- 全 A 股动态股票池（上市 ≥180 交易日、非停牌、粗流动性过滤；",
        "  ST 过滤仅 paper live，历史回测关闭并记录限制）",
        "- 特征：Qlib 官方 Alpha158（158 因子，经 canonical 数据 provider）",
        "- 标签：未来 20 个交易日调整后收益",
        "- 模型：LightGBM（参数固定，见 config/strategy_v1.yaml）",
        "- 组合：Top 20 等权 + 5% 现金缓冲；100 股手数；保守成本模型",
        "", "## 2. 股票池", "",
        "动态构建（list_date/delist_date/停牌/流动性），历史回测不使用今天的",
        "股票列表；退市股保留在历史股票池中（无生存者偏差，有专门测试）。",
        "流动性阈值为源单位粗过滤（volume/amount 源侧缩放，详见",
        "experiments/strategy_v1/run_001/liquidity_analysis.md）。",
        "", "## 3. 特征 / 4. 模型 / 5. 标签", "",
        f"- 特征：Alpha158（qlib 官方）；模型：LightGBM，seed={manifest['model_seed']}，",
        f"  params={manifest['model_params']}",
        f"- 标签：未来 20 交易日调整后收益（{summary['label'] if 'label' in summary else 'adjusted_return'}）",
        "", "## 6. train / validation / test", "",
        f"- train {manifest['time_split']['train']}  "
        f"valid {manifest['time_split']['valid']}  "
        f"test {manifest['time_split']['test']}",
        f"- 2026 起为 paper live（完全 out-of-sample，未参与任何调参）",
        "", "## 7. walk-forward", "",
        "季度重训 + 月调仓（7 年滚动窗口）；结果见 walkforward_predictions.parquet。",
        "", "## 8. rebalance / 9. execution / 10. transaction costs", "",
        "见 docs/步骤3-执行模型.md（T+1 开盘、涨跌停与停牌 NO_TRADE、",
        "0.025% 佣金+0.05% 印花税(卖)+过户费+滑点 0.05%/边，全部可配置）。",
        "", "## 11. portfolio construction / 12. benchmark", "",
        "Top 20 等权（4.75%/只）+ 5% 现金；基准：CSI300/CSI500/CSI1000 买入持有、",
        "全市场等权、60 日动量 Top20（同一引擎、同一成本）。",
        "", "## 13. performance", "",
        "| 指标 | strategy_v1 | momentum | CSI300 | CSI500 |",
        "| --- | --- | --- | --- | --- |",
    ]
    mom = summary.get("momentum_baseline") or {}
    rows = {
        "累计收益": (s.get("cumulative_return"), mom.get("cumulative_return"),
                     b.get("000300.SH", {}).get("cumulative_return"),
                     b.get("000905.SH", {}).get("cumulative_return")),
        "年化收益": (s.get("annualized_return"), mom.get("annualized_return"),
                     b.get("000300.SH", {}).get("annualized_return"),
                     b.get("000905.SH", {}).get("annualized_return")),
        "年化波动": (s.get("annualized_volatility"), mom.get("annualized_volatility"),
                     b.get("000300.SH", {}).get("annualized_volatility"),
                     b.get("000905.SH", {}).get("annualized_volatility")),
        "Sharpe": (s.get("sharpe"), mom.get("sharpe"),
                   b.get("000300.SH", {}).get("sharpe"),
                   b.get("000905.SH", {}).get("sharpe")),
        "最大回撤": (s.get("max_drawdown"), mom.get("max_drawdown"),
                     b.get("000300.SH", {}).get("max_drawdown"),
                     b.get("000905.SH", {}).get("max_drawdown")),
        "Calmar": (s.get("calmar"), mom.get("calmar"),
                   b.get("000300.SH", {}).get("calmar"),
                   b.get("000905.SH", {}).get("calmar")),
    }
    for name, vals in rows.items():
        lines.append(f"| {name} | {' | '.join(fmt(v) for v in vals)} |")
    lines += [
        "",
        f"- IR vs CSI300：{fmt(s.get('information_ratio'))}；",
        f"alpha(年化) {fmt(s.get('alpha_annualized'))}，beta {fmt(s.get('beta'))}",
        f"- 月胜率：{fmt(s.get('win_rate_monthly'), 3)}；"
        f"成交 {s.get('n_trades')} 笔；平均单边换手 {fmt(s.get('avg'), 3)}",
        "", "## 14. IC / 15. RankIC / 16. quantile return", "",
        f"- valid：IC mean {fmt(ic['valid']['ic_mean'])}，"
        f"ICIR {fmt(ic['valid']['icir'])}，RankIC {fmt(ic['valid']['rank_ic_mean'])}",
        f"- test：IC mean {fmt(ic['test']['ic_mean'])}，"
        f"ICIR {fmt(ic['test']['icir'])}，RankIC {fmt(ic['test']['rank_ic_mean'])}",
        f"- Top-Bottom(Q5-Q1) 月均收益差：{fmt(summary.get('top_bottom_spread', {}).get('spread_mean'), 4)}",
        f"（正比例 {fmt(summary.get('top_bottom_spread', {}).get('spread_positive_ratio'), 3)}）",
        "", "## 17. annual results", "",
    ]
    for y, r in sorted(s.get("yearly_returns", {}).items()):
        lines.append(f"- {y}: {fmt(r, 3)}")
    lines += ["", "## 18. drawdown / 19. turnover", "",
              f"- 最大回撤 {fmt(s.get('max_drawdown'), 3)}（图见 reports/figures/2_drawdown.png）",
              f"- 换手（图见 reports/figures/10_turnover.png）",
              "", "## 20. sanity check / 21. leakage audit", "",
              "- 见 reports/步骤3-人工核对.md 与 reports/步骤3-时点正确性审计.md",
              "", "## 22. limitations（诚实记录）", "",
              "- volume/amount 源侧缩放：流动性过滤为粗过滤，精确流动性数据待 STEP 4",
              "- 历史 ST 状态缺失：回测关闭 ST 过滤（记录限制，避免未来函数）",
              "- 成交假设 T+1 开盘整单成交；未建模盘中冲击（资金规模下影响极小）",
              "- 特征输入为调整价（与 qlib Alpha158 官方口径一致）",
              "", "## 23. next improvements", "",
              "- STEP 4：干净的成交量源重建流动性过滤；财务因子（STEP 2 PIT 数据）接入",
              "- 更多基线（行业中性、低换手变体）；参数敏感性分析（独立实验，不调优本策略）",
              ""]
    p = PROJECT_ROOT / "reports" / "步骤3-策略v1.md"
    p.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {p}")

    # ---------- model evaluation report ----------
    ml = ["# STEP 3 模型评估报告（strategy_v1）", "",
          "核心问题：LightGBM+Alpha158 是否真的预测到了横截面 alpha？",
          "（而不是'回测收益高所以模型好'）", ""]
    ml += ["## IC / RankIC（月度横截面）", "",
           "| 区间 | 月数 | IC mean | IC std | ICIR | IC>0 占比 | RankIC mean | RankICIR |",
           "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for period in ("valid", "test"):
        r = ic[period]
        ml.append(f"| {period} | {r['n_months']} | {fmt(r['ic_mean'])} | "
                  f"{fmt(r['ic_std'])} | {fmt(r['icir'])} | {fmt(r['ic_positive_ratio'], 3)} | "
                  f"{fmt(r['rank_ic_mean'])} | {fmt(r['rank_icir'])} |")
    ml += ["", "图：reports/figures/7_ic_series.png、8_rank_ic_series.png", "",
           "## 分位组合收益（Q1 最差 … Q5 最好）", "",
           "| 分位 | 平均未来 20 日收益 |",
           "| --- | --- |"]
    for q in summary.get("quantile_summary", []):
        ml.append(f"| Q{int(q['quantile'])} | {fmt(q['mean_return'])} |")
    ml += ["", "图：reports/figures/9_quantile_returns.png", "",
           f"Q5-Q1 月均收益差 {fmt(summary.get('top_bottom_spread', {}).get('spread_mean'), 4)}"
           f"（{summary.get('top_bottom_spread', {}).get('n_months')} 个月，"
           f"正比例 {fmt(summary.get('top_bottom_spread', {}).get('spread_positive_ratio'), 3)}）", "",
           "## 模型 vs 动量基线", "",
           f"- strategy_v1 年化 {fmt(s.get('annualized_return'), 3)} vs "
           f"momentum {fmt(mom.get('annualized_return'), 3)}",
           f"- 两者 IC 与分位单调性决定'复杂模型是否超过简单方法'，结论以数据为准", "",
           "## 结论", "",
           "（由实际结果填写：是否存在稳定正 IC、分位是否单调、是否超过基线；",
           "如实记录，不美化。）"]
    p2 = PROJECT_ROOT / "reports" / "步骤3-模型评估.md"
    p2.write_text("\n".join(ml), encoding="utf-8")
    print(f"wrote {p2}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
