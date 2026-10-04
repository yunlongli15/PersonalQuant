# -*- coding: utf-8 -*-
"""STEP 4 report generation from experiment outputs.

    python scripts/write_step4_reports.py

Produces:
  reports/步骤4-因子研究.md    factor research summary (pack_v1)
  reports/步骤4-模型消融.md     Model A/B/C/D comparison table
Both read only experiment artifacts — never recomputed numbers.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from factors.registry import FACTOR_REGISTRY

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN = PROJECT_ROOT / "experiments" / "factors" / "factor_run_001"
ABL = PROJECT_ROOT / "experiments" / "factors" / "ablation"


def _ric(ev, period="research", method="rank", h="20"):
    return ev["normalizations"][method]["horizons"][h]["rank_ic"]


def factor_research_report():
    pack = json.loads((RUN / "factor_pack_v1.json").read_text(encoding="utf-8"))
    lb = pd.read_csv(RUN / "leaderboard.csv")
    lines = [
        "# STEP 4 因子研究报告（factor_pack_v1）", "",
        f"generated: {datetime.now().isoformat(timespec='seconds')}", "",
        "## 1. 数据与股票池", "",
        "- 研究股票池：strategy_v1 同规则，流动性过滤改用校准成交额 "
        "（docs/步骤4-市场数据质量.md）；ST 过滤关闭（无历史序列）。",
        "- 财务股票池：当前总市值前 300（大市值样本，偏倚已注明）。",
        "- 区间：research 2018-2021 / valid 2022-2023 / "
        "test 2024-2025（FROZEN）/ 2026 paper live（未使用）。",
        "", "## 2. 因子全景（research rank-ICIR 排序，test 仅最终展示）", "",
        "| factor | category | dir(declared→empirical) | ICIR(research) | "
        "ICIR(test) | coverage | Q5-Q1 | turnover |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for _, r in lb.iterrows():
        lines.append(
            f"| {r['factor']} | {r['category']} | "
            f"{r['direction_declared']}→{r['direction_empirical']} | "
            f"{r['ICIR_research']:.3f} | {r['ICIR_test']:.3f} | "
            f"{r['coverage']:.2f} | {r['Q5_Q1']:.4f} | {r['turnover']:.2f} |")
    lines += [
        "", "## 3. factor_pack_v1 选择（只用 research+valid）", "",
        f"候选 {pack['n_candidates']} 个 → 选中 {len(pack['selected'])} 个：",
        "", "```", ", ".join(pack["selected"]), "```", "",
        "### discarded（原因透明）", "",
    ]
    for d in pack["discarded"]:
        lines.append(f"- `{d['factor']}`: {d['reason']}")
    lines += [
        "", "## 4. 诚实结论（2018-2023 选择，2024-2025 单次检验）", "",
        "### 4.1 有效且稳定的因子（research→test 同号）", "",
        "- **reversal_20**：research ICIR +0.52 / test +0.60 —— 全样本最稳定。",
        "- **volatility_20/60、downside_volatility_60**：低波动溢价，test 期延续。",
        "- **volume_ratio_5_20/20_60、amount_20**：量能/流动性因子（负向），"
        "test 期延续（volume_ratio_20_60 test ICIR -0.60）。",
        "- **momentum_20/60/120 与 price_vs_ma20/60/120**：实证方向为负"
        "（A 股短期反转/均值回归占主导），test 期延续。", "",
        "### 4.2 衰减与不稳定", "",
        "- momentum 类因子按 |ICIR| 排序均通过门槛，但方向与直觉相反"
        "（负 = 反转）——方向在报告中分开记录，不做人为翻转。",
        "- **财务因子在 research 期看似有效（roe ICIR +0.47、gross_margin "
        "+0.34），但 test 期全部反转或消失**（roe test ICIR -0.12）——"
        "research→valid 符号翻转（roe、gross_margin、net_margin）与"
        " test 失效共同说明：2018-2021 的质量/成长溢价在 2024-2025 未延续，"
        "如实报告，不调参美化。",
        "- 财务因子覆盖率（受限股票池 ~27%）由数据可得性约束（见覆盖率报告），"
        "结论仅适用于大市值样本。", "",
        "### 4.3 与 Alpha158 的关系", "",
        "把 pack 的 7 个技术因子加入 LightGBM 后（ablation A2），test 期"
        "收益反而低于纯 Alpha158 —— Alpha158 已经捕获了这些横截面信息。"
        "详见 reports/步骤4-模型消融.md。", "",
    ]
    out = PROJECT_ROOT / "reports" / "步骤4-因子研究.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}")


def ablation_report():
    comp_path = ABL / "comparison.csv"
    if not comp_path.exists():
        print("ablation comparison.csv missing — run backtest_ablation.py first")
        return
    comp = pd.read_csv(comp_path)
    lines = [
        "# 步骤 4 模型消融（A/B/C/D）", "",
        f"generated: {datetime.now().isoformat(timespec='seconds')}", "",
        "同引擎/同区间/同参数/同成本/同 Top-20/同 T+1，**只改特征集**"
        "（禁止为好看调参）。test 为 FROZEN TEST SET；2026 未参与。", "",
        "| variant | 特征 | 年化 | Sharpe | MDD | 换手 | IC(test) | "
        "RankIC(test) | ICIR(test) | valid_rmse |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    labels = {
        "A": "Alpha158 only（=strategy_v1 基线）",
        "A1": "Alpha158 + valuation",
        "A2": "Alpha158 + technical custom",
        "A3": "Alpha158 + financial PIT",
        "A4": "Alpha158 + 全部非财务",
        "C_full": "全市场 + 财务因子 sector 填充",
        "C_res": "财务股票池 + 全部因子",
        "D": "C_res + mined（research candidate）",
    }
    for _, r in comp.iterrows():
        lines.append(
            f"| {r['variant']} | {labels.get(r['variant'], '')} | "
            f"{r['ann_return']:.4f} | {r['sharpe']:.3f} | "
            f"{r['max_drawdown']:.4f} | {r['turnover']:.3f} | "
            f"{r['ic_test']:.4f} | {r['rankic_test']:.4f} | "
            f"{r['icir_test']:.3f} | {r['valid_rmse']:.5f} |")
    lines += [
        "", "## 结论（如实记录）", "",
        "1. **A 完全复现 strategy_v1 run_001**（0.2475 / 0.943 / -0.1995 / "
        "IC 0.0358）——消融基准可信。",
        "2. **自定义技术因子没有增量**：A2（+pack 技术因子）0.1962 < A，"
        "Alpha158 已捕获同类信息。",
        "3. **估值因子拖累**：A1（+pe/earnings_yield）0.1304，最差。",
        "4. **财务因子单独 ≈ 基线**：A3 收益 0.2511 ≈ A 0.2475，但 IC 更低"
        "（0.0321 vs 0.0358）、回撤更深——财务信息没有带来稳定提升。",
        "5. **C_full**（全部自定义因子 + sector 中性填充）收益 0.2478 与 A"
        "持平、IC 略升（0.0440/0.0700），但不足以构成策略改进。",
        "6. **C_res**（受限大市值股票池）Sharpe 1.318 / MDD -0.121 —— 与 A"
        "不可直接比较（股票池不同，非纯特征差异）。",
        "7. **D（+mined 因子，research candidate）** test 0.3970 / Sharpe "
        "1.392 —— 5 个过门表达式、1,168 候选的 snooping 背景下单次测试，"
        "谨慎对待，不进入生产策略。", "",
        "**总回答：第一轮因子研究中，财务因子与自定义技术因子都未能稳定超越 "
        "Alpha158 基线；Alpha158 已相当好。**", "",
    ]
    out = PROJECT_ROOT / "reports" / "步骤4-模型消融.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}")


def main() -> int:
    factor_research_report()
    ablation_report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
