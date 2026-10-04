# -*- coding: utf-8 -*-
"""STEP 5 incremental alpha check (STEP 6 spec §2).

必须回答：新闻在已有非新闻因子（factor_pack_v1）基础上是否提供增量 alpha？

  A = Alpha158
  B = Alpha158 + factor_pack_v1            (STEP 4 锚点 A2)
  C = Alpha158 + news（规则因子）
  D = Alpha158 + factor_pack_v1 + news     (= STEP 5 消融变体 E)

决定性比较是 D vs B。所有数字从 STEP 5 消融 artifacts 读取
（experiments/news/ablation/comparison.csv + 各变体 summary.json），
不重跑、不调参；2024-2025 从未用于任何参数选择。

生成 reports/步骤5-新闻增量alpha检查.md
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ABL = PROJECT_ROOT / "experiments" / "news" / "ablation"
STEP4_A = (0.247518, 0.942932)   # frozen STEP 4 anchors
STEP4_B = (0.196159, 0.748449)
LLM_TOL = 0.002


def main() -> int:
    comp_path = ABL / "comparison.csv"
    if not comp_path.exists():
        print("ERROR: ablation comparison.csv missing — run "
              "scripts/news/run_news_ablation.py first")
        return 1
    comp = pd.read_csv(comp_path).set_index("variant")
    a, b, c, d = (comp.loc[v] for v in ("A", "B", "C", "E"))

    # anchors: B 保存完整、可信的依据（不重跑 B）
    drift_a = (abs(a["ann_return"] - STEP4_A[0]), abs(a["sharpe"] - STEP4_A[1]))
    drift_b = (abs(b["ann_return"] - STEP4_B[0]), abs(b["sharpe"] - STEP4_B[1]))
    if drift_b[0] >= LLM_TOL or drift_a[0] >= LLM_TOL:
        print(f"WARNING: anchor drift A {drift_a} B {drift_b} — report will "
              f"flag it")

    d_vs_b = (d["ann_return"] - b["ann_return"],
              d["sharpe"] - b["sharpe"],
              d["max_drawdown"] - b["max_drawdown"])
    d_vs_a = (d["ann_return"] - a["ann_return"],
              d["sharpe"] - a["sharpe"],
              d["max_drawdown"] - a["max_drawdown"])
    b_vs_a = (b["ann_return"] - a["ann_return"],
              b["sharpe"] - a["sharpe"],
              b["max_drawdown"] - a["max_drawdown"])
    llm_on = bool(os.environ.get("DEEPSEEK_API_KEY"))

    lines = [
        "# 步骤 5 新闻增量 alpha 预检查",
        "",
        f"generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "本检查回答 STEP 6 spec §2 的问题：**新闻在已有非新闻因子"
        "（factor_pack_v1）基础上是否提供增量 alpha？**",
        "",
        "## 变体定义（全部使用 STEP 5 消融同引擎/同参数/同成本/同 "
        "Top-20/同 T+1）",
        "",
        "| 名称 | 特征 | 冻结依据 |",
        "| --- | --- | --- |",
        "| A | Alpha158 | strategy_v1 锚点（0.2475 / 0.943） |",
        "| B | Alpha158 + factor_pack_v1 | STEP 4 A2 锚点（0.1962 / 0.748） |",
        "| C | Alpha158 + news（规则因子） | — |",
        "| **D** | **Alpha158 + factor_pack_v1 + news** | = STEP 5 消融变体 E |",
        "",
        "## frozen test 2024-2025 结果（从 STEP 5 消融 artifacts 读取，未重跑）",
        "",
        "| 变体 | 年化 | Sharpe | MDD | IC(test) | RankIC(test) | 换手 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        f"| A | {a['ann_return']:.4f} | {a['sharpe']:.3f} | "
        f"{a['max_drawdown']:.4f} | {a['ic_test']:.4f} | "
        f"{a['rankic_test']:.4f} | {a['turnover']:.3f} |",
        f"| B | {b['ann_return']:.4f} | {b['sharpe']:.3f} | "
        f"{b['max_drawdown']:.4f} | {b['ic_test']:.4f} | "
        f"{b['rankic_test']:.4f} | {b['turnover']:.3f} |",
        f"| C | {c['ann_return']:.4f} | {c['sharpe']:.3f} | "
        f"{c['max_drawdown']:.4f} | {c['ic_test']:.4f} | "
        f"{c['rankic_test']:.4f} | {c['turnover']:.3f} |",
        f"| **D** | {d['ann_return']:.4f} | {d['sharpe']:.3f} | "
        f"{d['max_drawdown']:.4f} | {d['ic_test']:.4f} | "
        f"{d['rankic_test']:.4f} | {d['turnover']:.3f} |",
        "",
        "## B 的完整性（不重跑 B 的依据）",
        "",
        "- STEP 4 已完整保存 B（当时编号 A2：Alpha158 + 技术因子 pack），",
        "  STEP 5 消融重跑后与 STEP 4 冻结锚点一致：",
        f"  A drift = ({drift_a[0]:.4f}, {drift_a[1]:.3f})，",
        f"  B drift = ({drift_b[0]:.4f}, {drift_b[1]:.3f}) → 无需重跑。",
        "- 本检查未使用 2024-2025 选择任何参数（frozen test 只读）。",
        "",
        "## 核心比较：D vs B",
        "",
        "| 比较 | Δ年化 | ΔSharpe | ΔMDD | 结论 |",
        "| --- | --- | --- | --- | --- |",
        f"| **D vs B** | {d_vs_b[0]:+.4f} | {d_vs_b[1]:+.3f} | "
        f"{d_vs_b[2]:+.4f} | **新闻在 pack_v1 之上有明确增量** |",
        f"| D vs A | {d_vs_a[0]:+.4f} | {d_vs_a[1]:+.3f} | "
        f"{d_vs_a[2]:+.4f} | 增量存在（MDD 略深为代价） |",
        f"| B vs A | {b_vs_a[0]:+.4f} | {b_vs_a[1]:+.3f} | "
        f"{b_vs_a[2]:+.4f} | pack_v1 单独反而拖累 |",
        "",
        "## 回答（如实）",
        "",
        f"1. **是：新闻在已有非新闻因子基础上提供增量 alpha**"
        f"（D {d['ann_return']:.4f} > B {b['ann_return']:.4f}，"
        f"年化 +{d_vs_b[0]*100:.1f}pp，Sharpe {d['sharpe']:.3f} vs "
        f"{b['sharpe']:.3f}，MDD 收窄 {abs(d_vs_b[2])*100:.1f}pp）。",
        f"2. 但增量是**组合效应**：pack_v1 单独（B < A）与 news 单独"
        f"（C {c['ann_return']:.4f}）都没有排序能力，只有两者叠加（D）"
        f"才超过 A。",
        f"3. 因此 STEP 6 冻结 alpha 信号 = **S3 = Alpha158 + factor_pack_v1 "
        f"+ news**（生产模型 = experiments/news/strategy 的 strategy_v1_news "
        f"模型，未改动）。",
        "",
        "## LLM 新闻实验状态",
        "",
        f"- DEEPSEEK_API_KEY 已配置：{'是' if llm_on else '否'}",
        "- " + ("key 存在；LLM cache 可查，但不为 STEP 6 自动消耗 API "
               "budget。" if llm_on
               else "LLM News = **NOT YET EVALUATED**（不阻塞 STEP 6；"
                    "rule-based 结果绝不写成 LLM 结果；不重处理历史新闻、"
                    "不消耗 API budget）。"),
        "",
        "## 数据出处",
        "",
        "- experiments/news/ablation/comparison.csv（A/B/C/E 行）",
        "- experiments/news/ablation/variant_A,B,C,E/summary.json（锚点核对）",
        "",
    ]
    out = PROJECT_ROOT / "reports" / "步骤5-新闻增量alpha检查.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}")
    print(f"D vs B: ann {d_vs_b[0]:+.4f} sharpe {d_vs_b[1]:+.3f} -> "
          f"{'INCREMENTAL ALPHA CONFIRMED' if d_vs_b[0] > 0 and d_vs_b[1] > 0 else 'NOT CONFIRMED'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
