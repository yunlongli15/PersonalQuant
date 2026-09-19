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

已进入并完成 **STEP 5: Build news and alternative-data factor system**
（见下节）。

---

## STEP 5: Build news and alternative-data factor system

> 目标：严格 PIT、可追溯、可缓存、可复现、低成本的 A 股新闻/公告因子
> 系统；回答"新闻/公告信息是否给 Alpha158 + 现有策略带来真正的增量
> alpha"。

状态：**COMPLETED**（2026-09-10）

### 做了什么

- **Provider 抽象层**（news/providers/）：BaseNewsProvider + SSE 官方
  公告（按日全量，分页陷阱已修复：pageHelp.pageNo 被忽略，需用
  beginPage/endPage，pageSize=1000 一天一请求）、SZSE 官方 API（按股）、
  CNINFO（巨潮，按股/关键词，orgId 可推导）、AkShare 包装。业务层零
  direct HTTP；低并发、礼貌延迟、重试退避、raw 缓存、SOURCE_BLOCKED
  记录。
- **canonical news_documents**（DuckDB，171,667 条 2018-2026，2,478 只
  股票；document_id 去重 + source_count）→ **derived news_events**
  （规则分类 25 类事件 + novelty + PIT availability）→ **derived
  news_factors**（27 个因子进 FACTOR_REGISTRY，复用 STEP 4 评估引擎）。
- **严格 PIT**（docs/step5_news_pit.md）：发布日 ≤15:00 当日可用；
  盘后/周末/节假日/仅日期 → 下一交易日 09:30；发布时间未知 strict
  禁用；event_time/updated_at 与 publication_time 严格分离。
- **规则事件抽取**（无 LLM 先跑通）：25 类关键词分类 + 方向候选 +
  重要性分层；事件聚合（正/负/重大/风险分，同日冲突保留双侧）。
- **LLM 层**（DeepSeek）：结构化 JSON（区间校验、解析失败 =
  EXTRACTION_FAILED）、prompt 版本化、cache（doc_hash+prompt+model）、
  每日预算（超限 RULE_BASED_ONLY）、tier-1 文档过滤。**当前无
  DEEPSEEK_API_KEY → 全链路 rule-based 运行（系统自动检测，不因 API
  缺失失败）。**
- **新闻因子研究**：27 因子在 research/valid/test 上评估；衰减半衰期
  研究（1/3/5/10/20d 全为 ~0 —— 数据决定，不预设）；factor_pack_news_v1
  （3 因子：announcement_count_20d / news_risk_20d /
  shareholder_change_count_20d）。
- **新闻消融**（A/B/C/D/E + 8 个分组消融）：A/B 与 STEP 4 冻结锚点
  完全一致（drift 0.0000）；strategy_v1_news（不覆盖 strategy_v1）+
  paper-live 推荐。
- 验收：verify_step5.py **22/22 PASS**；全量测试 **302 个**；
  verify_step1/2/3/4 无回归；8 份报告 + 10 张图。

### 结果（诚实记录）

| 新闻因子 | research ICIR | test ICIR |
| --- | --- | --- |
| announcement_count_20d | +0.39 | +0.36（最稳定） |
| news_risk_20d | +0.35 | — |
| shareholder_change_count_20d | +0.36 | — |
| 其余 24 个因子 | < 0.3 未过门 | — |
| 衰减研究（5 个半衰期） | rank-IC ≈ 0 | 衰减权重无增量 |

| 消融（frozen test） | 年化 | Sharpe | MDD |
| --- | --- | --- | --- |
| A = Alpha158（锚点 ✓ drift 0.0000） | 0.2475 | 0.943 | -0.200 |
| C = Alpha158 + 新闻因子单独 | 0.1094 | 0.456 | -0.226 |
| N_risk = Alpha158 + news_risk_20d | 0.2639 | 0.968 | -0.212 |
| **E = Alpha158 + pack_v1 + 新闻** | **0.2812** | **1.022** | -0.235 |
| D = +LLM 新闻 | ≡ A（LLM 未启用，如实记录） | | |

**总回答（如实）**：规则公告信息单独使用没有排序能力（C < A），但
"公告强度 + 风险事件"维度与 factor_pack_v1 组合时提供了超越 Alpha158
的边际增量（E 0.2812 > A 0.2475，IC 0.0372 vs 0.0358；MDD 略深）。
LLM vs rule 的对比留待 DEEPSEEK API 可用（系统自动检测启用）。

### 数据与覆盖（如实）

- SSE（官方）：2018-2026-09 全量（分页修复 + 截断日 repair）；
  SZSE（官方）：按股回填 top-60 大市值（增量模式可续跑剩余股票）；
  总覆盖 2,478 只（新闻因子覆盖率 ~0.40，选择门槛 0.2 并记录原因）。
- 指数来源滞后 ~5 天：增量模式只推进已 settle 的日期。

### 如何重新运行

```bash
source .venv/Scripts/activate
python scripts/news/update_news.py --dry-run          # provider 检查
python scripts/news/update_news.py                    # 增量更新
python scripts/news/update_news.py --backfill-sse --start 2018-01-01
python scripts/news/update_news.py --backfill-szse --max-stocks 800
python scripts/news/build_events.py                   # 文档 -> 事件（+LLM 层可选）
python scripts/news/build_news_factors.py             # 评估 -> factor_pack_news_v1
python scripts/news/analyze_news_factor.py --factor news_count_5d
python scripts/news/run_news_ablation.py              # A/B/C/D/E 消融
python scripts/news/run_news_strategy.py              # strategy_v1_news
python scripts/news/generate_news_recommendation.py --date 2026-09-04
python scripts/news/write_news_reports.py             # 8 份报告
python scripts/news/make_figures_step5.py             # 10 张图
python scripts/verify_step5.py                        # 22 项验收
```

### 下一步

已进入并完成 **STEP 6: Portfolio Optimization and Advanced Strategy
Research**（见下节）。

---

## STEP 6: Portfolio Optimization and Advanced Strategy Research

> 目标：在已有的预测信号（SIGNAL）基础上研究怎样构建风险更低、回撤更
> 小、换手合理、更适合个人长期持有的股票组合（PORTFOLIO），并把
> signal 与 allocation 严格分离。

状态：**COMPLETED**（2026-09-10）

### 做了什么

- **STEP 5 完整性预检查**（reports/step5_incremental_alpha_check.md）：
  补齐 D vs B 比较 —— S3（Alpha158+pack_v1+news）0.2812/1.022 显著优于
  B（Alpha158+pack_v1）0.1962/0.748（Δ年化 +8.5pp、ΔSharpe +0.273）
  → **新闻在非新闻因子之上提供增量 alpha**，据此冻结 STEP 6 的 alpha
  信号（生产模型未动，未重跑冻结基线）。LLM News = NOT YET EVALUATED
  （无 DEEPSEEK_API_KEY），不阻塞、不伪装。
- **Portfolio Optimization Engine**（portfolio/ 包）：allocator（P0-P6）、
  constraints、covariance（sample/EWMA + PIT + sanity gate + 修复链）、
  risk_model（边际/成分风险贡献）、transaction_cost（复用冻结成本模型）、
  optimizer（SLSQP + water-fill 二次强制约束）、portfolio_metrics
  （含 VaR/CVaR/HHI/有效持仓数/行业集中度）、portfolio_registry、
  backtest（T+1/涨跌停/停牌/手数/成本/双口径换手/可解释性/审计）、
  rebalance（monthly/quarterly）。
- **信号冻结**：S3；portfolio 只做 allocation，不重训 alpha、不改 alpha
  排名（raw_rank 全程保存）。
- **研究期 OOS 预测**：年度 walk-forward（train 2015..Y-2、ES=Y-1、
  预测 Y）生成 2018-2021 的 S1/S2/S3 预测；发现并如实记录**新闻盲期**
  （新闻覆盖自 2018 起 → 2018-2019 模型训练窗口无新闻，无法分裂）；
  2020-2021 新闻生效。
- **研究（选择只用 research 2018-2021 + valid 2022-2023，协议先于结果
  写死）**：top_k 10/20/30/50 → 20；cash 5/10/15% → 5%；
  方法 P0-P6 → **return P0 等权**；频率 monthly vs quarterly → monthly；
  另做流动性约束补充研究与 benchmark 上下文（CSI300 买入持有 + 等权市场）。
- **frozen test 2024-2025 单次评估** 7 个方法（只记录，绝不用于选择）；
  **stress test**（2020/2022/2024 + 各期最大回撤窗口，含恢复天数）；
  **组合相关性/权重集中度/行业暴露/风险贡献**分析；
  **allocation audit**（权重和/现金缓冲/个股上限/行业上限/无做空/
  无杠杆/可交易/手数/回退记录）。
- **strategy_v2**（config/strategy_v2.yaml，未修改 strategy_v1）+
  9 项 candidate gates + paper live（500,000 资本 → BUY/SELL/HOLD +
  手数 + 预估费用；不连接券商）。
- 验收：verify_step6.py **25/25 PASS**；全量测试 **400 个**；
  verify_step1/2/3/4/5 无回归；2 份报告 + 12 张图。

### 结果（诚实记录，不美化）

| 阶段 | 结果 |
| --- | --- |
| 引擎锚点 | P0 ≡ strategy_v1_news，**drift 0.0000（NAV 逐位一致）** |
| research（OOS） | P0 等权 Sharpe 0.296；**没有任何优化器超过它** |
| validation（熊市） | 全部方法绝对收益为负；策略 −12.9% vs CSI300 −16.6%（IR +0.305） |
| frozen test | P0 0.2812/1.022/−0.2351；risk_parity 略优（1.051/−0.220，单次观察，未用于选择） |

**总回答（如实）**：**组合优化在本阶段没有带来增量 alpha 层面的改善**
—— 在 research+valid 上没有任何 P1-P6 方法通过预先写死的门槛（valid≥0.8×
稳定性门等），最终候选按规则退回 P0 等权。这不是调参失败，而是给定
alpha 强度下的真实结论：等权已足够好，样本内优化更多在拟合协方差噪声
（MVO/GMV 在 research 期反而更差）。若没有这一层检验，很容易把
frozen test 上偶然更好的 risk_parity 当作"优化器有效"——本阶段明确
拒绝这样做。

### candidate gates（spec §54）

7/9 通过；2 项未通过且**不重写门槛**：
- `2_validation_pass`（ann>0）：2022-2023 熊市，绝对收益为负 —— 但
  同期跑赢 CSI300（IR +0.305），相对表现单列记录。
- `9_no_pathological_concentration`：P0 等权作为冻结基线不施 20% 行业
  上限（锚点可复现的前提），实测行业集中度可达 ~40%；有效持仓数 ~61、
  单只 ≤ 4.75%，属已知基线属性而非路径性集中。
因此 strategy_v2 **保持研究候选状态，不晋升为生产候选**。

### 本阶段发现并如实记录的问题

1. 冻结预测 parquet 中约 44% 的行是**全 NaN 特征行**（冻结回测从未使用；
   引擎通过重建冻结 predictor 路径复现，锚点因此 bit 级一致）。
2. 候选股票历史不足时被协方差剔除 → 权重与协方差维度不一致（已修复：
   `_cov_aligned` 按冻结的等比口径缩放目标，剔除者留在现金）。
3. 500,000 资本 + 100 股手数下 paper live **实际投入仅 75.9%**（2 只低于
   1 手 + 取整残差）—— 小账户手数摩擦真实存在。
4. selection.json 的 numpy 整数被 `default=str` 序列化成字符串，导致
   读回后崩溃（已修复为 int/float）。

### 如何重新运行

```bash
source .venv/Scripts/activate
python scripts/portfolio/write_incremental_check.py      # STEP5 增量检查
python scripts/portfolio/build_alpha_predictions.py      # research 期 OOS 预测
python scripts/research_portfolio.py --method gmv --period test   # playground
python scripts/research_portfolio.py --method equal_weight --period test --check-anchor
python scripts/portfolio/run_portfolio_study.py --stage all       # 6 阶段研究
python scripts/portfolio/run_liquidity_study.py          # 流动性约束补充研究
python scripts/portfolio/add_benchmark_context.py        # benchmark 上下文
python scripts/portfolio/run_stress_test.py              # 压力测试
python scripts/portfolio/run_strategy_v2.py              # strategy_v2 + gates
python scripts/portfolio/generate_v2_recommendation.py --capital 500000
python scripts/portfolio/make_figures_step6.py           # 12 张图
python scripts/portfolio/write_step6_reports.py          # 2 份报告
python scripts/verify_step6.py                           # 25 项验收
python -m pytest tests/ -q                               # 400 测试
```

### 下一步

已进入并完成 **STEP 7: Build Personal Portfolio / Wealth Management and
GUI**（见下节）。

---

## STEP 7: Personal Portfolio / Wealth Management / GUI

> 目标：把 PersonalQuant 从"量化研究仓库"变成"个人投资终端" ——
> 研究系统（Research/Signal/Forecast/Allocation/Trade Plan）与个人
> 财富系统（真实资产记录与绩效）严格分离、又能联动闭环。

状态：**COMPLETED**（2026-09-10）

### 做了什么（7A-7G）

- **7A 财富数据库**：`data/wealth/wealth.db`（SQLite，本地单用户，
  git 忽略）——platforms/accounts/products/transactions/
  daily_snapshots/positions/income_records/benchmark_records/
  wealth_categories/audit_log + 视图 cash_flows/fees/dividends/
  v_latest_values（单一台账：外部与内部资金流是数据库级不变量）；
  recommendation/decision/execution 三张表；CRUD 全部写审计；
  交易修改/删除必须给理由；CSV/JSON 导出 + 一键 SQLite 备份。
- **7B 收益引擎**：`Investment P&L = Ending − Beginning − 外部净流入`
  （spec §7）；**万份收益**（spec §8）用"当日有效份额"处理日内转入，
  存入转出不会造成虚假的收益率下跌（spec §8.3 场景有测试），
  计算口径标记 exact/estimated；持仓成本（含买入费用）、已实现/
  未实现盈亏、分红、费用；TWR（资金流调整）与 XIRR（多笔不规则
  现金流，无解时返回 None 而非编造）；净资产变动分解（§27）带
  恒等式校验；Daily Update 只需输入"今日金额"。
- **7C 数据刷新**：pipeline/（freshness/jobs/refresh/signals）——
  8 个按依赖排序的刷新任务包装既有 STEP 2-6 入口；job store 记录
  每次运行（SQLite）；**离线模式记 SKIPPED，绝不记为成功**；
  数据新鲜度面板（OK/STALE/MISSING/UNKNOWN）含"日历本身滞后"盲区
  规则；`scripts/quant/refresh_all.py` 一键更新。
- **7D 预测引擎**：1D/5D/20D 预测 = **冻结 S3 分数**下的已实现收益
  条件分布（20 个分位桶 + 桶心插值，Top-20 内部也有区分度），
  输出期望收益/中位数/5-95% 区间/P(up)/趋势/样本数/版本；
  **PIT**：只用预测日之前已结束窗口的样本（embargo），未来数据
  投毒不变性有测试；不堆模型（spec §43）。
- **7E 交易计划**：trade_plan/ —— 冻结信号 → STEP 6 分配（方法读
  研究选择，不重调参）→ 手数化订单；**入场区间**来自个股 20 日
  波动（profile 乘数、上限 3%）+ 计划价 + 理由（绝不用"现价买入"）；
  目标价/止损/时间止损；**卖出必须给出原因**（多因）；成本复用共享
  TransactionCostModel；输出 trade_plan_<date>.csv/.json。
- **7F 本地 GUI**：FastAPI，仅绑定 127.0.0.1（启动器拒绝外部绑定）；
  **离线优先**：CSS/SVG 全部本地生成，零 CDN（每页有测试断言）；
  pages.py 只做格式化（AST 测试禁止其 import 任何引擎），所有数字来自
  webapp/services.py；页面覆盖 Dashboard / Wealth（含 Daily Update）/
  Quant（信号、预测、个股、交易计划、paper live、Research Lab）/
  Data Status / Settings。
- **7G 集成**：决策链（recommendation → accept/modify/reject →
  实际成交对比滑点，spec §33/§34）、模型 vs 实际持仓缺口
  （Underweight/Overweight，§36）、调度器（manual + daily 已实现，
  weekly/monthly 已声明）、闭环脚本
  `scripts/quant/run_full_loop.py`（**9/9 步通过**）、
  `scripts/verify_step7.py`（**29/29 PASS**，含 STEP 1-6 回归）。

### 结果（如实记录）

| 项目 | 结果 |
| --- | --- |
| 闭环 | data → factor → signal → forecast → allocation → trade plan → wealth → performance 全部打通（9/9） |
| 实时产物 | 3,027 只股票信号（2026-09-04）· 200 只 × 3 跨度预测 · 18 只持仓交易计划（占用 75.3%，费用 286 元，预期净收益 1.38%） |
| 数据新鲜度 | Market/Valuation ⚠ STALE（canonical 数据止于 2026-09-04，面板如实显示） |
| 测试 | STEP 7 新增 166 个（wealth 72 / pipeline 39 / trade_plan 17 / webapp 38）；全量 **566 passed**（400 → 566） |
| 回归 | verify_step1-6 全部 PASS（21/19/19/21/22/25） |

### 已知限制（如实）

1. Market/Valuation 增量刷新依赖既有在线 provider，离线模式下记为
   SKIPPED；本机数据止于 2026-09-04，GUI 会持续显示 STALE。
2. 预测为"分数分桶条件分布"，不是独立训练的 1D/5D 模型；桶边界
   随市场变化需要重新校准（每次刷新自动用最新可得样本）。
3. GUI 为桌面优先、单用户、无鉴权（本地回环绑定）；移动端未做。
4. 调度器不常驻：由 GUI 按钮/CLI/系统计划任务触发，重复调用幂等。
5. paper live / demo 财富数据均带标记，可一键清除（--clean-demo）。

### 如何重新运行

```bash
source .venv/Scripts/activate
python scripts/wealth/init_wealth_db.py            # 初始化财富库
python scripts/quant/refresh_all.py --status       # 数据新鲜度面板
python scripts/quant/refresh_all.py                # 一键更新（离线记 SKIPPED）
python scripts/quant/run_full_loop.py --demo-wealth  # 闭环端到端
python scripts/webapp/serve.py                     # GUI -> 127.0.0.1:8765
python scripts/verify_step7.py                     # 29 项验收
python -m pytest tests/ -q                         # 全部测试
```

### 后续维护（2026-09-13）

**数据刷新到 2026-09-11** + **板块交易权限**：

- 行情快照更新到 chenditc release 2026-09-12（行情至 2026-09-11，+5 个
  交易日）；新闻 2026-09-09；估值 2026-09-13；因子/信号/预测/交易计划
  全部重算到同一数据版本。新增可复现脚本
  `scripts/quant/update_market_snapshot.py`（下载→切换→重新 ingest）。
- **修复新快照引入的源侧缺陷**：7 只标的的历史复权因子被上游重定基准
  （原始价连续、复权价跳 2~6 倍），新增
  `scripts/quant/repair_factor_rebase.py`（与 STEP 3 的反方向修复），
  修复 23,026 行并登记 source_registry；修复后所有市场数据测试通过。
- **板块交易权限**（用户要求）：新增 `trade_plan/boards.py` 与
  `config/account_profile.yaml`。交易计划默认**先按权限过滤再取 Top-K**
  （科创板需 50 万、创业板 10 万、北交所 50 万），被排除标的完整列出，
  不给"买了也买不到"的标的分配资金；临界达标与未核实经验均提示。
- **小资金适配**：100 股手数在小账户上会吃掉大量额度（10 万 + Top-20
  只有 48.7% 可投），新增 `suggest_top_k`（只依据资金/手数算术，
  不读任何收益数字）自动选定持仓数，本次为 K=10。
- **新增文档**：[docs/USER_GUIDE.md](docs/USER_GUIDE.md)（使用说明书：
  界面含义、指标定义、板块权限、常见问题、系统边界）、
  [DATA.md](DATA.md)（仓库数据/模型清单与再生成方式）。

### 下一步

**STEP 8**（未定义，等待用户指令）。

---

## 迭代记录（STEP 7 之后，2026-09-13 起）

### 数据刷新到 2026-09-17

- 可复现快照更新：`scripts/quant/update_market_snapshot.py`（下载最新
  chenditc release → 切换 qlib_data → 重新导入 canonical）；
  修复了脚本自身的两个 bug（tar 解压层级、备份目录冲突）。
- **修复上游快照引入的复权因子缺陷**：7 只标的的历史 factor 被重定基准
  （原始价连续、复权价跳 2~6 倍）→ `scripts/quant/repair_factor_rebase.py`
  修复 23,026 行（与 STEP 3 的反方向修复），已登记 source_registry。
- 新闻公告 171,667 → **176,763 条**（覆盖 2,478 → 4,223 只）。

### 界面与财富管理（用户驱动的改进）

- **全中文界面**（14 个页面），零外部资源、仅绑定 127.0.0.1。
- **股票专用录入**：名称/代码/买入成本价/买入日期/股数/现价 → 市值与浮盈；
  首次建仓同时记买入交易与等额本金投入（否则本金会被当成收益）。
- **交易流水记账**：转入/转出（外部资金流，从收益中剔除）、分红、费用、
  买入/卖出；金额一律填正数，系统自动处理符号。
- **板块交易权限**：科创板 50 万 / 创业板 10 万 / 北交所 50 万；
  交易计划先按权限过滤再选 Top-K，被排除标的完整列出。

### 修掉的真实 bug（都由用户使用中发现）

| 问题 | 根因 | 影响 |
|---|---|---|
| 特征计算卡死 30 分钟 | 父进程先初始化 qlib → worker 子进程 joblib 死锁 | 信号无法更新 |
| 预测日期口径错乱 | 信号失败后仍用旧信号生成"当日"预测 | 会给出错误日期的建议 |
| **净资产假暴跌** | 按日汇总假设所有产品每天更新，部分更新=其余"消失" | 显示假亏 14.9 万 |
| 费用低估 0.055% | 未计券商 5 元最低佣金 | 净收益高估 |
| 分位分析崩溃 | 并列预测值使 `pd.qcut` 报 Bin edges 错 | 整轮回测失败 |
| 保存按钮无效 | 缺 `python-multipart`，表单 POST 直接断言失败 | 每日录入无法保存 |

### 新因子挖掘（16 个微结构因子）

- `factors/microstructure.py`：隔夜/日内分解、彩票效应(MAX)、偏度/峰度、
  Amihud 非流动性、换手率波动、52 周高点、Parkinson 波动、跳空频率、
  量价相关、量能趋势、**涨停/跌停次数（A 股特有）**。
- **单因子在 frozen test 中预测力延续**（涨停次数 ICIR -0.906 → **-0.831**；
  量能趋势 -0.543 → -0.665），与 STEP 4 财务因子"出样本即反转"形成对比。
- **但组合回测未提升策略**：S3 0.2812/1.022 → M 0.3053/1.148（IC 反而更低、
  MDD 更深）、N 0.1592/0.657。诚实结论：新因子保留为
  research candidate，**不进入 strategy_v2**。
- ⚠️ "N 明显更差"已被 `reports/step9_independent_info.md` 更正为**不显著**
  （t = −0.87，p = 0.40）；单因子结论不受影响。
- 报告：`reports/step8_micro_factors.md`。

## STEP 9: Incremental IC Factor Selection

> 目标：不再问"这个因子单独强不强"，而是问
> **"把它加进已有模型后，模型对未来横截面收益的预测信息是否真的增加？"**
> 并把这件事固化成一套可长期复用的统计协议。
>
> 状态：**COMPLETED**（2026-09-19）
> 协议配置：`config/factor_selection_v2.yaml`
> 报告：`reports/incremental_factor_selection_v2.md`

本阶段包含两个部分：**9.1 是一次发现，9.2 是对它的修正**。

### 9.1 残差信息研究（发现）

在当日横截面上把候选因子对 `Z = rank([Alpha158, M0 自定义因子])` 做正交
投影，用残差的 IC 度量"既有信息解释不掉的部分"：

- 75 个候选里只有 4 个通过独立信息门，看起来集中在波动率家族。
- 最强的单因子 `limit_up_count_20`（raw ICIR −0.733）残差 ICIR ≈ 0
  → 它是既有信息的**替代品**，不是**增量**。
- 组合层面：S3 / I / R / M / N 五个变体的差异**全部不显著**
  （p 0.15~0.83，年化 bootstrap 95% CI 全部跨零）。24 个月、月度超额
  标准差 4.98% → 80% 功效下**可检出的最小年化差异 41.1%**。
- 结论：**用 24 个月组合回测检验因子没有分辨力**；因子层（约 1500 只 ×
  72 个信号日）才有足够样本。

报告：`reports/step9_independent_info.md`。

### 9.2 协议修正（Incremental IC V2）

**为什么改**：残差独立信息有两个致命问题——
(1) R² 越高 → 残差越像噪声 → 残差相关越低 → **最冗余的因子看起来最独立**；
(2) 残差 IC 高不等于加进模型有用。

**改成什么**：直接配对比较两个模型

```
M0 = Alpha158 + factor_pack_v1 + news        （既有特征集）
M1 = M0 + F                                  （唯一差别）
ΔIC(t) = IC1(t) − IC0(t)                     逐日配对差，不是 mean(IC1)
```

- **walk-forward 4 折**：train 2018–2019/2020/2021/2022 → valid 2020/2021/
  2022/2023（扩张窗口，train_end < valid_start）。
- **标签越界保护**：验证年最后一个信号日的 20 日前瞻收益落到下一年，
  必须剔除（每年 12 → 11 个信号日）。
- **严格配对**：同数据、同参数、同种子、同股票池；**关闭 early stopping
  （验证集就是被评估期）与特征子采样**（否则 M0/M1 的差异混入抽样噪声）。
- **block bootstrap**（按月分块，1000 次）给 ΔIC 置信区间。
- **冗余主判据改为原始因子秩相关**（残差相关降级为诊断），
  `require_both`：原始相关与对**完整 M0** 的回归 R² 同时越线才判冗余。
- **Evidence Score**：权重全部写在 yaml（incremental ICIR 0.25 +
  incremental RankICIR 0.25 + 正向 fold 0.14 + 正向月份 0.10 +
  稳定性 0.10 + 独立性 0.08 + 覆盖率 0.05 + 换手 0.03），
  优先级 incremental IC > stability > independence > portfolio 收益。
- **两阶段筛选**：Stage A（2018-2021，只筛数据质量 + PIT 投毒检验）
  65 → 20；Stage B（4 折配对）20 → 最终 5 个 research candidate。

**结果（诚实记录）**：

- **0 / 20 个候选的 ΔIC 置信区间排除 0。** ΔIC 量级只有 0.0001~0.015。
- **修正后的冗余判据推翻了 9.1 的波动率结论**：`parkinson_vol_20`
  与既有因子秩相关 0.912、对完整 M0 的 R² 0.954 → 冗余；
  `amihud_20` 是 `amount_20` 的近似倒数（相关 0.92）→ 冗余。
- **置换重要性 ≈ 0**：打乱候选列后模型 IC 平均只掉 0.0006。
  候选改变了模型输出（pred_corr 低至 0.40），却没有改变排序质量——
  ΔIC 更可能来自"多加一列改变了训练路径"，而非"模型用上了这一列"。
- 最终 5 个 research candidate：`gap_count_20`、`high_52w_proximity`、
  `overnight_return_20`、`skewness_60`、`volume_price_corr_20`。
  **是"待观察清单"，不是"已证明有效清单"。**

### 9.3 Historical test 污染（如实记录）

2024-2025 已被评估 **3 次**（STEP 6 终评、step8 微结构消融、step9 独立信息
研究）。**不再声称它是 untouched test**，降级为 HISTORICAL TEST。

本阶段在代码层面禁止它进入选择路径：
`incremental/windows.py` 的两个守卫 + `tests/factors/test_no_test_usage.py`
的静态扫描（选择路径上的模块不得出现 2024/2025 日期字面量）。
本阶段全部数字只用 2018-2023，没有在 2024-2025 上跑任何东西。

### 9.4 Forward holdout

- 起点 `2026-09-18`（最后一个已被观察日期的次日），模式 `record_only`。
- `scripts/monitor_forward_holdout.py` 每月登记冻结预测、回填已实现收益。
- **当前 0 期**：holdout 尚未开始累积。目标是长期监控，不是现在出结论。

### 9.5 本阶段修掉的实现 bug（都会给出错误答案）

| # | 问题 | 后果 |
|---|---|---|
| 1 | 候选列用 `normalize_panel(..., "rank")`，而它是 `rank(axis=1)`；单列框架退化成常数 | **每个 ΔIC 都会精确等于 0**，看起来像"所有因子都没用"，实际是特征没进模型 |
| 2 | `delta_ic_table` / `prediction_impact` 整表 merge → `label_0`/`label_1` | Stage B 直接 KeyError 崩 |
| 3 | 冗余 R² 只对 Alpha158 回归，而相关判据用 M0 的 10 个自定义因子 | `require_both` 拿苹果比橘子 → `amihud_20`（相关 0.92）逃过判据并进入最终候选 |
| 4 | block 与 iid bootstrap 共用同一 RNG 流 | "iid 对照"失去意义 |
| 5 | Evidence Score 权重违反 §16 优先级 | 打分与声明的优先级不符 |

Bug 1 与 STEP 9 上一轮的 `rank` 轴 bug **是同一类**（第二次出现），
现已补回归测试 `tests/factors/test_walk_forward_selection.py::
test_custom_frames_rank_across_stocks_not_across_factors`，并且驱动在构建
设计矩阵后会显式检查"有没有常数列"并直接报错。

### 9.6 代码与验证

- 新增包 `incremental/`：`windows`（时间边界守卫）、`engine`（walk-forward
  配对引擎）、`stats`（block bootstrap / Evidence Score / 门槛）、
  `redundancy`（原始秩相关主判据 + 残差诊断）、`holdout`（前瞻登记）。
- 脚本：`scripts/run_incremental_factor_selection.py`（主协议）、
  `scripts/run_incremental_secondary.py`（ADD/REPLACE + 重要性，不参与选择）、
  `scripts/make_incremental_figures.py`（8 张图）、
  `scripts/monitor_forward_holdout.py`、`scripts/verify_incremental_factor_selection.py`。
- 测试：`tests/factors/test_incremental_ic.py`、`test_walk_forward_selection.py`、
  `test_block_bootstrap.py`、`test_factor_selection_freeze.py`、
  `test_prediction_impact.py`、`test_redundancy.py`、`test_no_test_usage.py`。
- 验收：`verify_incremental_factor_selection.py` **12/12 PASS**。
- 冻结：`factor_selection_manifest.json` 记录候选、折、模型、种子、
  数据快照、git commit、配置 sha256；配置改动会导致 freeze 校验失败。

### 9.7 下一步

**不自动进入**新闻/GUI/portfolio。本阶段完成后停下汇报。

---

## STEP 10: Clean Forward Holdout + Paper Live Monitoring

> 目标：从 **2026-09-18** 起建立一个真正只记录、不参与任何选择的 clean
> forward holdout，并把当前研究候选策略变成一个可持续运行的 paper-live
> 观察系统。
>
> 这一阶段不是继续优化策略，不是挖因子，不是调参数。核心是
> **LIVE RESEARCH DISCIPLINE**。
>
> 状态：**COMPLETED**（2026-09-19）
> 配置：`config/paper_live.yaml`｜包：`paper_live/`
> 报告：`reports/step10_forward_holdout.md`

### 10.1 历史 test 状态：正式降级

2024-2025 已被评估 **3 次**（STEP 6 终评、step8 微结构消融、step9 独立信息
研究），不再是 untouched test。正式标记为 **`HISTORICAL_TEST_OBSERVED`**，
只读、只报告。今后任何报告不得再写 "strict untouched test"。

### 10.2 clean forward holdout

- **起点 2026-09-18**（最后一个已被观察日期的次日；2026-01-01~09-17 曾用于
  paper-live 建议生成，不干净）。
- **`record_only = true`**：只记录 / 观察 / 评估。绝不用于选因子、选模型、
  调参数、调 prompt、调阈值、调成本、调 top_k、调调仓频率、调优化器、
  调风险限制。
- 表现差**不自动改**，表现好**也不自动加强**。

### 10.3 冻结了什么，为什么是 strategy_v2

依据**已有冻结状态**选择，不重新优化（spec §4）：

1. 只有 `config/strategy_v2.yaml` 带 `paper_live` 块（capital 500000）；
   `pipeline/signals.py` 也把 S3 称为 "the FROZEN production model"。
2. alpha = **S3**（Alpha158 + factor_pack_v1 + news）在 STEP 5 通过
   research+validation 增量检查（D > B）。
3. allocation = **equal_weight**，由 STEP 6 的研究期 + 验证期选出。
4. strategy_v2 的 candidate gates 有 **2 项未通过**，但两项都在 frozen test
   上。spec §4 明令不得依据 test 结果重新选择 —— 用它去否掉与用它去选中
   同样违规。因此原样保留，作为已知 caveat 带进观察期。

**冻结可证明**：config / model / feature pack 的 sha256 逐日校验。
`config_sha256()` 排除 freeze 块本身（否则写入 freeze 会改变 config 哈希，
形成自指，永远报 drift）。

### 10.4 Paper live 引擎（一条路径，两处使用）

同一段代码既跑历史引擎验证、也跑未来实盘观察，唯一差别是 root 与日期。

- **T 日收盘信号 → T+1 开盘成交**（禁止同日成交）。
- 100 股整数倍；理论股数 ≠ 实际股数，残差现金显式记录。
- 停牌 / 涨停（买）/ 跌停（卖）/ 无行情 → `NO_TRADE` 并记录原因。
- **先卖后买**（否则中间现金会变负；现实中卖出资金可立即用于买入）。
- **现金守卫**：下单按 T 日收盘价算、成交在 T+1 开盘，跳空高开时实际花费
  会超过计划 —— 钱不够就减量或不下单，绝不透支。
- **挂单机制**：当天收盘后运行时 T+1 尚未开盘，订单挂起，下次运行按
  T+1 开盘价成交。不这么做的话每次调仓信号都会"报出去但永远不成交"。
- **按日幂等**：同一天重跑是无操作（调度器重复触发不会把账户交易两次）。

### 10.5 append-only 与 revision

- 已写下的观测**永不覆盖**（内容不同即 `PermissionError`）。
- **不可回填**：新写入日期不得早于已记录的最大 forward 日期。
- 确实遇到数据源 bug 时必须给 `reason`，写新 revision，**旧版本保留**，
  并在 `revisions.jsonl` 留痕。
- `created_at` 不参与"是否变了"的比较（否则重跑必然产生 revision）。

### 10.6 监控（只观察，不反馈）

- 漂移四类：strategy（哈希）/ model（预测分布 z）/ news / data。
- 9 类告警：`PIT_FAILURE`、`STRATEGY_DRIFT`、`MODEL_DRIFT`、
  `CONCENTRATION_WARNING`、`DRAWDOWN_ALERT`、`ABNORMAL_TURNOVER`、
  `IC_NEGATIVE_STREAK`、`DATA_QUALITY_WARNING`、`STRATEGY_UNFROZEN`。
- **告警只报警**：不交易、不减仓、不改参数。告警文本里不得出现下单动作
  （`tests/forward/test_alerts.py` 有断言守着）。
- 样本不足时不给结论：窗口未走完记 NA（不填 0）；净值 < 60 天不年化、
  不算 Sharpe；年度不足 230 个观测日标记 `INCOMPLETE YEAR`。

### 10.7 历史引擎验证（24 个调仓日）

用**完全相同的引擎路径**跑 2024-01 至 2025-12 的 24 个调仓日，
结果写入 `experiments/paper_live/engine_validation/`（**未写 2026
forward holdout**）：

- T+1 成立（全部成交日严格晚于信号日）。
- 手数、成本、停牌/涨跌停 NO_TRADE、无未来数据全部通过。
- 观察到 2024-09-30 只成交 22/40（当月末 A 股急涨，多只标的涨停买不进），
  现金一度到 91.7% —— 这是**真实约束的如实记录**，不是 bug。

报告：`reports/paper_live_engine_validation.md`。

### 10.8 本阶段修掉的问题

| # | 问题 | 后果 |
|---|---|---|
| 1 | 持仓按上次成交价（成本）估值，而非当日市价 | delta 全错 → 超买超卖 → 现金变负 |
| 2 | 买卖按代码顺序执行 | 中间现金为负 |
| 3 | 按 T 收盘价下单、T+1 开盘成交，无现金守卫 | 跳空高开透支账户（实测 2025-04-30 现金 −3.3%） |
| 4 | T+1 未开盘时订单直接丢失 | 实盘每次调仓都"报出去但不成交" |
| 5 | 引擎绕过 provider 读全局日历 | 测试与真实日历不一致，T+1 判定错误 |
| 6 | PIT 审计查"库里有啥"而不是"消费了啥" | 历史回放被误判为 INVALID（price / financial / news 三处） |
| 7 | `write_freeze` 用 `yaml.safe_dump` 整份重写 config | 抹掉全部注释（"为什么这么冻结"的记录） |
| 8 | config 哈希包含 freeze 块 | 自指：写入 freeze 即改变哈希，永远 drift |
| 9 | 告警格式化未防 `None` | 漂移字段缺失时 `TypeError` 崩溃 |
| 10 | gitignore 被整份重写 | 丢掉 94 行按阶段分层的忽略规则，373 个文件暴露 |

### 10.9 代码与验收

- 新增包 `paper_live/`：`config`（冻结哈希）、`store`（append-only +
  revision）、`engine`（单日运行）、`execution`（手数/下单/T+1 成交）、
  `data`（唯一数据接触面）、`metrics`、`audit`（PIT）、`drift`、`alerts`、
  `report`。
- 脚本：`scripts/paper_live/{run_daily,run_rebalance,check_alerts,`
  `monthly_report,audit,freeze,validate_engine,build_dashboard}.py`、
  `scripts/install_scheduler.ps1`（默认 dry-run）、`scripts/verify_step10.py`。
- 测试：`tests/forward/` 13 个文件、**94 个测试**。
- 验收：`verify_step10.py` 21 项。
- 文档：`docs/{forward_holdout,paper_live,strategy_freeze,`
  `paper_live_execution,forward_monitoring}.md`。

### 10.10 下一步

**不自动进入 STEP 11。** 本阶段完成后停下汇报。

下一阶段（未开始）：**STEP 11: Build Personal Portfolio / Wealth Management + GUI**。
