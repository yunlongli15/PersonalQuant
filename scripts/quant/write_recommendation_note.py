# -*- coding: utf-8 -*-
"""Human-readable daily recommendation note (明日推荐).

    python scripts/quant/write_recommendation_note.py
    python scripts/quant/write_recommendation_note.py --capital 100000

Writes reports/paper_live/recommendation_<as_of>.md from the latest
trade plan: what to buy, at what price, how many shares, targets/stops,
which names are blocked by board permissions, and what the data vintage
is. Research use only — never an order.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "reports" / "paper_live"


def plan_as_of_guess() -> str:
    """Signal date the plan will use (so live prices are only applied when
    they are NEWER than the signal)."""
    from pipeline.signals import signals_state

    return str(signals_state().get("as_of") or "9999-12-31")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--capital", type=float, default=None)
    ap.add_argument("--top-k", type=int, default=None)
    ap.add_argument("--risk-profile", default="balanced")
    ap.add_argument("--horizon", type=int, default=20, choices=[1, 5, 20],
                    help="预测周期（交易日）：20=月度（已验证），"
                         "5=周度（未验证）")
    ap.add_argument("--strategy", default=None,
                    help="要求信号来自这个策略（S3_v1 / S3_v2）。"
                         "默认接受当前落盘的信号；指定后不匹配就报错退出，"
                         "免得拿 A 版本的信号写出标着 B 版本的建议书。"
                         "切换信号本身要用 "
                         "`refresh_signals(strategy=...)`。")
    args = ap.parse_args()

    from pipeline import freshness
    from trade_plan.plan import (account_profile, build_trade_plan,
                                 plan_summary_by_board, save_plan,
                                 suggest_top_k)

    prof = account_profile()
    capital = args.capital or float(prof["capital"])
    top_k = args.top_k
    sug = None
    if top_k is None:
        sug = suggest_top_k(capital, args.risk_profile)
        top_k = sug["chosen_top_k"]
    # Live-price overlay: when a newer session has closed but the
    # upstream snapshot has not published it, use the fetched closes so
    # the bands/targets/stops are actionable. The ranking stays at the
    # signal date — the note states both vintages.
    live, live_date = {}, None
    lp = PROJECT_ROOT / "data" / "quant" / "live_prices.json"
    if lp.exists():
        d = json.loads(lp.read_text(encoding="utf-8"))
        live_date = d.get("price_date")
        if live_date and live_date > str(plan_as_of_guess()):
            live = {k: v["close"] for k, v in d.get("prices", {}).items()}

    plan = build_trade_plan(capital=capital, top_k=top_k,
                            risk_profile=args.risk_profile,
                            horizon=args.horizon,
                            price_overrides=live or None)
    plan["holding_period"] = (f"weekly (5 trading days)" if args.horizon == 5
                              else f"monthly ({args.horizon} trading days)")
    plan["validated"] = args.horizon == 20
    if sug:
        plan["small_capital_rule"] = {
            "rule": sug["rule"], "chosen_top_k": sug["chosen_top_k"],
            "scans": sug["scans"]}
    save_plan(plan)

    from pipeline.signals import signals_state
    st = signals_state()
    if args.strategy and st.get("strategy") != args.strategy:
        raise SystemExit(
            f"拒绝生成：落盘信号来自 {st.get('strategy')!r}，"
            f"但要求 {args.strategy!r}。先用该策略刷新信号：\n"
            f"  python -c \"from pipeline.signals import refresh_signals; "
            f"refresh_signals(strategy='{args.strategy}')\"")
    fresh = {f.domain: f for f in freshness.data_status()}
    rows = plan["rows"]
    buys = [r for r in rows if r.get("shares", 0) > 0]
    skipped = [r for r in rows if r.get("shares", 0) == 0]

    L = []
    L.append(f"# 交易建议 · 基准信号日 {plan['as_of']} · "
             f"{plan.get('holding_period')}")
    L.append("")
    # 策略版本放在最顶上（spec §十八/§二十 / PHASE 7 §十四）。同一份目录里
    # 会并存多个版本的建议书 —— 不标版本的话，事后根本分不清哪份是谁生成的。
    _uses_news = st.get("uses_news", True)
    L.append(f"> **Strategy: {st.get('strategy', '未知')}**  ")
    L.append(f"> Features: {st.get('features_label', st.get('feature_version', '—'))}  ")
    L.append(f"> News factors: {'ENABLED' if _uses_news else '**DISABLED**'}  ")
    L.append(f"> Horizon: {args.horizon} trading days  ")
    L.append(f"> Model: `{st.get('model', '—')}`")
    L.append("")
    L.append(f"生成时间: {datetime.now():%Y-%m-%d %H:%M} · "
             f"**仅供研究，不构成投资建议，系统不会自动下单**")
    L.append("")
    if not plan.get("validated", True):
        L.append("> ⚠️ **本计划为周度（5 交易日）版本，不在验证范围内。** "
                 "系统冻结的策略是月度调仓 + 20 交易日预测；周度从未回测过，"
                 "换手成本约为月度的 3 倍。信号排序用同一个冻结模型，"
                 "目标价/止损来自 5 日预测分布。**请自行判断风险。**")
    L.append("")
    L.append("## 一句话结论")
    L.append("")
    L.append(f"可用资金 **{capital:,.0f} 元**，建议买入 **{len(buys)} 只**、"
             f"合计 **{plan['total_buy_value']:,.0f} 元**"
             f"（占资金 {plan['total_buy_value']/capital:.1%}），"
             f"预留现金 {plan['remaining_cash']:,.0f} 元"
             f"（{plan['remaining_cash']/capital:.1%}）。"
             f"组合预期净收益 **{plan['expected_net_return_pct']:+.2%}**"
             f"（{plan['horizon']} 个交易日，已扣双边成本），"
             f"预期年化波动 {plan['expected_volatility']:.1%}。")
    L.append("")
    L.append("## 买入清单")
    L.append("")
    L.append("| # | 代码 | 名称 | 板块 | 现价 | **建议买入价** | "
             "可接受区间 | 股数 | 金额 | 目标价 | 止损 | **预期净收益** |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in buys:
        L.append(
            f"| {r['raw_rank']} | {r['symbol']} | {r.get('name') or ''} | "
            f"{r.get('board_name')} | {r['current_price']:.2f} | "
            f"**{r['recommended_entry_price']:.2f}** | "
            f"{r['entry_low']:.2f}–{r['entry_high']:.2f} | {r['shares']} | "
            f"{r['buy_value']:,.0f} | {r.get('target_price')} | "
            f"{r.get('stop_loss')} | "
            f"{r.get('expected_net_return', 0) or 0:+.2%} |")
    L.append("")
    L.append(f"预估交易费用 **{plan['estimated_fees']:,.0f} 元**"
             f"（佣金+印花税+过户费+滑点，与回测同一模型）。")
    L.append("")

    if skipped:
        L.append("## 本次未买入（目标金额买不起 1 手 100 股）")
        L.append("")
        L.append("| # | 代码 | 名称 | 板块 | 现价 | 1 手金额 |")
        L.append("|---|---|---|---|---|---|")
        for r in skipped:
            L.append(f"| {r['raw_rank']} | {r['symbol']} | "
                     f"{r.get('name') or ''} | {r.get('board_name')} | "
                     f"{r['current_price']:.2f} | "
                     f"{r['current_price']*100:,.0f} |")
        L.append("")
        L.append("> 小账户的固有摩擦：本金不足时高价股无法买入，"
                 "这部分资金会留在现金里。")
        L.append("")

    ex = plan.get("excluded_restricted") or []
    if ex:
        L.append("## 因交易权限被排除（信号好但暂时买不了）")
        L.append("")
        L.append("| # | 代码 | 名称 | 板块 | 门槛 | 原因 |")
        L.append("|---|---|---|---|---|---|")
        for d in ex[:15]:
            L.append(f"| {d.get('raw_rank')} | {d['symbol']} | "
                     f"{d.get('name') or ''} | {d.get('board_name')} | "
                     f"{d.get('capital_required', 0)/10000:.0f} 万元 | "
                     f"{d.get('reason', '')} |")
        L.append("")
        L.append("> 资金达标并开通对应板块后，这些标的会自动回到候选池。")
        L.append("")

    L.append("## 板块分布")
    L.append("")
    L.append("| 板块 | 门槛 | 只数 | 可买 | 金额 |")
    L.append("|---|---|---|---|---|")
    for d in plan_summary_by_board(plan):
        L.append(f"| {d['board_name']} | "
                 f"{d['capital_required']/10000:.0f} 万元 | {d['n']} | "
                 f"{d['n_buyable']} | {d['value']:,.0f} |")
    L.append("")

    if plan.get("small_capital_rule"):
        rule = plan["small_capital_rule"]
        L.append("## 持仓数如何确定（小资金适配）")
        L.append("")
        L.append(f"规则：{rule['rule']} → **K = {rule['chosen_top_k']}**。"
                 f"该规则只依据资金与 100 股手数算术，"
                 f"不使用任何收益或回测数字。")
        L.append("")
        L.append("| K | 投入比例 | 可买只数 |")
        L.append("|---|---|---|")
        for s in rule["scans"]:
            mark = " ←选中" if s["top_k"] == rule["chosen_top_k"] else ""
            L.append(f"| {s['top_k']}{mark} | {s['invested']:.1%} | "
                     f"{s['n_positions']} |")
        L.append("")

    L.append("## 数据与模型")
    L.append("")
    L.append(f"- 信号：{st.get('model_version', 'strategy_v2/S3')}，"
             f"信号日 **{st.get('as_of')}**（全市场 "
             f"{st.get('n_symbols')} 只打分）")
    if plan.get("price_source", "").startswith("live"):
        L.append(f"- 价格：**{live_date} 收盘**（实时抓取，"
                 f"{len(plan.get('live_prices', {}))} 只）—— "
                 f"**排序基于 {st.get('as_of')}，价格基于 {live_date}**；"
                 f"上游快照尚未发布 {live_date} 的完整数据，"
                 f"因此排序比价格旧一个交易日。")
    else:
        # 没有实时价 = 用的是信号日收盘。若信号日不是今天，入场区间多半
        # 已经不是能成交的价格了，必须说出来（2026-09-22 用户实际反馈）。
        _age = (datetime.now().date() - datetime.strptime(
            str(plan["as_of"]), "%Y-%m-%d").date()).days
        if _age >= 1:
            L.append(
                f"- ⚠ **价格是 {plan['as_of']} 的收盘价（{_age} 天前）**，"
                f"入场区间可能已经失效。先跑 "
                f"`python scripts/quant/refresh_live_prices.py` 取当前价、"
                f"再重新生成计划；或直接以实际盘口为准。")
    L.append(f"- 分配方法：{plan['allocation_method']}"
             f"（{plan['optimizer_status']}）")
    L.append(f"- 数据新鲜度：" + "，".join(
        f"{k} {v.status}" for k, v in fresh.items()))
    stale = [k for k, v in fresh.items()
             if v.status in ("STALE", "MISSING")]
    if stale:
        L.append(f"- ⚠ **注意：{', '.join(stale)} 数据过期**，"
                 f"建议先运行 `python scripts/quant/refresh_all.py`。")
    L.append("")
    L.append("## 执行提醒")
    L.append("")
    L.append("1. 在**可接受区间内**成交即可，不必强求计划价。")
    L.append("2. 涨跌停/停牌时系统不会追单（与回测一致）。")
    L.append("3. 目标价与止损是模型估计，**不是保证**；"
             "达到止损请按纪律执行。")
    L.append("4. 成交后请在 GUI 的 Transactions 录入真实价格与费用，"
             "系统会统计实际滑点。")
    L.append("")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "" if args.horizon == 20 else f"_h{args.horizon}"
    p = OUT_DIR / f"recommendation_{plan['as_of']}{suffix}.md"
    p.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {p}")
    print(f"买入 {len(buys)} 只 / {plan['total_buy_value']:,.0f} 元；"
          f"排除受限 {len(ex)} 只；买不起 {len(skipped)} 只")
    return 0


if __name__ == "__main__":
    sys.exit(main())
