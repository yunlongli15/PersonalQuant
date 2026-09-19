# -*- coding: utf-8 -*-
"""持仓页（spec §20 / §21 / §35）。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from _shared import (export_button, line_chart, money, no_data, num, pct,
                     page_setup, unavailable_block)
from services import market_service, portfolio_service, strategy_service

page_setup("持仓", "💼")

pos = portfolio_service.positions()
if unavailable_block(pos, "还没有持仓数据"):
    st.caption("提示：在「交易流水」录入买入记录，或在「设置」导入 CSV。")
    st.stop()

rows = pos["rows"]

# ---------------------------------------------------------------- 过滤 §20
f1, f2, f3 = st.columns([1, 1, 2])
classes = sorted({r["asset_class_cn"] for r in rows})
pick = f1.multiselect("资产类别", classes, default=classes)
kw = f2.text_input("搜索代码/名称", "")
sort_key = f3.selectbox(
    "排序", ["市值 ↓", "浮盈 ↓", "权重 ↓", "代码 ↑"], index=0)

view = [r for r in rows if r["asset_class_cn"] in pick]
if kw:
    k = kw.strip().upper()
    view = [r for r in view if k in (r["symbol"] or "").upper()
            or k in (r["name"] or "").upper()]
keymap = {"市值 ↓": lambda r: -abs(r["market_value"]),
          "浮盈 ↓": lambda r: -(r["unrealized_pnl"] or 0),
          "权重 ↓": lambda r: -r["weight"],
          "代码 ↑": lambda r: r["symbol"] or ""}
view.sort(key=keymap[sort_key])

st.caption(f"共 {len(view)} 只 ｜ 总市值 {money(pos.get('total_value'))} "
           f"｜ 行情日 {pos.get('price_date') or '—'}")

df = pd.DataFrame([{
    "代码": r["symbol"], "名称": r["name"], "类别": r["asset_class_cn"],
    "数量": num(r["quantity"]), "成本价": num(r["avg_cost"], 3),
    "现价": num(r["price"], 3), "市值": money(r["market_value"]),
    "权重": pct(r["weight"]), "浮动盈亏": money(r["unrealized_pnl"]),
    "已实现": money(r["realized_pnl"]),
    "收益率": pct(r["return_pct"], signed=True),
} for r in view])
st.dataframe(df, hide_index=True, width="stretch")
export_button(view, "positions.csv", "导出持仓 CSV")

if pos.get("missing_price"):
    st.warning(f"缺现价（按成本计价）：{', '.join(pos['missing_price'])}")

st.markdown("---")

# ---------------------------------------------------------------- 个股详情 §21
st.subheader("个股详情")
if not view:
    no_data("没有可选的持仓")
    st.stop()

sym = st.selectbox("选择标的", [r["symbol"] for r in view if r["symbol"]])
row = next((r for r in view if r["symbol"] == sym), None)
if row is None:
    no_data()
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("市值", money(row["market_value"]))
c2.metric("浮动盈亏", money(row["unrealized_pnl"]),
          pct(row["return_pct"], signed=True))
c3.metric("成本 / 现价", f"{num(row['avg_cost'], 3)} / {num(row['price'], 3)}")
c4.metric("权重", pct(row["weight"]))

hist = market_service.price_history(sym, 250)
if hist:
    line_chart([{"date": h["date"], "value": h["close"]} for h in hist],
               height=280)
else:
    no_data("没有该标的的历史行情")

tab1, tab2 = st.tabs(["成交记录", "策略信号"])

with tab1:
    txns = portfolio_service.transactions(limit=1000)
    if txns.get("available"):
        mine = [t for t in txns["rows"] if t.get("ticker") == sym]
        if mine:
            st.dataframe(pd.DataFrame([{
                "日期": t["txn_date"], "类型": t["txn_type"],
                "数量": num(t["units"]), "价格": num(t["price"], 3),
                "金额": money(t["amount"]), "费用": money(t["fee"]),
                "来源": t.get("source")} for t in mine]),
                hide_index=True, width="stretch")
        else:
            no_data("该标的没有成交记录")
    else:
        no_data()

with tab2:
    from services import factor_service
    sig = factor_service.current_signals(limit=5000)
    if sig.get("available"):
        hit = [r for r in sig["rows"] if r["symbol"] == sym]
        if hit:
            r = hit[0]
            st.markdown(f"- 预测分：**{num(r['prediction'], 4)}**\n"
                        f"- 排名：**{int(r['raw_rank'])}** / {sig['n']}\n"
                        f"- 信号日：{r.get('signal_date')}")
        else:
            no_data("该标的当日没有信号")
    else:
        no_data(sig.get("reason", ""))

    st.caption("以上为模型信号，不构成买卖指令；系统不会下单。")
