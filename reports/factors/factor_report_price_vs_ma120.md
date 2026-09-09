# factor_report_price_vs_ma120.md

## definition

- factor: `price_vs_ma120`  ·  category: price_position  ·  version 1.0
- formula: `adj_close/MA(adj_close,120)-1`
- source: market  ·  PIT: True
- required fields: close, factor
- description: close relative to its 120-day moving average
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.924
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0014 | 0.1389 | -0.0098 | 0.500 | -0.0316 | -0.2047 | 0.417 |
| 5 | -0.0265 | 0.1461 | -0.1817 | 0.375 | -0.0593 | -0.3353 | 0.312 |
| 10 | -0.0171 | 0.1167 | -0.1466 | 0.417 | -0.0486 | -0.3207 | 0.333 |
| 20 | -0.0239 | 0.1185 | -0.2017 | 0.396 | -0.0531 | -0.3772 | 0.354 |
| 40 | -0.0186 | 0.0989 | -0.1878 | 0.458 | -0.0512 | -0.4449 | 0.417 |
| 60 | -0.0078 | 0.0896 | -0.0869 | 0.542 | -0.0400 | -0.3900 | 0.396 |

quantile mean forward 20d returns: Q1: 0.01424  Q2: 0.01200  Q3: 0.01307  Q4: 0.01051  Q5: 0.00590
Q5-Q1 long-short (gross, monthly): mean -0.00833, ann -0.1060, Sharpe -0.631, MDD -0.3612
top-quintile turnover: 0.498

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0433 | -0.330 | 0.500 |
| 2019 | 12 | -0.0468 | -0.364 | 0.250 |
| 2020 | 12 | -0.0003 | -0.002 | 0.500 |
| 2021 | 12 | -0.1218 | -0.989 | 0.167 |

regime split: up-market IC -0.0781 (n=28) / down-market IC -0.0179 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0014 | 0.1492 | 0.0097 | 0.542 | -0.0316 | -0.2048 | 0.417 |
| 5 | -0.0331 | 0.1521 | -0.2179 | 0.417 | -0.0593 | -0.3353 | 0.312 |
| 10 | -0.0225 | 0.1211 | -0.1859 | 0.417 | -0.0486 | -0.3207 | 0.333 |
| 20 | -0.0314 | 0.1245 | -0.2519 | 0.417 | -0.0530 | -0.3771 | 0.354 |
| 40 | -0.0260 | 0.1036 | -0.2510 | 0.438 | -0.0511 | -0.4446 | 0.417 |
| 60 | -0.0129 | 0.0918 | -0.1410 | 0.479 | -0.0400 | -0.3897 | 0.396 |

quantile mean forward 20d returns: Q1: 0.01423  Q2: 0.01203  Q3: 0.01311  Q4: 0.01046  Q5: 0.00589
Q5-Q1 long-short (gross, monthly): mean -0.00834, ann -0.1061, Sharpe -0.631, MDD -0.3614
top-quintile turnover: 0.498

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0434 | -0.330 | 0.500 |
| 2019 | 12 | -0.0468 | -0.364 | 0.250 |
| 2020 | 12 | -0.0003 | -0.002 | 0.500 |
| 2021 | 12 | -0.1217 | -0.989 | 0.167 |

regime split: up-market IC -0.0781 (n=28) / down-market IC -0.0179 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.972
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0107 | 0.1231 | -0.0870 | 0.417 | -0.0313 | -0.2330 | 0.417 |
| 5 | -0.0227 | 0.1320 | -0.1722 | 0.458 | -0.0587 | -0.3822 | 0.375 |
| 10 | -0.0427 | 0.1123 | -0.3803 | 0.375 | -0.0709 | -0.5384 | 0.333 |
| 20 | -0.0360 | 0.1487 | -0.2420 | 0.458 | -0.0711 | -0.4257 | 0.292 |
| 40 | -0.0556 | 0.1473 | -0.3772 | 0.458 | -0.0902 | -0.5449 | 0.333 |
| 60 | -0.0592 | 0.1264 | -0.4687 | 0.333 | -0.0914 | -0.6317 | 0.250 |

quantile mean forward 20d returns: Q1: 0.00441  Q2: 0.00547  Q3: 0.00944  Q4: 0.00441  Q5: -0.00919
Q5-Q1 long-short (gross, monthly): mean -0.01360, ann -0.1619, Sharpe -0.951, MDD -0.3415
top-quintile turnover: 0.564

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.1179 | -0.685 | 0.167 |
| 2023 | 12 | -0.0242 | -0.164 | 0.417 |

regime split: up-market IC -0.1479 (n=13) / down-market IC 0.0198 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0125 | 0.1339 | -0.0934 | 0.458 | -0.0313 | -0.2330 | 0.417 |
| 5 | -0.0305 | 0.1351 | -0.2256 | 0.417 | -0.0587 | -0.3822 | 0.375 |
| 10 | -0.0585 | 0.1157 | -0.5056 | 0.292 | -0.0709 | -0.5383 | 0.333 |
| 20 | -0.0511 | 0.1528 | -0.3345 | 0.375 | -0.0710 | -0.4257 | 0.292 |
| 40 | -0.0702 | 0.1521 | -0.4614 | 0.417 | -0.0901 | -0.5448 | 0.333 |
| 60 | -0.0766 | 0.1291 | -0.5934 | 0.292 | -0.0914 | -0.6317 | 0.250 |

quantile mean forward 20d returns: Q1: 0.00441  Q2: 0.00546  Q3: 0.00945  Q4: 0.00442  Q5: -0.00919
Q5-Q1 long-short (gross, monthly): mean -0.01361, ann -0.1619, Sharpe -0.951, MDD -0.3415
top-quintile turnover: 0.564

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.1179 | -0.685 | 0.167 |
| 2023 | 12 | -0.0242 | -0.164 | 0.417 |

regime split: up-market IC -0.1479 (n=13) / down-market IC 0.0198 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.972
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0032 | 0.1414 | 0.0226 | 0.417 | -0.0215 | -0.1248 | 0.458 |
| 5 | 0.0092 | 0.1303 | 0.0706 | 0.542 | -0.0196 | -0.1265 | 0.375 |
| 10 | 0.0032 | 0.1140 | 0.0281 | 0.458 | -0.0299 | -0.2072 | 0.333 |
| 20 | -0.0250 | 0.1035 | -0.2414 | 0.458 | -0.0704 | -0.5144 | 0.250 |
| 40 | -0.0172 | 0.1043 | -0.1645 | 0.417 | -0.0648 | -0.4795 | 0.375 |
| 60 | -0.0115 | 0.0905 | -0.1266 | 0.417 | -0.0607 | -0.5258 | 0.292 |

quantile mean forward 20d returns: Q1: 0.03602  Q2: 0.03425  Q3: 0.04159  Q4: 0.03203  Q5: 0.02684
Q5-Q1 long-short (gross, monthly): mean -0.00918, ann -0.0966, Sharpe -0.688, MDD -0.2631
top-quintile turnover: 0.548

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0469 | -0.283 | 0.417 |
| 2025 | 12 | -0.0939 | -0.992 | 0.083 |

regime split: up-market IC -0.0997 (n=15) / down-market IC -0.0216 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0046 | 0.1443 | -0.0317 | 0.458 | -0.0215 | -0.1248 | 0.458 |
| 5 | -0.0021 | 0.1412 | -0.0149 | 0.500 | -0.0196 | -0.1265 | 0.375 |
| 10 | -0.0069 | 0.1172 | -0.0586 | 0.417 | -0.0300 | -0.2073 | 0.333 |
| 20 | -0.0353 | 0.1066 | -0.3315 | 0.375 | -0.0704 | -0.5145 | 0.250 |
| 40 | -0.0289 | 0.1080 | -0.2673 | 0.458 | -0.0648 | -0.4794 | 0.375 |
| 60 | -0.0246 | 0.0971 | -0.2530 | 0.417 | -0.0607 | -0.5259 | 0.292 |

quantile mean forward 20d returns: Q1: 0.03602  Q2: 0.03424  Q3: 0.04157  Q4: 0.03207  Q5: 0.02683
Q5-Q1 long-short (gross, monthly): mean -0.00920, ann -0.0968, Sharpe -0.689, MDD -0.2631
top-quintile turnover: 0.548

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0469 | -0.283 | 0.417 |
| 2025 | 12 | -0.0939 | -0.992 | 0.083 |

regime split: up-market IC -0.0997 (n=15) / down-market IC -0.0216 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`momentum_60`: 0.884  `price_vs_ma60`: 0.846  `momentum_120`: 0.827  `momentum_20`: 0.596  `reversal_20`: -0.596

## redundancy cluster

cluster members: `momentum_60`, `price_vs_ma120`, `price_vs_ma60`

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.