# -*- coding: utf-8 -*-
"""设置 / 系统健康（spec §43 / §45 / §54 / §66 / §67）。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from _shared import PROJECT_ROOT, cfg, no_data, page_setup, render_chips, \
    unavailable_block
from services import health_service, portfolio_service

page_setup("设置", "🔧")

tab_health, tab_backup, tab_data, tab_prefs = st.tabs(
    ["系统健康", "备份", "数据更新", "显示"])

# ---------------------------------------------------------------- §66 健康
with tab_health:
    h = health_service.check()
    if unavailable_block(h, "健康检查不可用"):
        st.stop()
    overall = ("FAIL" if h["n_fail"] else
               ("WARNING" if h["n_warning"] else "PASS"))
    render_chips([(f"总体 {overall}", overall)])
    st.dataframe(pd.DataFrame([{
        "检查项": i["name"], "状态": i["status"], "说明": i["detail"]}
        for i in h["items"]]), hide_index=True, width="stretch")
    if overall == "FAIL":
        st.error("有检查项失败 —— 请先修好再依赖本终端的数字。")
    elif overall == "WARNING":
        st.warning("有检查项告警。数字仍然展示，但请留意说明列。")
    else:
        st.success("全部通过。")

# ---------------------------------------------------------------- §54 备份
with tab_backup:
    st.markdown("**备份个人资产库**（只备份个人数据，不动市场数据库）")
    stt = portfolio_service.wealth_status()
    if stt.get("available"):
        st.caption(f"当前：{stt['n_transactions']} 条流水 ｜ "
                   f"`{stt['db_path']}`")
    if st.button("立即备份到 backup/"):
        res = portfolio_service.backup()
        if res.get("available"):
            st.success(f"已备份到 `{res['path']}`")
        else:
            st.error(f"备份失败：{res.get('reason')}")
    st.info("恢复需要人工确认，且**不会**覆盖市场数据库。"
            "本页不提供一键恢复 —— 恢复是不可逆操作。")

    st.markdown("---")
    st.markdown("**导出个人数据**")
    if st.button("导出为 CSV（data/wealth/export/）"):
        res = portfolio_service.export_tables()
        if res.get("available"):
            st.success(f"已导出 {res['n_tables']} 张表到 `{res['dest']}`")
        else:
            st.error(f"导出失败：{res.get('reason')}")

# ---------------------------------------------------------------- §43 数据更新
with tab_data:
    st.markdown("**更新数据**")
    st.caption("只会读取/刷新数据，**不会重新训练模型**，也不会改动任何"
               "冻结策略。")
    dry = st.checkbox("先 dry-run（只检查不执行）", value=True)
    if st.button("运行 refresh_all"):
        with st.spinner("正在更新数据 …"):
            fres = health_service.refresh_all()
        jobs = fres.get("jobs", []) if fres.get("available") else []
        if not fres.get("available"):
            st.error(f"更新失败：{fres.get('reason')}")
        if jobs:
            st.dataframe(pd.DataFrame([{
                "任务": j.get("job"), "状态": j.get("status"),
                "耗时(s)": round(j.get("duration_s") or 0, 1),
                "说明": (j.get("detail") or j.get("error") or "")[:80]}
                for j in jobs]), hide_index=True, width="stretch")
        st.caption("提示：命令行运行更稳，且能看到完整进度："
                   "`python scripts/quant/refresh_all.py --continue-on-error`")

# ---------------------------------------------------------------- §45 显示
with tab_prefs:
    st.markdown("**当前界面配置**（来自 `config/gui.yaml`，不硬编码在页面里）")
    st.json(cfg("", {}), expanded=False)
    st.caption(f"精度：金额 {cfg('precision.money')} 位 / "
               f"百分比 {cfg('precision.pct')} 位 ｜ "
               f"基准默认 {cfg('benchmark.default')}")
    st.markdown("---")
    st.markdown("**安全边界**")
    render_chips([("NO BROKER", "INVALID"),
                  ("GUI 不可改冻结策略", "FROZEN")])
    st.markdown(
        f"- 连接券商：**{'允许' if cfg('safety.allow_broker') else '禁止'}**\n"
        f"- 界面改冻结策略："
        f"**{'允许' if cfg('safety.allow_freeze_change') else '禁止'}**\n"
        f"- API key：**只从环境变量读取，绝不写入本配置**（§47）\n"
        f"- 绑定地址：仅本机（`scripts/run_app.py` 拒绝外部绑定）")
