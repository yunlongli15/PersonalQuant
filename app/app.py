# -*- coding: utf-8 -*-
"""PersonalQuant · 个人投资终端（Streamlit 入口）。

    streamlit run app/app.py
    或：python scripts/run_app.py

定位（spec §1 / §65）：**完全本地运行的个人投资研究、组合管理与决策辅助终端**。
不是自动炒股机器人 —— 不连接券商、不自动下单、不涉及真实资金操作。

导航由 `st.navigation` 显式定义（§61），用户不需要手输 URL。
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
for p in (str(APP_DIR), str(PROJECT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from _shared import cfg, render_chips  # noqa: E402

PAGES = [
    ("仪表盘", "📊", "pages/dashboard.py", True),
    ("持仓", "💼", "pages/portfolio.py", False),
    ("交易流水", "📒", "pages/transactions.py", False),
    ("调仓建议", "🎯", "pages/recommendations.py", False),
    ("量化策略", "⚙️", "pages/quant_strategy.py", False),
    ("Paper Live", "🧪", "pages/paper_live_monitor.py", False),
    ("风险", "🛡️", "pages/risk.py", False),
    ("因子", "🔬", "pages/factors.py", False),
    ("新闻", "📰", "pages/news.py", False),
    ("回测", "📈", "pages/backtest.py", False),
    ("研究", "📚", "pages/research.py", False),
    ("设置", "🔧", "pages/settings.py", False),
]


def main() -> None:
    st.set_page_config(page_title=cfg("title", "PersonalQuant"), page_icon="📈",
                       layout="wide", initial_sidebar_state="expanded")

    nav = st.navigation(
        [st.Page(str(APP_DIR / rel), title=title, icon=icon, default=default)
         for title, icon, rel, default in PAGES],
        position="sidebar")

    with st.sidebar:
        st.markdown(f"### {cfg('title', 'PersonalQuant')}")
        render_chips([("本地运行", "LIVE_PAPER"), ("只读研究", "RESEARCH_ONLY")])
        st.caption("不连接券商 · 不自动下单 · 数据不出本机")

    nav.run()


main()
