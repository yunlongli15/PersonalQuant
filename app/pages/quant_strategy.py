# -*- coding: utf-8 -*-
"""量化策略状态（spec §23 / §37 / §56）。

只读。GUI **不得**修改任何冻结配置（§55）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from _shared import (export_button, no_data, num, pct, page_setup,
                     render_chips, unavailable_block)
from services import factor_service, strategy_service

page_setup("量化策略", "⚙️")

card = strategy_service.status_card()
if unavailable_block(card, "策略配置不可用"):
    st.stop()

chips = [(t, t.replace(" ", "_")) for t in card.get("tags", [])]
if card.get("status") == "DRIFT_DETECTED":
    chips.append(("DRIFT DETECTED", "INVALID"))
render_chips(chips)

st.markdown("---")
c1, c2 = st.columns(2)

with c1:
    st.subheader("策略配置（冻结）")
    st.markdown(
        f"| 项 | 值 |\n|---|---|\n"
        f"| 策略版本 | `{card['strategy_version']}` |\n"
        f"| alpha 信号 | `{card['alpha_signal']}` |\n"
        f"| 模型 | `{card['model']}` |\n"
        f"| 特征包 | {', '.join('`' + p.split('/')[-1] + '`' for p in card['feature_packs'])} |\n"
        f"| 标签周期 | {card['label_horizon_days']} 交易日 |\n"
        f"| 分配方法 | `{card['allocation_method']}` |\n"
        f"| Top-K | {card['top_k']} |\n"
        f"| 调仓 | {card['rebalance']['frequency']} / "
        f"{card['rebalance']['rule']} |\n"
        f"| 执行 | {card['execution']['model']} |\n"
        f"| 初始资金 | {card['capital_initial']:,.0f} |\n")

with c2:
    st.subheader("约束")
    cons = card["constraints"]
    st.markdown("\n".join(f"- `{k}` = {v}" for k, v in cons.items()))
    st.caption(f"冻结校验：{card.get('freeze_detail')}")
    st.caption(f"冻结于 {card.get('frozen_at')}")
    st.info("这些参数由研究阶段选定并冻结。**界面不提供任何修改入口** —— "
            "改参数＝新开 run，不是点一下按钮。")

st.markdown("---")
st.subheader("策略 vs 实际账户")
st.caption("真实账户是否偏离了模型目标（§37）。只比较，**不产生交易指令**。")
vs = strategy_service.versus_actual()
if unavailable_block(vs, "无法比较（缺少账户或信号）"):
    pass
else:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("信号日", vs.get("signal_date"))
    c2.metric("目标持仓数", vs["n_target"])
    c3.metric("实际持仓数", vs["n_actual"])
    c4.metric("重合度", pct(vs.get("overlap_ratio")))
    drift = [r for r in vs["rows"] if abs(r["drift"]) > 0.005]
    if drift:
        st.markdown("**权重偏离最大的标的：**")
        st.dataframe(pd.DataFrame([{
            "代码": r["symbol"], "目标": pct(r["target_weight"]),
            "实际": pct(r["actual_weight"]), "偏离": pct(r["drift"], signed=True),
            "状态": {"both": "都持有", "target_only": "仅目标",
                     "actual_only": "仅实际"}[r["status"]]}
            for r in drift[:20]]), hide_index=True, width="stretch")
        export_button(drift, "weight_drift.csv", "导出偏离 CSV")
    else:
        st.success("权重偏离均在 0.5% 以内")
    st.caption(vs.get("note", ""))

st.markdown("---")
st.subheader("当前信号")
sig = factor_service.current_signals(limit=50)
if unavailable_block(sig, "还没有信号快照"):
    pass
else:
    st.caption(f"信号日 {sig['state'].get('as_of')} ｜ "
               f"全市场 {sig['n']} 只 ｜ 显示前 50")
    st.dataframe(pd.DataFrame([{
        "排名": int(r["raw_rank"]), "代码": r["symbol"], "名称": r.get("name"),
        "预测分": num(r["prediction"], 4),
        "入选": "✓" if r.get("is_top") else ""}
        for r in sig["rows"]]), hide_index=True, width="stretch")
