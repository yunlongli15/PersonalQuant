# -*- coding: utf-8 -*-
"""新闻 / 公告（spec §32）。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from _shared import (export_button, no_data, num, page_setup, render_chips,
                     unavailable_block)
from services import news_service

page_setup("新闻", "📰")

render_chips([("RULE-BASED", "RESEARCH_ONLY")])
st.caption("事件分类由规则引擎产生（25 类）。"
           "LLM 分析若存在会单独标注 **AI GENERATED**。")

c1, c2, c3 = st.columns([1, 1, 2])
limit = c1.number_input("条数", min_value=10, max_value=500, value=100,
                        step=10)
symbols_raw = c2.text_input("代码（逗号分隔，可空）", "")
kinds = None
min_imp = None

news = news_service.latest(
    limit=int(limit),
    symbols=[s.strip().upper() for s in symbols_raw.split(",") if s.strip()]
    or None)
if unavailable_block(news, "还没有新闻事件数据"):
    st.stop()

st.caption(f"共 {news['n']} 条 ｜ 来源 `{news['source']}`")

df = pd.DataFrame([{
    "日期": r["date"], "代码": r["symbol"], "事件类型": r["event_type"],
    "方向": r["direction_cn"], "重要度": num(r["importance"], 2),
    "置信度": num(r["confidence"], 2), "新颖度": num(r["novelty"], 2),
    "风险": num(r["risk"], 2),
} for r in news["rows"]])
st.dataframe(df, hide_index=True, width="stretch")
export_button(news["rows"], "news_events.csv", "导出新闻 CSV")

st.markdown("---")
st.subheader("事件详情")
if news["rows"]:
    pick = st.selectbox("选择事件", range(len(news["rows"])),
                        format_func=lambda i: (
                            f"{news['rows'][i]['date']} "
                            f"{news['rows'][i]['symbol']} "
                            f"{news['rows'][i]['event_type']}"))
    r = news["rows"][pick]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("方向", r["direction_cn"])
    c2.metric("重要度", num(r["importance"], 2))
    c3.metric("新颖度", num(r["novelty"], 2))
    c4.metric("风险", num(r["risk"], 2))
else:
    no_data()

st.markdown("---")
st.subheader("LLM 分析")
llm = news_service.llm_analysis()
if llm.get("available"):
    render_chips([("AI GENERATED", "CANDIDATE")])
    st.markdown("以上内容由大模型生成，**不是模型事实**，也不能作为交易依据。")
else:
    st.info(f"**{llm.get('reason', '不可用')}**")
    st.caption("系统在无 API key 时按 RULE_BASED_ONLY 运行，功能不因此失败。")

cov = news_service.coverage()
if cov.get("available"):
    st.caption(f"覆盖 {cov['n_symbols']} 只标的 · {cov.get('note')}")
