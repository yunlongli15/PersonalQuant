# factor_report_amount_20.md

## definition

- factor: `amount_20`  ·  category: liquidity  ·  version 1.0
- formula: `log(MA(amount_cny,20))`
- source: market  ·  PIT: True
- required fields: amount, close, volume, market_scale
- description: log 20-day average calibrated turnover value (CNY)
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0193 | 0.1333 | 0.1447 | 0.625 | 0.0060 | 0.0400 | 0.583 |
| 5 | -0.0102 | 0.1273 | -0.0799 | 0.500 | -0.0320 | -0.2098 | 0.458 |
| 10 | -0.0193 | 0.1213 | -0.1592 | 0.500 | -0.0465 | -0.3042 | 0.396 |
| 20 | -0.0390 | 0.1312 | -0.2972 | 0.354 | -0.0676 | -0.4477 | 0.312 |
| 40 | -0.0507 | 0.1247 | -0.4064 | 0.396 | -0.0839 | -0.5867 | 0.333 |
| 60 | -0.0529 | 0.1223 | -0.4323 | 0.417 | -0.0922 | -0.6540 | 0.312 |

quantile mean forward 20d returns: Q1: 0.01634  Q2: 0.01373  Q3: 0.01195  Q4: 0.00862  Q5: 0.00507
Q5-Q1 long-short (gross, monthly): mean -0.01127, ann -0.1448, Sharpe -0.887, MDD -0.4651
top-quintile turnover: 0.338

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0739 | -0.608 | 0.167 |
| 2019 | 12 | -0.0177 | -0.178 | 0.417 |
| 2020 | 12 | -0.0263 | -0.139 | 0.500 |
| 2021 | 12 | -0.1523 | -1.093 | 0.167 |

regime split: up-market IC -0.0737 (n=28) / down-market IC -0.0590 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0178 | 0.1324 | 0.1342 | 0.604 | 0.0060 | 0.0401 | 0.583 |
| 5 | -0.0111 | 0.1264 | -0.0881 | 0.521 | -0.0320 | -0.2098 | 0.458 |
| 10 | -0.0195 | 0.1204 | -0.1616 | 0.458 | -0.0465 | -0.3042 | 0.396 |
| 20 | -0.0367 | 0.1315 | -0.2790 | 0.396 | -0.0676 | -0.4477 | 0.312 |
| 40 | -0.0464 | 0.1256 | -0.3694 | 0.417 | -0.0839 | -0.5867 | 0.333 |
| 60 | -0.0471 | 0.1216 | -0.3875 | 0.396 | -0.0922 | -0.6539 | 0.312 |

quantile mean forward 20d returns: Q1: 0.01634  Q2: 0.01373  Q3: 0.01193  Q4: 0.00864  Q5: 0.00507
Q5-Q1 long-short (gross, monthly): mean -0.01127, ann -0.1449, Sharpe -0.887, MDD -0.4653
top-quintile turnover: 0.338

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0739 | -0.608 | 0.167 |
| 2019 | 12 | -0.0177 | -0.178 | 0.417 |
| 2020 | 12 | -0.0263 | -0.139 | 0.500 |
| 2021 | 12 | -0.1523 | -1.093 | 0.167 |

regime split: up-market IC -0.0737 (n=28) / down-market IC -0.0590 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0292 | 0.1153 | -0.2532 | 0.375 | -0.0578 | -0.4156 | 0.417 |
| 5 | -0.0203 | 0.1370 | -0.1485 | 0.417 | -0.0509 | -0.3054 | 0.375 |
| 10 | -0.0609 | 0.1108 | -0.5492 | 0.250 | -0.0939 | -0.7148 | 0.208 |
| 20 | -0.0908 | 0.0807 | -1.1246 | 0.125 | -0.1406 | -1.5834 | 0.083 |
| 40 | -0.0966 | 0.1085 | -0.8901 | 0.167 | -0.1519 | -1.2574 | 0.083 |
| 60 | -0.1157 | 0.1013 | -1.1417 | 0.042 | -0.1782 | -1.6096 | 0.042 |

quantile mean forward 20d returns: Q1: 0.01630  Q2: 0.00819  Q3: 0.00610  Q4: -0.00365  Q5: -0.01241
Q5-Q1 long-short (gross, monthly): mean -0.02870, ann -0.2820, Sharpe -3.446, MDD -0.4844
top-quintile turnover: 0.283

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.1024 | -1.365 | 0.167 |
| 2023 | 12 | -0.1788 | -2.104 | 0.000 |

regime split: up-market IC -0.1506 (n=13) / down-market IC -0.1289 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0339 | 0.1203 | -0.2816 | 0.417 | -0.0578 | -0.4156 | 0.417 |
| 5 | -0.0214 | 0.1432 | -0.1498 | 0.458 | -0.0509 | -0.3054 | 0.375 |
| 10 | -0.0550 | 0.1120 | -0.4911 | 0.250 | -0.0939 | -0.7148 | 0.208 |
| 20 | -0.0859 | 0.0878 | -0.9786 | 0.167 | -0.1406 | -1.5834 | 0.083 |
| 40 | -0.0917 | 0.1047 | -0.8759 | 0.167 | -0.1519 | -1.2575 | 0.083 |
| 60 | -0.1123 | 0.0919 | -1.2218 | 0.042 | -0.1782 | -1.6098 | 0.042 |

quantile mean forward 20d returns: Q1: 0.01630  Q2: 0.00819  Q3: 0.00612  Q4: -0.00369  Q5: -0.01238
Q5-Q1 long-short (gross, monthly): mean -0.02868, ann -0.2818, Sharpe -3.440, MDD -0.4841
top-quintile turnover: 0.283

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.1024 | -1.365 | 0.167 |
| 2023 | 12 | -0.1789 | -2.104 | 0.000 |

regime split: up-market IC -0.1506 (n=13) / down-market IC -0.1289 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0019 | 0.1369 | 0.0139 | 0.458 | -0.0195 | -0.1123 | 0.375 |
| 5 | -0.0360 | 0.1669 | -0.2159 | 0.292 | -0.0735 | -0.3641 | 0.292 |
| 10 | -0.0351 | 0.1737 | -0.2022 | 0.333 | -0.0736 | -0.3306 | 0.333 |
| 20 | -0.0286 | 0.1553 | -0.1841 | 0.417 | -0.0684 | -0.3487 | 0.333 |
| 40 | -0.0431 | 0.1287 | -0.3348 | 0.375 | -0.0881 | -0.5602 | 0.292 |
| 60 | -0.0460 | 0.1112 | -0.4139 | 0.333 | -0.1015 | -0.7571 | 0.292 |

quantile mean forward 20d returns: Q1: 0.03749  Q2: 0.03345  Q3: 0.03992  Q4: 0.02558  Q5: 0.03428
Q5-Q1 long-short (gross, monthly): mean -0.00321, ann -0.1062, Sharpe -0.520, MDD -0.2503
top-quintile turnover: 0.252

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0354 | -0.173 | 0.417 |
| 2025 | 12 | -0.1015 | -0.559 | 0.250 |

regime split: up-market IC -0.0319 (n=15) / down-market IC -0.1294 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0027 | 0.1404 | 0.0195 | 0.417 | -0.0195 | -0.1124 | 0.375 |
| 5 | -0.0403 | 0.1522 | -0.2646 | 0.292 | -0.0735 | -0.3642 | 0.292 |
| 10 | -0.0303 | 0.1623 | -0.1866 | 0.375 | -0.0736 | -0.3306 | 0.333 |
| 20 | -0.0174 | 0.1441 | -0.1204 | 0.500 | -0.0684 | -0.3487 | 0.333 |
| 40 | -0.0306 | 0.1234 | -0.2477 | 0.375 | -0.0881 | -0.5602 | 0.292 |
| 60 | -0.0304 | 0.1090 | -0.2792 | 0.292 | -0.1015 | -0.7571 | 0.292 |

quantile mean forward 20d returns: Q1: 0.03749  Q2: 0.03345  Q3: 0.03993  Q4: 0.02557  Q5: 0.03428
Q5-Q1 long-short (gross, monthly): mean -0.00321, ann -0.1062, Sharpe -0.520, MDD -0.2503
top-quintile turnover: 0.252

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0354 | -0.173 | 0.417 |
| 2025 | 12 | -0.1015 | -0.559 | 0.250 |

regime split: up-market IC -0.0319 (n=15) / down-market IC -0.1294 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`amount_60`: 0.952  `amihud_20`: -0.910  `max_return_20`: 0.463  `downside_volatility_60`: 0.357  `momentum_120`: 0.348

## redundancy cluster

cluster members: `amount_20`, `amount_60`

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.