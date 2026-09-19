# -*- coding: utf-8 -*-
"""交易流水（spec §10 / §12 / §22 / §44）。

**这是记账，不是下单。** 页面里没有任何通往券商的路径。
每一次写入都会自动进 audit_log（wealth/repository 强制）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from _shared import (export_button, money, no_data, num, page_setup,
                     unavailable_block)
from services import portfolio_service

page_setup("交易流水", "📒")

st.caption("这里只做**记账**，系统不会把任何一笔发到券商。")

TXN_CN = {"buy": "买入", "sell": "卖出", "dividend": "分红",
          "deposit": "转入", "withdrawal": "转出",
          "transfer_in": "转入(内部)", "transfer_out": "转出(内部)",
          "subscribe": "申购", "redeem": "赎回", "fee": "费用",
          "split": "拆股", "adjustment": "调整"}

tab_list, tab_add, tab_import = st.tabs(["流水列表", "记一笔", "导入 CSV"])

# ------------------------------------------------------------------ 列表
with tab_list:
    txns = portfolio_service.transactions(limit=500)
    if unavailable_block(txns, "还没有流水"):
        pass
    else:
        rows = txns["rows"]
        c1, c2 = st.columns(2)
        kinds = sorted({t["txn_type"] for t in rows})
        pick = c1.multiselect("类型", kinds, default=kinds,
                              format_func=lambda k: TXN_CN.get(k, k))
        kw = c2.text_input("搜索代码/名称", "")
        view = [t for t in rows if t["txn_type"] in pick]
        if kw:
            k = kw.strip().upper()
            view = [t for t in view if k in (t.get("ticker") or "").upper()
                    or k in (t.get("product_name") or "").upper()]

        st.dataframe(pd.DataFrame([{
            "日期": t["txn_date"], "类型": TXN_CN.get(t["txn_type"],
                                                      t["txn_type"]),
            "代码": t.get("ticker"), "名称": t.get("product_name"),
            "数量": num(t["units"]), "价格": num(t["price"], 3),
            "金额": money(t["amount"]), "费用": money(t["fee"]),
            "外部流": money(t["cash_flow"]),
            "来源": t.get("source"), "备注": t.get("note"),
        } for t in view]), hide_index=True, width="stretch")
        export_button(view, "transactions.csv", "导出流水 CSV")

# ------------------------------------------------------------------ 记一笔
with tab_add:
    st.markdown("**新增一笔流水**（写库前会做校验，外部流/内部流不能混）")
    if st.session_state.get("_txn_result"):
        st.success(st.session_state.pop("_txn_result"))

    plist = portfolio_service.products()
    products = plist.get("rows", []) if plist.get("available") else []

    if not products:
        no_data("还没有任何产品 —— 先在「设置」里建账户，或导入一份 CSV。")
    else:
        labels = {p["product_id"]: f"{p['name']}"
                                    f"{' (' + p['ticker'] + ')' if p.get('ticker') else ''}"
                                    f" · {p['account']}"
                  for p in products}
        with st.form("add_txn"):
            c1, c2, c3 = st.columns(3)
            pid = c1.selectbox("产品", options=list(labels),
                               format_func=lambda i: labels[i])
            ttype = c2.selectbox("类型", options=list(TXN_CN),
                                 format_func=lambda k: TXN_CN[k])
            d = c3.date_input("日期")
            c4, c5, c6 = st.columns(3)
            units = c4.number_input("数量", min_value=0.0, value=0.0, step=100.0)
            price = c5.number_input("价格", min_value=0.0, value=0.0,
                                    step=0.01, format="%.4f")
            fee = c6.number_input("费用", min_value=0.0, value=0.0, step=0.01)
            amount = st.number_input("金额（不填则 = 数量×价格）",
                                     min_value=0.0, value=0.0, step=1.0)
            note = st.text_input("备注", "")
            ok = st.form_submit_button("记录（仅记账，不下单）")
        if ok:
            res = portfolio_service.add_transaction(
                txn_date=str(d), product_id=int(pid), txn_type=ttype,
                units=units, price=price or None, amount=amount, fee=fee,
                note=note)
            if res.get("available"):
                st.session_state["_txn_result"] = (
                    f"已记录 #{res['txn_id']}（{TXN_CN[ttype]}）。"
                    f"已写入审计日志。")
                st.rerun()
            else:
                st.error(f"记录失败：{res.get('reason')}")

# ------------------------------------------------------------------ 导入
with tab_import:
    st.markdown("**导入 CSV**（spec §12）")
    st.code("date,symbol,side,quantity,price,fees,account\n"
            "2026-09-18,600519.SH,BUY,100,1680.5,5.2,券商", language="text")
    up = st.file_uploader("选择 CSV 文件", type=["csv"])
    dry = st.checkbox("先预览（不写库）", value=True)
    if up is not None:
        tmp = Path(__file__).resolve().parents[2] / "data" / "quant" / \
            "_gui_import.csv"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(up.getvalue())
        d = portfolio_service.import_csv(tmp, dry_run=dry)
        if "n_imported" not in d:
            st.error(f"导入失败：{d.get('reason')}")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("可导入", d["n_imported"])
            c2.metric("重复跳过", d["n_skipped"])
            c3.metric("错误", d["n_errors"])
            if d["errors"]:
                st.error("以下行无法解析（**不会**猜值，请修正后重试）：")
                st.dataframe(pd.DataFrame(d["errors"]), hide_index=True)
            if d["created"]:
                st.info(f"将新建：{d['created']}")
            if not dry and d["n_imported"]:
                st.success("已写入，全部经过 audit_log。")
