# 新因子挖掘与回测（2026-09-19）

> 目标：挖一批**新的**有效因子，并诚实回答"它们能不能提升策略"。
> 纪律同 STEP 4/5/6：因子入选只用 research 2018-2021 + valid 2022-2023；
> frozen test 2024-2025 只做**单次**最终评估；回测冻结配置（Top-20 等权、
> T+1、同一成本模型）。

---

## 1. 新增了什么（16 个候选因子）

全部是现有因子库里**没有**的、A 股有文献/经验支持的维度：

| 类别 | 因子 | 假设 |
|---|---|---|
| 隔夜/日内分解 | `overnight_return_20`、`intraday_return_20`、`overnight_intraday_ratio_20` | A 股隔夜与日内收益预测方向相反，拆开比单一动量多一层信息 |
| 彩票/偏度 | `max_return_20`、`skewness_60`、`kurtosis_60` | 投资者偏好极端正收益，这类股票后续跑输（MAX 效应） |
| 流动性/冲击 | `amihud_20`、`turnover_volatility_20`、`amount_share_20` | Amihud 非流动性溢价；换手率的**波动**而非水平 |
| 位置/波动 | `high_52w_proximity`、`parkinson_vol_20` | 52 周高点效应；高低价波动率比收盘价更有效 |
| A 股特有 | `limit_up_count_20`、`limit_down_count_20` | 涨跌停次数直接反映资金与情绪极值 |
| 量价关系 | `volume_price_corr_20`、`volume_trend_5_60`、`gap_count_20` | 放量上涨 vs 放量下跌；跳空频率 |

PIT 严格性：全部通过"未来数据投毒不变"测试（`tests/factors/test_no_future_data.py`，
本次还把测试夹具补上了 open/high/low，否则读 bars 的因子等于没被测到）。

---

## 2. 单因子表现（rank-ICIR，20 日）

| 因子 | research 2018-2021 | valid 2022-2023 | **test 2024-2025（单次）** | 结论 |
|---|---|---|---|---|
| **limit_up_count_20** | -0.906 | -0.928 | **-0.831** | 极强且三期一致 |
| **volume_trend_5_60** | -0.543 | -0.455 | **-0.665** | 延续且更强 |
| **max_return_20** | -0.610 | -0.833 | **-0.492** | 延续 |
| **skewness_60** | -0.502 | -0.732 | **-0.453** | 延续 |
| **parkinson_vol_20** | -0.496 | — | -0.368 | 减弱但同向 |
| amihud_20 | +0.283 | — | +0.233 | 同向（未过门槛） |
| volume_price_corr_20 | -0.513 | -0.620 | **-0.116** | ⚠️ 大幅衰减 |

**这与 STEP 4 的财务因子形成鲜明对比**：那批因子 research 期看着有效、
一到 test 就反转（roe test ICIR -0.12）；这批微结构因子在 frozen test 中
**基本全部同向延续**。

> 注意 ICIR 绝对值偏大（-0.9）意味着 IC 非常稳定，但也说明这些因子高度
> 依赖横截面排序中的极端组；不能按"ICIR 越大越好"线性外推收益。

---

## 3. 组合回测（**核心问题：能不能提升策略？**）

同引擎 / 同区间 / 同参数 / 同成本 / 同 Top-20 / 同 T+1，只改特征集：

| 变体 | 自定义因子 | 年化 | Sharpe | MDD | Calmar | IC(test) | ICIR |
|---|---|---|---|---|---|---|---|
| **S3（冻结基线）** | 10 | 0.2812 | 1.022 | -0.2351 | 1.196 | 0.0372 | 0.446 |
| **M**（Alpha158 + 新选因子） | 11 | **0.3053** | **1.148** | -0.2743 | 1.113 | 0.0303 | 0.297 |
| **N**（S3 + 新选因子） | 15 | 0.1592 | 0.657 | -0.3052 | 0.522 | 0.0287 | 0.290 |

S3 **精确复现冻结锚点**（0.2812 / 1.022 / -0.2351）——基准可信。

### 诚实结论

1. **M 的收益与 Sharpe 高于 S3**（年化 +2.4pp、Sharpe +0.13），
   但 **MDD 深了 3.9pp、IC/ICIR 反而更低**。IC 更低而收益更高，说明改善
   **不是来自更好的排序能力**，更可能来自不同的风险暴露（恰好押中 2024-25
   的某段风格）。在 24 个月的样本上，+0.13 Sharpe 的差异**不足以判定为真实
   改进**。
2. **N 明显更差**（年化 -12.2pp、Sharpe -0.37）。把 15 个自定义因子叠在
   冻结的 10 个之上，模型在训练期过拟合、样本外退化——**因子越多不等于越好**。
3. 因此：**这批新因子有真实的单因子预测力（尤其涨停次数、量能趋势），
   但把它们加入组合并没有带来可信的提升。** 按项目纪律它们保持
   research candidate，**不进入 strategy_v2**。

---

## 4. 复现方法

```bash
# 单因子评估（research+valid 选择 → frozen test 单次）
python scripts/research_all_factors.py --run-id micro_run_001
# 产物: experiments/factors/micro_run_001/{evaluations/*.json, leaderboard.csv,
#        factor_pack_v1.json, factor_pack_v1.md}

# 组合消融回测（S3 / M / N）
python scripts/portfolio/run_micro_ablation.py --variants S3,M,N
# 产物: experiments/factors/micro_ablation/{variant_*/summary.json, comparison.csv}
```

## 5. 顺带修掉的两个真实 bug

1. **`quantile_analysis` 遇到并列预测值会崩**（`Bin edges must be unique`）：
   预测值高度离散（小特征集 + LightGBM 叶节点值重复）时 `pd.qcut` 直接抛错，
   整轮回测失败。改为基于排名的分桶（连续预测值结果相同，离散时优雅降级）。
2. **消融脚本特征列表可能重复**：新包与旧包都含 `amount_20`，LightGBM
   拒绝重名特征直接报错。已按首次出现去重。
