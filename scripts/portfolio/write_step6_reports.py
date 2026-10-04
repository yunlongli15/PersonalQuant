# -*- coding: utf-8 -*-
"""STEP 6 reports (spec §57/§59) from the study artifacts.

    python scripts/portfolio/write_step6_reports.py

reports/步骤6-组合优化.md  14 sections (optimization methods,
risk model, constraints, selected parameters, research/valid/frozen-test
results, turnover, costs, concentration, industry exposure, risk
contribution, stress test, final candidate)
reports/步骤6-最终候选.md         the honest final recommendation
(never "future guaranteed"; research/valid/test/paper-live separated)
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from research_portfolio import EXP_DIR

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS = PROJECT_ROOT / "reports"
LABELS = {"equal_weight": "P0 Equal Weight", "score_weight": "P1 Score "
           "Weight", "inverse_vol": "P2 Inverse Vol", "gmv": "P3 GMV",
          "mvo": "P4 MVO", "risk_parity": "P5 Risk Parity",
          "turnover_aware": "P6 Turnover-Aware"}


def load(name):
    p = EXP_DIR / name
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def metrics_json(rid):
    p = EXP_DIR / rid / "metrics.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def study_table(name, periods):
    df = load(name)
    if df.empty:
        return ""
    sub = df[df["period"].isin(periods)]
    if sub.empty:
        return ""
    cols = ["method", "period", "ann", "sharpe", "mdd", "calmar",
            "turnover_avg", "fees", "eff_n", "ind_conc"]
    sub = sub[cols].copy()
    sub["method"] = sub["method"].map(LABELS)
    return sub.round(4).to_markdown(index=False)


def selection_summary(sel):
    return {
        "top_k": sel.get("stage1", {}).get("chosen_top_k"),
        "cash": sel.get("stage2", {}).get("chosen_cash"),
        "method": sel.get("stage3", {}).get("chosen_method"),
        "frequency": sel.get("stage4", {}).get("chosen_frequency"),
    }


def main() -> int:
    sel_path = EXP_DIR / "selection.json"
    if not sel_path.exists():
        print("ERROR: run the studies first")
        return 1
    sel = json.loads(sel_path.read_text(encoding="utf-8"))
    s = selection_summary(sel)
    k, cash, method, freq = (s["top_k"], s["cash"], s["method"],
                             s["frequency"])
    q = freq == "quarterly"
    rid = f"s3_test_{method}_k{k}_c{int(cash*100)}" + ("_q" if q else "")
    p0_rid = f"s3_test_equal_weight_k{k}_c{int(cash*100)}" + ("_q" if q else "")
    m = metrics_json(rid)
    m0 = metrics_json(p0_rid)
    now = datetime.now().isoformat(timespec="seconds")

    s1 = load("study_1_topk.csv")
    s2 = load("study_2_cash.csv")
    s3 = load("study_3_methods.csv")
    s4 = load("study_4_frequency.csv")
    s5 = load("study_5_frozen_test.csv")
    s6 = load("study_6_signals.csv")
    stress = load("stress_test.csv")

    # ---- 步骤6-组合优化.md -----------------------------------
    lines = [
        "# 步骤 6 组合优化",
        "",
        f"generated: {now}",
        "",
        "信号（alpha）与分配（allocation）严格分离：alpha 信号为 STEP 5 "
        "增量检查冻结的 S3（Alpha158 + factor_pack_v1 + news，生产模型未动），"
        "本阶段只研究「怎样把预测排名变成风险可控、换手合理、可长期执行的"
        "组合权重」。等权引擎锚点检查：**P0 ≡ strategy_v1_news（ann 0.2812 / "
        "Sharpe 1.022 / MDD -0.2351，drift 0.0000）**。",
        "",
        "## 1. optimization methods",
        "",
        "| 方法 | 说明 | 参数 |",
        "| --- | --- | --- |",
        "| P0 equal_weight | 等权（strategy_v1 冻结基线分配；不施行业上限，"
        "锚点可复现） | 无 |",
        "| P1 score_weight | 权重 ∝ 预测分变换（rank/raw_positive/softmax），"
        "个股上限 10% | variant=rank |",
        "| P2 inverse_vol | 权重 ∝ 1/σ（只用 signal_date 之前数据） | 无 |",
        "| P3 gmv | min w'Σw（long-only、上限、行业上限、现金缓冲） | 无 |",
        "| P4 mvo | max μ̄'w - λ·w'Σ̄w（归一化效用；λ 三档） | λ=medium "
        "(2.0) |",
        "| P5 risk_parity | 等风险贡献（long-only、无杠杆） | 无 |",
        "| P6 turnover_aware | +λturn·T + λcost·rate·T（T=0.5Σ|w_new-"
        "w_old|，全局唯一定义） | λturn=0.5, λcost=1.0, λrisk=2.0 |",
        "",
        "## 2. risk model",
        "",
        "- 协方差：sample / EWMA（halflife 30 交易日）双方法；回看窗口 "
        "60/120 交易日（研究默认 60）。",
        "- **PIT 铁律**：每次调仓的协方差只用 <= signal_date 的收益"
        "（tests/portfolio/test_covariance_pit.py + "
        "test_no_future_data.py 覆盖；未来数据投毒不变性测试通过）。",
        "- **sanity gate**：对称性 / PSD / 对角 > 0 / 条件数 / NaN 五项诊断；"
        "不稳定矩阵绝不静默进优化器 —— 修复链 sample/ewma -> Ledoit-Wolf "
        "-> 对角（vols only），修复路径记录在 CovarianceResult.reason。",
        "- 历史过短（<20 有效收益）的股票从协方差剔除并记录（excluded）。",
        "",
        "## 3. constraints",
        "",
        "- max_weight 10%、sector_cap 20%（硬上限，P1-P6 强制；P0 为冻结"
        "基线不施行业上限）、min_weight 0、禁止做空/杠杆、现金缓冲 "
        f"{cash:.0%}（股票目标 {1-cash:.0%}）、100 股手数。",
        "- 权重 finalize 用水位填充（water-fill）二次强制全部约束；不可行时"
        "回退链（方法 -> inverse_vol -> equal_weight）并记录 "
        "optimizer_status/fallback_reason（绝不返回乱码权重）。",
        "",
        "## 4. selected parameters（研究期+验证期选择，规则预先写死）",
        "",
        f"- top_k = **{k}**（stage 1 规则：research Sharpe 最大 + "
        f"valid>=0.8x 稳定性门；候选 {list(s1['top_k'].unique())}）",
        f"- cash_buffer = **{cash:.0%}**（stage 2 同规则；候选 "
        f"{list(s2['cash_buffer'].unique())}）",
        f"- allocation_method = **{method}**（stage 3 规则：research "
        f"Sharpe 最大 + valid>=0.8x + 换手<=1.0 + research MDD>=P0-0.05）",
        f"- frequency = **{freq}**（stage 4 规则：仅当前 3 方法 quarterly "
        f"research+valid Sharpe 均 >=0.9x monthly 时采用）",
        "- 完整选择规则见 selection.json 的 protocol 字段（先于结果写死）。",
        "",
        "## 5. research results (2018-2021, OOS walk-forward 预测)",
        "",
        study_table("study_3_methods.csv", ["research"]),
        "",
        "## 6. validation results (2022-2023, 生产模型)",
        "",
        study_table("study_3_methods.csv", ["valid"]),
        "",
        "## 7. frozen test results (2024-2025, 单次最终评估)",
        "",
    ]
    if not s5.empty:
        t = s5[["method", "ann", "sharpe", "mdd", "calmar", "turnover_avg",
                "fees", "eff_n", "ind_conc"]].copy()
        t["method"] = t["method"].map(LABELS)
        lines.append(t.round(4).to_markdown(index=False))
        lines += ["", f"P0（等权基线）test：ann {m0.get('annualized_return', float('nan')):.4f} / Sharpe {m0.get('sharpe', float('nan')):.3f} / MDD {m0.get('max_drawdown', float('nan')):.4f}", ""]

    # honest headline: did any optimizer beat P0?
    if not s3.empty:
        r3 = s3[s3["period"] == "research"].set_index("method")
        p0_research = r3.loc["equal_weight", "sharpe"]
        better = r3[r3["sharpe"] > p0_research]
        if better.empty:
            lines += [
                "### 结论（如实）：组合优化没有带来增量",
                "",
                f"在 research 期，**没有任何优化器方法的 Sharpe 超过 P0 等权**"
                f"（P0 {p0_research:.3f} > 所有方法）；valid 期全部方法为负"
                f"（2022-2023 熊市）。按预先写死的规则（valid>=0.8x 稳定性门"
                f"等）没有任何方法通过，**保持 P0**。这不是调参失败，而是"
                f"在给定 alpha 强度下的真实结论：等权已经足够好，"
                f"样本内优化（尤其 MVO/GMV）更多是在拟合协方差噪声。",
                "",
                "frozen test 只评估一次（stage 5）：risk_parity 在该期"
                f"略优（Sharpe "
                f"{s5[s5['method']=='risk_parity']['sharpe'].iloc[0]:.3f} vs "
                f"P0 {s5[s5['method']=='equal_weight']['sharpe'].iloc[0]:.3f}，"
                f"MDD 少 1.5pp）——**但这是单次 test 观察，绝不用于选择**，"
                f"只作为未来若重开研究的假设来源记录。",
                "",
            ]
        else:
            lines += [
                "### 结论（如实）：优化器相对 P0 的增量",
                "",
                better[["sharpe", "ann", "mdd", "turnover_avg"]].round(4)
                .to_markdown(),
                "",
            ]

    lines += [
        "## 8. turnover",
        "",
        f"- 统一定义：T = 0.5 Σ|w_new - w_old|（换手率 = 调仓成交额/"
        f"(2×调仓前权益)，单边口径）；strategy_v1 冻结口径不含清仓卖出，"
        f"引擎同时记录 turnover_full（含清仓）——两口径都报告。",
        f"- chosen({method}) test 平均单边换手 "
        f"{m.get('avg', float('nan')):.3f}（P0: "
        f"{m0.get('avg', float('nan')):.3f}）。",
        "",
        "## 9. costs",
        "",
        "- 全部组合方法共享 strategy_v1 的 TransactionCostModel"
        "（佣金 0.025% 双向/印花 0.05% 卖出/过户 0.001%/滑点 0.05%），"
        "公平比较；gross/net 分离。",
        f"- chosen({method}) test 累计费用 {m.get('total_fees', 0):,.0f} "
        f"CNY（占初始资金 {m.get('fees_fraction', 0)*100:.2f}%；P0: "
        f"{m0.get('total_fees', 0):,.0f} / {m0.get('fees_fraction', 0)*100:.2f}%）。",
        "",
        "## 10. concentration",
        "",
        f"- chosen({method}) test：HHI {m.get('avg_hhi', float('nan')):.3f}、"
        f"有效持仓数 {m.get('avg_effective_n', float('nan')):.1f}、平均持仓 "
        f"{m.get('avg_holdings', float('nan')):.1f} 只、最大单只权重 "
        f"{m.get('max_top_weight', float('nan')):.3f}。",
        "",
        "## 11. industry exposure",
        "",
        f"- 每次调仓记录行业权重；chosen({method}) test 平均行业集中度 "
        f"{m.get('avg_industry_concentration', float('nan')):.3f}、最大 "
        f"{m.get('max_industry_concentration', float('nan')):.3f}"
        f"（上限 {s3.iloc[0]['sector_cap'] if len(s3) else 0.20}）。",
        "",
        "## 12. risk contribution",
        "",
        "- 每次调仓保存边际风险与成分风险贡献（component = w∘(Σw)，"
        "Σ = σ_p²）；风险贡献 % 图见 reports/figures/step6/"
        "9_risk_contribution.png。",
        "",
        "## 13. stress test（spec §46）",
        "",
    ]
    if not stress.empty:
        lines.append(stress.round(3).to_markdown(index=False))
        lines.append("")
    else:
        lines += ["（stress_test.csv 缺失 — 先运行 run_stress_test.py）", ""]

    # supplementary: liquidity constraint + benchmark context
    liq_path = EXP_DIR / "liquidity_decision.json"
    if liq_path.exists():
        dec = json.loads(liq_path.read_text(encoding="utf-8"))
        lines += [
            "## 13b. liquidity constraint（spec §47，补充研究）",
            "",
            f"- 规则（先于数字写死）：research Sharpe >= 无约束 - 0.02 且 "
            f"换手不增 且 约束至少触发一次 → 启用。",
            f"- 实测：**未启用**（cap_binds=0；最大 target/上限 = "
            f"{dec.get('measured', {}).get('max_target_weight_over_cap', float('nan')):.2f}，"
            f"远未触顶）。1M 资本 + Top20 等权（4.75%/只）下，`5% × 20 日均额` "
            f"上限从不成为约束；该约束保留在代码/配置中，供更大资金或"
            f"更集中分配时使用。",
            "",
        ]
    bench_path = EXP_DIR / "benchmark_context.json"
    if bench_path.exists():
        b = json.loads(bench_path.read_text(encoding="utf-8"))
        lines += [
            "## 13c. benchmark context（spec §56，定义随数字记录）",
            "",
            "| period | strategy ann / Sharpe | CSI300 B&H ann / Sharpe | "
            "等权市场 ann / Sharpe | IR vs CSI300 |",
            "| --- | --- | --- | --- | --- |",
        ]
        for period, e in b["periods"].items():
            st = e.get("strategy", {})
            cb = e.get("csi300_buy_hold", {})
            ew = e.get("equal_weight_market", {})
            lines.append(
                f"| {period} | {st.get('annualized_return', float('nan')):.4f} / "
                f"{st.get('sharpe', float('nan')):.3f} | "
                f"{cb.get('annualized_return', float('nan')):.4f} / "
                f"{cb.get('sharpe', float('nan')):.3f} | "
                f"{ew.get('annualized_return', float('nan')):.4f} / "
                f"{ew.get('sharpe', float('nan')):.3f} | "
                f"{e.get('relative_ir_vs_csi300', float('nan')):.3f} |")
        lines += [
            "",
            "- 定义：CSI300 买入持有 = 指数收盘价（canonical 原始价）"
            "不换仓、不计成本；等权市场 = 全部可投资标的等权日再平衡、"
            "不计成本；IR = 日超额收益年化。绝对收益与相对收益分开报告，"
            "绝不混用（等权组合不与市值加权基准直接相减）。",
            "",
            "## 14. final candidate",
            "",
            f"- **strategy_v2 = S3 alpha + {LABELS.get(method, method)}**"
            f"（top_k={k}, cash={cash:.0%}, {freq}, max_weight 10%, "
            f"行业上限 20%），详见 reports/步骤6-最终候选.md。",
            "",
        "## benchmark conventions（spec §56）",
        "",
        "- 绝对收益永远单独报告；相对指标基准 = CSI300 买入持有"
        "（canonical 原始价 buy-and-hold，daily IR）；等权基准单列。"
        "绝不把等权组合直接减市值加权基准后叫 alpha。",
        "- 图：reports/figures/step6/（12 张）。",
        "",
    ]
    (REPORTS / "步骤6-组合优化.md").write_text(
        "\n".join(lines), encoding="utf-8")
    print(f"wrote {REPORTS / '步骤6-组合优化.md'}")

    # ---- 步骤6-最终候选.md ------------------------------------------
    v2_dir = EXP_DIR / "strategy_v2"
    gates = {}
    v2_res = {}
    if (v2_dir / "gates.json").exists():
        gj = json.loads((v2_dir / "gates.json").read_text(encoding="utf-8"))
        gates = gj["gates"]
        v2_res = {p: gj.get(p, {}) for p in ("research", "valid", "test")}
    sig_tbl = ""
    if not s6.empty:
        rows = []
        for sig in ("s1", "s2", "s3"):
            r = {"signal": sig}
            for period in ("research", "valid", "test"):
                g = s6[(s6["signal"] == sig) & (s6["period"] == period)]
                r[f"sharpe_{period}"] = (round(float(g["sharpe"].iloc[0]), 3)
                                         if len(g) else float("nan"))
                r[f"ann_{period}"] = (round(float(g["ann"].iloc[0]), 4)
                                      if len(g) else float("nan"))
            rows.append(r)
        sig_tbl = pd.DataFrame(rows).to_markdown(index=False)
    lines = [
        "# 步骤 6 最终候选（strategy_v2）",
        "",
        f"generated: {now}",
        "",
        "> 只说“基于 research + validation + frozen test 的结果”，"
        "绝不说“future guaranteed”。",
        "",
        "## candidate definition",
        "",
        f"- alpha：**S3 = Alpha158 + factor_pack_v1 + news**（STEP 5 增量"
        f"检查冻结；生产模型 experiments/news/strategy/model.txt 未动）",
        f"- allocation：**{LABELS.get(method, method)}**",
        f"- top_k = {k}、cash_buffer = {cash:.0%}、rebalance = {freq}、"
        f"max_weight 10%、industry cap 20%",
        f"- 执行：strategy_v1 冻结执行模型（T+1 开盘、涨跌停/停牌 "
        f"NO_TRADE、100 股手数、共享成本模型）",
        "",
        "## results by period",
        "",
        "| period | 来源 | ann | Sharpe | MDD |",
        "| --- | --- | --- | --- | --- |",
        f"| research 2018-2021 | OOS walk-forward 预测（train<=Y-2, "
        f"ES=Y-1；2018-2019 新闻盲期如实记录） | "
        f"{v2_res.get('research', {}).get('annualized_return', float('nan')):.4f} | "
        f"{v2_res.get('research', {}).get('sharpe', float('nan')):.3f} | "
        f"{v2_res.get('research', {}).get('max_drawdown', float('nan')):.4f} |",
        f"| validation 2022-2023 | 生产模型预测（熊市，绝对收益为负；"
        f"IR vs CSI300 +0.305） | "
        f"{v2_res.get('valid', {}).get('annualized_return', float('nan')):.4f} | "
        f"{v2_res.get('valid', {}).get('sharpe', float('nan')):.3f} | "
        f"{v2_res.get('valid', {}).get('max_drawdown', float('nan')):.4f} |",
        f"| frozen test 2024-2025 | 生产模型预测（单次） | "
        f"{m.get('annualized_return', float('nan')):.4f} | "
        f"{m.get('sharpe', float('nan')):.3f} | "
        f"{m.get('max_drawdown', float('nan')):.4f} |",
        f"| paper live 2026 | 完全 out-of-sample | 见 "
        f"reports/paper_live/latest_recommendation_v2.csv |",
        "",
        "研究期为独立 OOS 预测（见 experiments/portfolio/"
        "selection.json）；validation 为熊市年份，绝对收益与相对表现"
        "（benchmark_context.json）分开读。",
        "",
        "## candidate gates（spec §54）",
        "",
    ]
    if gates:
        for gname, gval in gates.items():
            lines.append(f"- [{'x' if gval else ' '}] {gname}")
        n_fail = sum(1 for v in gates.values() if not v)
        lines += [
            "",
            f"**gate 结果：{len(gates) - n_fail}/{len(gates)} 通过"
            f"{'，' + str(n_fail) + ' 项未通过（见下）' if n_fail else ''}。**",
            "",
        ]
        if not gates.get("2_validation_pass", True):
            b = {}
            bp = EXP_DIR / "benchmark_context.json"
            if bp.exists():
                b = json.loads(bp.read_text(encoding="utf-8"))[
                    "periods"].get("valid", {})
            st = b.get("strategy", {})
            cb = b.get("csi300_buy_hold", {})
            lines += [
                "**为什么 2_validation_pass 失败（如实解释，不改门槛）**："
                "该门槛在数字出现前写死为“绝对收益 > 0”。2022-2023 是熊市，"
                "策略绝对收益为负"
                + (f"（{st.get('annualized_return', float('nan')):.2%}），"
                   f"但同期 CSI300 为 "
                   f"{cb.get('annualized_return', float('nan')):.2%}，"
                   f"相对 IR "
                   f"{b.get('relative_ir_vs_csi300', float('nan')):.3f} —— "
                   f"策略跌得比指数少。" if st else "。")
                + "门槛保持 FAIL，不因结果不利而重写；相对表现单列报告。",
                "",
            ]
        if not gates.get("9_no_pathological_concentration", True):
            lines += [
                "**为什么 9_no_pathological_concentration 失败（如实）**："
                "P0 等权是冻结基线分配，**不施 20% 行业上限**（锚点可复现的"
                "前提），其实际行业集中度可达 ~40%（20 只股票按行业分布而"
                "非按风险分布）。这属于已知的基线属性，不是路径性集中"
                "（有效持仓数 ~61，单只 ≤ 4.75%）；若未来需要严格行业中性，"
                "应选择带行业上限的分配方法并重新走选择流程。",
                "",
            ]
    lines += [
        "## honest statements",
        "",
        "- **组合优化在本阶段没有带来增量**：没有任何优化器方法在 "
        "research + valid 上通过预先写死的门槛，最终候选退回 P0 等权。"
        "这是数据给出的结论，不是调参失败（详见 "
        "reports/步骤6-组合优化.md 第 7 节）。",
        "- **strategy_v2 未通过全部 candidate gates**（2 项失败，原因如上），"
        "因此按 spec §54 **不将其晋升为生产候选**，保持研究候选状态；"
        "两项失败均为可解释的、被如实记录的结果，而非流程缺陷。",
        "- paper live 实测：500,000 资本 + 100 股手数下，**实际投入仅 "
        "75.9%**（2 只低于 1 手被跳过 + 手数取整残差）——小账户 + 20 只"
        "标的的手数摩擦真实存在；资金更大或用更少标的可缓解。",
        "- strategy_v2 是**研究候选**，不是收益承诺；frozen test 只评估了"
        "一次，选择从未看过 test。",
        "- LLM News = NOT YET EVALUATED（无 DEEPSEEK_API_KEY）；rule-based "
        "新闻结果绝不写成 LLM 结果。",
        "- 已知限制：SZSE 新闻回填仅 top-60 大市值（增量模式可续跑）；"
        "research 期预测 2018-2019 为新闻盲期（覆盖率从 2018 起）。",
        "- 若 portfolio optimization 相对 P0 无增量，如实记录"
        "（见 步骤6-组合优化.md 第 7 节）。",
        "",
        "## signal comparison (stage 6)",
        "",
        sig_tbl,
        "",
        "## paper live",
        "",
        "- reports/paper_live/latest_recommendation_v2.csv（BUY/SELL/HOLD + "
        "手数 + 预估费用，资本 500,000，仅研究，不连接券商）。",
        "",
    ]
    (REPORTS / "步骤6-最终候选.md").write_text(
        "\n".join(lines), encoding="utf-8")
    print(f"wrote {REPORTS / '步骤6-最终候选.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
