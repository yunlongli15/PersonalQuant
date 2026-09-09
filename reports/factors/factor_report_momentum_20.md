# factor_report_momentum_20.md

## definition

- factor: `momentum_20`  ·  category: momentum  ·  version 1.0
- formula: `adj_close[t]/adj_close[t-20]-1`
- source: market  ·  PIT: True
- required fields: close, factor
- description: 20-trading-day momentum on adjusted close
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.999
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0094 | 0.1229 | 0.0762 | 0.542 | -0.0263 | -0.1904 | 0.458 |
| 5 | -0.0123 | 0.1367 | -0.0899 | 0.458 | -0.0463 | -0.2769 | 0.396 |
| 10 | -0.0174 | 0.1061 | -0.1644 | 0.396 | -0.0478 | -0.3537 | 0.354 |
| 20 | -0.0366 | 0.1005 | -0.3639 | 0.375 | -0.0615 | -0.5170 | 0.292 |
| 40 | -0.0293 | 0.0945 | -0.3095 | 0.438 | -0.0565 | -0.4914 | 0.354 |
| 60 | -0.0138 | 0.0872 | -0.1581 | 0.458 | -0.0396 | -0.3809 | 0.333 |

quantile mean forward 20d returns: Q1: 0.01563  Q2: 0.01341  Q3: 0.01341  Q4: 0.01099  Q5: 0.00228
Q5-Q1 long-short (gross, monthly): mean -0.01335, ann -0.1483, Sharpe -1.024, MDD -0.4760
top-quintile turnover: 0.791

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0864 | -0.854 | 0.083 |
| 2019 | 12 | -0.0855 | -0.706 | 0.250 |
| 2020 | 12 | -0.0137 | -0.115 | 0.500 |
| 2021 | 12 | -0.0606 | -0.510 | 0.333 |

regime split: up-market IC -0.0780 (n=28) / down-market IC -0.0385 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0155 | 0.1326 | 0.1169 | 0.562 | -0.0263 | -0.1905 | 0.458 |
| 5 | -0.0166 | 0.1383 | -0.1203 | 0.479 | -0.0463 | -0.2769 | 0.396 |
| 10 | -0.0232 | 0.1074 | -0.2157 | 0.458 | -0.0477 | -0.3536 | 0.354 |
| 20 | -0.0427 | 0.1034 | -0.4128 | 0.375 | -0.0615 | -0.5169 | 0.292 |
| 40 | -0.0358 | 0.0941 | -0.3802 | 0.417 | -0.0565 | -0.4913 | 0.354 |
| 60 | -0.0197 | 0.0859 | -0.2288 | 0.438 | -0.0396 | -0.3808 | 0.333 |

quantile mean forward 20d returns: Q1: 0.01562  Q2: 0.01343  Q3: 0.01339  Q4: 0.01100  Q5: 0.00228
Q5-Q1 long-short (gross, monthly): mean -0.01334, ann -0.1483, Sharpe -1.024, MDD -0.4759
top-quintile turnover: 0.791

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0864 | -0.854 | 0.083 |
| 2019 | 12 | -0.0855 | -0.706 | 0.250 |
| 2020 | 12 | -0.0137 | -0.115 | 0.500 |
| 2021 | 12 | -0.0605 | -0.509 | 0.333 |

regime split: up-market IC -0.0780 (n=28) / down-market IC -0.0385 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 1.000
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0125 | 0.1302 | -0.0960 | 0.500 | -0.0341 | -0.2309 | 0.458 |
| 5 | -0.0260 | 0.1341 | -0.1937 | 0.458 | -0.0536 | -0.3357 | 0.375 |
| 10 | -0.0267 | 0.1019 | -0.2620 | 0.417 | -0.0486 | -0.3707 | 0.375 |
| 20 | -0.0204 | 0.1145 | -0.1780 | 0.542 | -0.0469 | -0.3461 | 0.417 |
| 40 | -0.0503 | 0.1322 | -0.3805 | 0.417 | -0.0798 | -0.5168 | 0.333 |
| 60 | -0.0378 | 0.1227 | -0.3083 | 0.375 | -0.0595 | -0.4065 | 0.333 |

quantile mean forward 20d returns: Q1: 0.00141  Q2: 0.00486  Q3: 0.00898  Q4: 0.00724  Q5: -0.00794
Q5-Q1 long-short (gross, monthly): mean -0.00935, ann -0.1208, Sharpe -0.951, MDD -0.2916
top-quintile turnover: 0.838

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0978 | -0.671 | 0.333 |
| 2023 | 12 | 0.0039 | 0.039 | 0.500 |

regime split: up-market IC -0.1072 (n=13) / down-market IC 0.0243 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0137 | 0.1378 | -0.0990 | 0.500 | -0.0341 | -0.2309 | 0.458 |
| 5 | -0.0358 | 0.1350 | -0.2654 | 0.417 | -0.0536 | -0.3357 | 0.375 |
| 10 | -0.0441 | 0.0991 | -0.4449 | 0.417 | -0.0486 | -0.3706 | 0.375 |
| 20 | -0.0374 | 0.1145 | -0.3267 | 0.417 | -0.0469 | -0.3461 | 0.417 |
| 40 | -0.0631 | 0.1338 | -0.4716 | 0.333 | -0.0798 | -0.5168 | 0.333 |
| 60 | -0.0538 | 0.1227 | -0.4385 | 0.333 | -0.0594 | -0.4065 | 0.333 |

quantile mean forward 20d returns: Q1: 0.00141  Q2: 0.00486  Q3: 0.00898  Q4: 0.00723  Q5: -0.00794
Q5-Q1 long-short (gross, monthly): mean -0.00934, ann -0.1208, Sharpe -0.951, MDD -0.2915
top-quintile turnover: 0.838

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0978 | -0.671 | 0.333 |
| 2023 | 12 | 0.0039 | 0.039 | 0.500 |

regime split: up-market IC -0.1072 (n=13) / down-market IC 0.0243 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.999
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0015 | 0.1393 | -0.0107 | 0.458 | -0.0342 | -0.2027 | 0.375 |
| 5 | 0.0126 | 0.1337 | 0.0946 | 0.500 | -0.0187 | -0.1152 | 0.417 |
| 10 | -0.0084 | 0.1042 | -0.0803 | 0.500 | -0.0425 | -0.3155 | 0.417 |
| 20 | -0.0311 | 0.0946 | -0.3287 | 0.417 | -0.0718 | -0.5952 | 0.250 |
| 40 | -0.0201 | 0.0779 | -0.2582 | 0.375 | -0.0569 | -0.5206 | 0.250 |
| 60 | -0.0206 | 0.0667 | -0.3089 | 0.292 | -0.0568 | -0.6444 | 0.208 |

quantile mean forward 20d returns: Q1: 0.03715  Q2: 0.03496  Q3: 0.04090  Q4: 0.03300  Q5: 0.02471
Q5-Q1 long-short (gross, monthly): mean -0.01244, ann -0.1327, Sharpe -1.098, MDD -0.2891
top-quintile turnover: 0.837

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0802 | -0.602 | 0.250 |
| 2025 | 12 | -0.0634 | -0.598 | 0.250 |

regime split: up-market IC -0.1170 (n=15) / down-market IC 0.0035 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0059 | 0.1379 | -0.0429 | 0.500 | -0.0342 | -0.2027 | 0.375 |
| 5 | -0.0005 | 0.1389 | -0.0036 | 0.458 | -0.0187 | -0.1151 | 0.417 |
| 10 | -0.0196 | 0.1073 | -0.1828 | 0.458 | -0.0425 | -0.3155 | 0.417 |
| 20 | -0.0431 | 0.0987 | -0.4362 | 0.375 | -0.0718 | -0.5952 | 0.250 |
| 40 | -0.0308 | 0.0831 | -0.3710 | 0.292 | -0.0569 | -0.5205 | 0.250 |
| 60 | -0.0325 | 0.0766 | -0.4239 | 0.292 | -0.0568 | -0.6443 | 0.208 |

quantile mean forward 20d returns: Q1: 0.03715  Q2: 0.03496  Q3: 0.04091  Q4: 0.03301  Q5: 0.02470
Q5-Q1 long-short (gross, monthly): mean -0.01244, ann -0.1327, Sharpe -1.098, MDD -0.2891
top-quintile turnover: 0.837

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0802 | -0.602 | 0.250 |
| 2025 | 12 | -0.0634 | -0.598 | 0.250 |

regime split: up-market IC -0.1170 (n=15) / down-market IC 0.0035 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`reversal_20`: -1.000  `price_vs_ma20`: 0.798  `price_vs_ma60`: 0.792  `price_vs_ma120`: 0.596  `momentum_60`: 0.507

## redundancy cluster

cluster members: `momentum_20`, `reversal_20`

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.