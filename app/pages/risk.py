# -*- coding: utf-8 -*-
"""风险（spec §30 / §36 / §38）。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from _shared import (bar_chart, export_button, money, no_data, num, pct,
                     page_setup, unavailable_block)
from services import performance_service, portfolio_service, risk_service

page_setup("风险", "🛡️")

bench = st.selectbox("基准", ["CSI300", "CSI500", "CSI1000", "EW_MARKET"])
rk = risk_service.metrics(benchmark=bench)
if unavailable_block(rk, "风险指标不可用"):
    st.stop()

nav_based = rk.get("nav_based")
hold_based = rk.get("holdings_based")

st.subheader("组合风险")
if not nav_based:
    st.info(f"**NO DATA** — {rk.get('note', '需要净值序列')}\n\n"
            "波动率 / 回撤 / VaR 需要先录入每日快照（「交易流水」或每日更新）。")
else:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("年化波动", pct(nav_based.get("volatility")))
    c2.metric("最大回撤", pct(nav_based.get("max_drawdown")))
    c3.metric("VaR 95% (1日)", pct(nav_based.get("var_95_1d")))
    c4.metric("CVaR 95% (1日)", pct(nav_based.get("cvar_95_1d")))
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("最差单日", pct(nav_based.get("worst_day")))
    c6.metric("Beta", num(nav_based.get("beta"), 3))
    c7.metric("Alpha(年化)", pct(nav_based.get("alpha_annualized")))
    c8.metric("信息比率", num(nav_based.get("information_ratio"), 3))
    st.caption(f"基准 `{bench}`（买入持有）；样本 {nav_based.get('n_days')} 天。"
               "VaR/CVaR 用历史模拟法，样本 < 20 天时不给值。")

st.markdown("---")
st.subheader("持仓集中度")
if not hold_based:
    no_data("没有持仓")
else:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("持仓数", hold_based.get("n_positions"))
    c2.metric("HHI", num(hold_based.get("hhi"), 4))
    c3.metric("有效持仓数", num(hold_based.get("effective_n"), 1))
    c4.metric("最大单只权重", pct(hold_based.get("top_weight")))
    c5, c6 = st.columns(2)
    c5.metric("前 5 大权重", pct(hold_based.get("top5_weight")))
    c6.metric("现金比例", pct(hold_based.get("cash_ratio")))

st.markdown("---")
st.subheader("行业暴露")
sec = risk_service.sector_exposure()
if unavailable_block(sec, "行业数据不可用"):
    pass
else:
    rows = [r for r in sec["rows"] if r["value"] > 0]
    if rows:
        st.bar_chart(pd.Series({r["industry"]: r["weight"] for r in rows}),
                     height=260, color="#0072B2")
        if sec.get("unknown_weight"):
            st.caption(f"未分类占比 {pct(sec['unknown_weight'])}")
    else:
        no_data()
    st.caption(sec.get("note", ""))

st.markdown("---")
st.subheader("收益贡献（§36）")
attr = performance_service.attribution()
if unavailable_block(attr, "无法做贡献分解"):
    pass
else:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**贡献最大**")
        st.dataframe(pd.DataFrame([{
            "代码": r["symbol"], "名称": r["name"], "类别": r["asset_class"],
            "损益": money(r["pnl"])} for r in attr["top_contributors"]]),
            hide_index=True, width="stretch")
    with c2:
        st.markdown("**拖累最大**")
        det = attr["top_detractors"]
        if det:
            st.dataframe(pd.DataFrame([{
                "代码": r["symbol"], "名称": r["name"],
                "类别": r["asset_class"], "损益": money(r["pnl"])}
                for r in det]), hide_index=True, width="stretch")
        else:
            no_data("没有负贡献标的")
    st.caption(attr.get("note", ""))

st.markdown("---")
st.subheader("集中度提示（§38）")
alert = risk_service.concentration_alert(threshold=0.25)
if alert.get("available"):
    if alert["ok"]:
        st.success("没有单只权重超过 25%")
    else:
        st.warning(f"{len(alert['over'])} 只超过 25%："
                   + ", ".join(f"{r['symbol']} {pct(r['weight'])}"
                               for r in alert["over"][:8]))
        st.caption(alert["note"])
