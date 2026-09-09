# ROADMAP — Personal A-Share Quantitative Investment System

每个阶段只有在验收标准全部满足后才标记 COMPLETED。
每次完成一个阶段后，先停下来汇报，未经允许不自动开始下一阶段。

## STEP 1: Establish Qlib research environment

> 目标：在本机建立稳定、可重复的 Qlib 量化研究环境，使用 Qlib 官方中国 A 股
> 示例数据，完整运行一次官方 LightGBM + Alpha158 workflow 和回测。

状态：**COMPLETED**（2026-09-05）

### 做了什么

- 检查机器环境（Windows 11、i5-14600KF 20 线程、32GB 内存、RTX 4070 Ti），
  写入 `docs/environment_check.md`。
- 建立项目目录结构（README / CLAUDE.md / ROADMAP / pyproject.toml / config /
  scripts / tests / docs / data / qlib_data / reports / logs）。
- 因系统 Python 3.13 无 pyqlib wheel，通过 winget 用户级安装 Python 3.12，
  在项目内创建 `.venv` 虚拟环境（不触碰系统 Python）。
- 安装 pyqlib 0.9.7（官方 PyPI）、lightgbm、matplotlib、mlflow、fire，
  并将 pandas 固定在 2.2.3（qlib 0.9.7 与 pandas 3.x 不兼容）。
- 下载中国市场示例数据：qlib 官方 CLI 数据集已按官方声明暂停，且其回退数据包
  （SunsetWolf v2/latest）实测缺少 Alpha158 必需的 `vwap` 字段；按官方 README
  指引改用社区数据源 chenditc/investment_data（release 2026-09-04，538 MB，
  SHA256 校验一致），解压到项目 `qlib_data/`。日历 2000-01-04 ~ 2026-09-04，
  6,148 个 instrument，字段含 open/high/low/close/volume/amount/vwap/adjclose/
  factor/change。
- 编写 `tests/test_qlib_data.py`：验证 init / 交易日历 / instrument 列表 /
  个股日线读取 / 时间索引 / 数据完整性。
- 复制官方 workflow 配置到 `config/workflow_config_lightgbm_Alpha158.yaml`
  （仅把 provider_uri 指向本项目 `qlib_data/cn_data`，其余与官方完全一致），
  完整运行 LightGBM + Alpha158 workflow 与回测。
- 生成 `reports/step1_qlib_baseline.md` 基线报告；日志存于
  `logs/step1_qlib_workflow.log`。
- 编写 `scripts/verify_step1.py` 一键验证脚本（PASS/FAIL 输出）。
- git init、.gitignore（排除 venv/qlib_data/logs/缓存等）、首次 commit。

### 使用环境

- Windows 11 Pro 23H2；Intel i5-14600KF（14C/20T）；32GB RAM；RTX 4070 Ti
- Python 3.12.x（用户级安装）→ 项目虚拟环境 `.venv`
- pyqlib 0.9.7 + lightgbm 4.7.0（CPU 版，workflow 用 20 线程）+ mlflow 3.16 + pandas 2.2.3
- 中国市场数据：`qlib_data/`（1d 频率，chenditc/investment_data 2026-09-04）

### 基线结果（官方 workflow，详见 reports/step1_qlib_baseline.md）

- 训练：2008–2014；验证：2015–2016；测试/回测：2017-01-01 ~ 2020-08-01
- IC 0.047 / ICIR 0.382 / RankIC 0.049
- 回测（topk=50，含双边成本）：超额年化 11.06%、IR 1.31、最大回撤 -8.6%
- 期末账户 2.073 亿（初始 1 亿）；总运行时间约 90 秒

### 解决的问题

1. Python 3.13 无 pyqlib wheel → 用户级安装 Python 3.12 建 venv。
2. 清华 pip 镜像缺 pyqlib → 安装时显式指定官方 PyPI 索引。
3. wmic 在 Win11 上不可用 → 改用 PowerShell Get-CimInstance。
4. pandas 3.0.5 被 pip 自动安装，与 qlib 0.9.7 存在兼容风险 → 固定 pandas==2.2.3。
5. mlflow 3.x 默认禁用文件存储后端，qlib recorder 直接报错 →
   设置 `MLFLOW_ALLOW_FILE_STORE=true` 重跑成功。
6. 官方 CLI 数据暂停且回退包缺 vwap 字段 → 按官方 README 改用 chenditc 数据源。

### 如何重新运行

```bash
source .venv/Scripts/activate
python scripts/verify_step1.py                 # 一键验证环境（21 项 PASS/FAIL）
# 重跑官方 workflow（本机约 2 分钟）
PYTHONIOENCODING=utf-8 MPLBACKEND=Agg MLFLOW_ALLOW_FILE_STORE=true \
    qrun config/workflow_config_lightgbm_Alpha158.yaml
```

### 下一步

已进入并完成 **STEP 2: Build local A-share data infrastructure**（见下节）。

---

## STEP 2: Build local A-share data infrastructure

> 目标：建立 PersonalQuant 自己的数据基础设施（RAW / CANONICAL / DERIVED
> 分层），包括证券主表、交易日历、日行情、估值、生命周期、行业、公司行为、
> SSE 年报 metadata、按需 PDF 财务提取管线、PIT 语义、审计与质量体系。

状态：**COMPLETED**（2026-09-05）

### 做了什么

- 接入 sse-reports-archive（metadata-only；**未运行 phase3b 全量 PDF 下载**），
  导入 63,612 行 report_documents + 2,468 行 lifecycle。
- 建立 canonical 数据层：DuckDB（data/duckdb/personal_quant.duckdb）+
  Parquet（data/parquet/，按域/年分区），RAW/CANONICAL/DERIVED 严格分层。
- 市场数据：日线 17,882,574 行（2000–2026，原始价格+factor）、证券主表
  6,148（含官方上市/退市日期）、估值快照 4,598、CSRC 行业 5,360、
  公司行为 7,530、交易日历 6,465 天。
- 统一股票代码 `600519.SH` 形式（normalize_symbol + 24 个测试）。
- 数据源策略：东财 push2 快照被 WAF 封禁 → 腾讯行情替代；push2his 时断时续
  → 腾讯 K 线回退；全部 raw 响应缓存、单连接、礼貌延迟。
- **按需 PDF 财务管线**：ReportDocumentProvider（CNINFO 单份获取+三重校验）
  → FinancialDocumentExtractor（PyMuPDF+pdfplumber，章节/列映射/单位/行标签
  全容错）→ PIT 财务指标（financial_metrics）→ extraction_audit 审计。
- 真实验证：6 份年报（5 家公司 × 2022/2023/2024），14 指标与公开披露一致
  （详见 reports/step2_financial_extraction_demo.md）。
- PIT 语义：availability_date=announcement_date、次日可用、strict 模式、
  `availability_date_unknown` 处理、`NOT_AVAILABLE_AT_TIME` 查询语义。
- 财务查询 API：get_financial_metric / get_financial_report /
  get_latest_available_annual_report（42 个测试全过）。
- 质量体系 16/16 PASS（重复/价格/日历/公告日一致性/PIT/哈希/提取值等）。
- Qlib 交叉验证：canonical↔qlib 零差异；vs 腾讯不复权平均相对差 ~3e-8；
  日历 vs 新浪 100% 覆盖。
- bootstrap_data.py（11 步一键重建）+ verify_step2.py（19/19 PASS）。
- OFFLINE/ONLINE 双模式（PQ_MODE）；LEVEL 1/2/3 缓存策略。

### 使用环境

- 同 STEP 1（Python 3.12 venv）+ duckdb 1.5.5 / pymupdf 1.28.2 /
  pdfplumber 0.11.10 / akshare 1.18.94

### 解决的问题

1. 东财 push2/push2his WAF 间歇封禁 → 腾讯行情/K 线替代 + 自动回退。
2. 系统代理（127.0.0.1:7890）间歇拒绝连接 → 默认直连（可切回）。
3. Qlib 数据源价格为 Yahoo 调整价 → canonical 存原始价（÷factor）+
   保留 factor 列，与交易所口径可比。
4. 年报格式差异：银行/保险行标签（归属于本行…、负债总额）、多种单位声明
   （单位：万元 /（人民币百万元）/以人民币百万元列示）、审计报告页干扰
   章节定位、跨页资产负债表、'其中：营业成本' 标签 → 提取器逐项容错。
5. URL 派生公告日期 127 行越界 → 强制降级 availability_date_unknown。
6. 深交所/腾讯列表混入债券等非股票代码 → 按股票代码前缀过滤。

### 如何重新运行

```bash
source .venv/Scripts/activate
python scripts/bootstrap_data.py --skip-bars    # 全量重建（11 步，质量检查自动执行）
python scripts/verify_step2.py                  # 19 项验收检查
python scripts/demo_financial_extraction.py     # 按需年报提取 demo
python scripts/crosscheck_qlib.py               # 交叉验证
python -m pytest tests/ -q                      # 42 测试
```

### 下一步

已进入并完成 **STEP 3: Build first real low-frequency alpha strategy**（见下节）。

---

## STEP 3: Build first real low-frequency alpha strategy

> 目标：第一个真正属于本项目自己的 A 股低频量化策略——月度调仓、
> 全 A 股动态股票池、Alpha158 特征、LightGBM 预测未来 20 日收益、
> Top-20 等权组合、T+1 开盘执行、严格 PIT 与可复现实验体系。

状态：**COMPLETED**（2026-09-08）

### 做了什么

- **Qlib 集成（方案 A，轻量 Custom FeatureProvider）**：只替换 FeatureProvider
  一层，从 canonical parquet 直读数据（pyarrow，多进程安全），qlib 官方
  expression/Alpha158 机制原样运行；单一事实来源，零数据复制。决策记录于
  docs/step3_qlib_integration.md。
- **策略引擎**：月度调仓（每月最后交易日收盘信号 → T+1 开盘执行）、
  动态股票池（上市 180 日/停牌/流动性过滤，历史回测不用今天的列表）、
  Top-20 等权 + 5% 现金缓冲、100 股手数、保守成本模型、涨跌停/停牌
  NO_TRADE（docs/step3_execution_model.md）。
- **三个基线**：CSI300/500/1000 买入持有、全市场等权、60 日动量（同引擎
  同成本）。
- **训练/验证/测试**：2015–2021 / 2022–2023 / 2024–2025；2026 完全
  out-of-sample（paper live）。Walk-forward：季度重训 + 月调仓。
- **模型评估**：月度 IC/RankIC 序列、Q1–Q5 分位收益、IC 稳定性、
  与动量基线对比（reports/step3_model_evaluation.md）。
- **防泄漏体系**：10 项 PIT 审计（10/10 PASS）、sanity check（10 个历史
  调仓日人工核对）、temporal split / no-future-leakage / survivorship /
  执行时点 / 持仓不变量等 11 个策略测试文件（全部通过）。
- **Paper live**：generate_recommendation.py 输出 BUY/HOLD 与手数（仅研究，
  不连接券商）；reports/paper_live/latest_recommendation.csv。
- **可复现**：manifest（git commit/data snapshot/版本/参数）、固定 seed、
  特征与标签 DERIVED 层缓存、experiments/strategy_v1/run_001 与 run_001_wf。

### 结果（诚实记录，不美化）

| 指标 | strategy_v1 | 动量基线 | 等权市场 | CSI300 |
| --- | --- | --- | --- | --- |
| 年化收益 | 24.8% | -22.9% | 20.4% | 17.0% |
| Sharpe | 0.94 | -0.55 | 0.70 | 0.86 |
| 最大回撤 | -20.0% | -54.7% | -28.7% | -15.7% |
| 月胜率 | 60.9% | 34.8% | — | — |

- IC（test）：0.036，ICIR 0.58，正比率 74%；RankIC 0.046。
- Q1→Q5 未来 20 日收益单调：1.11% → 1.96%（排序能力真实但温和）。
- Walk-forward：IC 0.070，回测 +50.2%（与固定 split 一致）。
- 结论：LightGBM+Alpha158 存在真实的弱横截面 alpha，显著超过简单动量基线；
  相对等权市场的超额为 +4.4pp/年（模型选择有正贡献）。
- 注意：测试期（2024–2025）为小盘风格强势市场，策略的绝对收益含风格
  成分；alpha/beta 与 IR 分解已给出（IR 0.43，alpha 11.7%/年）。

### 数据质量修复（本阶段发现的 canonical 层问题，已修复并注册）

1. Yahoo 源 factor 错乱（48 只股票复权因子跳变 → 假 ±100-400% 调整收益）：
   scripts/repair_factors.py 修复 22,906 行，新增因子连续性质量检查。
2. 停牌占位行（57.7 万行 NaN close）污染 NAV 标记与执行：剔除并新增
   NaN 价格质量检查。
3. 上述修复仅影响北交所等非股票池标的时，已在报告中注明。

### 如何重新运行

```bash
source .venv/Scripts/activate
python scripts/backtest_strategy.py --strategy strategy_v1 --start 2024-01-01 --end 2025-12-31 --run-id run_001
python scripts/backtest_strategy.py --strategy strategy_v1 --walk-forward --run-id run_001_wf
python scripts/generate_recommendation.py --date 2026-09-04 --capital 500000
python scripts/verify_step3.py                 # 19 项验收
python scripts/make_figures.py                 # 10 张图
python scripts/write_reports.py                # 2 份报告
python -m pytest tests/ -q                     # 86 测试
```

### 下一步

已进入并完成 **STEP 4: Factor Research and Alpha Mining**（见下节）。

---

## STEP 4: Factor Research and Alpha Mining

> 目标：建立严谨、可复现、严格 PIT 的因子研究平台；回答哪些因子有效/
> 稳定/衰减、是否与 Alpha158 重复、财务因子是否提供新 alpha、浅层
> Alpha Mining 的 out-of-sample 表现。

状态：**COMPLETED**（2026-09-09）

### 做了什么

- **市场数据质量审计与修复**（docs/step4_market_data_quality.md）：
  确认 volume/amount 存在每股常数缩放（Yahoo 伪影，组内 CV≈0.11、
  跨股差 ~230×）→ 逐股校准（腾讯 K 线 ground truth，5,460/5,557 股，
  99.7% 常数模型成立）→ data/parquet/market/market_scale.parquet
  （repair_version 记录）；canonical 原列永不修改（strategy_v1 位级不变）。
  因子引擎使用校准列 amount_cny / volume_shares。
- **因子研究平台**（factors/ 包，31 个候选因子）：统一接口 + 注册表
  （方向/公式/来源/PIT 要求）、技术因子（动量/反转/波动/量价位置/量能/
  流动性）、PIT 财务因子（估值/质量/成长/现金流，严格
  signal_date > availability_date）、横截面归一化（rank/winsorized_zscore）、
  缺失值策略（sector_median/drop，记录在案）、IC/RankIC/ICIR/衰减
  （1/5/10/20/40/60 日）/分位/多空/稳定性/相关性聚类评估器。
- **PIT 财务管线**（docs/step4_financial_factor_pit.md）：提取器 v1.1
  （eps/bps 每股指标、繁体（H 股）报告支持 + H 股安全护栏——B/C 表
  锚点会命中年报管理层讨论的交叉引用，识别后诚实 EXTRACTION_FAILED）、
  lazy 增量抓取（分块运行、断点续跑，~1,600 份年报提取，111 只大市值股）、
  覆盖率报告（按年×因子+缺失归因，绝不猜值）。
- **factor_pack_v1 选择**：research 2018-2021 + valid 2022-2023 选择，
  test 2024-2025 只做一次最终评估；覆盖率/ICIR/方向一致性/相关性聚类
  四道门，每步丢弃原因记录在案。
- **浅层 Alpha Mining**（非遗传编程）：表达式解析（深度≤3、算子白名单
  + - * / rank zscore log abs）、beam search（每代≤1,000 候选、1,168 个
  测试）、综合评分（ICIR+稳定性+换手+相关性+覆盖率）、validation 排序、
  snooping diagnostics（候选数/各期最优分）、自动 gate → factor_pack_v2
  候选（research candidate，非生产策略）。
- **Model A/B/C/D ablation**：同引擎/同参数/同成本/同 Top-20/同 T+1，
  只改特征集；A 完全复现 strategy_v1 run_001。
- 验收：verify_step4.py 21/21 PASS；全量测试 186 个；
  verify_step1/2/3 无回归。

### 结果（诚实记录，不美化）

| 因子研究（2018-2023 选择 → 2024-2025 单次检验） | 结论 |
| --- | --- |
| reversal_20 | research ICIR +0.52 → test +0.60，最稳定 |
| volatility_20/60 | 低波动溢价，test 延续 |
| volume_ratio_5_20/20_60、amount_20 | 量能/流动性（负向），test 延续 |
| momentum_20/60/120、price_vs_ma* | 实证方向为负（A 股短期反转主导），test 延续 |
| 财务因子（roe ICIR 0.47 等） | research 期看似有效，**test 期全部反转或消失**（roe test ICIR -0.12） |
| factor_pack_v1 | 7 个技术因子（财务因子未通过稳定性门，如实丢弃） |

| Ablation（test 2024-2025） | 年化 | Sharpe | MDD | IC |
| --- | --- | --- | --- | --- |
| A = Alpha158（复现 run_001 ✓） | 0.2475 | 0.943 | -0.200 | 0.0358 |
| A1 = +估值 | 0.1304 | 0.542 | -0.274 | 0.0291 |
| A2 = +pack 技术因子 | 0.1962 | 0.748 | -0.279 | 0.0351 |
| A3 = +财务因子 | 0.2511 | 0.923 | -0.251 | 0.0321 |
| C_full = 全部 | 0.2478 | 1.017 | -0.214 | 0.0440 |
| C_res = 全部（受限大市值池，不可与 A 直接比） | 0.2740 | 1.318 | -0.121 | 0.0344 |
| D = +mined（research candidate） | 0.3970 | 1.392 | -0.212 | 0.0414 |

**总回答（如实）**：第一轮因子研究中，**财务因子与自定义技术因子都未能
稳定超越 Alpha158 基线**（A2 < A 说明 Alpha158 已捕获技术信息；
财务因子单独 ≈ 基线、IC 更低；受限股票池 C_res 的优势来自大市值股票池
本身，非纯特征差异）。D 的 mined 因子 test 表现好，但这是 1,168 候选
snooping 背景下的单次检验，仅作 research candidate，不进入生产策略。

### 数据质量修复（本阶段发现并修复）

1. volume/amount 每股常数缩放（Yahoo 伪影）→ market_scale 校准表
   （详见上）。
2. **指数伪标的入池**（qlib 源含 000300/000852/000905/000906/000985.SH、
   399300.SZ 六个指数，与股票共用代码段）：run_001 从未选中它们、影响
   为零；strategy_v1 代码保持冻结；STEP 4 因子股票池已显式排除
   （config index_exclude）。
3. 提取器 v1.1：每股指标（基本每股收益）标签含"（元/股）"后缀曾被
   边界规则拒绝 → 修复；双挂牌银行的 CNINFO 年报为繁体（H 股）版本 →
   繁体标签 + 财务摘要定位 + B/C 表护栏（防止把管理层讨论的交叉引用
   当报表值）；extraction_audit 主键序列错位 → 冲突回退修复；
   失败提取会清除旧的错误值（绝不残留）。

### 如何重新运行

```bash
source .venv/Scripts/activate
python scripts/audit_market_data.py                    # 离线审计
python scripts/calibrate_market_scale.py --limit 60    # 校准（全量约 3h，断点续跑）
python scripts/factor_prepare.py                       # DERIVED 缓存（日历/标签/股票池/财务快照）
python scripts/fetch_financial_universe.py --max-reports N   # lazy 财务抓取（分块）
python scripts/research_factor.py --factor roe         # 单因子研究
python scripts/research_all_factors.py                 # 全因子研究 -> factor_pack_v1
python scripts/run_alpha_mining.py                     # 浅层挖掘 -> factor_pack_v2 候选
python scripts/backtest_ablation.py                    # Model A/B/C/D 消融
python scripts/financial_coverage.py                   # 财务覆盖率报告
python scripts/make_figures_step4.py                   # 10 张图
python scripts/write_step4_reports.py                  # 因子研究/消融报告
python scripts/verify_step4.py                         # 21 项验收
python -m pytest tests/ -q                             # 186 测试
```

### 下一步

**STEP 5: Build news and alternative-data factors**（未开始，暂定）

