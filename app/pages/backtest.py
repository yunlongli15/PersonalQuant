# -*- coding: utf-8 -*-
"""回测结果浏览（spec §33）。

**只读。** 页面不提供参数修改入口 —— 改参数＝新开 run，不是点按钮。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from _shared import (line_chart, no_data, num, pct, page_setup,
                     unavailable_block)
from services import backtest_service

page_setup("回测", "📈")

res = backtest_service.results()
if unavailable_block(res, "还没有回测结果"):
    st.stop()

pick = st.selectbox("选择回测", res["runs"],
                    format_func=lambda r: r["label"])
s = pick.get("strategy") or {}

if s:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("累计收益", pct(s.get("cumulative_return"), signed=True))
    c2.metric("年化", pct(s.get("annualized_return"), signed=True))
    c3.metric("Sharpe", num(s.get("sharpe"), 3))
    c4.metric("最大回撤", pct(s.get("max_drawdown")))
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("年化波动", pct(s.get("annualized_volatility")))
    c6.metric("Calmar", num(s.get("calmar"), 3))
    c7.metric("月胜率", pct(s.get("win_rate_monthly")))
    c8.metric("交易笔数", s.get("n_trades") or "—")
    if s.get("information_ratio") is not None:
        c9, c10, c11, c12 = st.columns(4)
        c9.metric("信息比率", num(s.get("information_ratio"), 3))
        c10.metric("Alpha(年化)", pct(s.get("alpha_annualized")))
        c11.metric("Beta", num(s.get("beta"), 3))
        c12.metric("天数", s.get("n_days"))

st.markdown("---")
nav = backtest_service.nav_curve(pick["key"])
if unavailable_block(nav, "没有净值曲线"):
    pass
else:
    st.subheader("净值曲线")
    line_chart(nav["series"], height=320)

if pick.get("benchmarks"):
    st.subheader("基准")
    st.dataframe(pd.DataFrame([{
        "基准": k, "累计收益": pct((v or {}).get("cumulative_return"), True),
        "Sharpe": num((v or {}).get("sharpe"), 3),
        "最大回撤": pct((v or {}).get("max_drawdown"))}
        for k, v in pick["benchmarks"].items()]),
        hide_index=True, width="stretch")

st.markdown("---")
st.info("**回测结果是历史研究，不是收益承诺。** "
        "2024-2025 为 HISTORICAL TEST（已被观察多次），"
        "2026 年数据仅用于 paper live 观察，绝不回流到参数选择。")
