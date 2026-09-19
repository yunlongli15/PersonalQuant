# -*- coding: utf-8 -*-
"""研究浏览（spec §34）。

研究输出**只读**。这里只是把 `reports/` 与 `experiments/` 的结论摆出来，
不提供任何"重跑/调参"入口。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from _shared import PROJECT_ROOT, no_data, page_setup

page_setup("研究", "📚")

REPORTS = [
    ("reports/step1_qlib_baseline.md", "STEP 1 Qlib 基线"),
    ("reports/step2_data_catalog.md", "STEP 2 数据目录"),
    ("reports/step3_strategy_v1.md", "STEP 3 strategy_v1"),
    ("reports/step4_factor_research.md", "STEP 4 因子研究"),
    ("reports/step4_model_ablation.md", "STEP 4 模型消融"),
    ("reports/step5_news_factor_evaluation.md", "STEP 5 新闻因子"),
    ("reports/step5_news_ablation.md", "STEP 5 新闻消融"),
    ("reports/step6_portfolio_optimization.md", "STEP 6 组合优化"),
    ("reports/step6_final_candidate.md", "STEP 6 最终候选"),
    ("reports/step8_micro_factors.md", "STEP 8 微结构因子"),
    ("reports/step9_independent_info.md", "STEP 9 独立信息研究"),
    ("reports/incremental_factor_selection_v2.md", "STEP 9 增量 IC 协议"),
    ("reports/step10_forward_holdout.md", "STEP 10 Forward Holdout"),
    ("reports/paper_live_engine_validation.md", "Paper Live 引擎验证"),
    ("reports/step11_existing_asset_system_audit.md",
     "STEP 11 既有系统审计"),
]

have = [(p, t) for p, t in REPORTS if (PROJECT_ROOT / p).exists()]
if not have:
    no_data("还没有研究报告")
    st.stop()

st.caption(f"共 {len(have)} 份报告，全部只读。")
pick = st.selectbox("选择报告", have, format_func=lambda x: x[1])
text = (PROJECT_ROOT / pick[0]).read_text(encoding="utf-8")

st.markdown(f"**`{pick[0]}`**")
with st.expander("展开查看全文", expanded=False):
    st.markdown(text)

st.download_button("下载 Markdown", text,
                   file_name=Path(pick[0]).name, mime="text/markdown")

st.markdown("---")
st.subheader("重要结论（诚实记录）")
st.markdown(
    "- **自定义因子第一轮未稳定超越 Alpha158 基线**（STEP 4）\n"
    "- **组合优化没有带来增量**，最终退回 P0 等权（STEP 6）\n"
    "- **新增因子有单因子预测力，但加入组合未提升策略**（STEP 8）\n"
    "- **24 个月组合回测的可检出最小年化差异约 41pp** —— "
    "该样本无法区分策略优劣（STEP 9）\n"
    "- **修正后判据推翻了\"波动率家族有独立信息\"的结论**（STEP 9 V2）\n"
    "- **最强单因子 limit_up_count_20 的独立信息 ≈ 0**（替代品而非增量）")
