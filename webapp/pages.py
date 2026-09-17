# -*- coding: utf-8 -*-
"""HTML rendering (STEP 7F). Formatting only — all values arrive from
webapp/services.py. No external assets, so the UI works offline."""

from __future__ import annotations

from typing import Dict, List, Optional

from . import svg

CSS = """
:root{--bg:#0f1419;--panel:#161c23;--ink:#e6edf3;--muted:#8b98a5;
--line:#242c36;--ok:#3fb950;--warn:#d29922;--bad:#f85149;--accent:#58a6ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.5 "Segoe UI",system-ui,-apple-system,sans-serif}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
header{display:flex;align-items:center;gap:18px;padding:12px 20px;
background:var(--panel);border-bottom:1px solid var(--line);
position:sticky;top:0;z-index:10;flex-wrap:wrap}
header .brand{font-weight:600;letter-spacing:.3px}
nav{display:flex;gap:14px;flex-wrap:wrap}
nav a{color:var(--muted)}
nav a.active{color:var(--ink);font-weight:600}
main{padding:20px;max-width:1400px;margin:0 auto}
.grid{display:grid;gap:16px}
.cols-4{grid-template-columns:repeat(auto-fit,minmax(210px,1fr))}
.cols-2{grid-template-columns:repeat(auto-fit,minmax(420px,1fr))}
.card{background:var(--panel);border:1px solid var(--line);
border-radius:10px;padding:16px}
.card h2{margin:0 0 12px;font-size:15px;color:var(--muted);
font-weight:600;text-transform:uppercase;letter-spacing:.6px}
.kpi{font-size:26px;font-weight:600;margin:4px 0}
.kpi.small{font-size:19px}
.pos{color:var(--ok)}.neg{color:var(--bad)}.muted{color:var(--muted)}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:7px 8px;text-align:right;border-bottom:1px solid var(--line)}
th:first-child,td:first-child,th.l,td.l{text-align:left}
th{color:var(--muted);font-weight:500;position:sticky;top:56px;
background:var(--panel)}
tr:hover td{background:#1b232c}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;
font-size:12px;border:1px solid var(--line)}
.badge.ok{color:var(--ok);border-color:#1f4d29}
.badge.warn{color:var(--warn);border-color:#5c4512}
.badge.bad{color:var(--bad);border-color:#5c1f1c}
.chart{width:100%;height:auto;background:transparent}
.chart-title{fill:var(--muted);font-size:12px}
.axis{fill:var(--muted);font-size:10px}
.grid{stroke:var(--line);stroke-width:1}
.donut-center{fill:var(--ink);font-size:16px;font-weight:600}
form.stack{display:grid;gap:10px;max-width:560px}
label{display:grid;gap:4px;font-size:13px;color:var(--muted)}
input,select,button{padding:8px 10px;border-radius:6px;
border:1px solid var(--line);background:#0d1117;color:var(--ink);
font-size:14px}
button{background:var(--accent);color:#06121f;font-weight:600;
border:none;cursor:pointer;padding:10px 16px}
button.secondary{background:#21262d;color:var(--ink)}
.note{color:var(--muted);font-size:12px;margin-top:8px}
.banner{padding:10px 14px;border-radius:8px;margin-bottom:14px;
border:1px solid var(--line);background:var(--panel)}
.banner.warn{border-color:#5c4512;color:var(--warn)}
.banner.bad{border-color:#5c1f1c;color:var(--bad)}
footer{color:var(--muted);font-size:12px;padding:22px 20px;
text-align:center}
"""

#: 界面中文名（内部枚举值保持不变，只影响显示）
PRODUCT_TYPE_CN = {
    "cash": "现金", "money_fund": "货币基金", "bond_fund": "债券基金",
    "index_fund": "指数基金", "qdii": "QDII 基金", "stock": "股票",
    "etf": "ETF", "gold": "黄金", "other": "其他",
}
PLATFORM_KIND_CN = {
    "fund_platform": "基金平台", "bank": "银行", "broker": "券商",
    "cash": "现金", "other": "其他",
}

NAV = [
    ("/", "总览"),
    ("/wealth/overview", "资产总览"),
    ("/wealth/daily-update", "每日录入"),
    ("/wealth/positions", "持仓明细"),
    ("/wealth/transactions", "交易流水"),
    ("/wealth/performance", "收益表现"),
    ("/wealth/accounts", "账户总览"),
    ("/quant/signals", "今日信号"),
    ("/quant/forecasts", "价格预测"),
    ("/quant/trade-plan", "交易计划"),
    ("/quant/paper-live", "模拟盘"),
    ("/quant/research", "研究状态"),
    ("/data/status", "数据状态"),
    ("/settings", "设置"),
]


def esc(s) -> str:
    return (str("" if s is None else s).replace("&", "&amp;")
            .replace("<", "&lt;").replace(">", "&gt;"))


def money(v, digits: int = 2) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):,.{digits}f}"
    except (TypeError, ValueError):
        return esc(v)


def pct(v, digits: int = 2) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v)*100:.{digits}f}%"
    except (TypeError, ValueError):
        return esc(v)


def signed_class(v) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "muted"
    return "pos" if f > 0 else ("neg" if f < 0 else "muted")


def layout(title: str, active: str, body: str) -> str:
    nav = "".join(
        f'<a href="{href}" class="{"active" if href == active else ""}">'
        f'{esc(label)}</a>' for href, label in NAV)
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · PersonalQuant</title><style>{CSS}</style></head>
<body><header><span class="brand">PersonalQuant</span>
<nav>{nav}</nav></header><main>{body}</main>
<footer>本地运行 · 仅研究用途 · 不构成投资建议 · 无自动下单</footer>
</body></html>"""


def kpi(label: str, value: str, sub: str = "", cls: str = "") -> str:
    return (f'<div class="card"><h2>{esc(label)}</h2>'
            f'<div class="kpi {cls}">{value}</div>'
            f'<div class="note">{esc(sub)}</div></div>')


def table(headers: List[str], rows: List[List[str]],
          left_cols: Optional[List[int]] = None) -> str:
    left = set(left_cols or [0])
    head = "".join(
        f'<th class="{"l" if i in left else ""}">{esc(h)}</th>'
        for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join(
            f'<td class="{"l" if i in left else ""}">{c}</td>'
            for i, c in enumerate(r)) + "</tr>" for r in rows)
    if not rows:
        body = (f'<tr><td class="l muted" colspan="{len(headers)}">'
                f'暂无数据</td></tr>')
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def not_available(vm: Dict) -> str:
    return (f'<div class="banner warn">{esc(vm.get("reason", "暂无数据"))}'
            f'</div>')


# ---------------------------------------------------------------------------
# pages
# ---------------------------------------------------------------------------

def dashboard(wealth: dict, signals: dict, data: dict) -> str:
    body = []
    if not wealth.get("available"):
        body.append(f'<div class="banner warn">财富数据库：'
                    f'{esc(wealth.get("reason"))}</div>')
    else:
        body.append('<div class="grid cols-4">'
                    + kpi("总资产", money(wealth["net_worth"]),
                          f'数据日期 {esc(wealth.get("as_of") or "—")}')
                    + kpi("今日盈亏", money(wealth["day_pnl"]),
                          "投资收益（已剔除本金进出）",
                          signed_class(wealth["day_pnl"]))
                    + kpi("今年盈亏", money(wealth["year_pnl"]),
                          "年初至今", signed_class(wealth["year_pnl"]))
                    + kpi("累计收益率", pct(wealth.get("twr")),
                          f'TWR · XIRR {pct(wealth.get("mwr_xirr"))}')
                    + "</div>")
        body.append('<div class="grid cols-2" style="margin-top:16px">')
        body.append('<div class="card"><h2>资产净值</h2>'
                    + svg.line_chart([{"name": "资产净值",
                                       "points": wealth["curve_points"]}],
                                     title="资产净值（元）")
                    + "</div>")
        body.append('<div class="card"><h2>资产配置</h2>'
                    + svg.donut(list(wealth["by_category"].items()),
                                title="按资产类别")
                    + "</div></div>")
        body.append('<div class="grid cols-2" style="margin-top:16px">'
                    '<div class="card"><h2>累计投资收益</h2>'
                    + svg.line_chart([{"name": "P&L",
                                       "points": wealth["pnl_points"]}],
                                     title="累计投资收益（元）")
                    + "</div>")
        body.append('<div class="card"><h2>按平台分布</h2>'
                    + svg.bar_chart([k for k, _ in
                                     sorted(wealth["by_platform"].items(),
                                            key=lambda kv: -kv[1])],
                                    [v for _, v in
                                     sorted(wealth["by_platform"].items(),
                                            key=lambda kv: -kv[1])],
                                    title="各平台市值（元）")
                    + "</div></div>")

    # quant signals
    body.append('<div class="card" style="margin-top:16px">'
                '<h2>今日量化信号</h2>')
    if not signals.get("available"):
        body.append(not_available(signals))
    else:
        rows = [[f'{r.get("raw_rank")}', esc(r.get("symbol")),
                 esc(r.get("name")), f'{r.get("prediction"):+.4f}']
                for r in signals["rows"][:10]]
        body.append(table(["#", "代码", "名称", "信号分"], rows,
                          left_cols=[0, 1, 2]))
        body.append(f'<div class="note">数据日期 {esc(signals.get("as_of"))} · '
                    f'{signals.get("n_symbols")} symbols scored · '
                    f'<a href="/quant/signals">all signals</a></div>')
    body.append("</div>")

    # data status
    body.append('<div class="card" style="margin-top:16px">'
                '<h2>数据状态</h2>')
    if not data.get("available"):
        body.append(not_available(data))
    else:
        rows = []
        for r in data["rows"]:
            badge = {"OK": '<span class="badge ok">✓ OK</span>',
                     "STALE": '<span class="badge warn">⚠ DATA STALE</span>',
                     "MISSING": '<span class="badge bad">✗ missing</span>',
                     "UNKNOWN": '<span class="badge">— not computed</span>'} \
                .get(r["status"], esc(r["status"]))
            rows.append([esc(r["domain"]), esc(r["latest"] or "—"),
                         esc(r["expected"] or "—"), badge,
                         esc(r.get("detail") or "")])
        body.append(table(["数据域", "最新", "应有", "状态", "说明"], rows, left_cols=[0, 1, 2, 4]))
    body.append("</div>")
    return layout("总览", "/", "".join(body))


def wealth_overview(vm: dict) -> str:
    body = ['<h2 style="margin-top:0">资产总览</h2>']
    if not vm.get("available"):
        body.append(f'<div class="banner warn">{esc(vm.get("reason"))}'
                    f'<div class="note">Add products and today\'s amounts '
                    f'in <a href="/wealth/daily-update">Daily Update</a>.'
                    f'</div></div>')
        return layout("资产总览", "/wealth/overview", "".join(body))
    body.append('<div class="grid cols-4">'
                + kpi("净资产", money(vm["net_worth"]),
                      f'数据日期 {esc(vm.get("as_of") or "—")}')
                + kpi("累计投入本金", money(vm["invested_capital"]))
                + kpi("累计盈亏", money(vm["total_pnl"]), "已剔除本金进出",
                      signed_class(vm["total_pnl"]))
                + kpi("分红收入 / 费用", f'{money(vm["income"])} / '
                      f'{money(vm["fees"])}')
                + "</div>")
    body.append('<div class="grid cols-2" style="margin-top:16px">'
                '<div class="card"><h2>资产净值曲线</h2>'
                + svg.line_chart([{"name": "net worth",
                                   "points": vm["curve_points"]}],
                                 title="资产净值（元）")
                + "</div><div class=\"card\"><h2>资产配置</h2>"
                + svg.donut(list(vm["by_category"].items()),
                            title="按资产类别") + "</div></div>")
    rows = [[esc(h["name"]), esc(h["product_type"]),
             money(h["units"], 2), money(h["nav"], 4),
             money(h["market_value"]), pct(h["weight"])]
            for h in vm["holdings"]]
    body.append('<div class="card" style="margin-top:16px">'
                '<h2>持仓明细</h2>'
                + table(["名称", "类型", "份额", "净值", "市值", "占比"],
                        rows, left_cols=[0, 1]) + "</div>")
    return layout("资产总览", "/wealth/overview", "".join(body))


def daily_update_page(products: List[dict], platforms: List[dict],
                      product_types: List[str], as_of: str,
                      result: Optional[dict] = None) -> str:
    """每日录入：日期 + 渠道 + 今日金额 + 今日收益。

    用户只做两件事：选渠道（已有的选，没有的当场新建）、抄平台上显示的
    两个数字。收益/万份收益/份额/持仓由系统推导，并与用户填的收益对账。
    """
    body = ['<h2 style="margin-top:0">每日录入</h2>']
    if result:
        if result.get("ok"):
            body.append(
                f'<div class="banner">已保存 {esc(result.get("n"))} 条'
                f'（{esc(result.get("as_of"))}）'
                + "".join(f'<div class="note">· {esc(w)}</div>'
                          for w in (result.get("warnings") or []))
                + "</div>")
        else:
            body.append(f'<div class="banner bad">'
                        f'{esc(result.get("error"))}</div>')
    body.append('<div class="note">只需填两个数字：<b>今日金额</b>'
                '（账户里现在有多少钱）和 <b>今日收益</b>（平台 App 上显示的'
                '当日收益，选填）。收益、万份收益、份额、持仓由系统推导；'
                '转入/转出请记在「交易流水」，不要填在这里。</div>')

    form = ['<form method="post" action="/wealth/daily-update">',
            '<div class="card" style="margin-top:12px">',
            '<h2>① 今日账户</h2>',
            f'<label style="max-width:240px">日期'
            f'<input type="date" name="as_of" value="{esc(as_of)}"></label>']
    if not products:
        form.append('<div class="note">还没有任何产品 —— 用下面的'
                    '「② 新建产品」添加第一个。</div>')
    else:
        form.append('<table><thead><tr>'
                    '<th class="l">渠道</th><th class="l">产品</th>'
                    '<th class="l">类型</th><th>上次金额</th>'
                    '<th>今日金额</th><th>今日收益(元)</th>'
                    '</tr></thead><tbody>')
        for p in products:
            ptype = PRODUCT_TYPE_CN.get(p["product_type"],
                                        p["product_type"])
            form.append(
                f'<tr><td class="l">{esc(p["platform"])}</td>'
                f'<td class="l">{esc(p["name"])}</td>'
                f'<td class="l">{esc(ptype)}</td>'
                f'<td>{esc(p.get("last_value") or "—")}</td>'
                f'<td><input name="amount_{p["product_id"]}" '
                f'inputmode="decimal" placeholder="今日金额" '
                f'style="width:130px"></td>'
                f'<td><input name="income_{p["product_id"]}" '
                f'inputmode="decimal" placeholder="选填" '
                f'style="width:110px"></td></tr>')
        form.append('</tbody></table>')
    form.append('<div style="margin-top:14px">'
                '<button type="submit">保存今日数据</button></div>'
                '</div>')

    opts = "".join(
        f'<option value="{esc(x["name"])}">{esc(x["name"])}'
        f'（{esc(PLATFORM_KIND_CN.get(x["kind"], x["kind"]))}）</option>'
        for x in platforms)
    type_opts = "".join(
        f'<option value="{t}">{esc(PRODUCT_TYPE_CN.get(t, t))}</option>'
        for t in product_types)
    form.append(
        '<div class="card" style="margin-top:16px">'
        '<h2>② 新建产品（首次录入时用）</h2>'
        '<table><thead><tr><th class="l">渠道（已有）</th>'
        '<th class="l">或新建渠道</th><th class="l">产品名称</th>'
        '<th class="l">类型</th><th>金额</th><th>今日收益</th>'
        '</tr></thead><tbody><tr>'
        f'<td class="l"><select name="new_platform">{opts}</select></td>'
        '<td class="l"><input name="new_platform_name" '
        'placeholder="新渠道名"></td>'
        '<td class="l"><input name="new_product_name" '
        'placeholder="如：债券基金A"></td>'
        f'<td class="l"><select name="new_product_type">{type_opts}</select>'
        '</td>'
        '<td><input name="new_amount" inputmode="decimal" '
        'placeholder="今日金额" style="width:120px"></td>'
        '<td><input name="new_income" inputmode="decimal" '
        'placeholder="选填" style="width:100px"></td>'
        '</tr></tbody></table>'
        '<div class="note">渠道：下拉里选已有的；若要新建，填右边那格'
        '（会自动创建该渠道）。</div>'
        '<div style="margin-top:14px">'
        '<button type="submit">保存今日数据</button></div>'
        '</div></form>')
    body.append("".join(form))
    return layout("每日录入", "/wealth/daily-update", "".join(body))


def positions_page(rows: List[dict]) -> str:
    body = ['<h2 style="margin-top:0">持仓明细</h2>',
            '<div class="card">']
    body.append(table(
        ["名称", "类型", "数据日期", "份额", "净值", "市值", "成本", "浮动盈亏"],
        [[esc(r["name"]), esc(r["product_type"]), esc(r["as_of"]),
          money(r["units"]), money(r["nav"], 4), money(r["market_value"]),
          money(r["avg_cost"], 4), money(r["unrealized_pnl"])]
         for r in rows], left_cols=[0, 1, 2]))
    body.append("</div>")
    return layout("持仓明细", "/wealth/positions", "".join(body))


def transactions_page(rows: List[dict]) -> str:
    body = ['<h2 style="margin-top:0">交易流水</h2>',
            '<div class="card">']
    body.append(table(
        ["日期", "产品", "类型", "份额", "价格", "金额", "费用", "资金流"],
        [[esc(r["txn_date"]), esc(r["product_name"]), esc(r["txn_type"]),
          money(r["units"]), money(r["price"], 4), money(r["amount"]),
          money(r["fee"]), money(r["cash_flow"])] for r in rows],
        left_cols=[0, 1, 2]))
    body.append('<div class="note">external cash flow is signed '
                '(deposit +, withdrawal −); buy/sell are internal and must '
                'not carry one</div></div>')
    return layout("交易流水", "/wealth/transactions", "".join(body))


def performance_page(vm: dict, income: List[dict],
                     decomposition: Optional[dict] = None) -> str:
    body = ['<h2 style="margin-top:0">收益表现</h2>']
    if not vm.get("available"):
        body.append(not_available(vm))
        return layout("收益表现", "/wealth/performance", "".join(body))
    body.append('<div class="grid cols-4">'
                + kpi("当日收益率", pct(vm.get("daily_return")))
                + kpi("本月盈亏", money(vm.get("month_pnl")),
                      "", signed_class(vm.get("month_pnl")))
                + kpi("今年盈亏", money(vm.get("year_pnl")),
                      "", signed_class(vm.get("year_pnl")))
                + kpi("时间加权 / 资金加权收益率",
                      f'{pct(vm.get("twr"))} / {pct(vm.get("mwr_xirr"))}')
                + "</div>")
    if decomposition:
        body.append('<div class="card" style="margin-top:16px">'
                    '<h2>资产变动拆解</h2>')
        rows = [[esc(k), money(v)] for k, v in
                [("External Contributions", decomposition["external_contributions"]),
                 ("Investment P&L", decomposition["investment_pnl"]),
                 ("Dividends", decomposition["dividends"]),
                 ("Fees", -decomposition["fees"]),
                 ("Withdrawals", -decomposition["withdrawals"]),
                 ("Net Change", decomposition["net_change"])]]
        body.append(table([f'{esc(decomposition["start"])} → '
                           f'{esc(decomposition["end"])}', "amount"], rows))
        body.append(f'<div class="note">reconciliation error '
                    f'{money(decomposition["reconciliation_error"], 6)} '
                    f'(must be 0)</div></div>')
    body.append('<div class="card" style="margin-top:16px">'
                '<h2>万份收益 (money-market income)</h2>')
    body.append(table(
        ["日期", "产品", "当日收益", "万份收益", "年化", "口径"],
        [[esc(r["income_date"]), esc(r["product_name"]),
          money(r["daily_income"]), money(r["income_per_10000"], 4),
          pct(r["annualized_yield"]), esc(r["calculation_method"])]
         for r in income], left_cols=[0, 1]))
    body.append("</div>")
    return layout("收益表现", "/wealth/performance", "".join(body))


def accounts_page(rows: List[dict]) -> str:
    body = ['<h2 style="margin-top:0">账户总览</h2>', '<div class="card">',
            table(["平台", "类型", "账户", "产品数", "市值"],
                  [[esc(r["platform"]), esc(r["kind"]), esc(r["account"]),
                    str(r["n_products"]), money(r["value"])] for r in rows],
                  left_cols=[0, 1, 2]), "</div>"]
    return layout("账户总览", "/wealth/accounts", "".join(body))


def signals_page(vm: dict) -> str:
    body = ['<h2 style="margin-top:0">Today\'s signals</h2>']
    if not vm.get("available"):
        body.append(not_available(vm))
    else:
        body.append(f'<div class="note">数据日期 {esc(vm.get("as_of"))} · '
                    f'model {esc(vm.get("model_version"))} · '
                    f'{vm.get("n_symbols")} symbols · ranking is the frozen '
                    f'S3 signal; the UI never re-orders it</div>')
        body.append('<div class="card" style="margin-top:12px">')
        body.append(table(
            ["排名", "代码", "名称", "信号分"],
            [[str(r["raw_rank"]), esc(r["symbol"]), esc(r.get("name")),
              f'{r["prediction"]:+.4f}'] for r in vm["rows"]],
            left_cols=[0, 1, 2]))
        body.append("</div>")
    return layout("今日信号", "/quant/signals", "".join(body))


def forecasts_page(vm: dict) -> str:
    body = ['<h2 style="margin-top:0">价格预测</h2>']
    if not vm.get("available"):
        body.append(not_available(vm))
        return layout("价格预测", "/quant/forecasts", "".join(body))
    model = vm.get("model", {})
    body.append(f'<div class="note">{esc(model.get("method", ""))} · '
                f'{esc(model.get("base_model", ""))} · horizons '
                f'{esc(model.get("horizons"))} · 数据日期 '
                f'{esc(vm.get("as_of"))}</div>')
    rows = vm["rows"]
    by_symbol: Dict[str, dict] = {}
    for r in rows:
        by_symbol.setdefault(r["symbol"], {"name": r.get("name")})[
            f'h{r["horizon"]}'] = r
    table_rows = []
    for sym, d in by_symbol.items():
        cells = [esc(sym), esc(d.get("name"))]
        for h in (1, 5, 20):
            r = d.get(f"h{h}")
            cells.append(f'{pct(r["expected_return"])} / '
                         f'{pct(r["p_up"], 0)}' if r else "—")
        table_rows.append(cells)
    body.append('<div class="card" style="margin-top:12px">')
    body.append(table(["代码", "名称", "1日 预期/上涨概率", "5日 预期/上涨概率", "20日 预期/上涨概率"], table_rows, left_cols=[0, 1]))
    body.append('<div class="note">estimates from the conditional '
                'distribution of realized returns — not promises</div>'
                "</div>")
    return layout("价格预测", "/quant/forecasts", "".join(body))


def symbol_page(vm: dict) -> str:
    body = [f'<h2 style="margin-top:0">{esc(vm.get("symbol"))} '
            f'{esc(vm.get("name") or "")}</h2>']
    if not vm.get("available"):
        body.append(f'<div class="banner warn">no forecast for '
                    f'{esc(vm.get("symbol"))} yet</div>')
        return layout("个股详情", "/quant/signals", "".join(body))
    hist = vm.get("history", [])
    if hist:
        body.append('<div class="card"><h2>历史价格</h2>'
                    + svg.line_chart([{"name": "close", "points": hist}],
                                     title="历史收盘价（元）—— 仅历史数据")
                    + "</div>")
    rows = [[str(h["horizon"]) + "D", pct(h["expected_return"]),
             pct(h["q05"]) + " … " + pct(h["q95"]),
             pct(h["p_up"], 0), esc(h["trend"]), str(h["n_obs"])]
            for h in sorted(vm["horizons"], key=lambda x: x["horizon"])]
    body.append('<div class="card" style="margin-top:16px">'
                '<h2>分周期预测</h2>'
                + table(["周期", "预期收益", "5–95%区间", "上涨概率", "趋势", "样本数"], rows) + "</div>")
    return layout("个股详情", "/quant/signals", "".join(body))


def trade_plan_page(vm: dict) -> str:
    body = ['<h2 style="margin-top:0">交易计划</h2>']
    if not vm.get("available"):
        body.append(not_available(vm))
        body.append(f'<div class="note">Generate one with '
                    f'<code>python scripts/quant/refresh_all.py --only '
                    f'portfolio_refresh</code></div>')
        return layout("交易计划", "/quant/trade-plan", "".join(body))
    body.append('<div class="grid cols-4">'
                + kpi("可投入资金", money(vm["capital"]),
                      f'{esc(vm["frequency"])} · {esc(vm["risk_profile"])}')
                + kpi("买入金额合计", money(vm["total_buy_value"]),
                      f'{pct(vm["total_buy_value"]/vm["capital"])} invested')
                + kpi("预估交易费用", money(vm["estimated_fees"]),
                      f'cash residual {money(vm["remaining_cash"])}')
                + kpi("预期净收益",
                      money(vm["expected_net_return_value"]),
                      pct(vm["expected_net_return_pct"]) + " on capital",
                      signed_class(vm["expected_net_return_value"]))
                + "</div>")
    body.append(f'<div class="note">allocation = '
                f'{esc(vm["allocation_method"])} '
                f'({esc(vm["optimizer_status"])}) · expected volatility '
                f'{pct(vm.get("expected_volatility"))} · '
                f'{vm["n_positions"]} positions · signal '
                f'{esc(vm.get("signal_version"))} · never an order — '
                f'accept/modify/reject is yours</div>')
    rows = []
    for r in vm["rows"]:
        badge = esc(r.get("board_name") or "")
        if r.get("can_buy") is False:
            badge = f'<span class="badge bad">{badge} 不可买</span>'
        elif "临界" in (r.get("restriction_reason") or ""):
            badge = f'<span class="badge warn">{badge} 临界</span>'
        note = ""
        if r.get("shares", 0) == 0:
            note = "买不起1手"
        rows.append([
            esc(r["symbol"]), esc(r.get("name")), badge,
            str(r.get("raw_rank")),
            money(r["current_price"]), money(r["recommended_entry_price"]),
            f'{money(r["entry_low"])}–{money(r["entry_high"])}',
            str(r["shares"]), money(r["buy_value"]),
            money(r.get("target_price")), money(r.get("stop_loss")),
            pct(r.get("expected_return")), note])
    body.append('<div class="card" style="margin-top:16px"><h2>建议下单清单'
                '（仅供参考）</h2>'
                + table(["代码", "名称", "板块", "排名", "现价", "建议买入价", "可接受区间", "股数", "金额", "目标价", "止损", "预期净收益", "备注"], rows,
                        left_cols=[0, 1, 2])
                + "</div>")
    ex = vm.get("excluded_restricted") or []
    if ex:
        exrows = [[esc(d["symbol"]), esc(d.get("name")),
                   esc(d.get("board_name")), str(d.get("raw_rank")),
                   money(d.get("capital_required"), 0),
                   esc(d.get("reason"))] for d in ex[:20]]
        body.append('<div class="card" style="margin-top:16px">'
                    '<h2>因交易权限被排除（未占用资金）</h2>'
                    + table(["代码", "名称", "板块", "排名", "门槛(元)", "原因"], exrows, left_cols=[0, 1, 2, 5])
                    + '<div class="note">这些标的信号很好但账户暂时买不了；'
                      '开通对应板块后会自动回到候选池</div></div>')
    return layout("交易计划", "/quant/trade-plan", "".join(body))


def research_page(vm: dict) -> str:
    body = ['<h2 style="margin-top:0">研究状态</h2>',
            '<div class="banner">status: <b>RESEARCH CANDIDATE</b> — '
            'not a live strategy. Selection used research 2018-2021 + '
            'validation 2022-2023 only; the frozen test was evaluated '
            'once and never used for selection.</div>']
    m = vm.get("test_metrics", {})
    body.append('<div class="grid cols-4">'
                + kpi("冻结检验 Sharpe", f'{m.get("sharpe", float("nan")):.3f}'
                      if m else "—", "2024-2025")
                + kpi("冻结检验 年化", pct(m.get("annualized_return"))
                      if m else "—")
                + kpi("冻结检验 最大回撤", pct(m.get("max_drawdown"))
                      if m else "—")
                + kpi("候选门槛",
                      f'{sum(1 for v in vm.get("gates", {}).values() if v)}'
                      f'/{len(vm.get("gates", {}))}'
                      if vm.get("gates") else "—",
                      "gates are recorded, never rewritten")
                + "</div>")
    if vm.get("gates"):
        rows = [[esc(k), '<span class="badge ok">PASS</span>' if v else
                 '<span class="badge bad">FAIL</span>']
                for k, v in vm["gates"].items()]
        body.append('<div class="card" style="margin-top:16px">'
                    '<h2>候选门槛</h2>'
                    + table(["门槛", "结果"], rows) + "</div>")
    body.append('<div class="card" style="margin-top:16px">'
                '<h2>冻结流程</h2>'
                '<div class="note">signal: strategy_v2 / S3 '
                '(Alpha158 + factor_pack_v1 + news) · allocation: '
                'equal weight · top_k 20 · cash 5% · monthly · '
                'max weight 10% · industry cap 20% · '
                'strategy_v1 and all frozen packs are unmodified.</div>'
                "</div>")
    return layout("研究状态", "/quant/research", "".join(body))


def paper_live_page(vm: dict) -> str:
    body = ['<h2 style="margin-top:0">模拟盘</h2>',
            '<div class="note">research simulation only — no broker '
            'connection, no orders</div>']
    if not vm.get("available"):
        body.append(not_available(vm))
    else:
        body.append('<div class="card" style="margin-top:12px">')
        rows = [[esc(r.get("symbol")), esc(r.get("action")),
                 money(r.get("shares")), money(r.get("target_weight"), 4),
                 money(r.get("price")), esc(r.get("industry"))]
                for r in vm["rows"]]
        body.append(table(["代码", "操作", "股数", "目标权重", "价格", "行业"], rows, left_cols=[0, 1, 5]))
        body.append(f'<div class="note">{esc(vm.get("path"))}</div></div>')
    return layout("模拟盘", "/quant/paper-live", "".join(body))


def data_page(vm: dict) -> str:
    body = ['<h2 style="margin-top:0">数据状态</h2>']
    if not vm.get("available"):
        body.append(not_available(vm))
    else:
        if vm["stale"]:
            body.append('<div class="banner warn">⚠ DATA STALE — '
                        + esc(", ".join(r["domain"] for r in vm["stale"]))
                        + '</div>')
        rows = []
        for r in vm["rows"]:
            badge = {"OK": '<span class="badge ok">✓ OK</span>',
                     "STALE": '<span class="badge warn">⚠ DATA STALE</span>',
                     "MISSING": '<span class="badge bad">✗ missing</span>',
                     "UNKNOWN": '<span class="badge">— not computed</span>'} \
                .get(r["status"], esc(r["status"]))
            rows.append([esc(r["domain"]), esc(r["latest"] or "—"),
                         esc(r["expected"] or "—"), badge,
                         esc(r.get("detail") or "")])
        body.append('<div class="card">'
                    + table(["数据域", "最新", "应有", "状态", "说明"], rows, left_cols=[0, 1, 2, 4])
                    + "</div>")
        job_rows = [[esc(j.get("job_name")), esc(j.get("status")),
                     esc(j.get("finished_at")),
                     f'{j.get("duration_s"):.1f}s'
                     if j.get("duration_s") is not None else "—",
                     esc((j.get("error") or j.get("detail") or "")[:160])]
                    for j in vm.get("jobs", [])]
        body.append('<div class="card" style="margin-top:16px">'
                    '<h2>最近任务运行</h2>'
                    + table(["任务", "状态", "完成时间", "耗时", "说明"],
                            job_rows, left_cols=[0, 1, 2, 4]) + "</div>")
        body.append('<div class="note">Refresh with '
                    '<code>python scripts/quant/refresh_all.py</code>. '
                    'Offline runs are recorded SKIPPED, never as success.'
                    "</div>")
    return layout("数据状态", "/data/status", "".join(body))


def settings_page(vm: dict) -> str:
    body = ['<h2 style="margin-top:0">设置</h2>']
    cost = vm.get("cost_model", {})
    body.append('<div class="card"><h2>交易成本模型（全局共用）</h2>'
                + table(["项目", "取值"],
                        [[esc(k), money(v, 6)] for k, v in cost.items()])
                + '<div class="note">one model for backtests, trade plans '
                  'and wealth accounting — rate changes live in '
                  'config/strategy_v1.yaml</div></div>')
    p = vm.get("portfolio", {})
    body.append('<div class="card" style="margin-top:16px">'
                '<h2>组合配置 / strategy_v2</h2>'
                + table(["项目", "取值"],
                        [[esc(k), esc(v)] for k, v in
                         list(p.get("constraints", {}).items())])
                + f'<div class="note">allocation method: '
                  f'{esc(vm.get("strategy_v2", {}).get("allocation_method"))}'
                  f' · top_k {esc(vm.get("strategy_v2", {}).get("top_k"))}'
                  f'</div></div>')
    body.append('<div class="card" style="margin-top:16px">'
                '<h2>平台</h2>'
                + table(["平台", "类型", "状态"],
                        [[esc(r["name"]), esc(r["kind"]), esc(r["status"])]
                         for r in vm.get("platforms", [])], left_cols=[0, 1, 2])
                + "</div>")
    body.append('<div class="card" style="margin-top:16px">'
                '<h2>备份</h2><form method="post" action="/settings/backup">'
                '<button type="submit">Back up wealth database</button>'
                '</form><div class="note">writes backup/wealth_*.db and '
                'never uploads anything</div></div>')
    return layout("设置", "/settings", "".join(body))
