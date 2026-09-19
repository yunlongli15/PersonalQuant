# -*- coding: utf-8 -*-
"""Paper Live / Forward Holdout（spec §28 / §29）。

样本不足时说 NOT ENOUGH DATA，**绝不对短样本做年化**（§29 / §41）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from _shared import (line_chart, money, no_data, num, pct, page_setup,
                     render_chips, unavailable_block)
from services import market_service, strategy_service

page_setup("Paper Live", "🧪")

render_chips([("LIVE PAPER", "LIVE_PAPER"), ("RECORD ONLY", "RESEARCH_ONLY")])

pl = strategy_service.paper_live()
if unavailable_block(pl, "Paper live 不可用"):
    st.stop()

st.markdown(
    f"**Forward 起点** {pl['forward_start_date']} ｜ "
    f"**策略** `{pl['strategy_version']}` ｜ "
    f"**模式** {'只记录（不参与任何选择）' if pl['record_only'] else '—'}")

st.markdown("---")

c1, c2, c3, c4 = st.columns(4)
c1.metric("观测天数", pl["n_observation_days"])
c2.metric("当前市值", money(pl.get("current_value")) if pl.get("current_value")
          else "—")
c3.metric("初始资金", money(pl.get("capital_initial")))
c4.metric("累计收益", pct(pl.get("cumulative_return"), signed=True))

if not pl["enough_data"]:
    st.warning(
        f"**NOT ENOUGH DATA** — 目前只有 {pl['n_observation_days']} 个观测日。\n\n"
        "按 §29：样本不足时**不做年化、不给 Sharpe**，也不据此评价策略。"
        "2026-09-18 之后的数据只记录、只观察，绝不回流到任何选择。")
else:
    c5, c6 = st.columns(2)
    c5.metric("最大回撤", pct(pl.get("max_drawdown")))
    q = pl.get("prediction_quality") or {}
    c6.metric("IC", num(q.get("ic_mean"), 4),
              help=f"n={q.get('n_dates', 0)}")

st.markdown("---")
st.subheader("观察记录")

if not pl["rows"]:
    no_data("forward holdout 尚无观测记录。\n\n"
            "数据快照截至 2026-09-17，起点是 2026-09-18 —— "
            "这是**预期状态**，不是故障。")
    st.markdown(
        "**为什么现在是空的**\n\n"
        "1. clean forward holdout 从 2026-09-18 开始\n"
        "2. 当前行情数据到 2026-09-17\n"
        "3. 所以还没有任何一期可以记录\n\n"
        "等新数据到位后运行：\n"
        "```bash\n"
        "python scripts/paper_live/run_daily.py\n"
        "python scripts/paper_live/build_dashboard.py\n"
        "```")
else:
    line_chart([{"date": r["date"], "value": r["portfolio_value"]}
                for r in pl["rows"]], height=260)
    st.dataframe(pd.DataFrame(pl["rows"]), hide_index=True,
                 width="stretch")

st.markdown("---")
st.subheader("历史 Test 状态")
st.markdown(
    "**2024-2025 = HISTORICAL_TEST_OBSERVED**\n\n"
    "该区间已被评估三次（STEP 6 终评、step8 微结构消融、step9 独立信息研究），"
    "**不再是 untouched test**。它只用于历史对照，不能作为干净的样本外证据。")
render_chips([("HISTORICAL TEST OBSERVED", "HISTORICAL_TEST_OBSERVED")])
