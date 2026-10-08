# -*- coding: utf-8 -*-
"""每日状态文本（spec §44）。

只做格式化，不做任何金融计算 —— 数字全部由 engine/ledger 传进来。
这跟 webapp/pages.py 的纪律一致：展示层不许自己算钱。
"""

from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

from . import state as S


def _money(x) -> str:
    return "—" if x is None else f"{float(x):,.2f}"


def _pct(x) -> str:
    return "—" if x is None else f"{float(x):+.2%}"


def render_daily(result, s_cfg: dict, exp: dict, prices: Dict[str, float],
                 previous_value: Optional[float] = None,
                 overrides: Optional[List[dict]] = None,
                 preflight: Optional[dict] = None) -> str:
    state = result.state
    t = result.totals
    L: List[str] = []
    add = L.append

    # 三个时间必须分开说（spec §3）：混成一个 date 是上线前最难发现的错。
    run_date = (preflight or {}).get("system_run_date") or "—"
    mkt_last = (preflight or {}).get("market_data_last_date") \
        or result.run_date
    sig_date = (preflight or {}).get("signal_date") or "—"
    nxt = (preflight or {}).get("next_trading_date")
    nxt_status = (preflight or {}).get("next_session_status", "—")

    add("DAILY EXIT PAPER")
    add(f"  system_run_date        {run_date}")
    add(f"  market_data_last_date  {mkt_last}")
    add(f"  signal_date            {sig_date}")
    add(f"  next_trading_date      {nxt or '—'}  （{nxt_status}）")
    add(f"  as_of（本次推进到）     {result.run_date}")
    if result.sessions:
        add(f"  sessions               {result.sessions[0]} … "
            f"{result.sessions[-1]}（共 {len(result.sessions)} 个交易日）")
    else:
        add("  sessions               无（本次为无操作重跑）")
    if exp.get("experiment_id"):
        add(f"  experiment             {exp['experiment_id']}  "
            f"本金 {_money(exp.get('initial_capital'))}")
    else:
        add("  experiment             —（dry-run：尚未创建实验、"
            "本金未锁定）")
    add("")

    equity = float(t["portfolio_value"])
    day_pnl = None if previous_value is None else equity - float(previous_value)
    cum = (equity / float(state["initial_capital"]) - 1.0
           if state["initial_capital"] else None)
    add("Portfolio:")
    add(f"  Cash            {_money(t['cash'])}")
    add(f"  Reserved        {_money(t['reserved_cash'])}")
    add(f"  Available       {_money(t['available_cash'])}")
    add(f"  Market Value    {_money(t['position_value'])}")
    add(f"  Total Equity    {_money(equity)}")
    add(f"  Daily P&L       {_money(day_pnl)}")
    add(f"  Cumulative      {_pct(cum)}")
    add(f"  Fees (total)    {_money(t.get('fees_total'))}")
    add("")

    positions = S.open_positions(state)
    add(f"OPEN POSITIONS ({len(positions)} / {s_cfg['top_k']})")
    if not positions:
        add("  （空仓）")
    for sym, p in sorted(positions.items()):
        px = prices.get(sym, p.get("last_price"))
        mv = int(p["entry_shares"]) * float(px or 0.0)
        cost = float(p["entry_value"]) + float(p.get("entry_fee") or 0.0)
        ret = (mv - cost) / cost if cost else 0.0
        tag = " [等成交]" if p.get("status") == S.PositionStatus.PENDING_EXIT \
            .value else ""
        add(f"  {sym} {p.get('name',''):<8} {int(p['entry_shares']):>6} 股  "
            f"成本 {p['entry_price']:>9.3f}  现价 "
            f"{'—' if px is None else f'{float(px):.3f}':>9}  "
            f"{ret:+.2%}  持有 {int(p.get('holding_sessions') or 0):>2} 日  "
            f"目标 {p['target_price']:.3f} / 止损 {p['stop_loss']:.3f}"
            f"{tag}")
    add("")

    pend = S.pending_list(state)
    add(f"PENDING ENTRIES ({len(pend)})")
    if not pend:
        add("  （无）")
    for o in pend:
        add(f"  {o['symbol']} {o.get('name',''):<8} {int(o['quantity']):>6} 股  "
            f"限价 {o['limit_price']:>9.3f}  "
            f"目标* {o.get('target_price_at_signal') or 0:>8.3f}  "
            f"止损* {o.get('stop_loss_at_signal') or 0:>8.3f}  "
            f"信号日 {o['signal_date']}  "
            f"执行日 {o.get('resolved_exec_date') or '下一交易日'}  "
            f"预留 {_money(o['reserved_cash'])}")
    if pend:
        add("  * 同上：目标/止损在成交时按实际成交价重新锚定并锁定。")
    add("")

    exits = [e for r in result.reports for e in r.exits]
    add(f"EXITS TODAY ({len(exits)})")
    if not exits:
        add("  （无）")
    for e in exits:
        extra = ""
        if e.get("both_hit_same_day"):
            extra = f"  [同日双触发→{e.get('resolution_applied')}]"
        add(f"  {e['symbol']} {e.get('name',''):<8} {e['shares']:>6} 股  "
            f"{e['entry_price']:.3f} → {e['exit_price']:.3f}  "
            f"{e['reason']}  {e['realized_pnl']:+,.2f}  "
            f"持有 {e.get('holding_sessions', 0)} 日{extra}")
    add("")

    new_orders = [o for r in result.reports for o in r.new_orders]
    fills = [f for r in result.reports for f in r.entries_filled]
    nofills = [f for r in result.reports for f in r.entries_no_fill]
    add(f"NEW RECOMMENDATIONS ({len(new_orders)})   "
        f"成交 {len(fills)} / 未成交 {len(nofills)}")
    for o in new_orders:
        exp_ret = o.get("expected_return")
        add(f"  {o['symbol']} {o.get('name',''):<8} {int(o['quantity']):>6} 股  "
            f"限价 {o['limit_price']:>8.3f}  区间 "
            f"[{o.get('entry_low') or 0:.3f}, {o.get('entry_high') or 0:.3f}]  "
            f"目标* {o['target_price_at_signal']:>8.3f}  "
            f"止损* {o['stop_loss_at_signal']:>8.3f}  "
            f"预测 {('—' if exp_ret is None else f'{float(exp_ret):+.2%}'):>7}  "
            f"预估费 {_money(o.get('estimated_fee'))}")
    est_fee_total = sum(float(o.get("estimated_fee") or 0.0)
                        for o in new_orders)
    add(f"  预计总费用（按限价全额成交的最坏情况）：{_money(est_fee_total)}")
    if new_orders:
        add("  * 目标/止损按**计划价**预估。入场成交时它们会以**实际成交价**"
            "重新锚定并**锁定**"
            "（成交价 ≤ 限价 ⇒ 锁定目标必然高于成本）。")
    if not new_orders:
        notes = [n for r in result.reports for n in r.notes]
        for n in notes[:5]:
            add(f"  · {n}")
    add("")

    ovr = overrides or []
    add(f"MANUAL OVERRIDES ({len(ovr)})")
    if not ovr:
        add("  （无 —— 本实验完全按系统建议执行）")
    for o in ovr:
        add(f"  {o.get('signal_date')} {o.get('symbol')}: "
            f"系统 {o.get('system_action')} → 用户 {o.get('user_action')}"
            f"（{o.get('override_reason') or '未注明'}）")
    add("")

    add(f"FEES TODAY: {_money(result.fees)}")
    add("")
    add("ACCOUNTING CHECKS")
    add(f"  cash 对账：账本重算 "
        f"{_money(t.get('cash_from_ledger'))} == state {_money(t['cash'])}  [OK]")
    add(f"  cash ≥ 0 / reserved ≥ 0 / available ≥ 0 / 持仓 ≥ 0  [OK]")
    add(f"  组合价值 == cash + 持仓市值  [OK]")
    if preflight:
        add("")
        add("PREFLIGHT CHECKS")
        for name, c in preflight["checks"].items():
            add(f"  {name:<18} {c['status']:<5} {c['detail']}")
    for n in result.notes:
        add(f"  ! {n}")
    return "\n".join(L)


def render_start_banner(exp: dict, s_cfg: dict, preflight: Optional[dict],
                        next_exec: Optional[str] = None) -> str:
    """正式实验第一次运行时打印的横幅（spec §15）。

    这样以后任何时候翻日志，都能一眼看出正式实验从哪一刻、哪个信号日开始。
    """
    pf = preflight or {}
    bar = "=" * 45
    return "\n".join([
        bar,
        "DAILY EXIT PAPER V1 — OFFICIAL START",
        bar,
        "",
        f"Experiment:        {exp.get('experiment_id')}",
        f"Strategy:          {s_cfg['strategy_version']}",
        f"Base Strategy:     {exp.get('base_strategy')}",
        "",
        f"First Signal Date: {exp.get('first_signal_date')}",
        f"Next Execution:    {next_exec or '（下一交易日，尚未观测到）'}",
        "",
        f"Initial Capital:   {float(exp.get('initial_capital') or 0):,.2f}"
        f"   ← 已锁定",
        "",
        f"Database Last:     {pf.get('market_data_last_date')}",
        f"Calendar Last:     {pf.get('market_data_last_date')}",
        f"Feature Last:      "
        f"{(pf.get('checks', {}).get('feature_date', {}) or {}).get('detail', '—')[:60]}",
        "",
        "Positions:         0（空仓）",
        "Pending Orders:    见下方 NEW RECOMMENDATIONS",
        "",
        "Status:            CLEAN START",
        bar,
    ])


def render_daily_markdown(result, s_cfg: dict, exp: dict,
                          prices: Dict[str, float],
                          previous_value: Optional[float] = None,
                          preflight: Optional[dict] = None,
                          overrides: Optional[List[dict]] = None) -> str:
    """`reports/<实验名>/daily_<DATE>.md`（spec §26）。

    目录与标题都取自实验配置，不写死 —— 两个实验并存时，写死会让
    clean 的日报顶着 v1 的名字落盘（2026-10-08 实测如此）。

    只陈述**事实**（现金 / 持仓 / 成交 / 费用），不做任何"策略好不好"的
    结论 —— 前几天几笔的成败说明不了任何事（spec §23 / §24）。
    """
    state = result.state
    t = result.totals
    pf = preflight or {}
    exits = [e for r in result.reports for e in r.exits]
    fills = [f for r in result.reports for f in r.entries_filled]
    nofills = [f for r in result.reports for f in r.entries_no_fill]
    new_orders = [o for r in result.reports for o in r.new_orders]
    by_reason = {k: [e for e in exits if e["reason"] == k]
                 for k in ("TARGET_HIT", "STOP_HIT", "TIME_STOP")}
    equity = float(t["portfolio_value"])
    day_pnl = None if previous_value is None else equity - float(previous_value)
    cum_pnl = equity - float(state["initial_capital"])
    cum_ret = (cum_pnl / float(state["initial_capital"])
               if state["initial_capital"] else None)
    sell_fees = sum(float(e.get("fee") or 0) for e in exits)

    # 标题跟着**实验身份**走，不能写死。写死的话 clean 实验的日报
    # 抬头会是 "daily_exit_paper_v1"，而下面那行 Experiment 写的却是
    # daily_exit_paper_clean_v1 —— 同一份文件自称两个名字。
    L = [f"# {s_cfg['strategy_version']} — {result.run_date}", ""]
    L += [f"- Experiment: `{exp.get('experiment_id') or '—'}`",
          f"- System run date: {pf.get('system_run_date') or '—'}",
          f"- Market data last date: {pf.get('market_data_last_date') or result.run_date}",
          f"- Signal date: {pf.get('signal_date') or '—'}",
          f"- Execution date: "
          f"{result.reports[0].entries_filled[0]['exec_date'] if fills else '—'}",
          ""]
    L += ["## Portfolio", "",
          "| | |", "|---|---:|",
          f"| Portfolio Value | {equity:,.2f} |",
          f"| Cash | {float(t['cash']):,.2f} |",
          f"| Reserved | {float(t['reserved_cash']):,.2f} |",
          f"| Available | {float(t['available_cash']):,.2f} |",
          f"| Invested (market value) | {float(t['position_value']):,.2f} |",
          f"| Daily P&L | {'—' if day_pnl is None else f'{day_pnl:+,.2f}'} |",
          f"| Cumulative P&L | {cum_pnl:+,.2f} |",
          f"| Cumulative Return | {'—' if cum_ret is None else f'{cum_ret:+.2%}'} |",
          ""]
    L += [f"## Open Positions ({len(S.open_positions(state))} / {s_cfg['top_k']})", ""]
    if S.open_positions(state):
        L += ["| symbol | shares | entry | last | target | stop | held |",
              "|---|---:|---:|---:|---:|---:|---:|"]
        for sym, p in sorted(S.open_positions(state).items()):
            px = prices.get(sym, p.get("last_price"))
            L.append(f"| {sym} | {int(p['entry_shares'])} | "
                     f"{p['entry_price']:.3f} | "
                     f"{'—' if px is None else f'{float(px):.3f}'} | "
                     f"{p['target_price']:.3f} | {p['stop_loss']:.3f} | "
                     f"{int(p.get('holding_sessions') or 0)} |")
    else:
        L.append("（空仓）")
    L.append("")

    L += [f"## New Entries ({len(fills)})", ""]
    for f in fills:
        L.append(f"- {f['symbol']} {f['shares']} 股 @ {f['fill_price']:.3f} "
                 f"（限价 {f['limit_price']:.3f}，计划价 "
                 f"{f['planned_entry_price']:.3f}）exec {f['exec_date']}")
    if not fills:
        L.append("（无）")
    L.append("")

    L += [f"## Exits ({len(exits)})", ""]
    for k, label in (("TARGET_HIT", "Target Exits"),
                     ("STOP_HIT", "Stop Exits"),
                     ("TIME_STOP", "Time Stops")):
        L.append(f"**{label} ({len(by_reason[k])})**")
        for e in by_reason[k]:
            extra = "（同日双触发→按止损）" if e.get("both_hit_same_day") else ""
            L.append(f"- {e['symbol']} {e['shares']} 股 "
                     f"{e['entry_price']:.3f} → {e['exit_price']:.3f}"
                     f"{extra} 净 {e['realized_pnl']:+,.2f}")
        if not by_reason[k]:
            L.append("（无）")
        L.append("")

    L += [f"## No Fills ({len(nofills)})", ""]
    for f in nofills:
        L.append(f"- {f['symbol']}：{f['reason']}")
    if not nofills:
        L.append("（无）")
    L.append("")

    L += [f"## Pending Entries ({len(S.pending_list(state))})", ""]
    for o in S.pending_list(state):
        L.append(f"- {o['symbol']} {int(o['quantity'])} 股 限价 "
                 f"{o['limit_price']:.3f} 信号日 {o['signal_date']}")
    if not S.pending_list(state):
        L.append("（无）")
    L.append("")

    L += ["## Fees", "",
          f"- 今日合计：{result.fees:,.2f}（买入 {result.fees - sell_fees:,.2f} "
          f"/ 卖出 {sell_fees:,.2f}）",
          f"- 累计：{float(t.get('fees_total') or 0):,.2f}", ""]

    L += [f"## Manual Overrides ({len(overrides or [])})", ""]
    for o in (overrides or []):
        L.append(f"- {o['symbol']}：系统 {o['system_action']} → 用户 "
                 f"{o['user_action']}（{o.get('override_reason') or '未注明'}）")
    if not overrides:
        L.append("（无 —— 完全按系统建议执行）")
    L.append("")

    L += ["## Status", "",
          f"- Data Status: "
          f"{'PASS' if (pf.get('checks', {}).get('data_freshness', {}).get('status') == 'PASS') else '—'}",
          f"- Accounting Status: PASS"
          f"（cash {float(t['cash']):,.2f} == 账本重算 "
          f"{float(t.get('cash_from_ledger') or 0):,.2f}）", "",
          "> 本报告只陈述事实。前几笔的成败不构成任何策略结论"
          "（spec §23 / §24：规则固定、市场真实变化、观察结果）。", ""]
    return "\n".join(L)


def render_state(state: dict, s_cfg: dict, prices: Dict[str, float],
                 totals: Dict[str, float]) -> str:
    """`--show-state`：只看当前状态，不推进任何东西。"""
    L: List[str] = ["PAPER STATE (read-only)"]
    L.append(f"  as_of         {state.get('as_of')}")
    L.append(f"  cash          {_money(totals['cash'])}")
    L.append(f"  reserved      {_money(totals['reserved_cash'])}")
    L.append(f"  available     {_money(totals['available_cash'])}")
    L.append(f"  position      {_money(totals['position_value'])}")
    L.append(f"  equity        {_money(totals['portfolio_value'])}")
    positions = S.open_positions(state)
    L.append(f"  holdings      {len(positions)} / {s_cfg['top_k']}")
    for sym, p in sorted(positions.items()):
        L.append(f"    {sym} {int(p['entry_shares'])} 股 @ "
                 f"{p['entry_price']:.3f}  目标 {p['target_price']:.3f} / "
                 f"止损 {p['stop_loss']:.3f}  入场 {p['entry_exec_date']}")
    pend = S.pending_list(state)
    L.append(f"  pending       {len(pend)}")
    for o in pend:
        L.append(f"    {o['symbol']} {int(o['quantity'])} 股 限价 "
                 f"{o['limit_price']:.3f} 信号日 {o['signal_date']}")
    return "\n".join(L)
