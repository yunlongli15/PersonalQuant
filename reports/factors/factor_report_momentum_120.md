# factor_report_momentum_120.md

## definition

- factor: `momentum_120`  ·  category: momentum  ·  version 1.0
- formula: `adj_close[t]/adj_close[t-120]-1`
- source: market  ·  PIT: True
- required fields: close, factor
- description: 120-trading-day momentum on adjusted close
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.984
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0062 | 0.1331 | 0.0464 | 0.625 | -0.0121 | -0.0816 | 0.562 |
| 5 | -0.0275 | 0.1310 | -0.2100 | 0.417 | -0.0495 | -0.3128 | 0.375 |
| 10 | -0.0149 | 0.1205 | -0.1238 | 0.479 | -0.0384 | -0.2505 | 0.417 |
| 20 | -0.0111 | 0.1266 | -0.0880 | 0.479 | -0.0326 | -0.2167 | 0.438 |
| 40 | -0.0062 | 0.1051 | -0.0592 | 0.479 | -0.0327 | -0.2751 | 0.354 |
| 60 | -0.0004 | 0.0998 | -0.0036 | 0.542 | -0.0283 | -0.2562 | 0.417 |

quantile mean forward 20d returns: Q1: 0.01197  Q2: 0.01096  Q3: 0.01224  Q4: 0.01255  Q5: 0.00800
Q5-Q1 long-short (gross, monthly): mean -0.00397, ann -0.0648, Sharpe -0.384, MDD -0.2760
top-quintile turnover: 0.433

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0244 | -0.159 | 0.583 |
| 2019 | 12 | -0.0174 | -0.138 | 0.333 |
| 2020 | 12 | 0.0060 | 0.036 | 0.500 |
| 2021 | 12 | -0.0947 | -0.702 | 0.333 |

regime split: up-market IC -0.0564 (n=28) / down-market IC 0.0008 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0030 | 0.1395 | 0.0218 | 0.583 | -0.0120 | -0.0816 | 0.562 |
| 5 | -0.0319 | 0.1334 | -0.2393 | 0.438 | -0.0495 | -0.3128 | 0.375 |
| 10 | -0.0166 | 0.1236 | -0.1344 | 0.479 | -0.0384 | -0.2505 | 0.417 |
| 20 | -0.0170 | 0.1316 | -0.1291 | 0.500 | -0.0326 | -0.2168 | 0.438 |
| 40 | -0.0136 | 0.1132 | -0.1201 | 0.417 | -0.0327 | -0.2751 | 0.354 |
| 60 | -0.0052 | 0.1079 | -0.0486 | 0.500 | -0.0283 | -0.2561 | 0.417 |

quantile mean forward 20d returns: Q1: 0.01196  Q2: 0.01095  Q3: 0.01226  Q4: 0.01254  Q5: 0.00800
Q5-Q1 long-short (gross, monthly): mean -0.00396, ann -0.0648, Sharpe -0.384, MDD -0.2760
top-quintile turnover: 0.433

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0244 | -0.160 | 0.583 |
| 2019 | 12 | -0.0174 | -0.138 | 0.333 |
| 2020 | 12 | 0.0060 | 0.036 | 0.500 |
| 2021 | 12 | -0.0947 | -0.702 | 0.333 |

regime split: up-market IC -0.0564 (n=28) / down-market IC 0.0007 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.998
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0042 | 0.1059 | -0.0393 | 0.542 | -0.0170 | -0.1519 | 0.500 |
| 5 | -0.0166 | 0.1188 | -0.1401 | 0.542 | -0.0431 | -0.3053 | 0.500 |
| 10 | -0.0392 | 0.1114 | -0.3517 | 0.417 | -0.0581 | -0.4449 | 0.375 |
| 20 | -0.0321 | 0.1394 | -0.2302 | 0.458 | -0.0582 | -0.3662 | 0.417 |
| 40 | -0.0526 | 0.1435 | -0.3665 | 0.375 | -0.0786 | -0.4828 | 0.333 |
| 60 | -0.0484 | 0.1186 | -0.4084 | 0.375 | -0.0720 | -0.5300 | 0.333 |

quantile mean forward 20d returns: Q1: 0.00402  Q2: 0.00470  Q3: 0.00843  Q4: 0.00547  Q5: -0.00808
Q5-Q1 long-short (gross, monthly): mean -0.01210, ann -0.1567, Sharpe -0.959, MDD -0.3391
top-quintile turnover: 0.491

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0972 | -0.567 | 0.333 |
| 2023 | 12 | -0.0192 | -0.142 | 0.500 |

regime split: up-market IC -0.1259 (n=13) / down-market IC 0.0219 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0055 | 0.1141 | -0.0484 | 0.417 | -0.0169 | -0.1518 | 0.500 |
| 5 | -0.0239 | 0.1183 | -0.2020 | 0.500 | -0.0431 | -0.3053 | 0.500 |
| 10 | -0.0564 | 0.1114 | -0.5064 | 0.333 | -0.0581 | -0.4449 | 0.375 |
| 20 | -0.0492 | 0.1383 | -0.3560 | 0.417 | -0.0581 | -0.3662 | 0.417 |
| 40 | -0.0703 | 0.1415 | -0.4967 | 0.292 | -0.0785 | -0.4828 | 0.333 |
| 60 | -0.0699 | 0.1170 | -0.5973 | 0.292 | -0.0720 | -0.5299 | 0.333 |

quantile mean forward 20d returns: Q1: 0.00402  Q2: 0.00470  Q3: 0.00840  Q4: 0.00550  Q5: -0.00808
Q5-Q1 long-short (gross, monthly): mean -0.01210, ann -0.1567, Sharpe -0.959, MDD -0.3391
top-quintile turnover: 0.491

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0971 | -0.567 | 0.333 |
| 2023 | 12 | -0.0192 | -0.142 | 0.500 |

regime split: up-market IC -0.1259 (n=13) / down-market IC 0.0219 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.999
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0022 | 0.1145 | 0.0188 | 0.542 | -0.0122 | -0.0834 | 0.458 |
| 5 | 0.0002 | 0.1437 | 0.0017 | 0.458 | -0.0161 | -0.0899 | 0.375 |
| 10 | -0.0038 | 0.1104 | -0.0346 | 0.417 | -0.0282 | -0.2098 | 0.375 |
| 20 | -0.0354 | 0.1027 | -0.3452 | 0.417 | -0.0749 | -0.5680 | 0.292 |
| 40 | -0.0305 | 0.1080 | -0.2823 | 0.417 | -0.0724 | -0.5440 | 0.375 |
| 60 | -0.0203 | 0.0949 | -0.2137 | 0.458 | -0.0629 | -0.5535 | 0.250 |

quantile mean forward 20d returns: Q1: 0.03845  Q2: 0.03635  Q3: 0.04013  Q4: 0.03047  Q5: 0.02533
Q5-Q1 long-short (gross, monthly): mean -0.01312, ann -0.1414, Sharpe -1.013, MDD -0.3571
top-quintile turnover: 0.468

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0648 | -0.437 | 0.333 |
| 2025 | 12 | -0.0850 | -0.757 | 0.250 |

regime split: up-market IC -0.0894 (n=15) / down-market IC -0.0507 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0068 | 0.1192 | -0.0569 | 0.500 | -0.0122 | -0.0835 | 0.458 |
| 5 | -0.0113 | 0.1466 | -0.0772 | 0.458 | -0.0161 | -0.0899 | 0.375 |
| 10 | -0.0129 | 0.1082 | -0.1192 | 0.417 | -0.0282 | -0.2098 | 0.375 |
| 20 | -0.0445 | 0.1060 | -0.4194 | 0.375 | -0.0749 | -0.5680 | 0.292 |
| 40 | -0.0449 | 0.1065 | -0.4214 | 0.417 | -0.0724 | -0.5440 | 0.375 |
| 60 | -0.0373 | 0.0952 | -0.3911 | 0.417 | -0.0629 | -0.5535 | 0.250 |

quantile mean forward 20d returns: Q1: 0.03845  Q2: 0.03634  Q3: 0.04015  Q4: 0.03047  Q5: 0.02532
Q5-Q1 long-short (gross, monthly): mean -0.01313, ann -0.1415, Sharpe -1.014, MDD -0.3571
top-quintile turnover: 0.468

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0647 | -0.437 | 0.333 |
| 2025 | 12 | -0.0850 | -0.758 | 0.250 |

regime split: up-market IC -0.0894 (n=15) / down-market IC -0.0507 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`price_vs_ma120`: 0.827  `momentum_60`: 0.651  `price_vs_ma60`: 0.544  `momentum_20`: 0.356  `reversal_20`: -0.356

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.