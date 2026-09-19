# STEP 11 既有个人资产系统审计

> 目的（spec §2）：在写任何新 GUI 之前，先查清项目里**已经有什么**，
> 优先复用，不重新实现同一功能。
> 本文记录：找到了什么 / 可复用 / 需重构 / 冲突。

## 0. 结论先行

**项目里已经有一套可用的个人资产管理系统**（STEP 7 交付），而且它已经实现了
本阶段 spec 要求的大部分会计功能：

| spec 要求 | 现状 | 位置 |
|---|---|---|
| §9 持仓市值 = 数量 × 现价（动态） | ✅ 已有 | `wealth/engine.py::Holding.market_value` |
| §13 交易流水 = 唯一真相，持仓由它重建 | ✅ 已有 | `engine.holdings_from_ledger` |
| §14 资金流水 / 外部流 | ✅ 已有 | `EXTERNAL_FLOW_TYPES` + `net_external_flow` |
| §15 P&L 剔除资本流 | ✅ 已有 | `engine.investment_pnl` |
| §16 TWR | ✅ 已有 | `engine.twr` / `twr_period_return` |
| §16 XIRR | ✅ 已有 | `engine.xirr` |
| §17 benchmark | ✅ 已有 | `benchmark_records` + 视图 |
| §44 审计留痕 | ✅ 已有 | `repository._insert/_update/_delete` **强制**写 `audit_log` |
| §54 备份 | ✅ 已有 | `wealth/db.py::backup` |

**因此本阶段的正确做法是扩展，不是另起一套。** 下面列出必须新增的部分。

---

## 1. 找到了什么

### 1.1 `wealth/` —— 个人财富核心（8 个模块，STEP 7）

数据库：`data/wealth/wealth.db`（SQLite，WAL，`foreign_keys=ON`）

**13 张表 + 4 个视图**：

| 表 | 用途 |
|---|---|
| `platforms` | 渠道（天天盈 / 支付宝 / 券商 / 现金…） |
| `accounts` | 账户（属于某个平台） |
| `products` | 产品/标的（`product_type` 含 stock/etf/fund/cash…） |
| `transactions` | **流水（真相来源）**：txn_type / units / price / amount / fee / cash_flow |
| `daily_snapshots` | 每日快照（units / nav / market_value / cash_flow） |
| `positions` | 物化持仓（as_of / units / avg_cost / realized / unrealized） |
| `income_records` | 万份收益记录 |
| `benchmark_records` | 基准收盘 |
| `recommendations` / `decisions` / `executions` | 决策链 |
| `audit_log` | **所有写入自动留痕** |
| `wealth_categories` | 分类 |
| 视图 | `cash_flows` / `fees` / `dividends` / `v_latest_values` |

**关键不变量（DB 层强制，不是文档约定）**：`create_transaction` 校验
外部流（deposit/withdrawal/transfer_in/out）必须 `cash_flow != 0`，
内部流（buy/sell/subscribe/redeem/dividend/fee/split/adjustment）必须
`cash_flow == 0`。这正是 spec §15"不能因为存入 10 万就算当天赚了 10 万"的
实现。

**`wealth/engine.py` 已实现的会计**：`investment_pnl`、`net_external_flow`、
`holdings_from_ledger`、`xirr`、`twr`、`twr_period_return`、`annualize`、
`decompose_change`、`value_series`（**前向填充**，避免"部分产品没录入导致
净资产假暴跌"）、`performance`、`portfolio_summary`、`positions_at`、
`write_positions`、万份收益（`effective_units` / `money_market_day` /
`seven_day_annualized`）。

**`wealth/service.py`**：`record_daily_update`（用户只填金额+收益，其余推导）、
`record_stock_update`（股票专用：成本价/股数/买入日期）、`latest_summary`、
`decompose_period`。

**`wealth/repository.py`**：全部写操作都过 `_insert/_update/_delete`，
**自动写 audit_log**；`update_transaction` / `delete_transaction` **强制要求
reason**。`export_csv` / `export_json` 已可导出 10 张表。

### 1.2 `webapp/` —— 已有 GUI（FastAPI，STEP 7）

- `app.py`：**15 个页面路由 + 7 个 JSON 接口**，仅绑定 127.0.0.1。
- `pages.py`（42KB）：15 个页面渲染函数；**有 AST 测试**
  （`test_pages_module_has_no_financial_arithmetic`）断言它不 import
  numpy/pandas/wealth.engine/pipeline/trade_plan/portfolio —— 即"UI 不算金融"。
- `services.py`（13.7KB）：**已经是 view-model 服务层**，15 个函数，
  全部防御式返回 `{"available": False, "reason": ...}`。
- `svg.py`：手写 SVG 图表（零外部资源，有测试断言无 CDN）。

### 1.3 其它可直接读的数据

| 数据 | 位置 |
|---|---|
| 交易建议（权威） | `data/quant/trade_plans/trade_plan_<date>.json` + `.csv`（30 字段/行） |
| 信号 | `data/quant/signals_latest.parquet`（symbol/prediction/raw_rank/name） |
| 数据新鲜度 | `pipeline/freshness.py::data_status()` |
| 新闻事件 | `data/derived/news/news_events.parquet`（176,763 行 × 18 列，含 direction/importance/novelty/risk） |
| 因子排行榜 | `experiments/factors/{factor_run_001,micro_run_001}/leaderboard.csv`（19 列） |
| 策略回测 | `experiments/strategy_v1/run_*/summary.json`、`experiments/portfolio/*/metrics.json` |
| Paper live | `forward_holdout/dashboard/forward_dashboard.{parquet,json}`（**生成器已存在，文件尚未生成**） |
| 板块权限 | `trade_plan/boards.py::eligibility` |

---

## 2. 必须新增的（真正的缺口）

| # | 缺口 | 说明 |
|---|---|---|
| 1 | **CSV 导入**（§12） | `wealth/` 只有导出，**没有导入**。需要 `import_portfolio.py` + GUI 入口 |
| 2 | **拆股/送股**（§50 `test_split`） | `split` 是合法 txn_type，但 `holdings_from_ledger` 里是**显式空操作**（"units adjusted by the caller; never compute"）—— 没有任何实现 |
| 3 | **现金余额 API**（§14） | 现金被建模成 `product_type='cash'` 的产品，没有独立的余额函数 |
| 4 | **费用拆分**（§10） | 现有 `fee` 是聚合值；spec 要 commission / stamp_duty / other_fee 分列 |
| 5 | **面向 GUI 的新闻读取器** | 只有 `freshness.news_latest()` 碰过 news_events |
| 6 | **因子排行榜读取器** | leaderboard.csv 无读取封装 |
| 7 | **对账**（§52） | 现金+各类资产 = 总资产的检查不存在 |
| 8 | **demo 账户**（§69） | 不存在 |
| 9 | **Streamlit** | 全仓库 0 处引用；**本阶段已安装 1.64.0** |
| 10 | **`services/` 统一层**（§5/§48） | `webapp/services.py` 已存在，但只服务 FastAPI |

---

## 3. 冲突与决策

### 3.1 冲突：spec §3 要求 Streamlit，但项目已有 FastAPI GUI（§2 要求不重复实现）

**事实**：`webapp/` 有 15 个页面、7 个 JSON 接口、14 个页面测试、
以及"UI 不算金融"的 AST 测试守卫，是**可用且被测试覆盖的**。

**决策：两个前端共存，共享同一套引擎，职责分开。**

| | `webapp/`（FastAPI，保留） | `app/`（Streamlit，新增） |
|---|---|---|
| 定位 | **录入型**：每日录入、交易流水、设置 | **终端型**：仪表盘、分析、研究浏览 |
| 页面 | 15（表单为主） | 12（图表为主） |
| 状态 | **不动**，保留全部测试 | 新增 |

**理由**：① spec 明确要求 Streamlit；② 直接删/改 `webapp/` 会破坏 STEP 7 的
14 个页面测试，属于"重构没坏的东西"；③ 两者共享 `wealth/engine.py` 与
`services/`，**没有第二套会计实现**。

**代价（如实记录）**：两个前端在"交易流水录入"上有功能重叠。未来应择一
合并；本阶段不做，避免动 STEP 7 的测试基线。

### 3.2 冲突：spec §6–§10 的会计模型 vs 现有 `wealth` 模型

**事实**：spec 想要 `personal_accounts / asset_classes / assets / positions / transactions`；
现有是 `platforms / accounts / products / positions / transactions`。

**映射关系**（语义等价，只是命名不同）：

| spec | 现有 | 说明 |
|---|---|---|
| `personal_accounts` | `accounts` | 已有 |
| `asset_classes` | `products.product_type` + `models.PRODUCT_TYPES` | 枚举已存在（cash/money_fund/bond_fund/index_fund/qdii/stock/etf/gold/other） |
| `assets` | `products`（含 ticker / name / currency / market） | 已有；`status` 有，`exchange`/`source` 可从 ticker 后缀推 |
| `positions` | `positions` + `engine.holdings_from_ledger` | 已有，且市值动态计算 |
| `transactions` | `transactions` | 已有；差 fee 拆分（见 §2 缺口 4） |

**决策：不新建表，不新建数据库。** 直接复用 `wealth.db`。
理由：§46 说"个人账户数据与 market data 逻辑分开" —— 已经分开了
（SQLite vs DuckDB）。再建一个 `portfolio.duckdb` 会**重复**个人数据层，
与 §2 冲突。唯一需要的是**加列**（费用拆分），用 `ALTER TABLE` 迁移，
不动既有列、不动既有不变量。

### 3.3 `services/` 与 `webapp/services.py` 的关系

**决策**：`services/` 是新的统一服务层，**复用** `webapp/services.py`
（import 并再导出），只新增缺口部分。

不把 `webapp/services.py` 搬过来，是因为那会改动被 14 个测试覆盖的文件
（CLAUDE.md 铁律：不重构没坏的东西）。**代价**：shared 的 view-model
暂时"住"在 webapp 里，命名上不理想。已记入后续清理项。

---

## 4. 复用清单（本阶段直接用，不重写）

- 会计：`wealth/engine.py` 全部（TWR / XIRR / P&L / 持仓重建 / 万份收益）
- 写入与审计：`wealth/repository.py`（自动 audit_log + reason 强制）
- 备份：`wealth/db.py::backup`
- 视图模型：`webapp/services.py` 的 15 个函数
- 计划与权限：`trade_plan/plan.py`、`trade_plan/boards.py`
- 新鲜度：`pipeline/freshness.py`
- 图表：`webapp/svg.py`（Streamlit 版本改用 Altair/内置，不引 CDN）

## 5. 本阶段不做（避免越界）

- 不改 `strategy_v1` / `strategy_v2` / `factor_pack` / `paper_live` 冻结配置
- 不写 forward holdout
- 不接券商、不自动下单
- 不把 API key 放进 GUI 配置
