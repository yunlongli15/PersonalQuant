# -*- coding: utf-8 -*-
"""One-off: translate the GUI strings to Chinese.

    python scripts/webapp/translate_ui.py [--check]

Exact-match replacements only (no regex), applied to webapp/*.py. The
routes and Python identifiers are untouched — only user-visible text.
Run with --check to list any remaining English labels.
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

WEBAPP = Path(__file__).resolve().parents[2] / "webapp"

MAP = {
    # 导航
    '("/*", "*")': '("/*", "*")',
    '"/", "Dashboard"': '"/", "总览"',
    '"/wealth/overview", "Wealth"': '"/wealth/overview", "资产总览"',
    '"/wealth/daily-update", "Daily Update"': '"/wealth/daily-update", "每日录入"',
    '"/wealth/positions", "Positions"': '"/wealth/positions", "持仓明细"',
    '"/wealth/transactions", "Transactions"': '"/wealth/transactions", "交易流水"',
    '"/wealth/performance", "Performance"': '"/wealth/performance", "收益表现"',
    '"/wealth/accounts", "Accounts"': '"/wealth/accounts", "账户总览"',
    '"/quant/signals", "Signals"': '"/quant/signals", "今日信号"',
    '"/quant/forecasts", "Forecasts"': '"/quant/forecasts", "价格预测"',
    '"/quant/trade-plan", "Trade Plan"': '"/quant/trade-plan", "交易计划"',
    '"/quant/paper-live", "Paper Live"': '"/quant/paper-live", "模拟盘"',
    '"/quant/research", "Research"': '"/quant/research", "研究状态"',
    '"/data/status", "Data Status"': '"/data/status", "数据状态"',
    '"/settings", "Settings"': '"/settings", "设置"',
    # 页面标题
    'layout("Dashboard"': 'layout("总览"',
    'layout("Wealth"': 'layout("资产总览"',
    'layout("Daily Update"': 'layout("每日录入"',
    'layout("Positions"': 'layout("持仓明细"',
    'layout("Transactions"': 'layout("交易流水"',
    'layout("Performance"': 'layout("收益表现"',
    'layout("Accounts"': 'layout("账户总览"',
    'layout("Signals"': 'layout("今日信号"',
    'layout("Forecasts"': 'layout("价格预测"',
    'layout("Stock"': 'layout("个股详情"',
    'layout("Trade Plan"': 'layout("交易计划"',
    'layout("Research"': 'layout("研究状态"',
    'layout("Paper Live"': 'layout("模拟盘"',
    'layout("Data Status"': 'layout("数据状态"',
    'layout("Settings"': 'layout("设置"',
    # 标题 / 区块
    '"Total Net Worth"': '"总资产"',
    '"Today P&L"': '"今日盈亏"',
    '"YTD P&L"': '"今年盈亏"',
    '"Cumulative Return"': '"累计收益率"',
    '"Net worth"': '"资产净值"',
    '"Asset allocation"': '"资产配置"',
    '"Cumulative investment P&L"': '"累计投资收益"',
    '"By platform"': '"按平台分布"',
    '"Today\\\'s quant signals"': '"今日量化信号"',
    '"Data status"': '"数据状态"',
    '"Net Worth"': '"净资产"',
    '"Invested Capital"': '"累计投入本金"',
    '"Total P&L"': '"累计盈亏"',
    '"Income / Fees"': '"分红收入 / 费用"',
    '"Net worth curve"': '"资产净值曲线"',
    '"Allocation"': '"资产配置"',
    '"Holdings"': '"持仓明细"',
    '"Daily Return"': '"当日收益率"',
    '"Month P&L"': '"本月盈亏"',
    '"TWR / XIRR"': '"时间加权 / 资金加权收益率"',
    '"Net worth change decomposition"': '"资产变动拆解"',
    '"万份收益 (money-market income)"': '"万份收益"',
    '"每日录入"': '"每日录入"',
    '"Today\\\'s signals"': '"今日信号"',
    '"Price history"': '"历史价格"',
    '"Forecast by horizon"': '"分周期预测"',
    '"Orders (recommendation only)"': '"建议下单清单（仅供参考，系统不会下单）"',
    '"Candidate Gates"': '"候选门槛"',
    '"Frozen Pipeline"': '"冻结流程"',
    '"Frozen pipeline"': '"冻结流程"',
    '"Last job runs"': '"最近任务运行"',
    '"Transaction cost model (shared)"': '"交易成本模型（全局共用）"',
    '"Portfolio / strategy_v2"': '"组合配置 / strategy_v2"',
    '"Platforms"': '"平台"',
    '"Backup"': '"备份"',
    '"Stock"': '"个股详情"',
    '"Signals"': '"今日信号"',
    '"Accounts"': '"账户总览"',
    '"Trade Plan"': '"交易计划"',
    '"Paper live"': '"模拟盘"',
    '"Trade plan"': '"交易计划"',
    '"Forecasts"': '"价格预测"',
    '"Capital"': '"可投入资金"',
    '"Total Buy Value"': '"买入金额合计"',
    '"Estimated Fees"': '"预估交易费用"',
    '"Expected Net Return"': '"预期净收益"',
    '"Frozen Test Sharpe"': '"冻结检验 Sharpe"',
    '"Frozen Test Ann."': '"冻结检验 年化"',
    '"Frozen Test MDD"': '"冻结检验 最大回撤"',
    # KPI 副标题
    '"investment P&L (flows excluded)"': '"投资收益（已剔除本金进出）"',
    '"year to date"': '"年初至今"',
    '"flows excluded"': '"已剔除本金进出"',
    '"on capital"': '"占资金比例"',
    # 表格表头
    '["domain", "latest", "expected", "status",\n                           "note"]':
        '["数据域", "最新", "应有", "状态", "说明"]',
    '["domain", "latest", "expected", "status",\n                             "note"]':
        '["数据域", "最新", "应有", "状态", "说明"]',
    '["#", "symbol", "name", "signal"]': '["#", "代码", "名称", "信号分"]',
    '["name", "type", "units", "nav", "value", "weight"]':
        '["名称", "类型", "份额", "净值", "市值", "占比"]',
    '["name", "type", "as of", "units", "nav", "value", "avg cost",\n         "unrealized"]':
        '["名称", "类型", "数据日期", "份额", "净值", "市值", "成本", "浮动盈亏"]',
    '["date", "product", "type", "units", "price", "amount", "fee",\n         "cash flow"]':
        '["日期", "产品", "类型", "份额", "价格", "金额", "费用", "资金流"]',
    '["date", "product", "daily income", "per 10,000", "annualized",\n         "method"]':
        '["日期", "产品", "当日收益", "万份收益", "年化", "口径"]',
    '["platform", "kind", "account", "products", "value"]':
        '["平台", "类型", "账户", "产品数", "市值"]',
    '["rank", "symbol", "name", "signal"]': '["排名", "代码", "名称", "信号分"]',
    '["symbol", "name", "1D exp/P(up)", "5D exp/P(up)",\n                       "20D exp/P(up)"]':
        '["代码", "名称", "1日 预期/上涨概率", "5日 预期/上涨概率", '
        '"20日 预期/上涨概率"]',
    '["horizon", "expected", "5–95% interval", "P(up)",\n                         "trend", "n obs"]':
        '["周期", "预期收益", "5–95%区间", "上涨概率", "趋势", "样本数"]',
    '["symbol", "name", "board", "#", "last",\n                         "plan price", "entry band", "shares", "value",\n                         "target", "stop", "exp", "note"]':
        '["代码", "名称", "板块", "排名", "现价", "建议买入价", "可接受区间", '
        '"股数", "金额", "目标价", "止损", "预期收益", "备注"]',
    '["symbol", "name", "board", "#", "门槛(元)",\n                             "原因"]':
        '["代码", "名称", "板块", "排名", "门槛(元)", "原因"]',
    '["gate", "result"]': '["门槛", "结果"]',
    '["symbol", "action", "shares", "target weight",\n                           "price", "industry"]':
        '["代码", "操作", "股数", "目标权重", "价格", "行业"]',
    '["job", "status", "finished", "took", "detail"]':
        '["任务", "状态", "完成时间", "耗时", "说明"]',
    '["item", "value"]': '["项目", "取值"]',
    '["platform", "kind", "status"]': '["平台", "类型", "状态"]',
    # 状态标签
    '"✓ OK"': '"✓ 正常"',
    '"⚠ DATA STALE"': '"⚠ 数据过期"',
    '"✗ missing"': '"✗ 缺失"',
    '"— not computed"': '"— 未计算"',
    '"no rows"': '"暂无数据"',
    '"no data yet"': '"暂无数据"',
    # 说明文字
    '"as of "': '"数据日期 "',
    'f"as of {esc(': 'f"数据日期 {esc(',
    '"wealth database: "': '"财富数据库："',
    '"no signal snapshot yet — run "': '"尚无信号快照 —— 请运行 "',
    '"Daily Update page or scripts/wealth/init_wealth_db.py."':
        '"每日录入页面，或 scripts/wealth/init_wealth_db.py。"',
    '"Enter today\\\'s amount per product. Income, "':
        '"每个产品填入今日金额即可。收益、"',
    '"no forecasts yet — run forecast_refresh"': '"尚无预测 —— 请运行 forecast_refresh"',
    '"no portfolio snapshot yet"': '"尚无组合快照"',
    '"no paper-live run yet"': '"尚无模拟盘运行记录"',
    '"allocation = "': '"分配方法 = "',
    '"estimated volatility "': '"预期波动 "',
    '"positions · signal "': '"只持仓 · 信号 "',
    '"never an order — accept/modify/reject is yours"':
        '"仅为建议，绝不自动下单——是否采纳由你决定"',
    '"refresh with "': '"刷新命令："',
    '"offline runs are recorded SKIPPED, never as success."':
        '"离线运行时任务记为 SKIPPED，绝不记为成功。"',
    '"one model for backtests, trade plans and wealth accounting — "':
        '"回测、交易计划、财富记账共用同一模型 —— "',
    '"rate changes live in config/strategy_v1.yaml"':
        '"费率在 config/strategy_v1.yaml 中修改"',
    '"allocation method: "': '"分配方法："',
    '"writes backup/wealth_*.db and never uploads anything"':
        '"写入 backup/wealth_*.db，绝不上传任何数据"',
    '"platform kind"': '"平台类型"',
    '"status: "': '"状态："',
    '"not a live strategy. Selection used research 2018-2021 + "':
        '"不是实盘策略。选择只用了 research 2018-2021 + "',
    '"validation 2022-2023 only; the frozen test was evaluated "':
        '"validation 2022-2023；冻结检验只评估一次，"',
    '"once and never used for selection."': '"从未用于选择。"',
    '"selection used research 2018-2021 + "': '"选择只用了 research 2018-2021 + "',
    '"estimates from the conditional distribution of realized "':
        '"估计值来自已实现收益的条件分布 —— "',
    '"returns — not promises"': '"是模型估计，不是承诺"',
    '"price history (CNY) — historical data only"':
        '"历史收盘价（元）—— 仅历史数据"',
    '"close (CNY) — historical data only"': '"历史收盘价（元）—— 仅历史数据"',
    '"by category"': '"按资产类别"',
    '"market value by platform (CNY)"': '"各平台市值（元）"',
    '"net worth (CNY)"': '"资产净值（元）"',
    '"cumulative investment P&L (CNY)"': '"累计投资收益（元）"',
    '"external cash flow is signed "': '"外部资金流带符号 "',
    '"(deposit +, withdrawal −); buy/sell are internal and must "':
        '"（转入为正、转出为负）；买卖是内部变动，"',
    '"not carry one"': '"不应带外部资金流"',
    '"reconciliation error "': '"对账差额 "',
    '"(must be 0)"': '"（应为 0）"',
    '" (100-share lots)"': '"（100 股整数倍）"',
    '"never an order"': '"绝不自动下单"',
    '"recommendation only"': '"仅供参考"',
    '"engine offline"': '"引擎离线"',
}

# 追加：正则兜底（用于跨行的 f-string 片段）
REGEX_MAP = [
    (r'"Today\\\'s quant signals"', '"今日量化信号"'),
    (r'"management · {esc\(', '"管理 · {esc('),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    files = ["pages.py", "app.py", "svg.py"]
    total = 0
    for name in files:
        p = WEBAPP / name
        if not p.exists():
            continue
        src = p.read_text(encoding="utf-8")
        before = src
        for en, zh in MAP.items():
            if en in src:
                src = src.replace(en, zh)
                total += 1
        if src != before:
            p.write_text(src, encoding="utf-8")
            print(f"  {name}: translated")

    if args.check:
        print("\n--- 剩余疑似英文标签 ---")
        pat = re.compile(r'"[A-Za-z][A-Za-z /()%\-\.]{3,40}"')
        for name in files:
            p = WEBAPP / name
            if not p.exists():
                continue
            for i, line in enumerate(p.read_text(encoding="utf-8")
                                     .splitlines(), 1):
                if line.strip().startswith("#"):
                    continue
                for m in pat.findall(line):
                    if any(k in m for k in ("http", "utf-8", "svg", "path",
                                            "text/", "chart", "axis",
                                            "badge", "card", "banner",
                                            "grid", "kpi", "note", "table",
                                            "line", "fill", "stroke")):
                        continue
                    print(f"  {name}:{i}: {m}")
    print(f"\nreplacements applied: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
