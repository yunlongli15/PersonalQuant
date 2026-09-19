# -*- coding: utf-8 -*-
"""仪表盘（spec §18 / §19 / §56 / §58）。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from _shared import (bar_chart, cfg, export_button, line_chart, money,
                     multi_line_chart, no_data, pct, page_setup, render_chips,
                     unavailable_block)
from services import (market_service, news_service, performance_service,
                      portfolio_service, recommendation_service,
                      strategy_service)

page_setup("仪表盘", "📊")

# ---------------------------------------------------------------- 顶部状态卡
card = strategy_service.status_card()
if not unavailable_block(card, "策略状态不可用"):
    chips = []
    for t in card.get("tags", []):
        chips.append((t, t.replace(" ", "_")))
    if card.get("status") == "DRIFT_DETECTED":
        chips.append(("DRIFT DETECTED", "INVALID"))
    render_chips(chips)
    st.caption(f"策略版本 **{card['strategy_version']}** ｜ "
               f"冻结于 {card.get('frozen_at')} ｜ "
               f"forward 起点 {card.get('forward_start_date')} ｜ "
               f"模型 `{card.get('model')}`")

val = portfolio_service.valuation()
alloc = portfolio_service.allocation()
perf = performance_service.summary()

st.markdown("---")

# ---------------------------------------------------------------- 三栏布局 §58
left, mid, right = st.columns([1, 2, 1])

with left:
    st.subheader("资产")
    if unavailable_block(val, "还没有账户数据"):
        st.caption("提示：先在「交易流水」录入或导入成交记录。")
    else:
        total = (val.get("market_value") or 0) + (val.get("cash_recorded") or 0)
        st.metric("总资产", money(total), help="持仓市值 + 已记录的现金")
        st.metric("持仓市值", money(val.get("market_value")))
        st.metric("现金（已记录）", money(val.get("cash_recorded")))
        st.metric("持仓数", int(val.get("n_positions") or 0))
        if val.get("missing_price"):
            st.warning(f"{len(val['missing_price'])} 只标的缺现价，"
                       f"按成本计价：{', '.join(val['missing_price'][:5])}")

with mid:
    st.subheader("净值曲线")
    snaps = portfolio_service.snapshots()
    if unavailable_block(snaps, "还没有每日快照"):
        st.caption("录入「每日更新」后这里会出现净值曲线。")
    else:
        line_chart(snaps["series"], height=cfg("chart.height", 320))

with right:
    st.subheader("资产配置")
    if unavailable_block(alloc, "暂无配置数据"):
        pass
    else:
        rows = [r for r in alloc["rows"] if r["value"] > 0]
        if rows:
            st.bar_chart(pd.Series({r["label"]: r["weight"] for r in rows}),
                         height=cfg("chart.height", 320), color="#0072B2")
        else:
            no_data()

st.markdown("---")

# ---------------------------------------------------------------- 收益指标行
c1, c2, c3, c4, c5 = st.columns(5)
if perf.get("available"):
    c1.metric("累计收益", pct(perf.get("cumulative_return"), signed=True))
    c2.metric("TWR", pct(perf.get("twr"), signed=True))
    c3.metric("XIRR", pct(perf.get("mwr_xirr"), signed=True))
    c4.metric("最大回撤", pct(perf.get("max_drawdown")))
    c5.metric("外部净流入", money(perf.get("external_net_flow")))
else:
    st.info(f"**NO DATA** — {perf.get('reason', '暂无收益数据')}")

st.markdown("---")

# ---------------------------------------------------------------- 底部三块
b1, b2, b3 = st.columns(3)

with b1:
    st.subheader("当前策略")
    if card.get("available"):
        st.markdown(
            f"- 版本：**{card['strategy_version']}**\n"
            f"- alpha：`{card['alpha_signal']}`\n"
            f"- Top-K：**{card['top_k']}**\n"
            f"- 调仓：{card['rebalance']['frequency']} / "
            f"{card['rebalance']['rule']}\n"
            f"- 分配：`{card['allocation_method']}`\n"
            f"- 标签：FROZEN · PAPER（不可由界面修改）")

with b2:
    st.subheader("最新建议")
    rec = recommendation_service.latest()
    if unavailable_block(rec, "还没有交易计划"):
        pass
    else:
        top = rec["rows"][:cfg("dashboard.top_signals", 8)]
        st.caption(f"信号日 **{rec.get('signal_date')}** ｜ "
                   f"共 {rec['n_rows']} 条 ｜ PAPER ONLY")
        st.dataframe(
            pd.DataFrame([{"代码": r["symbol"], "名称": r["name"],
                           "动作": r["action"], "排名": r["rank"],
                           "目标权重": pct(r["target_weight"])}
                          for r in top]),
            hide_index=True, width="stretch")

with b3:
    st.subheader("最新新闻")
    news = news_service.latest(limit=cfg("dashboard.top_news", 8))
    if unavailable_block(news, "还没有新闻数据"):
        pass
    else:
        st.caption("规则分类（非 LLM）")
        st.dataframe(
            pd.DataFrame([{"日期": r["date"], "代码": r["symbol"],
                           "类型": r["event_type"],
                           "方向": r["direction_cn"]}
                          for r in news["rows"]]),
            hide_index=True, width="stretch")
