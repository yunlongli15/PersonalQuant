# Incremental IC Factor Selection Protocol V2（STEP 9）

> 日期：2026-09-19 ｜ 协议配置：`config/factor_selection_v2.yaml`
> 报告：`reports/incremental_factor_selection_v2.md`
> 候选表：`reports/incremental_factor_candidates.csv`
> 冻结清单：`experiments/factors/incremental_v2/factor_selection_manifest.json`

## 0. 结论先行

1. **没有任何候选因子的增量信息在统计上成立。** 20 个进入 Stage B 的候选，
   ΔIC 的 block bootstrap 95% 置信区间**没有一个排除 0**（0/20）。
   ΔIC 的绝对量级只有 0.0001 ~ 0.015（IC 单位）。

2. **修正后的冗余判据推翻了上一轮的波动率结论。** STEP 9 上一版（残差相关
   聚类）认为 `parkinson_vol_20` / `volatility_60` / `downside_volatility_60`
   携带"独立信息"。改用**原始因子**秩相关做主判据后：`parkinson_vol_20`
   与既有因子秩相关 0.912、对完整 M0 的 R² 0.954 —— 它是冗余的。

3. **模型几乎没有真的用到这些候选列。** 置换候选列后 IC 平均只掉
   0.0006（最好的 `gap_count_20`），其余为 0 甚至为负。
   它们改变了模型输出（`prediction_corr` 低至 0.40），却没有改变**排序质量**。

4. **最终 5 个候选是"值得继续观察"的清单，不是"已证明有效"的清单。**
   状态一律 `research_candidate`，不进入 strategy_v2。

5. **本轮修掉 3 个会让结论完全错误的实现 bug**（详见 §11），其中
   "候选列退化成常数"会让**每一个** ΔIC 都精确等于 0——看起来像
   "所有因子都没用"，实际是特征根本没进模型。

---

## 1. 为什么修改方法

上一阶段（`reports/step9_independent_info.md`）用的是**残差独立信息**：

```
r = rank(candidate) − rank([Alpha158, M0 自定义因子])·β
resid_IC = spearman(r, forward_return)
```

它的结论是"75 个候选里只有 4 个携带独立信息，且集中在波动率家族"。

**致命问题**：这些因子的 R² 高达 0.89~0.93，残差只剩 7~11% 的方差，
其中大部分是噪声。噪声之间天然不相关，于是**最冗余的因子看起来最独立**。
实测三个波动率因子的残差两两相关只有 0.19~0.71，全部逃过了 |corr| ≥ 0.8
的聚类门。

更要命的是：残差 IC 高**不代表**加进模型有用。残差是一个统计构造，
模型能不能从中提取信息是另一回事。

## 2. 原 residual 方法的两条局限

1. **判据本身有偏**：R² 越高 → 残差越像噪声 → 残差相关越低 → 越像"独立"。
   方向恰好反了。
2. **测的不是决策量**：我们要回答的是"加进去模型会不会更好"，
   残差 IC 只是一个代理，而且没有把"模型能不能用"纳入考虑。

## 3. Incremental IC 的定义

对每个候选 F，构造两个模型：

```
M0 = Alpha158 + factor_pack_v1 + factor_pack_news_v1     （既有特征集）
M1 = M0 + F                                              （唯一差别）
```

训练数据、模型、超参、随机种子、标签、股票池、调仓日、执行**全部相同**。

对每个验证信号日 t：

```
IC0(t), IC1(t)                横截面 Pearson
RankIC0(t), RankIC1(t)        横截面 Spearman
ΔIC(t)     = IC1(t) − IC0(t)      ← 核心评价量
ΔRankIC(t) = RankIC1(t) − RankIC0(t)
```

**评价的不是 mean(IC1)，而是 mean(ΔIC)**——配对差，逐日计算。

### 协议模型与生产模型的刻意差异

| 参数 | strategy_v1 生产 | 本协议 | 原因 |
|---|---|---|---|
| early_stopping | 50 轮 | **关闭** | 早停需要验证集，而验证集正是被评估期 → 直接泄漏 |
| feature_fraction | 0.8 | **1.0** | 子采样会引入与"特征个数"相关的随机性，M0/M1 的差异会混入抽样噪声 |
| bagging_fraction | 0.8 | **1.0** | 同上 |
| 迭代数 | 早停决定 | **固定 400** | 无数据依赖的停止点 |

代价要说清楚：**这是该因子可用信息量的上界**。生产模型有子采样，
同一个因子只会更弱。

## 4. Walk-forward 设计

严格时间外推，**禁止 2018-2023 一次性训练+验证**（那等于对整个验证期
过拟合）：

| 折 | 训练 | 验证 | 训练信号日 | 验证信号日 |
|---|---|---|---|---|
| fold1 | 2018-01-01 ~ 2019-12-31 | 2020 | 24 | 11 |
| fold2 | 2018-01-01 ~ 2020-12-31 | 2021 | 36 | 11 |
| fold3 | 2018-01-01 ~ 2021-12-31 | 2022 | 48 | 11 |
| fold4 | 2018-01-01 ~ 2022-12-31 | 2023 | 60 | 11 |

训练集是**扩张**窗口（都从 2018-01 开始），不是滑动窗口。

**标签越界保护**：每个验证年最后一个信号日的 20 日前瞻收益会落到下一年
（2023-12-29 → 2024-01-26）。留着它就等于把 2024 的价格带进选择路径，
因此每个验证年剔除 1 个信号日（12 → 11）。

## 5. Candidate screening（Stage A，2018-2021）

只筛数据质量，不看增量价值：

| 门 | 阈值 | 结果 |
|---|---|---|
| coverage | ≥ 0.60 | 主要淘汰项 |
| 极端数值占比 | ≤ 0.05 | 通过 |
| turnover | ≤ 0.90 | 淘汰 2 个 |
| **PIT 投毒检验** | 必须通过 | **65/65 通过** |

PIT 检验不是读 registry 的标记，而是**真的跑一遍**：把信号日 t 之后的所有
行情 ×7+3 重新计算因子，断言 t 日的值逐位不变。

65 个候选 → **20 个进入 Stage B**。被拒的主因是覆盖率（新闻因子 0.41、
财务因子 0.05~0.22——它们本来就只有部分股票有数据）。

> 候选池已排除 M0 里已有的 10 个因子（加入它们等于没加）。
> 上一轮"进入独立信息门"的 4 个里，`downside_volatility_60` 等
> 在 Stage A 或 Stage B 被淘汰，理由见下。

## 6. Candidate results（Stage B）

按 ΔIC 降序，全部 20 个：

| 因子 | raw ICIR | **ΔIC** | **ΔRankIC** | ΔICIR | 正向 fold | **bootstrap 95% CI** | pred_corr | R² | max_corr | 状态 |
|---|---|---|---|---|---|---|---|---|---|---|
| **gap_count_20** | +0.382 | **+0.0150** | +0.0147 | 0.180 | 0.75 | [−0.0146, +0.0157] | 0.398 | 0.275 | 0.022 | PASS |
| high_52w_proximity | +0.059 | +0.0021 | +0.0037 | 0.093 | 0.75 | [−0.0048, +0.0045] | 0.866 | 0.763 | 0.595 | PASS |
| amihud_20 | −0.201 | +0.0031 | +0.0019 | 0.197 | 0.50 | [−0.0038, +0.0048] | 0.903 | **0.962** | **0.919** | REJECT |
| momentum_20 | −0.501 | +0.0020 | +0.0028 | 0.152 | 0.50 | [−0.0022, +0.0061] | 0.907 | **1.000** | **1.000** | REJECT |
| overnight_return_20 | −0.032 | +0.0010 | +0.0013 | 0.066 | 0.75 | [−0.0059, +0.0034] | 0.908 | 0.431 | 0.159 | PASS |
| skewness_60 | −0.094 | +0.0017 | +0.0024 | 0.120 | 0.50 | [−0.0066, +0.0033] | 0.911 | 0.691 | 0.290 | PASS |
| volume_price_corr_20 | −0.315 | +0.0016 | +0.0015 | 0.097 | 0.75 | [−0.0096, +0.0392] | 0.899 | 0.806 | 0.454 | PASS |
| momentum_120 | −0.138 | +0.0008 | +0.0019 | 0.040 | 0.75 | [−0.0078, +0.0037] | 0.882 | 0.752 | 0.632 | PASS |
| limit_down_count_20 | −0.295 | +0.0026 | +0.0022 | 0.034 | 0.75 | [−0.0043, +0.0049] | 0.627 | 0.586 | 0.381 | PASS |
| amount_60 | +0.044 | +0.0006 | +0.0013 | 0.045 | 0.50 | [−0.0041, +0.0069] | 0.904 | **0.980** | **0.954** | REJECT |
| downside_volatility_60 | −0.356 | +0.0004 | +0.0012 | 0.029 | 0.75 | [−0.0173, +0.0175] | 0.887 | **0.924** | 0.708 | PASS |
| intraday_return_20 | +0.026 | +0.0008 | −0.0003 | 0.048 | 0.50 | [−0.0080, +0.0016] | 0.907 | 0.431 | 0.158 | REJECT |
| overnight_intraday_ratio_20 | −0.034 | −0.0033 | −0.0035 | −0.220 | 0.50 | [−0.0019, +0.0080] | 0.908 | 0.431 | 0.160 | REJECT |
| parkinson_vol_20 | −0.536 | +0.0005 | +0.0004 | 0.036 | 0.50 | [−0.0051, +0.0070] | 0.898 | **0.954** | **0.912** | REJECT |
| limit_up_count_20 | **−0.733** | −0.0002 | −0.0003 | −0.004 | 0.50 | [−0.0032, +0.0068] | 0.660 | 0.729 | 0.599 | REJECT |
| max_return_20 | −0.623 | +0.0001 | −0.0005 | 0.007 | 0.50 | [−0.0039, +0.0085] | 0.903 | **0.971** | **0.903** | REJECT |
| price_vs_ma60 | −0.467 | −0.0015 | −0.0012 | −0.100 | 0.50 | [−0.0039, +0.0052] | 0.895 | **1.000** | 0.802 | REJECT |
| volatility_60 | −0.461 | −0.0015 | +0.0003 | −0.103 | 0.25 | [−0.0086, +0.0017] | 0.891 | **0.941** | 0.808 | REJECT |
| kurtosis_60 | +0.264 | −0.0030 | −0.0027 | −0.184 | 0.25 | [−0.0045, +0.0061] | 0.909 | 0.787 | 0.124 | REJECT |
| price_vs_ma120 | −0.358 | −0.0020 | −0.0011 | −0.115 | 0.25 | [−0.0044, +0.0064] | 0.889 | **0.928** | 0.878 | REJECT |

**最刺眼的一行是 `limit_up_count_20`**：全库 raw ICIR 最强（−0.733），
ΔIC = **−0.0002**，即加进模型后不但没有增量，还略微变差。这与上一轮
"它是替代品不是增量"的结论一致，而且这次是用**模型层面**的证据确认的。

## 7. ΔIC

- 全样本均值区间：**0.0001 ~ 0.0150**。
- 正向月份比例最高 0.75，最低 0.25——**没有一致性**。
- 逐折看更清楚：

| 因子 | fold1 (2020) | fold2 (2021) | fold3 (2022) | fold4 (2023) |
|---|---|---|---|---|
| gap_count_20 | +0.0280 | **−0.0250** | +0.0080 | +0.0488 |
| high_52w_proximity | −0.0003 | +0.0006 | +0.0016 | +0.0064 |
| overnight_return_20 | **−0.0125** | +0.0056 | +0.0100 | +0.0011 |
| skewness_60 | −0.0033 | −0.0046 | +0.0066 | +0.0079 |
| volume_price_corr_20 | −0.0034 | +0.0035 | +0.0059 | +0.0003 |

`gap_count_20` 在 fold1 与 fold2 之间**换了符号**——它的"增量"高度依赖
时间段，不是稳定属性。

（完整逐折稳定性见 `reports/figures/incremental_v2/03_fold_stability.png`。）

## 8. ΔRankIC

与 ΔIC 基本同向（两者相关系数很高），没有出现"IC 涨、RankIC 不涨"的
分歧。唯一例外是 `intraday_return_20`：ΔIC +0.0008 但 ΔRankIC −0.0003，
Gate 4 因此拒绝。

## 9. Bootstrap CI

| | 值 |
|---|---|
| block bootstrap（block=3 个月，1000 次重抽） | 见上表最后一列 |
| **区间排除 0 的候选数** | **0 / 20** |
| block 区间平均宽 | 0.01429 |
| iid 区间平均宽 | 0.01414 |
| block / iid 比值 | **1.01** |

**诚实记录一个与预期相反的结果**：本协议特意用 block bootstrap 以尊重
时间相关性，但实测 block 区间只比 iid 宽 1%。也就是说在这个时间尺度上，
ΔIC 序列的序列相关很弱，分块与不分块结论一致。

这不代表"应该用 iid"——正自相关时的代价是实打实的（见
`tests/factors/test_block_bootstrap.py::test_block_interval_is_wider_than_iid_when_series_is_persistent`
的合成数据实验）。只是**在本数据上**它不是决定性因素。

## 10. Prediction impact（§8 / §22）

| 因子 | corr(pred0, pred1) | 平均 \|Δz\| | top-20 名单换手 |
|---|---|---|---|
| gap_count_20 | **0.398** | 0.798 | 大 |
| limit_down_count_20 | 0.627 | — | — |
| limit_up_count_20 | 0.660 | — | — |
| high_52w_proximity | 0.866 | 0.355 | — |
| …其余 | 0.88 ~ 0.91 | 0.29 左右 | — |

`gap_count_20` 把模型输出改变了 60%（corr 0.40）——**是所有候选里对模型
影响最大的**。但它对排序质量的影响只有 +0.0150 IC，且 CI 跨 0。

**预测变了 ≠ 预测变好了。** 这是本轮最重要的一条判读。

## 11. Redundancy（协议修正）

主判据改为**原始因子横截面秩相关**，残差相关降级为诊断。
`require_both`：原始相关与回归 R² **同时**越线才判冗余。

修正直接改变结论——上一轮被判定"有独立信息"的因子：

| 因子 | 与既有因子 max 秩相关 | 对完整 M0 的 R² | 判定 |
|---|---|---|---|
| amount_60 | 0.954 | 0.980 | redundant |
| amihud_20 | **0.919** | **0.962** | redundant |
| parkinson_vol_20 | 0.912 | 0.954 | redundant |
| max_return_20 | 0.903 | 0.971 | redundant |
| price_vs_ma120 | 0.878 | 0.928 | redundant |
| momentum_20 | **1.000** | **1.000** | redundant（= reversal_20 取负，而它在 M0 里） |
| price_vs_ma60 | 0.802 | **1.000** | redundant |

`amihud_20` 是最典型的例子：它是 `amount_20`（在 M0 里）的近似倒数，
秩相关 0.92。**但这个 bug 差点让它当选**——见 §13。

## 12. Candidate selection

最终 5 个 `research_candidate`（Evidence Score 降序）：

| # | 因子 | Evidence | ΔIC | ΔRankIC | pred_corr | R² | 独立性 |
|---|---|---|---|---|---|---|---|
| 1 | `gap_count_20` | 0.460 | +0.0150 | +0.0147 | 0.398 | 0.275 | **最强** |
| 2 | `high_52w_proximity` | 0.405 | +0.0021 | +0.0037 | 0.866 | 0.763 | 中 |
| 3 | `overnight_return_20` | 0.338 | +0.0010 | +0.0013 | 0.908 | 0.431 | 较强 |
| 4 | `skewness_60` | 0.320 | +0.0017 | +0.0024 | 0.911 | 0.691 | 中 |
| 5 | `volume_price_corr_20` | 0.318 | +0.0016 | +0.0015 | 0.899 | 0.806 | 弱 |

**这 5 个是"值得继续观察"的清单，不是"已证明有效"的清单。**
它们的 ΔIC 全部为正、至少 2 个 fold 同向、CI 上界 > 0，但
**CI 下界也全部 < 0**。

### secondary evidence（§18 / §21，不参与选择）

| 因子 | ADD ΔIC | REPLACE ΔIC | 替换对象 | 置换重要性（IC 降幅） |
|---|---|---|---|---|
| gap_count_20 | +0.0150 | +0.0151 | volatility_20 | +0.0006 |
| high_52w_proximity | +0.0021 | −0.0006 | momentum_60 | **−0.0045** |
| overnight_return_20 | +0.0010 | +0.0025 | volatility_20 | −0.0002 |
| skewness_60 | +0.0017 | −0.0003 | momentum_60 | −0.0002 |
| volume_price_corr_20 | +0.0016 | −0.0024 | reversal_20 | +0.0002 |

两点判读：

1. **置换重要性几乎全是 0（甚至为负）**：把候选列在验证集上随机打乱，
   模型 IC 平均只掉 0.0006，多数情况下反而上升。**说明 LightGBM 几乎
   没有依赖这些列做分裂。** ΔIC 的来源更可能是"多加一列改变了模型的
   训练路径"，而不是"模型用上了这一列的信息"。
2. **REPLACE 基本不优于 ADD**（5 个里 3 个为负）。按 §18"先 ADD 再
   REPLACE"，ADD 尚未站稳，REPLACE 更无从谈起。

## 13. Historical test status（§29）

**2024-2025 不再是 untouched test。** 它已经被评估过 3 次
（STEP 6 终评、step8 微结构消融、step9 独立信息研究）。

本阶段的处理：
- 代码层面**禁止** 2024-2025 进入任何选择路径（`incremental/windows.py`
  的两个守卫 + `tests/factors/test_no_test_usage.py` 的静态扫描）。
- 本阶段的全部数字（Stage A / Stage B / 冗余 / bootstrap）**只用 2018-2023**。
- 本阶段**没有**在 2024-2025 上跑任何东西。

今后任何报告中**不得**再写 "strict untouched test"，只能写
"HISTORICAL TEST — observed multiple times"。

## 14. Forward holdout design（§25 / §26）

- **起点**：`2026-09-18`（最后一个已被观察日期的次日；2026-01-01 ~
  2026-09-17 曾用于 paper-live 建议生成，不干净）。
- **模式**：`record_only` —— 只记录、监控、评估，**绝不参与选择**。
- **登记**：`scripts/monitor_forward_holdout.py`，每月登记冻结的预测快照，
  标签窗口走完后回填已实现收益。
- **当前状态**：**0 期**。数据快照截至 2026-09-17，holdout 尚未开始累积。
- **不要因为样本短就急着评估**：holdout 是长期监控机制，不是现在就出结论。

## 15. Limitations（如实）

1. **0/20 的 CI 排除 0**，所以本阶段的"最终候选"没有统计证据支撑。
   它们是**待观察清单**。
2. **协议模型是上界**：关闭子采样让 ΔIC 完全来自新增列，而生产模型
   （`feature_fraction=0.8`）只会更弱。
3. **置换重要性≈0** 提示 ΔIC 可能主要来自模型训练路径的改变，
   而非列本身被使用。这一点本阶段无法进一步区分，是下一轮的问题。
4. **block bootstrap 在本数据上与 iid 几乎相同**（比值 1.01），
   说明时间相关性在这个量级上不是主要不确定性来源；但样本只有 44 个
   信号日，block 长度 3 个月也只有约 15 个块。
5. **Stage A 的 20 个上限**按 |raw ICIR| 排序截断——这个排序本身用了
   研究期数据，属于一种（轻微的）研究期选择。
6. **财务与新闻因子几乎全被覆盖率门淘汰**（0.05~0.41），本阶段实际上
   只评估了市场类因子。这是数据可得性的限制，不是"它们无效"的证据。
7. **冗余判据依赖 R² 阈值的绝对水平**：180 列特征、约 1500 只股票时，
   纯噪声的期望 R² 约 0.12，所以 0.90 的门实际要求"至少 78% 被解释"。

## 16. 本轮修掉的实现 bug（都会给出错误答案）

| # | 问题 | 后果 | 发现方式 |
|---|---|---|---|
| 1 | 候选因子列用 `normalize_panel(..., "rank")`，而它是 `rank(axis=1)` | 单列框架退化成常数 → **每个 ΔIC 都精确等于 0**，看起来像"所有因子都没用" | 干跑后检查列的唯一值数，发现 = 1 |
| 2 | `delta_ic_table` / `prediction_impact` 整表 merge | 两张表都带 `label` → 变成 `label_0`/`label_1` → KeyError，Stage B 直接崩 | 干跑 |
| 3 | 冗余 R² 只对 Alpha158 回归，而相关判据用的是 M0 的 10 个自定义因子 | `require_both` 拿苹果比橘子 → `amihud_20`（与 amount_20 相关 0.92）逃过判据并进入最终候选 | 看到 "corr 0.92 但 R² 0.47" 不自洽 |
| 4 | block 与 iid bootstrap 共用同一个 RNG 流 | block=1 时两者不相等，"iid 对照"失去意义 | 单元测试 |
| 5 | Evidence Score 权重里 stability(0.04) < independence(0.10)，违反 §16 优先级 | 打分与实际声明的优先级不符 | 单元测试 |

Bug 1 现在有回归测试：`tests/factors/test_walk_forward_selection.py::
test_custom_frames_rank_across_stocks_not_across_factors`，
且驱动在构建设计矩阵后会显式检查"有没有常数列"并直接报错。

> 同一类 `rank` 轴 bug 在 STEP 9 上一轮已经出现过一次（当时把
> `amount_20` 的 raw ICIR 报成 1.47）。这次是第二次，所以补了测试。

## 17. 复现

```bash
source .venv/Scripts/activate

# 主协议（Stage A 筛选 + Stage B walk-forward 配对）
python scripts/run_incremental_factor_selection.py

# 次要证据（ADD / REPLACE / 重要性）—— 不参与选择
python scripts/run_incremental_secondary.py

# 图表
MPLBACKEND=Agg python scripts/make_incremental_figures.py

# 验收（12 项）
python scripts/verify_incremental_factor_selection.py

# forward holdout 监控（只记录，不选择）
python scripts/monitor_forward_holdout.py
```

产物：

| 路径 | 内容 |
|---|---|
| `experiments/factors/incremental_v2/stage_a_screen.csv` | Stage A 65 个候选的质量指标 + PIT 结果 |
| `experiments/factors/incremental_v2/candidate_metrics.csv` | Stage B 全指标 |
| `experiments/factors/incremental_v2/bootstrap.csv` | block / iid 置信区间 |
| `experiments/factors/incremental_v2/per_fold.csv` | 逐折 ΔIC |
| `experiments/factors/incremental_v2/delta_ic_series.csv` | 逐日 ΔIC / ΔRankIC / 残差 IC |
| `experiments/factors/incremental_v2/redundancy_matrix.csv` | 原始因子秩相关矩阵（主判据） |
| `experiments/factors/incremental_v2/secondary_add_replace.csv` | ADD / REPLACE / 置换重要性 |
| `experiments/factors/incremental_v2/factor_selection_manifest.json` | **冻结清单** |
| `reports/incremental_factor_candidates.csv` | 候选表（§33 字段） |
| `reports/figures/incremental_v2/*.png` | 8 张图 |
