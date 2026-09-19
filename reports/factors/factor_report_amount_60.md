# factor_report_amount_60.md

## definition

- factor: `amount_60`  ·  category: liquidity  ·  version 1.0
- formula: `log(MA(amount_cny,60))`
- source: market  ·  PIT: True
- required fields: amount, close, volume, market_scale
- description: log 60-day average calibrated turnover value (CNY)
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.969
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0187 | 0.1280 | 0.1462 | 0.625 | 0.0128 | 0.0870 | 0.604 |
| 5 | -0.0074 | 0.1170 | -0.0632 | 0.521 | -0.0214 | -0.1504 | 0.458 |
| 10 | -0.0157 | 0.1157 | -0.1353 | 0.438 | -0.0361 | -0.2436 | 0.375 |
| 20 | -0.0318 | 0.1224 | -0.2602 | 0.375 | -0.0543 | -0.3798 | 0.333 |
| 40 | -0.0435 | 0.1177 | -0.3699 | 0.396 | -0.0703 | -0.5119 | 0.333 |
| 60 | -0.0464 | 0.1181 | -0.3932 | 0.458 | -0.0792 | -0.5746 | 0.375 |

quantile mean forward 20d returns: Q1: 0.01632  Q2: 0.01246  Q3: 0.01167  Q4: 0.00812  Q5: 0.00714
Q5-Q1 long-short (gross, monthly): mean -0.00919, ann -0.1226, Sharpe -0.796, MDD -0.4074
top-quintile turnover: 0.214

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0587 | -0.491 | 0.250 |
| 2019 | 12 | -0.0009 | -0.010 | 0.417 |
| 2020 | 12 | -0.0315 | -0.183 | 0.417 |
| 2021 | 12 | -0.1260 | -0.886 | 0.250 |

regime split: up-market IC -0.0606 (n=28) / down-market IC -0.0454 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0176 | 0.1266 | 0.1392 | 0.625 | 0.0128 | 0.0871 | 0.604 |
| 5 | -0.0078 | 0.1158 | -0.0678 | 0.521 | -0.0214 | -0.1504 | 0.458 |
| 10 | -0.0156 | 0.1150 | -0.1356 | 0.438 | -0.0361 | -0.2436 | 0.375 |
| 20 | -0.0289 | 0.1231 | -0.2347 | 0.438 | -0.0543 | -0.3798 | 0.333 |
| 40 | -0.0385 | 0.1180 | -0.3261 | 0.438 | -0.0703 | -0.5119 | 0.333 |
| 60 | -0.0400 | 0.1168 | -0.3425 | 0.458 | -0.0792 | -0.5746 | 0.375 |

quantile mean forward 20d returns: Q1: 0.01633  Q2: 0.01245  Q3: 0.01169  Q4: 0.00810  Q5: 0.00715
Q5-Q1 long-short (gross, monthly): mean -0.00918, ann -0.1226, Sharpe -0.796, MDD -0.4073
top-quintile turnover: 0.214

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0587 | -0.491 | 0.250 |
| 2019 | 12 | -0.0009 | -0.010 | 0.417 |
| 2020 | 12 | -0.0315 | -0.183 | 0.417 |
| 2021 | 12 | -0.1260 | -0.886 | 0.250 |

regime split: up-market IC -0.0606 (n=28) / down-market IC -0.0454 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.989
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0288 | 0.1173 | -0.2455 | 0.458 | -0.0529 | -0.3665 | 0.458 |
| 5 | -0.0191 | 0.1425 | -0.1338 | 0.500 | -0.0442 | -0.2530 | 0.458 |
| 10 | -0.0568 | 0.1135 | -0.5006 | 0.292 | -0.0842 | -0.6123 | 0.250 |
| 20 | -0.0897 | 0.0855 | -1.0492 | 0.167 | -0.1339 | -1.3387 | 0.125 |
| 40 | -0.0935 | 0.1077 | -0.8687 | 0.208 | -0.1442 | -1.2027 | 0.083 |
| 60 | -0.1090 | 0.1020 | -1.0683 | 0.042 | -0.1662 | -1.4919 | 0.042 |

quantile mean forward 20d returns: Q1: 0.01706  Q2: 0.00780  Q3: 0.00535  Q4: -0.00427  Q5: -0.01140
Q5-Q1 long-short (gross, monthly): mean -0.02846, ann -0.2784, Sharpe -3.034, MDD -0.4793
top-quintile turnover: 0.160

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0857 | -0.854 | 0.250 |
| 2023 | 12 | -0.1821 | -2.503 | 0.000 |

regime split: up-market IC -0.1330 (n=13) / down-market IC -0.1350 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0337 | 0.1201 | -0.2802 | 0.542 | -0.0529 | -0.3665 | 0.458 |
| 5 | -0.0199 | 0.1483 | -0.1341 | 0.583 | -0.0442 | -0.2529 | 0.458 |
| 10 | -0.0500 | 0.1144 | -0.4370 | 0.292 | -0.0842 | -0.6121 | 0.250 |
| 20 | -0.0835 | 0.0926 | -0.9021 | 0.208 | -0.1339 | -1.3381 | 0.125 |
| 40 | -0.0881 | 0.1044 | -0.8437 | 0.208 | -0.1442 | -1.2026 | 0.083 |
| 60 | -0.1060 | 0.0924 | -1.1472 | 0.125 | -0.1662 | -1.4921 | 0.042 |

quantile mean forward 20d returns: Q1: 0.01706  Q2: 0.00781  Q3: 0.00533  Q4: -0.00426  Q5: -0.01140
Q5-Q1 long-short (gross, monthly): mean -0.02846, ann -0.2784, Sharpe -3.034, MDD -0.4793
top-quintile turnover: 0.161

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0857 | -0.853 | 0.250 |
| 2023 | 12 | -0.1821 | -2.503 | 0.000 |

regime split: up-market IC -0.1329 (n=13) / down-market IC -0.1350 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.988
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0042 | 0.1493 | 0.0278 | 0.417 | -0.0119 | -0.0632 | 0.375 |
| 5 | -0.0356 | 0.1551 | -0.2293 | 0.375 | -0.0657 | -0.3461 | 0.333 |
| 10 | -0.0299 | 0.1805 | -0.1654 | 0.375 | -0.0605 | -0.2610 | 0.375 |
| 20 | -0.0228 | 0.1603 | -0.1423 | 0.458 | -0.0560 | -0.2766 | 0.375 |
| 40 | -0.0379 | 0.1270 | -0.2983 | 0.333 | -0.0780 | -0.4971 | 0.292 |
| 60 | -0.0412 | 0.1057 | -0.3898 | 0.292 | -0.0921 | -0.7063 | 0.292 |

quantile mean forward 20d returns: Q1: 0.03630  Q2: 0.03259  Q3: 0.03921  Q4: 0.02791  Q5: 0.03470
Q5-Q1 long-short (gross, monthly): mean -0.00160, ann -0.0951, Sharpe -0.452, MDD -0.2438
top-quintile turnover: 0.139

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0237 | -0.117 | 0.417 |
| 2025 | 12 | -0.0882 | -0.447 | 0.333 |

regime split: up-market IC -0.0134 (n=15) / down-market IC -0.1270 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0049 | 0.1485 | 0.0330 | 0.375 | -0.0119 | -0.0633 | 0.375 |
| 5 | -0.0397 | 0.1423 | -0.2790 | 0.333 | -0.0657 | -0.3462 | 0.333 |
| 10 | -0.0265 | 0.1664 | -0.1592 | 0.375 | -0.0606 | -0.2611 | 0.375 |
| 20 | -0.0133 | 0.1470 | -0.0906 | 0.542 | -0.0560 | -0.2766 | 0.375 |
| 40 | -0.0271 | 0.1216 | -0.2231 | 0.333 | -0.0780 | -0.4972 | 0.292 |
| 60 | -0.0270 | 0.1051 | -0.2575 | 0.333 | -0.0921 | -0.7064 | 0.292 |

quantile mean forward 20d returns: Q1: 0.03630  Q2: 0.03259  Q3: 0.03922  Q4: 0.02790  Q5: 0.03470
Q5-Q1 long-short (gross, monthly): mean -0.00160, ann -0.0951, Sharpe -0.452, MDD -0.2438
top-quintile turnover: 0.139

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0237 | -0.117 | 0.417 |
| 2025 | 12 | -0.0882 | -0.447 | 0.333 |

regime split: up-market IC -0.0134 (n=15) / down-market IC -0.1270 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`amount_20`: 0.952  `amihud_20`: -0.914  `downside_volatility_60`: 0.402  `max_return_20`: 0.333  `momentum_120`: 0.313

## redundancy cluster

cluster members: `amount_20`, `amount_60`

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.