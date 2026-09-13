# CLAUDE.md — 本项目 AI 协作开发规范

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

Tradeoff: These guidelines bias toward caution over speed. For trivial tasks, use judgment.

1. Think Before Coding
Don't assume. Don't hide confusion. Surface tradeoffs.

Before implementing:

State your assumptions explicitly. If uncertain, ask.
If multiple interpretations exist, present them - don't pick silently.
If a simpler approach exists, say so. Push back when warranted.
If something is unclear, stop. Name what's confusing. Ask.
2. Simplicity First
Minimum code that solves the problem. Nothing speculative.

No features beyond what was asked.
No abstractions for single-use code.
No "flexibility" or "configurability" that wasn't requested.
No error handling for impossible scenarios.
If you write 200 lines and it could be 50, rewrite it.
Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

3. Surgical Changes
Touch only what you must. Clean up only your own mess.

When editing existing code:

Don't "improve" adjacent code, comments, or formatting.
Don't refactor things that aren't broken.
Match existing style, even if you'd do it differently.
If you notice unrelated dead code, mention it - don't delete it.
When your changes create orphans:

Remove imports/variables/functions that YOUR changes made unused.
Don't remove pre-existing dead code unless asked.
The test: Every changed line should trace directly to the user's request.

4. Goal-Driven Execution
Define success criteria. Loop until verified.

Transform tasks into verifiable goals:

"Add validation" → "Write tests for invalid inputs, then make them pass"
"Fix the bug" → "Write a test that reproduces it, then make it pass"
"Refactor X" → "Ensure tests pass before and after"
For multi-step tasks, state a brief plan:

1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

These guidelines are working if: fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

本文件给后续在此项目中工作的 Claude 提供开发规范。

## 项目定位

个人用 A 股低频量化投资研究与决策系统。**完全本地运行**，按 ROADMAP.md 分阶段推进。
当前阶段定义见 ROADMAP.md 顶部，**严禁超前开发未开始的阶段**。

## 铁律

1. **分阶段开发**：只做当前阶段（见 ROADMAP.md 状态行）。完成一个阶段后停下来
   汇报，未经用户明确指示不得自动开始下一阶段。
2. **严禁实盘交易**：任何阶段都不得接入券商 API、自动下单或涉及真实资金操作。
3. **不伪造结果**：不得修改官方示例/基准逻辑来“制造更好结果”；不得使用未来数据
   （标签与特征的时间对齐以 Qlib 官方实现为准）。
4. **不污染系统 Python**：所有 Python 工作都在项目虚拟环境 `.venv` 中进行。
   `.venv` 基于用户级安装的 Python 3.12（见 docs/environment_check.md 的决策）。
5. **不删除用户已有文件**：修改/删除前先查看内容，重要操作前确认。
6. **不跳过错误**：安装、导入、数据、workflow 任何一步失败都必须诊断并修复，
   不得静默绕过或降低标准。
7. **Qlib 版本锁定**：pyqlib 固定 0.9.7（官方最新，含 cp312 win wheel）。
   官方 Python 支持上限为 3.12，**不要升级到 3.13**。

## 环境速查

```bash
# 激活虚拟环境（Windows Git Bash）
source .venv/Scripts/activate

# 安装依赖（必须用官方 PyPI 索引——清华镜像缺 pyqlib）
python -m pip install -i https://pypi.org/simple <pkg>

# 验证环境
python scripts/verify_step1.py

# 官方 workflow（数据路径指向 qlib_data）
PYTHONIOENCODING=utf-8 MPLBACKEND=Agg MLFLOW_ALLOW_FILE_STORE=true \
    qrun config/workflow_config_lightgbm_Alpha158.yaml
```

- 数据目录：`qlib_data/`（来源 chenditc/investment_data 2026-09-04 release，
  qlib 官方 README 推荐数据源；官方 CLI 数据集已按官方声明暂停，且其回退包缺
  Alpha158 必需的 `vwap` 字段，勿再使用。日历 2000-01-04 ~ 2026-09-04）
- workflow 配置：`config/workflow_config_lightgbm_Alpha158.yaml`
  （内容与官方 `qlib v0.9.7 examples/benchmarks/LightGBM/` 中的配置一致，
  仅 `provider_uri` 指向项目本地数据目录）
- 日志：`logs/`；实验报告：`reports/`；mlflow 产物：`mlruns/`（git 忽略）
- **mlflow 3.x 必须加 `MLFLOW_ALLOW_FILE_STORE=true`**，否则 qlib 0.9.7 的
  文件存储 recorder 直接报 MlflowException（详见 reports/step1_qlib_baseline.md）

## 关键背景（决策记录）

- 系统原有 Python 3.13.8 无 pyqlib wheel（官方最高 cp312），因此用 winget 用户级
  安装了 Python 3.12 并创建项目 `.venv`。系统 Python 3.13 保持不动。
- pip 默认清华镜像缺 pyqlib，凡装 Qlib 相关包必须 `-i https://pypi.org/simple`。
- Win11 上 wmic 已被移除，系统信息查询用 `Get-CimInstance`。
- 机器 20 线程 / 32GB / RTX 4070 Ti：LightGBM 用 20 线程跑官方 workflow 可行；
  GPU 留给后续深度学习阶段。
- 官方 workflow 在本机（20 线程）完整跑一次约 2 分钟；跑之前先
  `python scripts/verify_step1.py`。
- **pandas 必须固定在 2.2.x**（qlib 0.9.7 为 pandas 2.x 时代产物，
  pip 会自动装 3.x，需显式 `pip install pandas==2.2.3`）。

## 本阶段（STEP 1）红线

以下内容属于后续阶段，**STEP 1 内不得开发**：实盘/券商 API/自动下单、新闻系统、
LLM 新闻分析、自定义复杂因子、Transformer、强化学习、GUI、Tushare、AkShare、
自动因子挖掘。

## STEP 2 数据层要点（2026-09-05 起）

- 分层：RAW（data/raw/）/ CANONICAL（data/parquet/ + DuckDB）/ DERIVED；
  研究数据与原始数据不混放。全部大文件 git 忽略。
- 股票代码唯一写法：`600519.SH`（personal_quant.symbols.normalize_symbol）。
- **价格口径**：canonical daily_bars 是**原始价格**（源 Yahoo 调整价 ÷ factor，
  factor 列保留）；任何复权需求用 factor 现场计算。
- **禁止全量下载年报 PDF**（sse-reports-archive 的 phase3b 永不运行）；
  只按需取单份 PDF（LEVEL 3 缓存默认关），提取结果永久入 financial_metrics。
- **PIT 铁律**：财务数据可用 ⟺ as_of_date > announcement_date；
  availability_date_unknown=true 的数据 strict 模式禁用。URL 派生公告日
  越界自动降级 unknown，不猜。
- 离线/在线：`PQ_MODE=offline` 禁网；历史回测必须 OFFLINE。
  在线抓取：单连接、随机 1-3s 延迟、指数退避、raw 缓存，禁止高并发/WAF 绕过。
- 东财 push2/push2his 会被 WAF 间歇封禁：估值快照用腾讯行情，日线对照用
  腾讯 K 线（provider 已内置回退）；系统代理 7890 不可靠，默认直连。
- 数据源/口径/决策全部记录于 docs/data_sources.md；每步导入登记 source_registry。
- 质量门禁：bootstrap 自动跑 quality.checks（16 项），verify_step2.py 19 项
  验收，改动数据管线后必须全绿再提交。
- 本阶段不修改 Qlib provider；STEP 3 再决定 Custom Provider 还是
  Dataset 层直读 DuckDB。

## STEP 3 策略要点（2026-09-08 起）

- 策略代码：personal_quant/strategy/；配置唯一来源 config/strategy_v1.yaml
  （参数改动必须新开 run 并记录，严禁为收益调参）。
- qlib 集成：只替换 FeatureProvider（qlib.init kwargs 注入），
  qlib 官方 expression/Alpha158 原样运行；qlib 语义中 Ref($close,-N) 是
  **未来 N 日**数据（官方 label 即为此设计）——任何 label 列严禁进入特征。
- 特征/标签缓存：data/derived/features（按月）、labels（按**日**键，勿改回月键）。
- 多进程铁律：qlib 的 joblib pool 在 Windows 上第二个 dataset() 调用会死锁；
  特征计算必须走每季度独立子进程（features.py 已实现，勿改回进程内循环）。
- DuckDB 单进程独占：实验运行期间不要并发跑其它 DB 任务。
- 执行模型：T+1 开盘、涨跌停/停牌 NO_TRADE、100 股手数、成本可配置
  （docs/step3_execution_model.md）。
- 泄漏审计与 sanity check：scripts/audit_point_in_time.py、
  scripts/sanity_check_strategy.py；改动策略后必须重跑。
- canonical 层修复（factor 跳变/NaN 占位行）已注册 source_registry；
  质量检查现为 18 项，bootstrap 自动执行。

## STEP 4 因子研究要点（2026-09-08 起）

- **冻结纪律**：strategy_v1 完全冻结；2024-2025 是 FROZEN TEST SET；
  2026 是 paper live；**因子选择只能用 2018-2023（research+valid）**，
  test 只做一次最终评估，严禁先看 test 再选因子。发现真实 bug 才修
  strategy_v1（单独修复并记录）；STEP 4 发现的指数伪标的入池问题
  （run_001 从未选中它们，影响为零）已记录，strategy_v1 代码未动。
- 因子平台：`factors/` 包（base/registry/technical/valuation/quality/
  growth/fundamental/normalization/evaluator/selection/mining/reports）；
  配置唯一来源 config/factor_research.yaml（参数改动必须新开 run）。
  因子代码不依赖 qlib、不调用策略模块。
- DERIVED 缓存：data/derived/factors/（calendar/labels/universes/
  financial_metrics 快照/industries）由 scripts/factor_prepare.py 生成；
  改数据管线后必须重跑 prep。研究脚本只读缓存（DB-free），
  可与 fetcher 并行；**任何 DuckDB 任务必须等 fetcher chunk 结束**。
- 市场数据修复：volume/amount 存在**每股常数缩放**（Yahoo 伪影，
  跨股差 ~230×）→ 校准表 data/parquet/market/market_scale.parquet
  （scripts/calibrate_market_scale.py，腾讯 K 线 ground truth，
  repair_version 记录）；**canonical 原列永不修改**；因子引擎使用
  校准列 amount_cny/volume_shares（fallback scale=1 并记录）。
  指数伪标的（000300/000852/000905/000906/000985.SH、399300.SZ）
  在因子股票池显式排除（config index_exclude）。
- 财务因子 PIT：可用 ⟺ signal_date > availability_date（=公告日，
  次一交易日可用），全系统唯一口径；availability_date_unknown 一律
  禁用。提取器 v1.1 新增 eps/bps（per_share 类不受报表单位乘数影响）。
  银行/保险无营业成本 → gross_margin 诚实 MISSING；负 PE 保留不删。
- 财务数据获取：lazy 增量（scripts/fetch_financial_universe.py，
  chunked 运行、断点续跑）；**严禁全量下载年报 PDF**；覆盖率如实报告
  （reports/step4_financial_factor_coverage.md），绝不猜值提覆盖率。
- Alpha Mining：shallow beam search（深度≤3、算子白名单
  + - * / rank zscore log abs、每代≤1000 候选）；search 只用 research、
  validation 排序、test 单次；**snooping diagnostics（候选数/各期最优分）
  必须记录**；mined 因子是 research candidate（factor_pack_v2 池），
  不是生产策略。

## STEP 5 新闻因子要点（2026-09-09 起）

- **Provider 抽象**：news/providers/（BaseNewsProvider + SSE/SZSE/CNINFO/
  AkShare）；业务层禁止直接 requests；官方交易所优先；被封禁记录
  SOURCE_BLOCKED 换合法源；低并发、随机 1-3s 延迟、重试退避、raw 缓存。
- **SSE 公告 API 分页陷阱**：pageHelp.pageNo 被忽略——分页必须用
  pageHelp.beginPage/endPage；pageSize=1000 一天一请求。旧分页代码会把
  >100 条的交易日截断（已用 --repair-truncated 修复，勿回退）。
- **PIT 铁律**（docs/step5_news_pit.md）：发布日≤15:00 → 当日可用；
  盘后/周末/节假日/仅日期 → 下一交易日 09:30；发布日未知 → strict
  禁用。event_time 与 publication_time 分开，因子只用 availability；
  updated_at 绝不代替 published_at。全链路 Asia/Shanghai tz-aware。
- **事件层**：规则分类（25 类，news/events.py，方向为 candidate）→
  NewsEvent；LLM 层（DeepSeek，结构化 JSON、prompt 版本、cache、
  budget）仅在 DEEPSEEK_API_KEY 存在时启用，无 key 时 RULE_BASED_ONLY
  （系统不因此失败）。LLM 输出绝不直接交易。
- **因子语义**：窗口按自然日（daily 日历 rolling）；计数因子 0=无事件
  （真实信息）；sentiment/importance/novelty/risk 无事件 = 0（中性，
  建模选择）；attention/shock 为比值语义，零基线 = NaN（未定义）。
  覆盖率：未抓取股票 NaN，绝不把缺失年填 0。
- **数据层**：canonical news_documents（DuckDB，document_id 去重 +
  source_count）；derived news_events/news_factors（parquet 快照，
  因子引擎直读）。backfill：SSE 按日全量（官方）；SZSE 按股（cap 排序，
  增量续跑）；incremental 模式只推进已 settle 的日期（官方索引滞后
  ~5 天）。
- 新闻因子进 FACTOR_REGISTRY（category=news），复用 STEP 4 评估引擎；
  选择只用 2018-2023；strategy_v1_news 不覆盖 strategy_v1。

## STEP 6 组合优化要点（2026-09-10 起）

- **SIGNAL != ALLOCATION**：alpha 信号冻结 = S3（Alpha158 + factor_pack_v1
  + news，STEP 5 增量检查 D>B 确认）；portfolio/ 只做 allocation，绝不
  重训 alpha、绝不静默改 alpha 排名（raw_rank 全程保存）。
- 引擎锚点：**P0 等权必须逐位复现 strategy_v1_news（drift 0.0000）**；
  改动执行/成本/股票池语义后必须重跑 `research_portfolio.py --method
  equal_weight --period test --check-anchor`。
- 候选不足（< top_k）时按冻结的"每股 invest_target/top_k"等比缩放目标，
  其余留现金（effective_target；锚点一致性的前提，勿改成集中持仓）。
- **P0 等权是冻结基线分配，不施行业上限**（否则锚点不可复现）；
  P1-P6 强制 max_weight 10% / sector_cap 20% / 无做空 / 无杠杆 /
  cash_buffer；优化器失败走回退链（方法→inverse_vol→equal_weight）并
  记录 optimizer_status/fallback_reason。
- 协方差 PIT 铁律：每次调仓只用 <= signal_date 的收益；sanity gate
  （对称/PSD/对角/条件数/NaN）不过关则修复链 sample→Ledoit-Wolf→对角，
  绝不静默提交不稳定矩阵；历史 <20 有效收益的股票被剔除时按等比缩放
  目标（_cov_aligned），勿直接丢弃。
- 选择协议**先于结果写死**（scripts/portfolio/run_portfolio_study.py
  docstring）：只用 research 2018-2021 + valid 2022-2023；test 单次评估。
  修改协议 = 新开实验并记录，禁止看结果改规则。
- strategy_v2（config/strategy_v2.yaml）= S3 + 选定分配；9 项 candidate
  gates 即使 FAIL 也如实记录，不重写门槛；未通过全部 gate 就保持研究
  候选、不晋升生产。
- 换手统一定义 T = 0.5·Σ|w_new − w_old|（含被清出持仓）；成本复用
  strategy_v1 的 TransactionCostModel（公平比较，勿另写一套）。
- 审计与可解释性每次调仓全部落盘（experiments/portfolio/ 每个 run 的
  weights/audit/trades/metrics）。

## 数据刷新与板块权限（2026-09-13 起）

- **行情刷新**：canonical 由 chenditc/investment_data 快照构建 →
  `scripts/quant/update_market_snapshot.py`（下载最新 release、切换
  qlib_data/、重新 ingest 新年份）；旧快照保留为 qlib_data_old/ 直到
  人工确认。增量"逐股抓取"不可行（数千只 × 单连接）。
- **每次刷新后必须跑**：`pytest tests/market_data` —— 新快照可能引入
  源侧缺陷。2026-09-12 快照就把 7 只标的的历史 factor 重定基准
  （原始价连续、复权价跳 2~6 倍）→
  `scripts/quant/repair_factor_rebase.py` 修复（把跳变后的正确水平
  反向外推到历史段；与修复方向相反的 `scripts/repair_factors.py`
  相区分）。修 factor 后必须重跑 factor_prepare（labels 会变）。
- **板块交易权限**：trade_plan/boards.py 判定板块与开通门槛
  （科创板 688 = 50 万 + 24 个月；创业板 300/301 = 10 万 + 24 个月；
  北交所 = 50 万；主板/ETF 无门槛）。**交易计划默认先按权限过滤再取
  Top-K**（`exclude_restricted=True`），被排除的标的写入
  `plan["excluded_restricted"]` 完整展示，绝不静默丢弃。
- 账户资金/经验来自 `config/account_profile.yaml`
  （capital + experience_months；auto_detect_capital 与财富库取大值）。
  经验未核实时**只提示不禁止**；资金临界（< 1.2× 门槛）时提示
  "20 日均资产需核实"。
- **小资金 K 规则**（`suggest_top_k`）：在「持仓 ≥ 5 只且投入 ≥ 60%」
  前提下取最大 K，只依据资金/手数算术，**不读任何收益或回测数字**；
  单只上限随之抬升（`_effective_max_weight`，K≥20 时仍为 10%，
  STEP 6 锚点不受影响）。
- 运行时 `refresh_all.py` 的 job 会把 argv 透传给被调脚本 →
  `pipeline/refresh.py:_own_argv()` 负责屏蔽（否则 argparse 冲突）。

## STEP 7 个人财富与 GUI 要点（2026-09-10 起）

- **Research DB（DuckDB/Parquet）与 Wealth DB（SQLite
  data/wealth/wealth.db）严格分离**：wealth/ 绝不 import duckdb、绝不
  引用研究回测产物；真实财富记录绝不进入 backtest。
- **P&L 铁律**：`Investment P&L = Ending − Beginning − 外部净流入`；
  只有 deposit/withdrawal/transfer_in/out 是外部流（DB 层强制），
  buy/sell/申购/赎回是内部流（cash_flow 必须为 0）。任何"今日资产 −
  昨日资产 = 收益"的写法都是 bug。
- **万份收益**：货币型产品用"当日有效份额"计算（日内转入按时间加权，
  时间未知按 0.5 并标 estimated），绝不用期末份额（会造出虚假的
  收益率下跌）；口径 exact/estimated 必须落库。
- 财富库所有写入走 wealth/repository.py（自动写 audit_log）；
  交易修改/删除必须给 reason；产品/账户改名等都要留痕。
- **数据新鲜度**：GUI 必须显示 Data Status；STALE 数据不得静默使用；
  刷新失败要 raise（job store 记录 FAILED），离线任务记 SKIPPED，
  **绝不把跳过记成成功**；交易日历本身滞后时市场域一律 STALE。
- **预测**：1D/5D/20D 为冻结分数的条件分布（20 分位桶 + 桶心插值），
  PIT embargo（只用预测日之前已结束窗口的样本）；不新增未过验收门
  的模型（spec §43）。
- **交易计划**：入场区间来自个股波动（上限 3%）+ 计划价；目标价/
  止损是模型估计不是承诺；卖出必须带原因；手数 100 股整数倍；
  成本复用 strategy_v1 的 TransactionCostModel（禁止第二套费率）；
  系统只输出建议，**永不自动下单**。
- **GUI 铁律**：只绑定 127.0.0.1（启动器拒绝外部绑定）；零外部资源
  （无 CDN/无外链，有测试断言）；pages.py 只做格式化（AST 测试禁止
  其 import 任何引擎）；金融计算只在 services.py/引擎层。
- LLM 只能是研究辅助（摘要/分类/解释），绝不影响信号与回测可复现性。
- DuckDB 单进程：**不要并发跑 verify/测试与 fetcher**（会锁冲突）。
