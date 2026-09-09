# STEP 4 财务因子 PIT 规则（统一口径）

## 1. 全系统唯一可用性规则

财务事实（年报/指标）对信号日 `d` 可用 ⟺ **`d > availability_date`**，
其中 `availability_date = announcement_date`（公告日）。即：公告日当天
不可用，从公告次一交易日开始可用（信号只发生在交易日，日历日"次日"
与"次一交易日"等价）。

- 例：2024 年报公告 2025-04-01 → 2025-03-31 不可用、2025-04-01 不可用、
  2025-04-02（次一交易日）起可用。
- `availability_date_unknown = true` 的数据 **strict 模式一律禁用**
  （因子管线为 strict）。
- 该规则与 STEP 2 的查询 API、`docs/point_in_time.md` 完全一致——
  全系统只有这一处口径，不存在"有的地方公告当日可用"。
- 实现：factors/fundamental.py 的 PIT join 逐信号日过滤
  `availability_date < d` 后按每股取最新财年值（等价于 merge_asof
  严格向后语义；tests/factors/test_pit_financial.py 覆盖公告日前/
  当日/次日三种情况）。

## 2. 财务因子定义（全部 PIT、全部来自年报）

| 因子 | 公式 | 特殊科目处理 |
| --- | --- | --- |
| roe | 披露加权平均 ROE；缺披露时 net_profit/net_assets（期末近似，报告注明 source_type） | 银行/保险披露口径照常提取 |
| roa | net_profit/total_assets（存储派生值） | — |
| gross_margin | (revenue-cost)/revenue | 银行/保险无营业成本 → MISSING（EXTRACTION_FAILED，不造值） |
| net_margin | net_profit/revenue | — |
| debt_to_asset | total_liabilities/total_assets | 银行 0.9+ 是真实结构，不做特殊截断 |
| revenue_growth / net_profit_growth | 同一报告上年列 t/(t-1)-1 | 上年列缺失 → MISSING，不猜 |
| operating_cash_flow | 绝对额（规模代理；可比形式见下两行） | — |
| ocf_to_assets | ocf/total_assets | 分母为 0 → NaN |
| ocf_to_net_profit | ocf/net_profit | \|net_profit\|≤1e-8 → NaN（无意义比值） |
| pe | close/eps | **eps<0 保留为负 PE**（亏损本身有信息；rank 归一化天然处理，绝不静默删除） |
| pb | close/bps；bps=披露每股净资产，缺失时 net_assets/(net_profit/eps)（同一报告三个披露数推算，亏损公司符号相消） | bps≤0 → NaN |
| ps | close×shares/revenue；shares=net_assets/bps（同 pb 口径） | revenue≤0 或 shares 缺失 → NaN |
| earnings_yield | eps/close | — |
| turnover_20/60 | MA(volume_shares,20/60)/shares | 只覆盖财务股票池（见 docs/step4_market_data_quality.md §4） |

每股指标（eps=基本每股收益、bps=归属于上市公司股东的每股净资产）由
提取器 v1.1 从"主要会计数据"章节提取；每股值**不受报表单位乘数影响**
（万元等单位只作用于金额行，per_share 类型按元/股直取——测试覆盖）。

## 3. 财务股票池与覆盖率（如实报告）

- 财务股票池 = 当前总市值前 300 的 A 股（大市值样本；存在大市值/生存者
  偏倚，已注明）。抽样原因：全市场 31,000+ PDF 严禁批量下载
  （STEP 2 铁律），lazy 管线单连接礼貌抓取，300×9 财年 ≈ 2,700 份
  是单会话可行规模。
- 覆盖率报告：reports/step4_financial_factor_coverage.md（按年 × 因子
  的 available_stocks/coverage_ratio）。**绝不为了提高覆盖率猜测数据**。
- 因子评估仍以全市场股票池为准（缺财务数据的股票 → 因子 MISSING，
  主评估 missing=drop，不做全市场 sector 填充冒充）；受限股票池
  （financial universe）评估单独输出；Model C 两个变体
  （C_full 全市场 + sector 中性填充 vs C_res 受限股票池）都跑并对比，
  不偷偷改股票池。

## 4. 缺失值策略（记录在案，不做静默填充）

- 主研究：技术因子 sector_median（CSRC 行业当前分类；行业变更罕见，
  限制已记录），财务因子 drop（只有真实值参与）。
- 对照：drop / cross_median / sector_median 三种策略的比较
  （config/factor_research.yaml missing.method；tests/factors/
  test_missing_data.py）。

## 5. 方向约定

registry 的 direction 是**经济直觉方向**（如 高 ROE=positive、
高负债=negative）；实证方向（empirical_direction）由评估器单独记录，
**绝不为了 IC 好看翻转因子方向**；方向未知/混合的因子标 neutral，
以数据为准（spec 第 13/33 条）。

## 6. 增量抓取与缓存（lazy + incremental）

`scripts/fetch_financial_universe.py`：逐（股票×财年）检查
financial_metrics 已有指标 → 缺则走 STEP 2 按需管线（metadata → CNINFO
单份 PDF → 提取 v1.1 → 校验 → financial_metrics + extraction_audit）；
已提取的报告永不重下（v1.0 老提取缺少 eps/bps 时补提取一次）。
可断点续跑；每 50 份刷新一次因子引擎快照
data/derived/factors/financial_metrics.parquet。
