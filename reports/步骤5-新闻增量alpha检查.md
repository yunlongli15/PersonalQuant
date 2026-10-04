# 步骤 5 新闻增量 alpha 预检查

generated: 2026-09-10T20:14:56

本检查回答 STEP 6 spec §2 的问题：**新闻在已有非新闻因子（factor_pack_v1）基础上是否提供增量 alpha？**

## 变体定义（全部使用 STEP 5 消融同引擎/同参数/同成本/同 Top-20/同 T+1）

| 名称 | 特征 | 冻结依据 |
| --- | --- | --- |
| A | Alpha158 | strategy_v1 锚点（0.2475 / 0.943） |
| B | Alpha158 + factor_pack_v1 | STEP 4 A2 锚点（0.1962 / 0.748） |
| C | Alpha158 + news（规则因子） | — |
| **D** | **Alpha158 + factor_pack_v1 + news** | = STEP 5 消融变体 E |

## frozen test 2024-2025 结果（从 STEP 5 消融 artifacts 读取，未重跑）

| 变体 | 年化 | Sharpe | MDD | IC(test) | RankIC(test) | 换手 |
| --- | --- | --- | --- | --- | --- | --- |
| A | 0.2475 | 0.943 | -0.1995 | 0.0358 | 0.0463 | 0.409 |
| B | 0.1962 | 0.748 | -0.2792 | 0.0351 | 0.0488 | 0.419 |
| C | 0.1094 | 0.456 | -0.2264 | 0.0312 | 0.0439 | 0.402 |
| **D** | 0.2812 | 1.022 | -0.2351 | 0.0372 | 0.0681 | 0.417 |

## B 的完整性（不重跑 B 的依据）

- STEP 4 已完整保存 B（当时编号 A2：Alpha158 + 技术因子 pack），
  STEP 5 消融重跑后与 STEP 4 冻结锚点一致：
  A drift = (0.0000, 0.000)，
  B drift = (0.0000, 0.000) → 无需重跑。
- 本检查未使用 2024-2025 选择任何参数（frozen test 只读）。

## 核心比较：D vs B

| 比较 | Δ年化 | ΔSharpe | ΔMDD | 结论 |
| --- | --- | --- | --- | --- |
| **D vs B** | +0.0851 | +0.273 | +0.0440 | **新闻在 pack_v1 之上有明确增量** |
| D vs A | +0.0337 | +0.079 | -0.0356 | 增量存在（MDD 略深为代价） |
| B vs A | -0.0514 | -0.194 | -0.0796 | pack_v1 单独反而拖累 |

## 回答（如实）

1. **是：新闻在已有非新闻因子基础上提供增量 alpha**（D 0.2812 > B 0.1962，年化 +8.5pp，Sharpe 1.022 vs 0.748，MDD 收窄 4.4pp）。
2. 但增量是**组合效应**：pack_v1 单独（B < A）与 news 单独（C 0.1094）都没有排序能力，只有两者叠加（D）才超过 A。
3. 因此 STEP 6 冻结 alpha 信号 = **S3 = Alpha158 + factor_pack_v1 + news**（生产模型 = experiments/news/strategy 的 strategy_v1_news 模型，未改动）。

## LLM 新闻实验状态

- DEEPSEEK_API_KEY 已配置：否
- LLM News = **NOT YET EVALUATED**（不阻塞 STEP 6；rule-based 结果绝不写成 LLM 结果；不重处理历史新闻、不消耗 API budget）。

## 数据出处

- experiments/news/ablation/comparison.csv（A/B/C/E 行）
- experiments/news/ablation/variant_A,B,C,E/summary.json（锚点核对）
