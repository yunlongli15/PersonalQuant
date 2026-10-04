# Personal A-Share Quantitative Investment System

个人用 A 股低频量化投资研究与决策系统。完全本地运行，不涉及实盘交易。

## 项目目标（总览）

```
A股数据 → 数据清洗与本地数据库 → 因子计算与因子挖掘 → 机器学习 Alpha 模型
→ 新闻/公告 NLP 因子 → 历史回测 → 组合优化 → 每周/每月调仓建议
→ 具体股票与目标持仓数量 → 个人真实持仓管理 → 可视化 GUI
```

分阶段推进，每阶段验收通过后才进入下一阶段（详见
[ROADMAP.md](ROADMAP.md)）。

## 当前状态

**STEP 1 ✅ / STEP 2 ✅ / STEP 3 ✅ / STEP 4 ✅ / STEP 5 ✅ / STEP 6 ✅ /
STEP 7 ✅ / STEP 9 ✅ / STEP 10 ✅ / STEP 11 ✅ / STEP 12 ✅**
— **V1.1.0**（`cat VERSION`）。
📄 发布说明 [docs/V1_RELEASE.md](docs/V1_RELEASE.md) ｜
🔒 冻结规则 [docs/V1_FREEZE.md](docs/V1_FREEZE.md)

> 🧪 **`daily_exit_paper_v1` —— 独立前瞻实验**（V1.1.0 新增）：
> 与 monthly paper_live 完全独立的 forward 模拟盘，S3 信号 + T+1 限价入场 +
> target / stop / time-stop 出场。**交易规则已冻结**，见
> [使用说明第 10 节](docs/USER_GUIDE.md#10-daily_exit_paper_v1-前瞻实验)。
> 状态：**已就绪，等待启动**（需要明确的初始本金与起始日）。

> 📖 **使用说明书：[docs/USER_GUIDE.md](docs/USER_GUIDE.md)** —— 怎么用、
> 面板每个数字什么意思、板块交易权限、常见问题、系统边界。
>
> 📦 **数据与模型清单：[DATA.md](DATA.md)** —— 仓库里包含哪些数据、
> 哪些需要重新生成、怎么生成。
>
> 🚀 **五分钟上手**（下面「快速开始」一节）。
>
> ⚠️ 当前数据快照：行情 / 因子 / 信号 / 预测 **2026-09-17**，
> 新闻公告 2026-09-11（官方索引滞后约 5 天，界面会如实标注）。
> **本系统仅用于研究，不构成投资建议，永不自动下单。**

## 快速开始

```bash
source .venv/Scripts/activate

# ---- 每天就这两条，顺序不能反 ----
python scripts/quant/refresh_all.py            # ① 更新数据与信号（5~7 分钟）
                                               #    产出「交易计划」「今日信号」「价格预测」
python scripts/run_daily.py                    # ② 每日流水线（约 5 秒）
                                               #    前瞻记录 + 日报 + 告警

python scripts/run_daily.py --dry-run          # 只想先看检查，用这个
python scripts/system_health.py                # 系统健康
python scripts/webapp/serve.py                 # 打开界面 127.0.0.1:8765

# 其它常用
python scripts/quant/refresh_all.py --status   # 看数据新鲜度
python scripts/quant/write_recommendation_note.py --capital 66000
                                               # 单独重出建议（改资金时用）
```

**为什么要两条、为什么先 ① 后 ②**：`refresh_all.py` 更新数据与信号，
`run_daily.py` 只**读**这些数据做记录与报告 —— **它不下载行情**。先跑 ② 的话，
它会对着旧的一天做记录（这就是"日期怎么没更新"的原因）。
分工与产出详见 **[docs/USER_GUIDE.md](docs/USER_GUIDE.md) 第 1 节**（唯一权威说法）。

两者都别在开着界面时跑（DuckDB 单进程独占）。

界面里最常用的两个页面：

- **每日录入**：填「今日金额 + 今日收益」（基金）或「今日现价」（股票），
  其余（收益、万份收益、份额、持仓、浮盈）全部由系统推导；
- **交易计划**：明日买卖清单，含建议买入价 / 可接受区间 / 目标价 / 止损 /
  股数 / 预估费用，并自动**排除当前买不了的板块**（科创板需 50 万等）。

- STEP 1：Qlib 0.9.7 研究环境 + 官方 LightGBM/Alpha158 workflow 完整回测
  （基线报告 `reports/step1_qlib_baseline.md`）
- STEP 2：本地 A 股数据基础设施 —— DuckDB + Parquet canonical 层
  （日线 17.9M 行 / 证券主表 6,148 / SSE 年报 metadata 63k+）、
  按需 PDF 财务提取管线（PIT + 审计）、质量体系 16/16、
  交叉验证与 bootstrap/verify 脚本
- STEP 3：第一个低频 Alpha 策略 strategy_v1 —— 月度调仓、Alpha158+LightGBM、
  Top-20 等权、T+1 执行、严格 PIT（测试期年化 24.8%、IC 0.036、
  显著胜动量基线；报告 reports/step3_strategy_v1.md）
- STEP 4：因子研究与 Alpha Mining 平台 —— 市场数据缩放审计与逐股校准、
  31 因子研究（IC/衰减/分位/稳定性/相关性）、PIT 财务因子管线
  （lazy 年报提取 + 覆盖率报告）、factor_pack_v1、浅层表达式挖掘
  （snooping 记录）、Model A/B/C/D 消融。诚实结论：自定义技术因子与
  财务因子第一轮未能稳定超越 Alpha158 基线（报告
  reports/step4_factor_research.md / step4_model_ablation.md）
- STEP 5：新闻/公告因子系统 —— 官方交易所优先的 Provider 抽象层
  （SSE 按日全量 / SZSE 按股 / CNINFO / AkShare）、canonical 公告库
  （171k 条 2018-2026）、严格 PIT（盘后→次日）、规则事件分类（25 类）
  + LLM 层（DeepSeek 自动检测、cache、预算）、27 个新闻因子评估、
  factor_pack_news_v1、A/B/C/D/E 消融（锚点 drift 0.0000）、
  strategy_v1_news（E：0.2812/1.022 vs A：0.2475/0.943）。
  诚实结论：公告强度+风险事件与 pack_v1 组合提供边际增量；
  LLM 对比留待 API（报告 reports/step5_news_factor_evaluation.md /
  step5_news_ablation.md）
- STEP 6：组合优化与高级策略研究 —— portfolio/ 引擎（P0-P6 分配方法、
  PIT 协方差 + sanity gate、约束/回退链、T+1 执行、风险贡献、
  allocation audit）、STEP 5 增量检查（D vs B 确认新闻增量）、
  research 期 OOS walk-forward 预测、6 阶段研究（选择协议先于结果写死）、
  frozen test 单次评估、压力测试、strategy_v2 + 9 项 candidate gates +
  paper live（500k）。诚实结论：**组合优化没有带来增量，最终候选退回
  P0 等权**（research 期无任何优化器超过等权；引擎锚点 drift 0.0000）；
  strategy_v2 因 2 项 gate 未通过保持研究候选状态
  （报告 reports/step6_portfolio_optimization.md /
  step6_final_candidate.md）
- STEP 7：个人财富管理 + 本地 GUI —— 财富库（SQLite，与研究会话严格
  分离）、收益引擎（P&L 剔除外部资金流、万份收益、TWR/XIRR、净资产
  变动分解）、数据刷新管线（job store + 新鲜度面板，离线记 SKIPPED）、
  预测引擎（1D/5D/20D 条件分布，PIT）、交易计划（入场区间/目标/止损/
  手数/费用/卖出原因）、本地 Web GUI（127.0.0.1、零外部资源）、
  决策链（推荐→接受/修改/拒绝→实际成交滑点）、闭环脚本（9/9 步）
- **STEP 7 之后**（2026-09-13 起）：
  - **数据刷新到 2026-09-17** + 可复现快照更新脚本；修复上游快照引入的
    复权因子重定基准缺陷（7 只标的、23,026 行）
  - **界面全中文**（14 个页面），零 CDN、仅绑定 127.0.0.1
  - **板块交易权限**：科创板 50 万 / 创业板 10 万 / 北交所 50 万，
    交易计划**先按权限过滤再选股**，被排除标的完整列出
  - **股票专用录入**：名称/代码/买入成本价/买入日期/股数/现价 → 市值与浮盈
    （与基金「账户里有多少钱」的口径分开）
  - **交易流水记账**：转入/转出（外部资金流，从收益中剔除）、分红、费用、
    买入/卖出
  - **修掉 4 个真实 bug**：特征计算死锁（父进程先初始化 qlib → worker 挂起）、
    预测日期口径错乱（用旧信号冒充当日）、**部分产品未录入时净资产假暴跌**
    （forward-fill 修复）、费用低估（最小佣金 5 元未计）
  - **新因子挖掘（16 个微结构因子）**：涨停次数、彩票效应、偏度、
    Parkinson 波动、量能趋势等——**frozen test 中预测力延续**（与 STEP 4
    财务因子"出样本即反转"形成对比），但**加入组合未提升策略**（诚实记录，
    research candidate，未进入 strategy_v2）。报告
    `reports/step8_micro_factors.md`
  - **STEP 10：Clean Forward Holdout + Paper Live Monitoring**
    - **2024-2025 正式降级为 `HISTORICAL_TEST_OBSERVED`**（已被评估 3 次：
      STEP 6 终评、step8、step9），不再声称是 untouched test。
    - **clean forward holdout 起点 2026-09-18**，`record_only`：只记录 /
      观察 / 评估，绝不用于选因子、选模型、调参数、调阈值、调成本、
      调 top_k、调调仓频率、调优化器、调风险限制。
    - **paper live 引擎**：同一条代码路径既跑历史验证、也跑未来实盘观察。
      T 日收盘信号 → T+1 开盘成交；100 股手数；涨跌停/停牌 NO_TRADE；
      挂单机制（T+1 未开盘时挂起，下次运行按 T+1 开盘价成交）；
      **按日幂等**（重跑不重复交易）。
    - **append-only + revision_id**：已写下的观测永远不覆盖；确实遇到数据源
      bug 时必须给理由、写新 revision、保留旧版本。
    - **冻结可证明**：config / model / feature pack 的 sha256 逐日校验，
      不一致即 `DRIFT_DETECTED`；config 哈希排除 freeze 块以免自指。
    - **只监控不反馈**：strategy / model / news / data 漂移与 9 类告警
      只产生 WARNING，绝不自动修复、绝不自动减仓。
    - 历史引擎验证：24 个调仓日跑通全部 §46 检查项（T+1、手数、成本、
      无未来数据、停牌/涨跌停）。报告
      `reports/step10_forward_holdout.md` /
      `reports/paper_live_engine_validation.md`
  - **STEP 9：Incremental IC 因子选择协议**（两段，第二段是对第一段的修正）
    - **(9.1 发现)** 把候选因子对「Alpha158 + 冻结 pack」做横截面正交投影，
      残差 IC 才是它新增的信息：75 个候选里只有 4 个通过，最强的
      `limit_up_count_20` raw ICIR −0.733 → **残差 +0.001**（既有信息的
      重新包装）。同时发现 **"加入因子反而变差"统计上不成立**——S3/I/R/M/N
      五个变体在 24 个月上无法区分（p = 0.15~0.83，年化 CI 全部跨零），
      该样本能可靠检出的最小年化差异是 **41%**。报告
      `reports/step9_independent_info.md`
    - **(9.2 修正)** 残差方法有偏（R² 越高、残差越像噪声、看起来越"独立"），
      改成**直接配对比较两个模型**：`M0 = Alpha158 + pack_v1 + news`，
      `M1 = M0 + F`，评价量是逐日配对的 `ΔIC = IC1 − IC0`。4 折 walk-forward
      （train 2018-19/20/21/22 → valid 2020/21/22/23）、标签越界保护、
      关闭早停与子采样、block bootstrap 置信区间、冗余主判据改为**原始因子
      秩相关**。**诚实结果：0/20 个候选的 ΔIC 置信区间排除 0；置换重要性
      ≈ 0（模型几乎没用到这些列）；修正后的判据推翻了 9.1 的波动率结论。**
      最终 5 个候选是"待观察清单"，不是"已证明有效清单"。报告
      `reports/incremental_factor_selection_v2.md`

  - **STEP 11：个人投资终端（Streamlit）** —— 先审计既有资产代码
    （`docs/step11_existing_asset_system_audit.md`），确认 `wealth/engine.py`
    已实现 TWR/XIRR/P&L/持仓重建，于是**扩展而非重写**。
    新增：`services/`（10 个服务模块，GUI 唯一接触面）、`app/`（12 个页面的
    Streamlit 终端）、CSV 导入（幂等、不猜值、自动审计）、拆股处理、
    现金余额与对账、演示账户、备份/恢复 CLI。
    修掉 4 个真实 bug（详见 `reports/step11_investment_terminal.md`），
    其中最隐蔽的是**页面文件名遮蔽同名包**——`app/pages/paper_live.py`
    会挡住 `paper_live/` 包，Streamlit 把页面目录放进 sys.path 后
    整个 Paper Live 功能失效。
    验收 `verify_step11.py` 27/27 PASS；`pytest` 922 passed。

## 环境要求

- Windows 10/11 x64（Linux/macOS 亦可，命令略有差异）
- Python 3.12（pyqlib 0.9.7 官方 wheel 支持 cp38–cp312，**不支持 3.13**）
- git
- 磁盘空间 ≥ 10 GB（Qlib cn 数据约 3–4 GB）

## 安装方法

```bash
# 1. 创建虚拟环境（如 .venv 不存在）
py -3.12 -m venv .venv        # 或: python3.12 -m venv .venv
source .venv/Scripts/activate  # Windows Git Bash
# Linux/macOS: source .venv/bin/activate

# 2. 安装依赖（使用官方 PyPI 索引，清华镜像缺 pyqlib）
python -m pip install --upgrade pip
python -m pip install -i https://pypi.org/simple pyqlib==0.9.7 lightgbm matplotlib mlflow fire

# 3. 下载中国市场示例数据（qlib 官方 README 推荐的数据源）
#    注意：qlib 官方 CLI 数据集已暂停（详见 docs/environment_check.md），
#    官方 README 指引使用 chenditc/investment_data 社区数据源：
curl -L -o /tmp/qlib_bin.tar.gz https://github.com/chenditc/investment_data/releases/latest/download/qlib_bin.tar.gz
tar -xzf /tmp/qlib_bin.tar.gz -C qlib_data --strip-components=1
rm /tmp/qlib_bin.tar.gz
```

## 运行方法

```bash
source .venv/Scripts/activate   # 激活虚拟环境

# --- STEP 1：Qlib 环境 ---
python scripts/verify_step1.py              # 一键验证 STEP 1 环境
PYTHONIOENCODING=utf-8 MPLBACKEND=Agg MLFLOW_DISABLE_AGENT_HINT=1 MLFLOW_ALLOW_FILE_STORE=true \
    qrun config/workflow_config_lightgbm_Alpha158.yaml   # 官方 workflow（约 2 分钟）

# --- STEP 3：策略 ---
python scripts/backtest_strategy.py --strategy strategy_v1 --start 2024-01-01 --end 2025-12-31 --run-id run_001
python scripts/generate_recommendation.py --date 2026-09-04 --capital 500000   # paper live（仅研究）
python scripts/verify_step3.py              # 19 项验收

# --- STEP 2：数据基础设施 ---
python scripts/bootstrap_data.py --skip-bars # 一键重建（11 步，含质量检查与 catalog）
python scripts/verify_step2.py              # 19 项验收检查（PASS/FAIL）
python scripts/demo_financial_extraction.py # 按需年报提取 demo
python scripts/crosscheck_qlib.py           # Qlib 交叉验证

# --- STEP 4：因子研究 ---
python scripts/research_factor.py --factor roe   # 单因子研究
python scripts/research_all_factors.py           # 全因子研究 -> factor_pack_v1
python scripts/run_alpha_mining.py               # 浅层 Alpha Mining（research candidate）
python scripts/backtest_ablation.py              # Model A/B/C/D 消融
python scripts/verify_step4.py                   # 21 项验收

# --- STEP 5：新闻因子 ---
python scripts/news/update_news.py --dry-run     # provider 检查
python scripts/news/update_news.py               # 公告增量更新
python scripts/news/build_events.py              # 文档 -> 规则事件（--llm 可选）
python scripts/news/build_news_factors.py        # 评估 -> factor_pack_news_v1
python scripts/news/run_news_ablation.py         # A/B/C/D/E 消融
python scripts/news/run_news_strategy.py         # strategy_v1_news
python scripts/verify_step5.py                   # 22 项验收

# --- STEP 6：组合优化 ---
python scripts/research_portfolio.py --method gmv --period test --check-anchor
python scripts/portfolio/run_portfolio_study.py --stage all     # 6 阶段研究
python scripts/portfolio/run_stress_test.py                     # 压力测试
python scripts/portfolio/run_strategy_v2.py                     # strategy_v2 + gates
python scripts/portfolio/generate_v2_recommendation.py --capital 500000
python scripts/verify_step6.py                   # 25 项验收

# --- STEP 7：个人财富管理 + GUI ---
python scripts/wealth/init_wealth_db.py          # 初始化财富库（SQLite）
python scripts/quant/refresh_all.py --status     # 数据新鲜度面板
python scripts/quant/run_full_loop.py --demo-wealth   # 闭环端到端
python scripts/webapp/serve.py                   # GUI -> http://127.0.0.1:8765
python scripts/verify_step7.py                   # 29 项验收

# --- STEP 7 之后：数据刷新 / 建议 / 因子 ---
python scripts/quant/update_market_snapshot.py --check   # 查上游有无新快照
python scripts/quant/update_market_snapshot.py --years 2026   # 更新并重新导入
python scripts/quant/repair_factor_rebase.py     # 修复复权因子重定基准（如需要）
python scripts/quant/write_recommendation_note.py --horizon 20 --capital 66000
                                                 # 生成交易建议（含真实费用）
python scripts/quant/refresh_live_prices.py --top 30   # 当日实时价（快照未发布时）
python scripts/research_all_factors.py --run-id micro_run_001   # 75 因子研究
python scripts/portfolio/run_micro_ablation.py --variants S3,M,N  # 因子消融回测
python scripts/research_independent_info.py      # 独立信息度量（残差 IC / R²，9.1）
python scripts/run_incremental_factor_selection.py   # STEP 9 主协议（两阶段 + walk-forward）
python scripts/run_incremental_secondary.py          # ADD/REPLACE + 重要性（不参与选择）
MPLBACKEND=Agg python scripts/make_incremental_figures.py   # 8 张图
python scripts/verify_incremental_factor_selection.py        # 12 项验收
python scripts/monitor_forward_holdout.py            # 前瞻 holdout（只记录，不选择）

# --- STEP 11：个人投资终端 ---
python scripts/run_app.py                            # 终端 http://127.0.0.1:8501
python scripts/make_demo_account.py                  # 生成演示账户（独立库）
PQ_WEALTH_DB=data/wealth/demo.db python scripts/run_app.py   # 用演示库看界面
python scripts/import_portfolio.py trades.csv        # 导入成交（默认 dry-run）
python scripts/backup_portfolio.py                   # 备份个人资产数据
python scripts/verify_step11.py                      # 27 项验收

# --- STEP 12：每日自动化 ---
python scripts/run_daily.py --dry-run                # 只做检查
python scripts/run_daily.py                          # 每日流水线（14 步）
python scripts/run_daily.py --history                # 运行历史
python scripts/system_health.py                      # 15 项系统健康
python scripts/check_daily_alerts.py                 # 最近一次运行的告警
python scripts/freeze_production.py --check          # 生产冻结校验
python scripts/quarterly_review.py --quarter 2026-Q3 # 季度评审（只出报告）
python scripts/verify_step12.py                      # 24 项验收

# --- STEP 10：forward holdout + paper live ---
python scripts/paper_live/freeze.py                  # 冻结策略（只做一次）
python scripts/paper_live/freeze.py --check          # 校验冻结未被改动
# 注意：下面是 STEP 10 的**底层**引擎，日常不要直接跑 ——
# scripts/run_daily.py（STEP 12）已经把它 + 另外 13 步一起跑了
python scripts/paper_live/run_daily.py --dry-run     # 只跑 paper live 引擎（不落盘）
python scripts/paper_live/run_daily.py               # 只跑 paper live 引擎（写 forward 记录）
python scripts/paper_live/run_rebalance.py --date 2026-09-30   # 调仓日 + 买卖清单
python scripts/paper_live/audit.py                   # PIT / 数据完整性审计
python scripts/paper_live/check_alerts.py            # 告警（只报警）
python scripts/paper_live/monthly_report.py --month 2026-10    # 月度复盘
python scripts/paper_live/build_dashboard.py         # dashboard 数据层
python scripts/paper_live/validate_engine.py --n 24  # 历史引擎验证
python scripts/verify_step10.py                      # 21 项验收
python scripts/portfolio/run_micro_ablation.py --variants S3,I,R \
    --variants-file experiments/factors/independent_info/variants.json \
    --out-dir experiments/factors/independent_ablation   # 独立信息消融
python -m pytest tests/ -q                       # 全部测试（613 个）

# 运行模式：PQ_MODE=offline 只读缓存（历史回测必须用）；PQ_PDF_CACHE=1 开启 PDF 缓存
```

STEP 1 基线结果见 `reports/step1_qlib_baseline.md`；
STEP 2 数据目录见 `reports/step2_data_catalog.md`。

## 目录结构

```
PersonalQuant/
├── README.md            # 本文件
├── CLAUDE.md            # AI 协作开发规范
├── ROADMAP.md           # 阶段路线图与进度（STEP 1/2 COMPLETED）
├── pyproject.toml       # 项目元信息与依赖声明
├── personal_quant/      # 数据基础设施包（STEP 2）
│   ├── symbols.py       #   统一股票代码 600519.SH
│   ├── db.py            #   DuckDB + canonical schema
│   ├── providers/       #   Qlib baseline / SSE 年报 / AkShare+腾讯
│   ├── financial/       #   按需 PDF 提取 + PIT + 查询 API
│   ├── ingest/          #   各数据源 → canonical 导入
│   ├── storage/         #   Parquet + 审计 + 数据源注册
│   ├── repair/          #   canonical 修复管线（STEP 4 市场缩放校准）
│   ├── strategy/        #   strategy_v1（STEP 3，冻结基线）+ 特征/回测/执行引擎
│   └── quality/         #   质量检查
├── factors/             # 因子研究平台（STEP 4/5：注册/评估/选择/挖掘/报告）
│   └── microstructure.py#   微结构因子（新一批：涨停/彩票/偏度/量价…）
├── news/                # 新闻系统（STEP 5：providers/事件/PIT/LLM/聚合）
├── portfolio/           # 组合优化（STEP 6：分配/协方差/约束/风险/回测引擎）
├── wealth/              # 个人财富（STEP 7：SQLite 财富库/收益引擎/决策链）
├── services/            # 应用服务层（STEP 11：GUI 唯一接触面，10 个模块）
├── app/                 # 个人投资终端（STEP 11：Streamlit，12 个页面）
├── pipeline/            # 数据刷新管线 + 每日流水线（daily/freeze/告警/日报）
├── trade_plan/          # 交易计划引擎（入场区间/目标/止损/手数/板块权限）
├── webapp/              # 本地 Web GUI（FastAPI，仅 127.0.0.1，零 CDN）
├── config/              # 策略/组合/账户档案等运行配置
├── scripts/             # bootstrap / verify / refresh / research / demo
├── tests/               # 613 个测试
├── docs/                # 使用说明书 + schema/数据源/PIT/执行模型文档
├── data/                # canonical parquet + derived（部分入库，见 DATA.md）
├── qlib_data/           # Qlib 基线数据（git 忽略，可脚本重新下载）
├── reports/             # 实验报告
├── logs/                # 运行日志
└── .venv/               # 项目虚拟环境（git 忽略）
```

## 重要约定

- **严禁实盘交易、券商 API、自动下单**。系统只输出建议，下单全部由用户手动完成。
- 数据与模型结果仅用于研究，**不构成投资建议**；目标价/止损是模型估计，不是承诺。
- **时间口径铁律**：因子/信号/回测只用 signal date 之前的数据。
  **2024-2025 = HISTORICAL TEST**（已被评估 3 次：STEP 6 终评、step8、
  step9），不再是 untouched test，**禁止**用于选因子/调参/排序/选阈值，
  代码层面有守卫（`incremental/windows.py`）与静态扫描测试。
  因子选择只能用 **2018-2023**；干净的样本外证据来自 **2026-09-18 起**的
  forward holdout（只记录、不选择）。
- **因子选择只看增量信息**：判据是 `ΔIC = IC1 − IC0`（配对），
  不是 `IC1`，更不是组合 Sharpe。优先级 incremental IC > stability >
  independence > 可复现 > portfolio 收益；权重全部在
  `config/factor_selection_v2.yaml`。
- **DISCOVERY / SELECTION / OBSERVATION 不得混淆**：历史研究负责发现，
  validation（2018-2023）负责选择，**forward holdout（2026-09-18 起）
  只负责观察**。三者在代码层面各有一条守卫拦截越界
  （`incremental/windows.py`、`incremental/holdout.py`、
  `paper_live/config.py::FORWARD_HOLDOUT_READ_ONLY`）。
  观察结果**不反馈**到任何决策：表现差不改，表现好也不加强。
- **统计显著性铁律**：任何"某变体更好/更差"的结论都必须给出**样本量与
  可检出效应**。24 个月组合回测的年化分辨力约 ±41pp（月度超额标准差 5%），
  低于此量级的差异一律只能说"无法区分"，不得写成"更好"或"更差"。
  因子层（约 1500 只 × 72 个信号日）才有足够样本支撑结论。
- **费用口径唯一**：回测、交易计划、财富记账共用同一个成本模型
  （含 5 元最低佣金）。
- 个人财富数据（`data/wealth/`）按设计**只在本机**，不入库、不上传。
