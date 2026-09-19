# -*- coding: utf-8 -*-
"""调仓建议（spec §24 / §25 / §26 / §27 / §63）。

**页面里只有 Export，没有 Submit Order。**（§27）
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from _shared import (export_button, money, no_data, num, pct, page_setup,
                     render_chips, unavailable_block)
from services import recommendation_service

page_setup("调仓建议", "🎯")

render_chips([("PAPER ONLY", "LIVE_PAPER"), ("NO BROKER", "INVALID"),
              ("非投资建议", "RESEARCH_ONLY")])

rec = recommendation_service.latest()
if unavailable_block(rec, "还没有交易计划（先跑 refresh_all.py）"):
    st.stop()

# ---------------------------------------------------------------- 元信息 §63
st.markdown(
    f"**信号日** {rec.get('signal_date')} ｜ "
    f"**执行** T+1 开盘 ｜ "
    f"**策略** `{rec.get('strategy_version')}` ｜ "
    f"**快照** {rec.get('data_snapshot')} ｜ "
    f"**模型** `{rec.get('model_version')}`")
st.caption(f"资金 {money(rec.get('capital'))} ｜ "
           f"计划买入 {money(rec.get('total_buy_value'))} ｜ "
           f"剩余现金 {money(rec.get('remaining_cash'))} "
           f"({pct(rec.get('cash_residual_pct'))}) ｜ "
           f"预估费用 {money(rec.get('estimated_fees'))} ｜ "
           f"预期净收益 {pct(rec.get('expected_net_return_pct'))}")

st.markdown("---")

# ---------------------------------------------------------------- 建议表 §24
rows = rec["rows"]
f1, f2 = st.columns([1, 3])
actions = sorted({r["action"] for r in rows if r["action"]})
pick = f1.multiselect("动作", actions, default=actions)
view = [r for r in rows if r["action"] in pick] if pick else rows

st.dataframe(pd.DataFrame([{
    "代码": r["symbol"], "名称": r["name"], "动作": r["action"],
    "排名": r["rank"], "预测分": num(r["prediction"], 4),
    "现价": num(r["current_price"], 3),
    "建议买入价": num(r["recommended_entry_price"], 3),
    "可接受区间": f"{num(r['entry_low'], 2)} ~ {num(r['entry_high'], 2)}",
    "目标权重": pct(r["target_weight"]),
    "股数": r["estimated_shares"],
    "金额": money(r["estimated_trade_value"]),
    "目标价": num(r["target_price"], 2),
    "止损": num(r["stop_loss"], 2),
    "板块": r["board"],
} for r in view]), hide_index=True, width="stretch")

export_button(view, f"recommendation_{rec.get('signal_date')}.csv",
              "导出建议 CSV（这是唯一的\"动作\"按钮）")

if rec.get("excluded_restricted"):
    with st.expander(f"因交易权限被排除（{len(rec['excluded_restricted'])} 只）"):
        st.dataframe(pd.DataFrame([{
            "代码": r.get("symbol"), "名称": r.get("name"),
            "板块": r.get("board_name"),
            "所需资金": money(r.get("capital_required")),
            "原因": r.get("reason")}
            for r in rec["excluded_restricted"]]),
            hide_index=True, width="stretch")

st.markdown("---")

# ---------------------------------------------------------------- 理由 §25
st.subheader("为什么是这些票")
st.caption("**结构化理由优先** —— 直接来自模型与约束，不是 LLM 编的解释。")
pick_sym = st.selectbox("选择标的", [r["symbol"] for r in view])
row = next((r for r in view if r["symbol"] == pick_sym), None)
if row:
    rf = row.get("reason_fields") or {}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("排名", f"{rf.get('rank')}", help="模型全市场排名")
    c2.metric("预测分", num(rf.get("prediction"), 4))
    c3.metric("目标权重", pct(rf.get("target_weight")))
    c4.metric("预期持有", f"{rf.get('holding_days')} 天"
              if rf.get("holding_days") else "—")
    if rf.get("volatility") is not None:
        st.caption(f"波动率 {pct(rf.get('volatility'))} ｜ "
                   f"行业 {rf.get('industry') or '—'} ｜ "
                   f"预期净收益 {pct(rf.get('expected_net_return'))}")
    if row.get("reasons"):
        st.markdown("**结构化理由：**")
        for t in row["reasons"]:
            st.markdown(f"- {t}")
    if not row.get("can_buy"):
        st.warning(f"当前不可买：{row.get('restriction_reason')}")
    st.caption("LLM 生成的解释若存在会单独标注 AI GENERATED；"
               "本页没有使用任何 LLM 输出。")

st.markdown("---")

# ---------------------------------------------------------------- 模拟 §26
st.subheader("调仓模拟")
st.caption("用**同一条引擎路径**算一遍：给多少资金、现在持有什么，会建议买什么。")
with st.form("sim"):
    c1, c2 = st.columns(2)
    capital = c1.number_input("资金", min_value=10000.0, value=500000.0,
                              step=10000.0)
    top_k = c2.number_input("Top-K", min_value=1, max_value=50, value=20)
    ok = st.form_submit_button("生成模拟（不写任何东西）")
if ok:
    sim = recommendation_service.simulate(capital=capital, top_k=int(top_k))
    if sim.get("available"):
        st.success(f"将买入 {sim['n_buys']} 只，金额 "
                   f"{money(sim['total_buy_value'])}，剩余现金 "
                   f"{money(sim['remaining_cash'])} "
                   f"({pct(sim['cash_residual_pct'])})")
        st.dataframe(pd.DataFrame([{
            "代码": r["symbol"], "名称": r["name"], "动作": r["action"],
            "价格": num(r["price"], 3), "股数": r["shares"],
            "金额": money(r["value"]), "权重": pct(r["weight"]),
            "可买": "是" if r["can_buy"] else "否"}
            for r in sim["rows"]]), hide_index=True,
            width="stretch")
        export_button(sim["rows"], "simulation.csv", "导出模拟 CSV")
        st.caption("模拟结果仅供参考；**系统不会下单**。")
    else:
        no_data(sim.get("reason", ""))
