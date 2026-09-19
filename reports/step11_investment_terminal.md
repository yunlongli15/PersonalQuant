# STEP 11 — 个人投资终端（Streamlit）

> 日期：2026-09-19 ｜ 验收：`scripts/verify_step11.py` **27/27 PASS**
> 测试：`pytest` **922 passed**（STEP 1–10 无回归）
> 审计：`docs/step11_existing_asset_system_audit.md`
> 使用说明：`docs/investment_terminal.md`

## 0. 一句话

把系统从 **Quant Research System** 升级为 **Personal Investment Terminal**：
打开界面就能看到总资产、持仓、收益、风险、策略状态、建议与新闻 ——
但**交易决定仍然由用户执行**，系统永不自动下单。

## 1. 先审计，再动手（spec §2）

审计结论：项目里**已经有一套可用的个人资产管理系统**（STEP 7），而且
spec 要求的大部分会计功能它已经实现了：

| spec 要求 | 现状 |
|---|---|
| 持仓市值 = 数量 × 现价（动态） | ✅ `engine.Holding.market_value` |
| 流水是唯一真相，持仓由它重建 | ✅ `engine.holdings_from_ledger` |
| P&L 剔除资本流 | ✅ `engine.investment_pnl`（DB 层强制外部流/内部流不变量） |
| TWR | ✅ `engine.twr` |
| XIRR | ✅ `engine.xirr` |
| benchmark | ✅ `benchmark_records` |
| 审计留痕 | ✅ `repository` 每次写入自动写 `audit_log` |
| 备份 | ✅ `db.backup` |

**因此本阶段是扩展，不是重写。** 真正的缺口只有 10 项，逐条补齐。

## 2. 冲突与决策

### 2.1 Streamlit（§3）vs 既有 FastAPI GUI（§2 要求不重复实现）

两个前端**共存，共享同一套引擎**，职责分开：

| | `webapp/`（保留） | `app/`（新增） |
|---|---|---|
| 定位 | 录入型（每日录入、流水、设置） | 终端型（仪表盘、分析、研究） |
| 页面 | 15 | 12 |

**代价如实记录**：两者在"交易流水录入"上功能重叠，未来应择一合并。
本阶段不动 `webapp/`，避免破坏 STEP 7 的 14 个页面测试。

### 2.2 不新建数据库

spec §6–§10 的表名（`personal_accounts`/`assets`/`transactions`）与现有
（`accounts`/`products`/`transactions`）语义等价，只是命名不同。
§46 要求"个人数据与市场数据逻辑分开"——**已经分开了**（SQLite vs DuckDB）。
再建一个 `portfolio.duckdb` 会重复个人数据层，与 §2 冲突。
**决策：复用 `wealth.db`，只加列（费用拆分），用 `ALTER TABLE` 幂等迁移。**

## 3. 做了什么

### 3.1 补齐的缺口

| # | 缺口 | 实现 |
|---|---|---|
| 1 | CSV 导入（§12） | `wealth/importer.py` + `scripts/import_portfolio.py` + GUI 入口 |
| 2 | 拆股/送股 | `holdings_from_ledger` 的 `split` 从**显式空操作**改成真实现（比例缩放股数与均价，总成本不变） |
| 3 | 现金余额（§14） | `engine.cash_balance`：**两种口径**（已记录 / 流水推导），差值本身是对账信号 |
| 4 | 费用拆分（§10） | `transactions` 加 `commission`/`stamp_duty`/`other_fee` 三列（幂等迁移） |
| 5 | 账本估值 | `engine.value_positions`：**流水 × 现价**，导入成交后立刻有数（原来只有快照口径，导入后显示 0） |
| 6 | 对账（§52） | `engine.reconcile` |
| 7 | 持仓一致性（§53） | `engine.position_consistency`（区分 `manual_override` 与真 `MISMATCH`） |
| 8 | demo 账户（§69） | `scripts/make_demo_account.py`，**独立演示库** |
| 9 | 备份/导出 | `scripts/backup_portfolio.py`（恢复需 `--confirm`，且先自动备份） |
| 10 | 服务层（§5/§48） | `services/` 10 个模块 |

### 3.2 服务层（GUI 的唯一接触面）

```
app/ (Streamlit 12 页面)   只做展示 / 输入 / 查询
    ↓ 只允许调用
services/                  10 个模块
    ↓ 复用（不重写）
wealth/ trade_plan/ pipeline/ factors/ portfolio/ paper_live/
```

**不自己实现 TWR/XIRR/P&L** —— 直接调 `wealth/engine.py` 里已有且经测试的
实现（§49）。`webapp/services.py` 同样是服务层，`services/` 复用它而不是
抄一遍。

### 3.3 12 个页面

仪表盘 / 持仓 / 交易流水 / 调仓建议 / 量化策略 / Paper Live / 风险 /
因子 / 新闻 / 回测 / 研究 / 设置。

全部支持 **CSV 导出**（§64）；页面顶部显示**数据时间戳**（§62）；
空数据一律显示 **NO DATA + 原因**，不是 Traceback（§60/§67）。

## 4. 修掉的 4 个真实 bug

| # | 问题 | 后果 | 发现方式 |
|---|---|---|---|
| 1 | **页面文件名遮蔽同名包**：`app/pages/paper_live.py` 挡住 `paper_live/` 包 | Streamlit 把页面目录放进 `sys.path` 后 `import paper_live` 解析到**页面文件**，整个 Paper Live 功能失效（"'paper_live' is not a package"） | 渲染仪表盘时出现意外的 Paper Live 报错 |
| 2 | `fetch_df()` 是 DuckDB API，却在 **sqlite3** 游标上调用 | 快照/流水/产品三个服务全部报 `AttributeError` | 仪表盘"每日快照 不可用" |
| 3 | 演示账户只给现金写快照 | 净值序列只剩现金，存入 30 万再买入显示成 **TWR −54%** | 演示账户渲染检查 |
| 4 | 入金当天的快照没带 `cash_flow` | 首日 P&L 把 30 万入金算成"当日收益" | 同上（P&L 铁律） |

Bug 1 最隐蔽：它只在实际用 Streamlit 跑页面时出现，静态检查完全看不出来。
修法是把页面改名为 `paper_live_monitor.py`（`st.Page` 的显示名不受影响）。

另有两处**测试自身**的问题被顺手改正：`decompose_change` 的
`reconciliation_error` 是**恒等式残差**（恒为 0），原来那条断言它非零的
测试是错的；以及 `app` 不是包，不能 `from app._shared import`。

## 5. 验收（§70）

`scripts/verify_step11.py` **27/27 PASS**，覆盖：
既有系统审计 / 账户 schema / 账本不变量 / 持仓重建 / 现金会计 / TWR / XIRR /
PnL / 基准 / 快照 / 对账 / 备份 / Portfolio API / 服务层 / GUI 启动（拒绝
非本地绑定）/ 12 个页面齐全 / 空态处理 / 建议渲染 / Paper Live 渲染 /
风险渲染 / 因子渲染 / 新闻渲染 / 数据时间戳 / 无券商 / 审计留痕 /
demo 账户 / **全量 pytest 无回归**。

## 6. 边界（如实）

1. **不连接券商、不自动下单、不涉及真实资金**（§13/§65）。
   建议页只有 **Export**，没有 Submit Order（§27）。
2. **GUI 不能修改任何冻结策略**（§55）：strategy_v1/v2、factor_pack、
   paper_live 全部只读；`config/gui.yaml` 里 `allow_freeze_change: false`。
3. **不写 forward holdout、不做任何 2026 数据选择**。
4. API key 只从环境变量读，**绝不进 `config/gui.yaml`、绝不进 git**（§47）。
5. 两个前端（FastAPI / Streamlit）功能有重叠，未合并。
6. 首个 Streamlit 版本，**大账户（数千笔流水）的页面性能未做压力测试**。
7. 演示账户的价格是**手写示例**，不是行情，也不构成任何建议。

## 7. 复现

```bash
source .venv/Scripts/activate

python scripts/make_demo_account.py                       # 造演示数据
PQ_WEALTH_DB=data/wealth/demo.db python scripts/run_app.py # 看界面
python scripts/import_portfolio.py trades.csv             # 导入成交（dry-run）
python scripts/backup_portfolio.py                        # 备份
python scripts/verify_step11.py                           # 27 项验收
python -m pytest tests/gui tests/portfolio_account -q     # 本阶段测试
```
