# factor_report_downside_volatility_60.md

## definition

- factor: `downside_volatility_60`  ·  category: volatility  ·  version 1.0
- formula: `sqrt(mean(min(ret,0)^2, 60))`
- source: market  ·  PIT: True
- required fields: close, factor
- description: 60-day downside semideviation
- declared (economic) direction: **negative**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0449 | 0.1580 | 0.2841 | 0.625 | 0.0420 | 0.2109 | 0.583 |
| 5 | 0.0267 | 0.1429 | 0.1871 | 0.542 | 0.0136 | 0.0719 | 0.458 |
| 10 | 0.0229 | 0.1238 | 0.1848 | 0.542 | -0.0016 | -0.0091 | 0.500 |
| 20 | -0.0154 | 0.1259 | -0.1226 | 0.438 | -0.0550 | -0.3399 | 0.333 |
| 40 | -0.0292 | 0.1232 | -0.2368 | 0.396 | -0.0717 | -0.4629 | 0.312 |
| 60 | -0.0378 | 0.1134 | -0.3335 | 0.333 | -0.0834 | -0.5932 | 0.292 |

quantile mean forward 20d returns: Q1: 0.00899  Q2: 0.01307  Q3: 0.01338  Q4: 0.01273  Q5: 0.00755
Q5-Q1 long-short (gross, monthly): mean -0.00144, ann -0.0438, Sharpe -0.238, MDD -0.2965
top-quintile turnover: 0.374

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0533 | -0.412 | 0.250 |
| 2019 | 12 | -0.0102 | -0.051 | 0.333 |
| 2020 | 12 | -0.0905 | -0.657 | 0.333 |
| 2021 | 12 | -0.0661 | -0.412 | 0.417 |

regime split: up-market IC -0.0033 (n=28) / down-market IC -0.1275 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0445 | 0.1559 | 0.2857 | 0.646 | 0.0420 | 0.2109 | 0.583 |
| 5 | 0.0253 | 0.1449 | 0.1743 | 0.542 | 0.0136 | 0.0719 | 0.458 |
| 10 | 0.0206 | 0.1255 | 0.1637 | 0.521 | -0.0016 | -0.0092 | 0.500 |
| 20 | -0.0197 | 0.1266 | -0.1553 | 0.417 | -0.0550 | -0.3400 | 0.333 |
| 40 | -0.0355 | 0.1216 | -0.2919 | 0.396 | -0.0717 | -0.4629 | 0.312 |
| 60 | -0.0445 | 0.1121 | -0.3973 | 0.333 | -0.0834 | -0.5932 | 0.292 |

quantile mean forward 20d returns: Q1: 0.00898  Q2: 0.01308  Q3: 0.01338  Q4: 0.01274  Q5: 0.00754
Q5-Q1 long-short (gross, monthly): mean -0.00144, ann -0.0437, Sharpe -0.238, MDD -0.2965
top-quintile turnover: 0.374

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0533 | -0.412 | 0.250 |
| 2019 | 12 | -0.0102 | -0.051 | 0.333 |
| 2020 | 12 | -0.0905 | -0.657 | 0.333 |
| 2021 | 12 | -0.0661 | -0.412 | 0.417 |

regime split: up-market IC -0.0033 (n=28) / down-market IC -0.1275 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0086 | 0.1311 | -0.0658 | 0.500 | -0.0373 | -0.2346 | 0.417 |
| 5 | 0.0098 | 0.1635 | 0.0601 | 0.500 | -0.0240 | -0.1140 | 0.417 |
| 10 | -0.0277 | 0.1299 | -0.2131 | 0.250 | -0.0696 | -0.4107 | 0.250 |
| 20 | -0.0524 | 0.1293 | -0.4052 | 0.375 | -0.0980 | -0.6037 | 0.333 |
| 40 | -0.0681 | 0.1159 | -0.5870 | 0.250 | -0.1164 | -0.8140 | 0.250 |
| 60 | -0.0894 | 0.0885 | -1.0103 | 0.208 | -0.1477 | -1.3453 | 0.083 |

quantile mean forward 20d returns: Q1: 0.00816  Q2: 0.00607  Q3: 0.00684  Q4: -0.00014  Q5: -0.00640
Q5-Q1 long-short (gross, monthly): mean -0.01455, ann -0.1679, Sharpe -1.137, MDD -0.3075
top-quintile turnover: 0.392

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0375 | -0.267 | 0.417 |
| 2023 | 12 | -0.1585 | -0.989 | 0.250 |

regime split: up-market IC -0.0224 (n=13) / down-market IC -0.1873 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0089 | 0.1351 | -0.0662 | 0.500 | -0.0373 | -0.2346 | 0.417 |
| 5 | 0.0130 | 0.1634 | 0.0795 | 0.458 | -0.0240 | -0.1140 | 0.417 |
| 10 | -0.0291 | 0.1305 | -0.2229 | 0.250 | -0.0696 | -0.4107 | 0.250 |
| 20 | -0.0526 | 0.1242 | -0.4237 | 0.333 | -0.0980 | -0.6037 | 0.333 |
| 40 | -0.0700 | 0.1121 | -0.6246 | 0.292 | -0.1164 | -0.8140 | 0.250 |
| 60 | -0.0919 | 0.0815 | -1.1277 | 0.083 | -0.1477 | -1.3454 | 0.083 |

quantile mean forward 20d returns: Q1: 0.00816  Q2: 0.00607  Q3: 0.00682  Q4: -0.00012  Q5: -0.00640
Q5-Q1 long-short (gross, monthly): mean -0.01456, ann -0.1679, Sharpe -1.137, MDD -0.3076
top-quintile turnover: 0.392

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0375 | -0.267 | 0.417 |
| 2023 | 12 | -0.1585 | -0.989 | 0.250 |

regime split: up-market IC -0.0224 (n=13) / down-market IC -0.1873 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0356 | 0.1667 | 0.2138 | 0.583 | 0.0212 | 0.0966 | 0.500 |
| 5 | -0.0385 | 0.1930 | -0.1994 | 0.375 | -0.0729 | -0.2888 | 0.375 |
| 10 | -0.0071 | 0.1886 | -0.0375 | 0.542 | -0.0325 | -0.1355 | 0.500 |
| 20 | 0.0094 | 0.1506 | 0.0625 | 0.458 | -0.0295 | -0.1436 | 0.417 |
| 40 | 0.0065 | 0.1205 | 0.0542 | 0.583 | -0.0298 | -0.1710 | 0.375 |
| 60 | 0.0238 | 0.1004 | 0.2372 | 0.625 | -0.0136 | -0.0988 | 0.500 |

quantile mean forward 20d returns: Q1: 0.02489  Q2: 0.03233  Q3: 0.04135  Q4: 0.03768  Q5: 0.03448
Q5-Q1 long-short (gross, monthly): mean 0.00959, ann 0.0789, Sharpe 0.386, MDD -0.1514
top-quintile turnover: 0.401

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0194 | -0.091 | 0.417 |
| 2025 | 12 | -0.0396 | -0.202 | 0.417 |

regime split: up-market IC 0.0661 (n=15) / down-market IC -0.1888 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0307 | 0.1650 | 0.1859 | 0.542 | 0.0212 | 0.0965 | 0.500 |
| 5 | -0.0404 | 0.1855 | -0.2175 | 0.417 | -0.0729 | -0.2888 | 0.375 |
| 10 | -0.0104 | 0.1834 | -0.0564 | 0.583 | -0.0325 | -0.1355 | 0.500 |
| 20 | 0.0030 | 0.1467 | 0.0201 | 0.458 | -0.0295 | -0.1436 | 0.417 |
| 40 | -0.0014 | 0.1188 | -0.0117 | 0.583 | -0.0298 | -0.1710 | 0.375 |
| 60 | 0.0146 | 0.1026 | 0.1422 | 0.542 | -0.0136 | -0.0988 | 0.500 |

quantile mean forward 20d returns: Q1: 0.02489  Q2: 0.03233  Q3: 0.04138  Q4: 0.03765  Q5: 0.03448
Q5-Q1 long-short (gross, monthly): mean 0.00959, ann 0.0789, Sharpe 0.386, MDD -0.1514
top-quintile turnover: 0.401

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0194 | -0.091 | 0.417 |
| 2025 | 12 | -0.0396 | -0.202 | 0.417 |

regime split: up-market IC 0.0661 (n=15) / down-market IC -0.1888 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`volatility_60`: 0.913  `volatility_20`: 0.709  `earnings_yield`: -0.526  `pe`: 0.497  `amount_60`: 0.402

## redundancy cluster

cluster members: `downside_volatility_60`, `volatility_20`, `volatility_60`

## interpretation & limitations

- declared direction `negative` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.