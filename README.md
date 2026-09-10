# Personal A-Share Quantitative Investment System

个人用 A 股低频量化投资研究与决策系统。完全本地运行，不涉及实盘交易。

## 项目目标（总览）

```
A股数据 → 数据清洗与本地数据库 → 因子计算与因子挖掘 → 机器学习 Alpha 模型
→ 新闻/公告 NLP 因子 → 历史回测 → 组合优化 → 每周/每月调仓建议
→ 具体股票与目标持仓数量 → 个人真实持仓管理 → 可视化 GUI
```

分阶段推进，**当前处于 STEP 1**，绝不超前开发。

## 当前状态

**STEP 1 ✅ / STEP 2 ✅ / STEP 3 ✅ / STEP 4 ✅ / STEP 5 ✅ / STEP 6 ✅ /
STEP 7 ✅**（详见 [ROADMAP.md](ROADMAP.md)）

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
python -m pytest tests/ -q                       # 全部测试（566 个）

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
│   ├── strategy/        #   strategy_v1（STEP 3，冻结基线）
│   └── quality/         #   16 项质量检查
├── factors/             # 因子研究平台（STEP 4/5：注册/评估/选择/挖掘/报告）
├── news/                # 新闻系统（STEP 5：providers/事件/PIT/LLM/聚合）
├── portfolio/           # 组合优化（STEP 6：分配/协方差/约束/风险/回测引擎）
├── config/              # workflow 等运行配置
├── scripts/             # bootstrap / verify / demo / crosscheck
├── tests/               # 400 个测试
├── docs/                # 数据 schema/数据源/PIT/提取/质量文档
├── data/                # RAW + parquet + duckdb（git 忽略）
├── qlib_data/           # Qlib 基线数据（git 忽略）
├── reports/             # 实验报告
├── logs/                # 运行日志
└── .venv/               # 项目虚拟环境（git 忽略）
```

## 重要约定

- 本阶段（STEP 1）仅使用 Qlib 官方示例数据与官方 workflow，不自行开发策略。
- 严禁实盘交易、券商 API、自动下单。
- 数据与模型结果仅用于研究，不构成投资建议。
