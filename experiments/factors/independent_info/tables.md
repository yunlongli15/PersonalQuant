# 独立信息研究（2026-09-19）

> 问题：把新因子直接叠加到 S3 上，年化从 0.2812 掉到 0.1592；
> 换成替换式组合反而升到 0.3053。本报告度量**既有信息解释不掉的部分**。

## 方法

对每个候选因子、每个信号日，在当日股票池横截面上：

```
x = rank(因子)                    缺失填中位数（中性）
Z = rank([Alpha158 158 列, S3 的 10 个自定义因子])
r = x − Z·β                       β 由伪逆最小二乘给出
R² = 1 − var(r)/var(x)            被既有信息解释的比例
raw_IC   = spearman(x, 未来 20 日收益)
resid_IC = spearman(r, 未来 20 日收益)   ← 独立信息
```

选因子只用 research 2018-01~2021-12，valid 2022-01~2023-12 复核；2026 paper live 未参与。

## 结果（按 |resid ICIR| 排序，前 25）

| factor | coverage | raw_icir_research | resid_icir_research | resid_icir_valid | r2 |
|---|---|---|---|---|---|
| downside_volatility_60 | 1.00 | -0.356 | -0.559 | -0.689 | 0.89 |
| high_52w_proximity | 1.00 | +0.059 | +0.518 | +0.109 | 0.72 |
| parkinson_vol_20 | 1.00 | -0.535 | -0.502 | -0.596 | 0.93 |
| volatility_60 | 0.96 | -0.460 | -0.456 | -0.663 | 0.89 |
| amihud_20 | 1.00 | -0.200 | -0.442 | +0.002 | 0.94 |
| momentum_120 | 0.98 | -0.137 | +0.441 | -0.027 | 0.69 |
| earnings_yield | 0.05 | +0.068 | -0.400 | -0.302 | 0.20 |
| roe | 0.05 | +0.353 | -0.350 | +0.230 | 0.15 |
| volume_trend_5_60 | 0.99 | -0.543 | +0.345 | -0.123 | 0.97 |
| gross_margin | 0.04 | +0.385 | -0.336 | -0.021 | 0.14 |
| news_sentiment_weighted | 0.43 | -0.079 | -0.297 | -0.027 | 0.47 |
| pe | 0.05 | -0.085 | +0.293 | +0.295 | 0.18 |
| momentum_20 | 0.99 | -0.501 | -0.292 | -0.268 | 1.00 |
| amount_share_20 | 1.00 | -0.068 | +0.291 | +0.565 | 0.99 |
| reversal_20 | 0.99 | +0.501 | -0.287 | +0.133 | 1.00 |
| price_vs_ma120 | 0.93 | -0.355 | +0.274 | -0.089 | 0.86 |
| buyback_event_count_20d | 0.43 | -0.143 | -0.272 | -0.008 | 0.25 |
| reversal_5 | 1.00 | +0.111 | -0.263 | +0.220 | 1.00 |
| novel_news_count_5d | 0.43 | -0.177 | -0.262 | -0.255 | 0.25 |
| roa | 0.06 | +0.214 | -0.259 | +0.193 | 0.15 |
| net_margin | 0.06 | +0.447 | -0.256 | -0.218 | 0.17 |
| news_attention_20d | 0.21 | +0.064 | +0.250 | -0.041 | 0.48 |
| price_vs_ma60 | 0.96 | -0.464 | -0.244 | -0.155 | 0.97 |
| event_sentiment_shock | 0.43 | -0.144 | +0.239 | +0.104 | 0.18 |
| news_count_1d | 0.43 | -0.257 | -0.237 | -0.082 | 0.30 |

`r2` 越接近 1 表示这个因子越是被既有特征复述；
`resid_icir` 才是它真正新增的信息。

## 选中的因子

- **I（独立信息包，共 4 个）**: ['downside_volatility_60', 'high_52w_proximity', 'parkinson_vol_20', 'volatility_60']
- **R（强但冗余对照，共 4 个）**: ['limit_up_count_20', 'max_return_20', 'momentum_20', 'price_vs_ma60']

## 被拒绝的因子（前 20）

| 因子 | 原因 |
|---|---|
| amihud_20 | research -0.0173 vs valid +0.0001 变号 |
| momentum_120 | research +0.0259 vs valid -0.0023 变号 |
| earnings_yield | coverage 0.05 |
| roe | coverage 0.05 |
| volume_trend_5_60 | research +0.0103 vs valid -0.0033 变号 |
| gross_margin | coverage 0.04 |
| news_sentiment_weighted | coverage 0.43 |
| pe | coverage 0.05 |
| momentum_20 | |resid ICIR| 0.292 |
| amount_share_20 | |resid ICIR| 0.291 |
| reversal_20 | |resid ICIR| 0.287 |
| price_vs_ma120 | |resid ICIR| 0.274 |
| buyback_event_count_20d | coverage 0.43 |
| reversal_5 | |resid ICIR| 0.263 |
| novel_news_count_5d | coverage 0.43 |
| roa | coverage 0.06 |
| net_margin | coverage 0.06 |
| news_attention_20d | coverage 0.21 |
| price_vs_ma60 | |resid ICIR| 0.244 |
| event_sentiment_shock | coverage 0.43 |

## 复现

```bash
python scripts/research_independent_info.py
python scripts/portfolio/run_micro_ablation.py --variants S3,I,R --variants-file experiments/factors/independent_info/variants.json --out-dir experiments/factors/independent_ablation
```
