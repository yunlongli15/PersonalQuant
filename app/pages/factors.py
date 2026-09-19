# -*- coding: utf-8 -*-
"""因子研究浏览（spec §31 / §34）。

**只读。** 界面不提供任何修改因子选择的入口（§31）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from _shared import (export_button, no_data, num, pct, page_setup,
                     render_chips, unavailable_block)
from services import factor_service

page_setup("因子", "🔬")

st.caption("这里展示的是**研究结果**。因子选择由研究协议决定，"
           "界面不提供修改入口。")

tab1, tab2, tab3 = st.tabs(["因子排行榜", "增量 IC（STEP 9）", "当前信号"])

with tab1:
    lb = factor_service.leaderboards()
    if unavailable_block(lb, "还没有因子研究结果"):
        pass
    else:
        board = st.selectbox("数据集", lb["boards"],
                             format_func=lambda b: f"{b['label']}（{b['n']} 个）")
        df = pd.DataFrame(board["rows"])
        st.dataframe(df, hide_index=True, width="stretch")
        export_button(board["rows"], f"leaderboard_{board['key']}.csv",
                      "导出排行榜 CSV")
        st.caption("ICIR_research 为研究期（2018-2021）；"
                   "RankIC_test / ICIR_test 为 frozen test（单次评估）。"
                   "**选择只用 research + valid，test 从未参与选因子。**")

with tab2:
    inc = factor_service.incremental()
    if unavailable_block(inc, "还没有增量 IC 结果"):
        pass
    else:
        render_chips([("RESEARCH CANDIDATE", "CANDIDATE")])
        st.markdown(
            "STEP 9 的结论：把候选因子加进冻结模型后，"
            "**ΔIC = IC1 − IC0** 才是它真正新增的信息。")
        df = pd.DataFrame(inc["rows"])
        show = [c for c in ["factor", "incremental_ic", "incremental_rank_ic",
                            "incremental_icir", "bootstrap_ci_low",
                            "bootstrap_ci_high", "prediction_corr",
                            "r2_existing", "evidence_score", "status"]
                if c in df.columns]
        st.dataframe(df[show], hide_index=True, width="stretch")
        export_button(inc["rows"], "incremental_factor_candidates.csv",
                      "导出 CSV")
        st.warning(inc.get("note", ""))
        st.caption("诚实结论：**没有任何候选的 ΔIC 置信区间排除 0**；"
                   "置换重要性 ≈ 0（模型几乎没用到这些列）。"
                   "它们保持 research candidate，未进入 strategy_v2。")

with tab3:
    sig = factor_service.current_signals(limit=100)
    if unavailable_block(sig, "还没有信号快照"):
        pass
    else:
        st.caption(f"信号日 {sig['state'].get('as_of')} ｜ 全市场 {sig['n']} 只")
        df = pd.DataFrame(sig["rows"])
        st.dataframe(df, hide_index=True, width="stretch")
        export_button(sig["rows"], "current_signals.csv", "导出信号 CSV")
