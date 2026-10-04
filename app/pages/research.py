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
    ("reports/步骤1-Qlib基线.md", "STEP 1 Qlib 基线"),
    ("reports/步骤2-数据目录.md", "STEP 2 数据目录"),
    ("reports/步骤3-策略v1.md", "STEP 3 strategy_v1"),
    ("reports/步骤4-因子研究.md", "STEP 4 因子研究"),
    ("reports/步骤4-模型消融.md", "STEP 4 模型消融"),
    ("reports/步骤5-新闻因子评估.md", "STEP 5 新闻因子"),
    ("reports/步骤5-新闻消融.md", "STEP 5 新闻消融"),
    ("reports/步骤6-组合优化.md", "STEP 6 组合优化"),
    ("reports/步骤6-最终候选.md", "STEP 6 最终候选"),
    ("reports/步骤8-微结构因子.md", "STEP 8 微结构因子"),
    ("reports/步骤9-独立信息研究.md", "STEP 9 独立信息研究"),
    ("reports/增量IC因子筛选协议v2.md", "STEP 9 增量 IC 协议"),
    ("reports/步骤10-前瞻留出样本.md", "STEP 10 Forward Holdout"),
    ("reports/模拟盘-引擎验证.md", "Paper Live 引擎验证"),
    ("reports/步骤11-既有资产系统审计.md",
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
