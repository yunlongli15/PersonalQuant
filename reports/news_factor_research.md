# 新闻因子研究（News Factor Research）

> 生成：`python scripts/news/run_news_factor_research.py`  
> 生成时间：2026-10-06T00:09:58  
> 新闻数据：`news_events_v2`（修复 SSE 采集后的集合），版本 `v2`  
> 因子版本：`news_research_0.1`

**本阶段不训练任何模型。** S3_v1 / S3_v2 / production_strategy / recommendation 全部未改动。

---

## 1. Data Source

| 项 | 值 |
|---|---|
| 事件表 | `news_events_v2` |
| 公告表 | `news_documents_v2` |
| 事件数（可用时间完整） | 2,004,764 |
| 股票数 | 4,909 |
| 事件日期范围 | 2014-11-03 ~ 2026-09-30 |
| 信号日（月频，月末最后交易日） | 105 个 |
| 评估区间 | 2018-01-01 ~ 2026-09-30 |

> 公告**正文不存在**：`news_documents_v2` 没有 `content` 列，事件层 `sentiment` / `risk` / `financial_impact` / `event_time` 四列 100% 为空。因此本阶段只用「标题 + 事件类型 + 方向 + 严重度 + 时间」这些结构化字段，不使用任何 NLP 输出 —— 与 spec §二十 一致。

---

## 2. Event Taxonomy

生产分类器（`news/events.py`）把 **57.3%** 的公告归入 `other`。研究层 taxonomy 在此基础上细分（不改上游代码，只读叠加）：

| materiality | 占比 |
|---|---|
| substantive | 50.9% |
| procedural | 28.3% |
| unknown | 20.8% |

细分后新增的可识别类别（此前全在 `other` 里）：

| 主题 | 占全部公告 |
|---|---|
| `procedural` | 28.28% |
| `equity_incentive` | 3.24% |
| `related_party` | 2.37% |
| `guarantee` | 1.61% |
| `debt_default` | 0.83% |

> **最重要的发现**：约 **30%** 的公告是纯程序性的（股东大会通知与决议、公司章程修订、法律意见书、内控制度）。任何「公告数量」类因子都有一大块波动来自行政流程，而不是信息。这就是为什么下面把 `procedural_count_20d` 设成**阴性对照**。

---

## 3. Candidate Factors

共 **31** 个候选因子（spec 要求 15–30）。

| # | 因子 | 定义 | 窗口 | 先验方向 | 类型 |
|---|---|---|---|---|---|
| 1 | `negative_event_count_5d` | 实质性负面事件数，过去 5 个交易日 | 5d | negative | sum |
| 2 | `negative_event_count_20d` | 实质性负面事件数，过去 20 个交易日 | 20d | negative | sum |
| 3 | `negative_event_count_60d` | 实质性负面事件数，过去 60 个交易日 | 60d | negative | sum |
| 4 | `negative_event_severity_20d` | 实质性负面事件的严重度之和（按 taxonomy 先验加权），20 日 | 20d | negative | sum |
| 5 | `regulatory_negative_count_20d` | regulatory 类事件数，20 日 | 20d | negative | sum |
| 6 | `litigation_negative_count_20d` | litigation 类事件数，20 日 | 20d | negative | sum |
| 7 | `investigation_count_20d` | investigation 类事件数，20 日 | 20d | negative | sum |
| 8 | `penalty_count_20d` | penalty 类事件数，20 日 | 20d | negative | sum |
| 9 | `pledge_risk_count_20d` | pledge 类事件数，20 日 | 20d | negative | sum |
| 10 | `shareholder_reduction_count_20d` | shareholder_reduce 类事件数，20 日 | 20d | negative | sum |
| 11 | `material_negative_count_20d` | 剔除程序性公告后的负面事件数，20 日 | 20d | negative | sum |
| 12 | `debt_default_count_20d` | 债务违约/破产重整/冻结类事件数，20 日 | 20d | negative | sum |
| 13 | `positive_event_count_5d` | 实质性正面事件数，过去 5 个交易日 | 5d | positive | sum |
| 14 | `positive_event_count_20d` | 实质性正面事件数，过去 20 个交易日 | 20d | positive | sum |
| 15 | `positive_event_count_60d` | 实质性正面事件数，过去 60 个交易日 | 60d | positive | sum |
| 16 | `repurchase_count_20d` | buyback 类事件数，20 日 | 20d | positive | sum |
| 17 | `shareholder_increase_count_20d` | shareholder_increase 类事件数，20 日 | 20d | positive | sum |
| 18 | `major_contract_count_20d` | major_contract 类事件数，20 日 | 20d | positive | sum |
| 19 | `equity_incentive_count_20d` | equity_incentive 类事件数，20 日 | 20d | positive | sum |
| 20 | `news_intensity_20d` | 实质性公告数 / 该股过去 120 日自身均值 | 20d | unknown | ratio |
| 21 | `abnormal_news_intensity_20d` | 实质性公告数的自身 z 分数（基线 120 日） | 20d | unknown | zscore |
| 22 | `first_negative_event_20d` | 过去 180 日首次出现负面事件（0/1），20 日窗口内 | 20d | negative | first |
| 23 | `new_event_type_count_20d` | 过去 180 日未出现过的主题数，20 日窗口内 | 20d | unknown | sum |
| 24 | `weighted_negative_event_20d` | 负面事件按 0.5^(龄/10交易日) 指数衰减加权 | 20d | negative | decay |
| 25 | `negative_event_days_20d` | 窗口内**有**负面事件的天数（不是条数） | 20d | negative | sum |
| 26 | `positive_negative_balance_20d` | (正面数 - 负面数) / (正面数 + 负面数 + 1)，20 日 | 20d | positive | balance |
| 27 | `positive_negative_balance_60d` | (正面数 - 负面数) / (正面数 + 负面数 + 1)，60 日 | 60d | positive | balance |
| 28 | `negative_positive_ratio_20d` | 负面数 / (正面数 + 1)，20 日 | 20d | negative | ratio2 |
| 29 | `negative_event_streak_60d` | 截至 T 连续出现负面事件的最大天数（60 日窗口内） | 60d | negative | streak |
| 30 | `procedural_count_20d` | 程序性公告数（股东大会/章程/法律意见书/内控制度），20 日 | 20d | unknown | **阴性对照** |
| 31 | `unknown_count_20d` | taxonomy 未能归类的公告数，20 日 | 20d | unknown | **阴性对照** |

## 4. Factor Definitions

每个因子的经济假设（注册表里逐条对应）：

- **`negative_event_count_5d`** — 负面事件提高信息不确定性并压制短期估值，窗口内越多越负
- **`negative_event_count_20d`** — 负面事件提高信息不确定性并压制短期估值，窗口内越多越负
- **`negative_event_count_60d`** — 负面事件提高信息不确定性并压制短期估值，窗口内越多越负
- **`negative_event_severity_20d`** — 同样是一件事，立案调查与一般诉讼的冲击量级差一个数量级；按严重度加权的信息量高于简单计数
- **`regulatory_negative_count_20d`** — regulatory 是具体风险来源，比混合计数更干净
- **`litigation_negative_count_20d`** — litigation 是具体风险来源，比混合计数更干净
- **`investigation_count_20d`** — investigation 是具体风险来源，比混合计数更干净
- **`penalty_count_20d`** — penalty 是具体风险来源，比混合计数更干净
- **`pledge_risk_count_20d`** — pledge 是具体风险来源，比混合计数更干净
- **`shareholder_reduction_count_20d`** — shareholder_reduce 是具体风险来源，比混合计数更干净
- **`material_negative_count_20d`** — **核心对照**：若 negative_event_count 的 IC 主要来自程序性公告，那么把程序性剔除后 IC 应显著下降；不下降才说明信号是真的
- **`debt_default_count_20d`** — 存续性风险事件，预期是最强的单点负面冲击
- **`positive_event_count_5d`** — 正面事件（增持/回购/中标/分红）是管理层与市场之间的正向信号
- **`positive_event_count_20d`** — 正面事件（增持/回购/中标/分红）是管理层与市场之间的正向信号
- **`positive_event_count_60d`** — 正面事件（增持/回购/中标/分红）是管理层与市场之间的正向信号
- **`repurchase_count_20d`** — buyback 的正向含义比混合计数更明确
- **`shareholder_increase_count_20d`** — shareholder_increase 的正向含义比混合计数更明确
- **`major_contract_count_20d`** — major_contract 的正向含义比混合计数更明确
- **`equity_incentive_count_20d`** — equity_incentive 的正向含义比混合计数更明确
- **`news_intensity_20d`** — 相对自身历史的异常放量比绝对条数更能反映信息冲击；绝对条数在很大程度上只是公司规模与活跃度的代理
- **`abnormal_news_intensity_20d`** — 用自身历史标准化，消除公司间固定差异
- **`first_negative_event_20d`** — **重点候选**：首次出现的负面事件信息量最大；第 10 次重复的边际信息接近于零。计数会把两者混为一谈
- **`new_event_type_count_20d`** — 新类型的公告意味着出现了此前没有的经营/治理维度
- **`weighted_negative_event_20d`** — 同样一条负面公告，昨天发生与 20 天前发生对当前定价的含义不同；权重公式取最简单可复现的指数衰减，不做参数搜索
- **`negative_event_days_20d`** — 一天发 5 条和 5 天各发 1 条含义不同：后者说明风险在持续
- **`positive_negative_balance_20d`** — 净情绪方向；分母加 1 是拉普拉斯式平滑，避免无事件股票的 0/0
- **`positive_negative_balance_60d`** — 净情绪方向；分母加 1 是拉普拉斯式平滑，避免无事件股票的 0/0
- **`negative_positive_ratio_20d`** — 与 balance 互补：对负面更敏感的非对称刻画
- **`negative_event_streak_60d`** — 连续暴露说明问题未解决，与单次冲击应当区分
- **`procedural_count_20d`** — **阴性对照**：行政流程公告按经济逻辑不该有预测力。它若拿到显著 IC，说明这套检验在捕风捉影，全表的结论都要打折
- **`unknown_count_20d`** — 第二个阴性对照：分类失败的残余不该携带信息

---

## 5. Data Quality

| 因子 | 唯一值比例 | 缺失率 | 截面标准差 | 截面中位数 | 最大同值占比 |
|---|---|---|---|---|---|
| `negative_event_count_5d` | 0.004 | 60.5% | 0.550 | 0.000 | 85.8% |
| `negative_event_count_20d` | 0.006 | 60.5% | 1.147 | 0.086 | 65.2% |
| `negative_event_count_60d` | 0.011 | 60.5% | 2.460 | 1.210 | 38.1% |
| `negative_event_severity_20d` | 0.045 | 60.5% | 0.683 | 0.073 | 65.1% |
| `regulatory_negative_count_20d` | 0.004 | 60.5% | 0.547 | 0.000 | 94.6% |
| `litigation_negative_count_20d` | 0.001 | 60.5% | 0.057 | 0.000 | 99.8% |
| `investigation_count_20d` | 0.001 | 60.5% | 0.046 | 0.000 | 99.8% |
| `penalty_count_20d` | 0.001 | 60.5% | 0.050 | 0.000 | 99.8% |
| `pledge_risk_count_20d` | 0.002 | 60.5% | 0.256 | 0.000 | 95.8% |
| `shareholder_reduction_count_20d` | 0.001 | 60.5% | 0.000 | 0.000 | 100.0% |
| `material_negative_count_20d` | 0.006 | 60.5% | 1.147 | 0.086 | 65.2% |
| `debt_default_count_20d` | 0.002 | 60.5% | 0.188 | 0.038 | 93.5% |
| `positive_event_count_5d` | 0.006 | 60.5% | 0.869 | 0.000 | 86.9% |
| `positive_event_count_20d` | 0.009 | 60.5% | 1.735 | 0.114 | 65.9% |
| `positive_event_count_60d` | 0.014 | 60.5% | 3.640 | 0.848 | 41.8% |
| `repurchase_count_20d` | 0.001 | 60.5% | 0.000 | 0.000 | 100.0% |
| `shareholder_increase_count_20d` | 0.001 | 60.5% | 0.000 | 0.000 | 100.0% |
| `major_contract_count_20d` | 0.002 | 60.5% | 0.197 | 0.000 | 97.9% |
| `equity_incentive_count_20d` | 0.007 | 60.5% | 1.238 | 0.000 | 92.2% |
| `news_intensity_20d` | 0.205 | 60.5% | 0.697 | 0.613 | 22.6% |
| `abnormal_news_intensity_20d` | 0.995 | 60.5% | 1.210 | -0.154 | 0.3% |
| `first_negative_event_20d` | 0.001 | 60.5% | 0.131 | 0.000 | 97.5% |
| `new_event_type_count_20d` | 0.012 | 60.5% | 3.464 | 3.719 | 16.6% |
| `weighted_negative_event_20d` | 0.110 | 60.5% | 0.706 | 0.056 | 65.1% |
| `negative_event_days_20d` | 0.006 | 60.5% | 1.147 | 0.086 | 65.2% |
| `positive_negative_balance_20d` | 0.028 | 60.5% | 0.392 | 0.000 | 52.2% |
| `positive_negative_balance_60d` | 0.072 | 60.5% | 0.485 | 0.029 | 26.7% |
| `negative_positive_ratio_20d` | 0.020 | 60.5% | 0.910 | 0.036 | 65.1% |
| `negative_event_streak_60d` | 0.003 | 60.5% | 0.578 | 0.952 | 58.4% |
| `procedural_count_20d` | 0.010 | 60.5% | 2.779 | 1.200 | 45.4% |
| `unknown_count_20d` | 0.009 | 60.5% | 2.137 | 1.019 | 42.6% |

> `最大同值占比 > 90%` 的因子标记 **LOW_DISCRIMINATION** 并直接判为无效 —— 它对绝大多数股票取同一个值，给不出排序。（这正是 S3_v2 那个 `regulatory_event_count_20d` 的死因：91.6%）

---

## 6. PIT Verification

因子只使用 `availability_time <= T` 的事件。事件的「日」取可用时间在 Asia/Shanghai 的日期，并已在上游把盘后公告推到次一交易日 09:30（docs/步骤5-新闻时点规则.md）。

永久回归测试：`tests/news_factors/test_news_factor_research.py`（`test_future_events_cannot_change_earlier_factor_values`）—— 把 T 之后的事件加进来，T 日的因子值必须纹丝不动。

---

## 7. IC / Rank IC

| 因子 | 筛选期(18-23) IC | ICIR | 正向月比 | 2018-20 | 2021-23 | 2024-26 | 全样本 ICIR |
|---|---|---|---|---|---|---|---|
| `negative_event_count_5d` | -0.0038 | -0.11 | 40% | -0.0055 | -0.0020 | -0.0014 | -0.08 |
| `negative_event_count_20d` | -0.0045 | -0.10 | 42% | -0.0030 | -0.0061 | -0.0084 | -0.12 |
| `negative_event_count_60d` | -0.0133 | -0.22 | 35% | -0.0133 | -0.0134 | -0.0039 | -0.17 |
| `negative_event_severity_20d` | -0.0042 | -0.09 | 43% | -0.0031 | -0.0053 | -0.0090 | -0.12 |
| `regulatory_negative_count_20d` | -0.0201 | -0.42 | 33% | -0.0271 | -0.0130 | -0.0075 | -0.32 |
| `litigation_negative_count_20d` | -0.0042 | -0.13 | 37% | -0.0079 | -0.0005 | +0.0026 | -0.08 |
| `investigation_count_20d` | -0.0099 | -0.30 | 40% | -0.0154 | -0.0045 | -0.0091 | -0.32 |
| `penalty_count_20d` | +0.0004 | +0.06 | 59% | -0.0049 | +0.0057 | -0.0039 | -0.03 |
| `pledge_risk_count_20d` | +0.0024 | +0.06 | 49% | +0.0065 | -0.0018 | -0.0007 | +0.05 |
| `shareholder_reduction_count_20d` | — | — | nan% | — | — | — | — |
| `material_negative_count_20d` | -0.0045 | -0.10 | 42% | -0.0030 | -0.0061 | -0.0084 | -0.12 |
| `debt_default_count_20d` | +0.0042 | +0.12 | 56% | +0.0024 | +0.0060 | -0.0044 | +0.04 |
| `positive_event_count_5d` | +0.0006 | +0.01 | 49% | +0.0048 | -0.0036 | +0.0067 | +0.06 |
| `positive_event_count_20d` | +0.0044 | +0.08 | 49% | +0.0154 | -0.0066 | +0.0003 | +0.07 |
| `positive_event_count_60d` | -0.0060 | -0.09 | 50% | +0.0105 | -0.0226 | +0.0071 | -0.03 |
| `repurchase_count_20d` | — | — | nan% | — | — | — | — |
| `shareholder_increase_count_20d` | — | — | nan% | — | — | — | — |
| `major_contract_count_20d` | -0.0073 | -0.25 | 35% | -0.0131 | -0.0015 | -0.0075 | -0.25 |
| `equity_incentive_count_20d` | +0.0096 | +0.19 | 60% | +0.0237 | -0.0044 | +0.0085 | +0.16 |
| `news_intensity_20d` | +0.0031 | +0.07 | 53% | +0.0068 | -0.0006 | -0.0121 | -0.04 |
| `abnormal_news_intensity_20d` | +0.0073 | +0.19 | 58% | +0.0066 | +0.0081 | -0.0117 | +0.04 |
| `first_negative_event_20d` | +0.0055 | +0.19 | 54% | +0.0059 | +0.0052 | -0.0001 | +0.14 |
| `new_event_type_count_20d` | -0.0110 | -0.22 | 43% | -0.0033 | -0.0187 | -0.0155 | -0.24 |
| `weighted_negative_event_20d` | -0.0036 | -0.08 | 46% | -0.0029 | -0.0044 | -0.0074 | -0.10 |
| `negative_event_days_20d` | -0.0045 | -0.10 | 42% | -0.0030 | -0.0061 | -0.0084 | -0.12 |
| `positive_negative_balance_20d` | +0.0052 | +0.11 | 57% | +0.0119 | -0.0015 | +0.0059 | +0.14 |
| `positive_negative_balance_60d` | +0.0048 | +0.08 | 60% | +0.0169 | -0.0072 | +0.0087 | +0.12 |
| `negative_positive_ratio_20d` | -0.0041 | -0.09 | 39% | -0.0040 | -0.0042 | -0.0086 | -0.12 |
| `negative_event_streak_60d` | -0.0120 | -0.25 | 39% | -0.0116 | -0.0124 | -0.0022 | -0.18 |
| `procedural_count_20d` | -0.0025 | -0.07 | 42% | -0.0000 | -0.0049 | -0.0014 | -0.06 |
| `unknown_count_20d` | -0.0139 | -0.26 | 35% | -0.0141 | -0.0136 | -0.0136 | -0.28 |

> 信号日为月频，全样本 116 个观测、每个筛选期约 36 个。**36 个观测的 ICIR 噪声很大**，不能当 t 统计量读，它在这里只是稳定性排序的一个参考。筛选只用 2018-2023 两段。

---

## 8. Quantile Returns

5 分层的各层平均 20 日前瞻收益，以及高减低：

| 因子 | Q1 | Q2 | Q3 | Q4 | Q5 | Q5-Q1 | 10分位高减低 |
|---|---|---|---|---|---|---|---|
| `negative_event_count_5d` | +0.0113 | +0.0098 | +0.0113 | +0.0124 | +0.0113 | +0.0000 | -0.0012 |
| `negative_event_count_20d` | +0.0115 | +0.0111 | +0.0114 | +0.0103 | +0.0117 | +0.0003 | -0.0009 |
| `negative_event_count_60d` | +0.0110 | +0.0100 | +0.0115 | +0.0122 | +0.0114 | +0.0005 | -0.0002 |
| `negative_event_severity_20d` | +0.0115 | +0.0112 | +0.0113 | +0.0102 | +0.0119 | +0.0005 | -0.0016 |
| `regulatory_negative_count_20d` | +0.0123 | +0.0097 | +0.0105 | +0.0126 | +0.0110 | -0.0013 | -0.0044 |
| `litigation_negative_count_20d` | +0.0121 | +0.0100 | +0.0098 | +0.0121 | +0.0122 | +0.0001 | -0.0025 |
| `investigation_count_20d` | +0.0121 | +0.0099 | +0.0098 | +0.0123 | +0.0119 | -0.0003 | -0.0031 |
| `penalty_count_20d` | +0.0120 | +0.0098 | +0.0098 | +0.0123 | +0.0120 | +0.0000 | -0.0027 |
| `pledge_risk_count_20d` | +0.0121 | +0.0097 | +0.0103 | +0.0119 | +0.0122 | +0.0001 | -0.0016 |
| `shareholder_reduction_count_20d` | +0.0121 | +0.0099 | +0.0097 | +0.0123 | +0.0121 | +0.0000 | -0.0025 |
| `material_negative_count_20d` | +0.0115 | +0.0111 | +0.0114 | +0.0103 | +0.0117 | +0.0003 | -0.0009 |
| `debt_default_count_20d` | +0.0113 | +0.0101 | +0.0110 | +0.0128 | +0.0108 | -0.0005 | -0.0038 |
| `positive_event_count_5d` | +0.0115 | +0.0099 | +0.0111 | +0.0125 | +0.0110 | -0.0004 | -0.0011 |
| `positive_event_count_20d` | +0.0111 | +0.0106 | +0.0116 | +0.0098 | +0.0130 | +0.0020 | +0.0017 |
| `positive_event_count_60d` | +0.0117 | +0.0109 | +0.0093 | +0.0117 | +0.0124 | +0.0007 | +0.0020 |
| `repurchase_count_20d` | +0.0121 | +0.0099 | +0.0097 | +0.0123 | +0.0121 | +0.0000 | -0.0025 |
| `shareholder_increase_count_20d` | +0.0121 | +0.0099 | +0.0097 | +0.0123 | +0.0121 | +0.0000 | -0.0025 |
| `major_contract_count_20d` | +0.0122 | +0.0097 | +0.0101 | +0.0123 | +0.0118 | -0.0004 | -0.0036 |
| `equity_incentive_count_20d` | +0.0113 | +0.0095 | +0.0100 | +0.0122 | +0.0130 | +0.0017 | +0.0019 |
| `news_intensity_20d` | +0.0116 | +0.0108 | +0.0109 | +0.0103 | +0.0125 | +0.0008 | +0.0000 |
| `abnormal_news_intensity_20d` | +0.0114 | +0.0108 | +0.0108 | +0.0109 | +0.0121 | +0.0007 | +0.0003 |
| `first_negative_event_20d` | +0.0119 | +0.0096 | +0.0103 | +0.0126 | +0.0117 | -0.0002 | -0.0042 |
| `new_event_type_count_20d` | +0.0118 | +0.0115 | +0.0114 | +0.0115 | +0.0100 | -0.0018 | -0.0029 |
| `weighted_negative_event_20d` | +0.0115 | +0.0111 | +0.0115 | +0.0105 | +0.0115 | +0.0001 | -0.0012 |
| `negative_event_days_20d` | +0.0115 | +0.0111 | +0.0114 | +0.0103 | +0.0117 | +0.0003 | -0.0009 |
| `positive_negative_balance_20d` | +0.0115 | +0.0114 | +0.0103 | +0.0112 | +0.0118 | +0.0003 | +0.0037 |
| `positive_negative_balance_60d` | +0.0111 | +0.0119 | +0.0116 | +0.0098 | +0.0117 | +0.0007 | +0.0023 |
| `negative_positive_ratio_20d` | +0.0115 | +0.0114 | +0.0113 | +0.0103 | +0.0116 | +0.0002 | -0.0013 |
| `negative_event_streak_60d` | +0.0118 | +0.0098 | +0.0102 | +0.0114 | +0.0129 | +0.0011 | +0.0009 |
| `procedural_count_20d` | +0.0121 | +0.0103 | +0.0108 | +0.0115 | +0.0115 | -0.0006 | -0.0004 |
| `unknown_count_20d` | +0.0120 | +0.0112 | +0.0127 | +0.0107 | +0.0095 | -0.0026 | -0.0041 |

---

## 9. Cross-Exchange Analysis

| 因子 | 全样本 IC | SSE IC | SZSE IC | 组内最大/全样本 |
|---|---|---|---|---|
| `negative_event_count_5d` | -0.0030 | -0.0033 | -0.0070 | 2.31 |
| `negative_event_count_20d` | -0.0057 | -0.0070 | +0.0029 | 1.23 |
| `negative_event_count_60d` | -0.0104 | -0.0111 | -0.0165 | 1.58 |
| `negative_event_severity_20d` | -0.0057 | -0.0069 | +0.0007 | 1.21 |
| `regulatory_negative_count_20d` | -0.0162 | -0.0165 | -0.0094 | 1.02 |
| `litigation_negative_count_20d` | -0.0023 | -0.0025 | -0.0342 | 15.03 |
| `investigation_count_20d` | -0.0098 | -0.0105 | +0.0841 | 8.61 |
| `penalty_count_20d` | -0.0007 | +0.0006 | -0.0495 | 68.20 |
| `pledge_risk_count_20d` | +0.0014 | +0.0009 | +0.0053 | 3.79 |
| `shareholder_reduction_count_20d` | — | — | — | — |
| `material_negative_count_20d` | -0.0057 | -0.0070 | +0.0029 | 1.23 |
| `debt_default_count_20d` | +0.0016 | +0.0007 | +0.0342 | 21.78 |
| `positive_event_count_5d` | +0.0025 | +0.0016 | +0.0109 | 4.41 |
| `positive_event_count_20d` | +0.0032 | +0.0021 | +0.0021 | 0.66 |
| `positive_event_count_60d` | -0.0020 | -0.0033 | -0.0009 | 1.65 |
| `repurchase_count_20d` | — | — | — | — |
| `shareholder_increase_count_20d` | — | — | — | — |
| `major_contract_count_20d` | -0.0074 | -0.0078 | -0.0001 | 1.05 |
| `equity_incentive_count_20d` | +0.0093 | +0.0081 | +0.0117 | 1.26 |
| `news_intensity_20d` | -0.0016 | -0.0023 | -0.0068 | 4.28 |
| `abnormal_news_intensity_20d` | +0.0015 | +0.0016 | -0.0042 | 2.92 |
| `first_negative_event_20d` | +0.0038 | +0.0028 | +0.0427 | 11.22 |
| `new_event_type_count_20d` | -0.0124 | -0.0140 | -0.0144 | 1.17 |
| `weighted_negative_event_20d` | -0.0048 | -0.0059 | +0.0012 | 1.23 |
| `negative_event_days_20d` | -0.0057 | -0.0070 | +0.0029 | 1.23 |
| `positive_negative_balance_20d` | +0.0055 | +0.0056 | -0.0068 | 1.24 |
| `positive_negative_balance_60d` | +0.0060 | +0.0055 | +0.0083 | 1.38 |
| `negative_positive_ratio_20d` | -0.0055 | -0.0065 | +0.0004 | 1.19 |
| `negative_event_streak_60d` | -0.0090 | -0.0091 | -0.0175 | 1.94 |
| `procedural_count_20d` | -0.0021 | -0.0026 | -0.0174 | 8.11 |
| `unknown_count_20d` | -0.0138 | -0.0150 | -0.0129 | 1.09 |

> **不能只看全市场平均。** 沪市公告密度约为深市 20 倍，若某因子在沪市为 0、深市显著，全市场 IC 会把它掩盖。比值 < 0.3 的因子按伪信号处理。

---

## 10. Liquidity Analysis

按当日 20 日均成交额分 5 组，组内 IC（L1 最低、L5 最高）：

| 因子 | L1 | L2 | L3 | L4 | L5 |
|---|---|---|---|---|---|
| `negative_event_count_5d` | -0.0022 | -0.0018 | -0.0087 | -0.0086 | +0.0013 |
| `negative_event_count_20d` | -0.0096 | +0.0008 | -0.0091 | -0.0071 | -0.0003 |
| `negative_event_count_60d` | -0.0112 | +0.0020 | -0.0165 | -0.0156 | -0.0107 |
| `negative_event_severity_20d` | -0.0100 | +0.0012 | -0.0087 | -0.0072 | -0.0007 |
| `regulatory_negative_count_20d` | -0.0078 | -0.0027 | -0.0137 | -0.0271 | -0.0177 |
| `litigation_negative_count_20d` | +0.0088 | -0.0108 | -0.0188 | -0.0111 | -0.0001 |
| `investigation_count_20d` | -0.0233 | -0.0122 | -0.0203 | -0.0125 | +0.0009 |
| `penalty_count_20d` | -0.0080 | -0.0004 | -0.0079 | +0.0066 | -0.0038 |
| `pledge_risk_count_20d` | +0.0052 | +0.0045 | -0.0099 | -0.0009 | +0.0029 |
| `shareholder_reduction_count_20d` | — | — | — | — | — |
| `material_negative_count_20d` | -0.0096 | +0.0008 | -0.0091 | -0.0071 | -0.0003 |
| `debt_default_count_20d` | -0.0080 | -0.0021 | +0.0053 | +0.0018 | +0.0019 |
| `positive_event_count_5d` | +0.0034 | +0.0057 | +0.0008 | +0.0050 | +0.0091 |
| `positive_event_count_20d` | +0.0013 | +0.0124 | +0.0038 | +0.0101 | +0.0153 |
| `positive_event_count_60d` | -0.0003 | +0.0030 | +0.0010 | +0.0092 | +0.0117 |
| `repurchase_count_20d` | — | — | — | — | — |
| `shareholder_increase_count_20d` | — | — | — | — | — |
| `major_contract_count_20d` | -0.0032 | -0.0024 | -0.0053 | -0.0064 | -0.0073 |
| `equity_incentive_count_20d` | -0.0007 | +0.0105 | +0.0120 | +0.0121 | +0.0287 |
| `news_intensity_20d` | -0.0015 | +0.0073 | +0.0080 | +0.0032 | +0.0013 |
| `abnormal_news_intensity_20d` | +0.0038 | +0.0078 | +0.0096 | +0.0002 | -0.0005 |
| `first_negative_event_20d` | -0.0037 | -0.0014 | +0.0149 | +0.0017 | +0.0135 |
| `new_event_type_count_20d` | -0.0077 | +0.0012 | +0.0040 | +0.0008 | -0.0063 |
| `weighted_negative_event_20d` | -0.0091 | +0.0017 | -0.0083 | -0.0063 | +0.0004 |
| `negative_event_days_20d` | -0.0096 | +0.0008 | -0.0091 | -0.0071 | -0.0003 |
| `positive_negative_balance_20d` | +0.0078 | +0.0072 | +0.0109 | +0.0124 | +0.0104 |
| `positive_negative_balance_60d` | +0.0091 | +0.0022 | +0.0140 | +0.0185 | +0.0159 |
| `negative_positive_ratio_20d` | -0.0100 | +0.0000 | -0.0095 | -0.0074 | -0.0016 |
| `negative_event_streak_60d` | -0.0124 | +0.0017 | -0.0086 | -0.0119 | -0.0115 |
| `procedural_count_20d` | -0.0002 | +0.0093 | +0.0095 | +0.0064 | -0.0023 |
| `unknown_count_20d` | -0.0057 | -0.0015 | +0.0009 | -0.0095 | -0.0117 |

> **市值控制做不到**：`data/parquet/valuation/daily_valuation.parquet` 只有 2026-09-30 一天的快照（4,605 行），没有历史序列。所以 §十三 要求的 within-market-cap IC **本报告无法提供**，用成交额（流动性）与价格作为相关代理。这是能力边界，不是省略。

---

## 11. Time Stability

逐年 rank IC：

| 因子 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|
| `negative_event_count_5d` | -0.006 | +0.000 | -0.011 | -0.014 | +0.006 | +0.002 | -0.006 | +0.010 | -0.011 |
| `negative_event_count_20d` | -0.012 | +0.007 | -0.004 | -0.009 | +0.012 | -0.021 | -0.012 | -0.000 | -0.015 |
| `negative_event_count_60d` | -0.023 | +0.002 | -0.018 | -0.008 | -0.000 | -0.032 | -0.003 | -0.003 | -0.006 |
| `negative_event_severity_20d` | -0.011 | +0.006 | -0.004 | -0.009 | +0.012 | -0.019 | -0.013 | -0.001 | -0.016 |
| `regulatory_negative_count_20d` | -0.023 | -0.028 | -0.030 | -0.009 | -0.003 | -0.027 | -0.025 | -0.005 | +0.015 |
| `litigation_negative_count_20d` | -0.005 | -0.006 | -0.013 | -0.003 | +0.004 | -0.002 | +0.004 | -0.006 | +0.016 |
| `investigation_count_20d` | -0.011 | -0.018 | -0.017 | +0.000 | -0.005 | -0.009 | -0.021 | -0.013 | +0.010 |
| `penalty_count_20d` | -0.008 | -0.004 | -0.002 | +0.002 | +0.013 | +0.002 | +0.004 | -0.006 | -0.014 |
| `pledge_risk_count_20d` | -0.005 | +0.013 | +0.012 | -0.002 | +0.005 | -0.008 | -0.002 | +0.002 | -0.003 |
| `material_negative_count_20d` | -0.012 | +0.007 | -0.004 | -0.009 | +0.012 | -0.021 | -0.012 | -0.000 | -0.015 |
| `debt_default_count_20d` | +0.002 | +0.004 | +0.001 | -0.007 | +0.006 | +0.019 | +0.001 | +0.001 | -0.020 |
| `positive_event_count_5d` | +0.004 | +0.015 | -0.005 | -0.016 | +0.004 | +0.001 | +0.007 | -0.001 | +0.018 |
| `positive_event_count_20d` | +0.012 | +0.023 | +0.011 | -0.014 | +0.002 | -0.007 | -0.009 | +0.007 | +0.005 |
| `positive_event_count_60d` | -0.007 | +0.025 | +0.013 | -0.019 | -0.004 | -0.045 | -0.006 | +0.017 | +0.011 |
| `major_contract_count_20d` | -0.005 | -0.016 | -0.018 | +0.004 | -0.005 | -0.003 | +0.000 | -0.016 | -0.006 |
| `equity_incentive_count_20d` | +0.021 | +0.034 | +0.016 | -0.007 | +0.007 | -0.013 | -0.002 | +0.012 | +0.019 |
| `news_intensity_20d` | +0.003 | +0.015 | +0.002 | -0.021 | +0.012 | +0.007 | -0.024 | -0.003 | -0.009 |
| `abnormal_news_intensity_20d` | +0.014 | +0.001 | +0.004 | -0.020 | +0.020 | +0.025 | -0.021 | -0.005 | -0.008 |
| `first_negative_event_20d` | +0.005 | +0.010 | +0.003 | -0.010 | +0.010 | +0.015 | +0.004 | -0.002 | -0.002 |
| `new_event_type_count_20d` | -0.016 | +0.012 | -0.006 | -0.044 | -0.000 | -0.012 | -0.024 | -0.017 | -0.000 |
| `weighted_negative_event_20d` | -0.012 | +0.008 | -0.004 | -0.009 | +0.012 | -0.016 | -0.012 | +0.002 | -0.015 |
| `negative_event_days_20d` | -0.012 | +0.007 | -0.004 | -0.009 | +0.012 | -0.021 | -0.012 | -0.000 | -0.015 |
| `positive_negative_balance_20d` | +0.017 | +0.010 | +0.009 | -0.007 | -0.006 | +0.008 | +0.001 | +0.005 | +0.015 |
| `positive_negative_balance_60d` | +0.011 | +0.017 | +0.023 | -0.009 | -0.002 | -0.011 | -0.002 | +0.015 | +0.016 |
| `negative_positive_ratio_20d` | -0.013 | +0.005 | -0.004 | -0.004 | +0.012 | -0.020 | -0.012 | +0.000 | -0.017 |
| `negative_event_streak_60d` | -0.020 | +0.003 | -0.018 | -0.008 | -0.005 | -0.024 | +0.003 | -0.005 | -0.006 |
| `procedural_count_20d` | -0.005 | +0.006 | -0.001 | -0.027 | +0.006 | +0.006 | -0.017 | +0.003 | +0.014 |
| `unknown_count_20d` | -0.028 | -0.004 | -0.010 | -0.043 | +0.007 | -0.005 | -0.009 | -0.025 | -0.003 |

---

## 11b. 是不是「公告数量」的代理？

每个因子与**公告总条数（60 交易日）**的横截面相关性（逐日 spearman 后取均值）：

| 因子 | 与总条数的相关 |
|---|---|
| `negative_event_count_5d` | +0.191 |
| `negative_event_count_20d` | +0.302 |
| `negative_event_count_60d` | +0.449 |
| `negative_event_severity_20d` | +0.303 |
| `regulatory_negative_count_20d` | +0.148 |
| `litigation_negative_count_20d` | +0.017 |
| `investigation_count_20d` | +0.025 |
| `penalty_count_20d` | +0.014 |
| `pledge_risk_count_20d` | +0.083 |
| `shareholder_reduction_count_20d` | — |
| `material_negative_count_20d` | +0.302 |
| `debt_default_count_20d` | +0.125 |
| `positive_event_count_5d` | +0.225 |
| `positive_event_count_20d` | +0.357 |
| `positive_event_count_60d` | +0.484 |
| `repurchase_count_20d` | — |
| `shareholder_increase_count_20d` | — |
| `major_contract_count_20d` | +0.051 |
| `equity_incentive_count_20d` | +0.235 |
| `news_intensity_20d` | +0.366 |
| `abnormal_news_intensity_20d` | +0.168 |
| `first_negative_event_20d` | +0.001 |
| `new_event_type_count_20d` | +0.626 |
| `weighted_negative_event_20d` | +0.299 |
| `negative_event_days_20d` | +0.302 |
| `positive_negative_balance_20d` | +0.055 |
| `positive_negative_balance_60d` | +0.067 |
| `negative_positive_ratio_20d` | +0.256 |
| `negative_event_streak_60d` | +0.390 |
| `procedural_count_20d` | +0.491 |
| `unknown_count_20d` | +0.407 |

> 总条数不含任何经济内容。一个因子若与它相关 0.9，它的 IC 有多少是「公告多」本身、有多少是内容，就很难分开了。这是 §十三 要求的代理变量检验的量化版本 —— 因为历史市值不可得（见 §10），这里用公告总量本身作为最保守的参照。

---

## 12. Multiple Testing Risk

- 候选（registry 声明）：**31**
- 实际评估：**31**
- 判为 strong：**0** / moderate：**4** / weak：**8** / low_discrimination：**12** / invalid：**7**

本次在 29 个因子上做了同样的检验。即使**全部因子都没有真实 alpha**，在 |IC| 上仍会有一两个因为抽样波动看起来不错（29 个独立检验、单侧 5% 水平下期望约 1.5 个假阳性）。

因此本报告**不把「历史 IC 高」当作有效证据**，而要求同时满足：

1. 两个筛选期符号一致；
2. 组内（沪市 / 深市 / 流动性分层）不大幅塌陷；
3. 2024-2026 段不翻转；
4. 截面分辨力足够（同值占比 < 90%）。

**阴性对照是这套判据的校准器**：`procedural_count_20d` 与 `unknown_count_20d` 按经济逻辑不该有信号。它们若被判为 strong，说明判据本身在捕风捉影，整张表都要打折。结果见 §13。

---

## 13. Factor Ranking

| 因子 | IC | ICIR | 稳定性 | SSE | SZSE | 组内保留(交易所) | 组内保留(流动性) | 判定 |
|---|---|---|---|---|---|---|---|---|
| `unknown_count_20d` | -0.0139 | -0.26 | 同号 | -0.0150 | -0.0129 | 1.01 | 0.40 | **moderate** |
| `negative_event_count_60d` | -0.0133 | -0.22 | 同号 | -0.0111 | -0.0165 | 1.32 | 0.99 | **moderate** |
| `negative_event_streak_60d` | -0.0120 | -0.25 | 同号 | -0.0091 | -0.0175 | 1.48 | 0.95 | **moderate** |
| `abnormal_news_intensity_20d` | +0.0073 | +0.19 | 同号 | +0.0016 | -0.0042 | — | — | **moderate** |
| `negative_event_count_20d` | -0.0045 | -0.10 | 同号 | -0.0070 | +0.0029 | 0.36 | 0.88 | **weak** |
| `material_negative_count_20d` | -0.0045 | -0.10 | 同号 | -0.0070 | +0.0029 | 0.36 | 0.88 | **weak** |
| `negative_event_days_20d` | -0.0045 | -0.10 | 同号 | -0.0070 | +0.0029 | 0.36 | 0.88 | **weak** |
| `negative_event_severity_20d` | -0.0042 | -0.09 | 同号 | -0.0069 | +0.0007 | 0.54 | 0.89 | **weak** |
| `negative_positive_ratio_20d` | -0.0041 | -0.09 | 同号 | -0.0065 | +0.0004 | 0.56 | 1.04 | **weak** |
| `weighted_negative_event_20d` | -0.0036 | -0.08 | 同号 | -0.0059 | +0.0012 | 0.48 | 0.91 | **weak** |
| `negative_event_count_5d` | -0.0038 | -0.11 | 同号 | -0.0033 | -0.0070 | 1.70 | 1.31 | **weak** |
| `procedural_count_20d` | -0.0025 | -0.07 | 同号 | -0.0026 | -0.0174 | 4.67 | -2.13 | **weak** |
| `regulatory_negative_count_20d` | -0.0201 | -0.42 | 同号 | -0.0165 | -0.0094 | 0.80 | 0.85 | **low_discrimination** |
| `investigation_count_20d` | -0.0099 | -0.30 | 同号 | -0.0105 | +0.0841 | -3.77 | 1.38 | **low_discrimination** |
| `equity_incentive_count_20d` | +0.0096 | +0.19 | **异号** | +0.0081 | +0.0117 | 1.06 | 1.34 | **low_discrimination** |
| `major_contract_count_20d` | -0.0073 | -0.25 | 同号 | -0.0078 | -0.0001 | 0.53 | 0.67 | **low_discrimination** |
| `first_negative_event_20d` | +0.0055 | +0.19 | 同号 | +0.0028 | +0.0427 | 5.98 | 1.31 | **low_discrimination** |
| `litigation_negative_count_20d` | -0.0042 | -0.13 | 同号 | -0.0025 | -0.0342 | 8.07 | 2.81 | **low_discrimination** |
| `debt_default_count_20d` | +0.0042 | +0.12 | 同号 | +0.0007 | +0.0342 | — | — | **low_discrimination** |
| `pledge_risk_count_20d` | +0.0024 | +0.06 | **异号** | +0.0009 | +0.0053 | — | — | **low_discrimination** |
| `penalty_count_20d` | +0.0004 | +0.06 | **异号** | +0.0006 | -0.0495 | — | — | **low_discrimination** |
| `shareholder_reduction_count_20d` | — | — | **异号** | — | — | — | — | **low_discrimination** |
| `repurchase_count_20d` | — | — | **异号** | — | — | — | — | **low_discrimination** |
| `shareholder_increase_count_20d` | — | — | **异号** | — | — | — | — | **low_discrimination** |
| `new_event_type_count_20d` | -0.0110 | -0.22 | 同号 | -0.0140 | -0.0144 | 1.15 | 0.13 | **invalid** |
| `positive_negative_balance_60d` | +0.0048 | +0.08 | **异号** | +0.0055 | +0.0083 | 1.15 | 1.99 | **invalid** |
| `positive_negative_balance_20d` | +0.0052 | +0.11 | **异号** | +0.0056 | -0.0068 | -0.10 | 1.79 | **invalid** |
| `positive_event_count_20d` | +0.0044 | +0.08 | **异号** | +0.0021 | +0.0021 | 0.66 | 2.71 | **invalid** |
| `positive_event_count_5d` | +0.0006 | +0.01 | **异号** | +0.0016 | +0.0109 | 2.52 | 1.95 | **invalid** |
| `positive_event_count_60d` | -0.0060 | -0.09 | **异号** | -0.0033 | -0.0009 | — | — | **invalid** |
| `news_intensity_20d` | +0.0031 | +0.07 | **异号** | -0.0023 | -0.0068 | — | — | **invalid** |

> IC 列报的是 **rank IC（Spearman）**，取两个筛选期的均值。
> 「稳定性」= 两个筛选期是否同号。
> 「组内保留」= **组内 IC 的均值 / 池化 IC**：接近 1 说明信号在组内也存在；接近 0 或为负说明池化 IC 全部来自组间构成差异（规模/流动性/交易所），不是横截面信息。低于 0.3 判为伪信号。

---

## 14. Recommended Candidate Factors

**先读这一段再读清单。** 本阶段最重要的结果是两个**阴性对照**的表现：

- `unknown_count_20d`（taxonomy 分不出来的残差，按构造不含任何经济内容）拿到全表**最高 IC（−0.0139）**，且组内保留 1.01 / 0.40；
- `procedural_count_20d`（程序性公告）为 weak，池化 IC 近零 —— 这个对照**表现正常**。

一个对照排第一、另一个正常，说明：**宽口径的「负面事件数」在很大程度上是「公告多」本身的代理**（与总条数相关 0.39~0.45），而不是事件内容的信息。这一点在 §11b 有量化。

另一头，内容最具体的几个因子（`regulatory_` / `investigation_` / `penalty_` / `litigation_` / `first_negative_event_`）与总条数**几乎不相关（0.00~0.15）**，说明它们确实在测别的东西 —— 但它们同时**太稀疏**：横截面上 >90% 的股票取同一值，排不出名次。

> **这就是本阶段真正的墙**：特异性与横截面分辨力此消彼长。能排序的只是数量，有内容的排不了序。S3_v2 撞的正是同一面墙。

**Strong**（0 个）

（无）

**Moderate**（4 个）

- `unknown_count_20d` — 第二个阴性对照：分类失败的残余不该携带信息
  - 与公告总条数相关 **0.41**（偏高：信号有相当部分来自数量本身）
  - ⚠ **这是阴性对照因子** —— 它不该有信号，它排在这里本身就是对整套判据的警告
  - ⚠ 部分来自组间差异（保留率 1.01 / 0.40）
  - ⚠ **阴性对照**：本不该有信号
- `negative_event_count_60d` — 负面事件提高信息不确定性并压制短期估值，窗口内越多越负
  - 与公告总条数相关 **0.45**（偏高：信号有相当部分来自数量本身）
- `negative_event_streak_60d` — 连续暴露说明问题未解决，与单次冲击应当区分
  - 与公告总条数相关 **0.39**（偏高：信号有相当部分来自数量本身）
- `abnormal_news_intensity_20d` — 用自身历史标准化，消除公司间固定差异
  - 与公告总条数相关 **0.17**
  - ⚠ 2024-2026 段符号翻转

## 15. Rejected Factors

**weak**（8 个）

- `negative_event_count_20d` — 筛选期 |IC| 0.0045 < 0.005
- `material_negative_count_20d` — 筛选期 |IC| 0.0045 < 0.005
- `negative_event_days_20d` — 筛选期 |IC| 0.0045 < 0.005
- `negative_event_severity_20d` — 筛选期 |IC| 0.0042 < 0.005
- `negative_positive_ratio_20d` — 筛选期 |IC| 0.0041 < 0.005
- `weighted_negative_event_20d` — 筛选期 |IC| 0.0036 < 0.005
- `negative_event_count_5d` — 筛选期 |IC| 0.0038 < 0.005
- `procedural_count_20d` — 筛选期 |IC| 0.0025 < 0.005

**low_discrimination**（12 个）

- `regulatory_negative_count_20d` — LOW_DISCRIMINATION：94.6% 的股票取同一值 —— 横截面几乎没有排序能力，不推荐入模
- `investigation_count_20d` — LOW_DISCRIMINATION：99.8% 的股票取同一值 —— 横截面几乎没有排序能力，不推荐入模
- `equity_incentive_count_20d` — LOW_DISCRIMINATION：92.2% 的股票取同一值 —— 横截面几乎没有排序能力，不推荐入模
- `major_contract_count_20d` — LOW_DISCRIMINATION：97.9% 的股票取同一值 —— 横截面几乎没有排序能力，不推荐入模
- `first_negative_event_20d` — LOW_DISCRIMINATION：97.5% 的股票取同一值 —— 横截面几乎没有排序能力，不推荐入模
- `litigation_negative_count_20d` — LOW_DISCRIMINATION：99.8% 的股票取同一值 —— 横截面几乎没有排序能力，不推荐入模
- `debt_default_count_20d` — LOW_DISCRIMINATION：93.5% 的股票取同一值 —— 横截面几乎没有排序能力，不推荐入模
- `pledge_risk_count_20d` — LOW_DISCRIMINATION：95.8% 的股票取同一值 —— 横截面几乎没有排序能力，不推荐入模
- `penalty_count_20d` — LOW_DISCRIMINATION：99.8% 的股票取同一值 —— 横截面几乎没有排序能力，不推荐入模
- `shareholder_reduction_count_20d` — LOW_DISCRIMINATION：100.0% 的股票取同一值 —— 横截面几乎没有排序能力，不推荐入模
- `repurchase_count_20d` — LOW_DISCRIMINATION：100.0% 的股票取同一值 —— 横截面几乎没有排序能力，不推荐入模
- `shareholder_increase_count_20d` — LOW_DISCRIMINATION：100.0% 的股票取同一值 —— 横截面几乎没有排序能力，不推荐入模

**invalid**（7 个）

- `new_event_type_count_20d` — 组内塌陷：保留率 交易所 1.15 / 流动性 0.13（<0.3 = 信号来自组间，不是横截面信息）
- `positive_negative_balance_60d` — 两筛选期符号相反（+0.0169 / -0.0072）
- `positive_negative_balance_20d` — 两筛选期符号相反（+0.0119 / -0.0015）
- `positive_event_count_20d` — 两筛选期符号相反（+0.0154 / -0.0066）
- `positive_event_count_5d` — 两筛选期符号相反（+0.0048 / -0.0036）
- `positive_event_count_60d` — 两筛选期符号相反（+0.0105 / -0.0226）
- `news_intensity_20d` — 两筛选期符号相反（+0.0068 / -0.0006）

---

## 16. Next Step

本阶段**到此为止**。

- 未创建 S3_v3；未改动 `production_strategy`（仍为 `S3_v1`）；未改动 recommendation；未改动任何历史结果。
- 上表判为 strong / moderate 的因子，状态为 `RECOMMENDED_FOR_NEXT_MODEL` —— 这是**建议**，不是模型改动。
- 是否进入下一个模型、以什么方式进入，等下一步指令。
