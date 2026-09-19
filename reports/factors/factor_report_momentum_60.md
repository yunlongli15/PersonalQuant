# factor_report_momentum_60.md

## definition

- factor: `momentum_60`  ·  category: momentum  ·  version 1.0
- formula: `adj_close[t]/adj_close[t-60]-1`
- source: market  ·  PIT: True
- required fields: close, factor
- description: 60-trading-day momentum on adjusted close
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.991
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0060 | 0.1395 | -0.0432 | 0.542 | -0.0319 | -0.2034 | 0.458 |
| 5 | -0.0251 | 0.1405 | -0.1783 | 0.396 | -0.0570 | -0.3423 | 0.312 |
| 10 | -0.0178 | 0.1061 | -0.1676 | 0.375 | -0.0490 | -0.3581 | 0.333 |
| 20 | -0.0303 | 0.1092 | -0.2777 | 0.375 | -0.0596 | -0.4653 | 0.354 |
| 40 | -0.0248 | 0.0888 | -0.2795 | 0.417 | -0.0582 | -0.5608 | 0.375 |
| 60 | -0.0177 | 0.0795 | -0.2222 | 0.479 | -0.0502 | -0.5461 | 0.312 |

quantile mean forward 20d returns: Q1: 0.01510  Q2: 0.01306  Q3: 0.01255  Q4: 0.01067  Q5: 0.00435
Q5-Q1 long-short (gross, monthly): mean -0.01075, ann -0.1255, Sharpe -0.841, MDD -0.4150
top-quintile turnover: 0.554

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0564 | -0.476 | 0.500 |
| 2019 | 12 | -0.0426 | -0.371 | 0.333 |
| 2020 | 12 | -0.0153 | -0.109 | 0.417 |
| 2021 | 12 | -0.1241 | -1.120 | 0.167 |

regime split: up-market IC -0.0782 (n=28) / down-market IC -0.0336 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0034 | 0.1465 | -0.0230 | 0.542 | -0.0319 | -0.2034 | 0.458 |
| 5 | -0.0300 | 0.1458 | -0.2056 | 0.458 | -0.0570 | -0.3423 | 0.312 |
| 10 | -0.0224 | 0.1096 | -0.2047 | 0.396 | -0.0490 | -0.3581 | 0.333 |
| 20 | -0.0362 | 0.1158 | -0.3124 | 0.333 | -0.0596 | -0.4652 | 0.354 |
| 40 | -0.0328 | 0.0946 | -0.3469 | 0.396 | -0.0581 | -0.5606 | 0.375 |
| 60 | -0.0229 | 0.0830 | -0.2761 | 0.417 | -0.0502 | -0.5460 | 0.312 |

quantile mean forward 20d returns: Q1: 0.01510  Q2: 0.01306  Q3: 0.01256  Q4: 0.01066  Q5: 0.00434
Q5-Q1 long-short (gross, monthly): mean -0.01075, ann -0.1255, Sharpe -0.842, MDD -0.4151
top-quintile turnover: 0.554

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0564 | -0.475 | 0.500 |
| 2019 | 12 | -0.0426 | -0.371 | 0.333 |
| 2020 | 12 | -0.0153 | -0.109 | 0.417 |
| 2021 | 12 | -0.1240 | -1.120 | 0.167 |

regime split: up-market IC -0.0782 (n=28) / down-market IC -0.0336 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.998
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0052 | 0.1145 | -0.0455 | 0.375 | -0.0219 | -0.1733 | 0.333 |
| 5 | -0.0150 | 0.1303 | -0.1153 | 0.375 | -0.0464 | -0.3042 | 0.292 |
| 10 | -0.0292 | 0.0986 | -0.2963 | 0.292 | -0.0534 | -0.4555 | 0.250 |
| 20 | -0.0308 | 0.1238 | -0.2486 | 0.458 | -0.0625 | -0.4517 | 0.375 |
| 40 | -0.0512 | 0.1415 | -0.3622 | 0.417 | -0.0803 | -0.5014 | 0.292 |
| 60 | -0.0565 | 0.1192 | -0.4738 | 0.292 | -0.0889 | -0.6616 | 0.208 |

quantile mean forward 20d returns: Q1: 0.00214  Q2: 0.00642  Q3: 0.00955  Q4: 0.00499  Q5: -0.00856
Q5-Q1 long-short (gross, monthly): mean -0.01070, ann -0.1339, Sharpe -0.933, MDD -0.3140
top-quintile turnover: 0.595

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0738 | -0.462 | 0.333 |
| 2023 | 12 | -0.0512 | -0.458 | 0.417 |

regime split: up-market IC -0.1097 (n=13) / down-market IC -0.0067 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0070 | 0.1228 | -0.0569 | 0.458 | -0.0219 | -0.1733 | 0.333 |
| 5 | -0.0238 | 0.1296 | -0.1835 | 0.375 | -0.0464 | -0.3042 | 0.292 |
| 10 | -0.0479 | 0.0992 | -0.4824 | 0.292 | -0.0534 | -0.4554 | 0.250 |
| 20 | -0.0475 | 0.1278 | -0.3718 | 0.333 | -0.0625 | -0.4517 | 0.375 |
| 40 | -0.0668 | 0.1434 | -0.4660 | 0.292 | -0.0803 | -0.5014 | 0.292 |
| 60 | -0.0748 | 0.1205 | -0.6206 | 0.208 | -0.0889 | -0.6615 | 0.208 |

quantile mean forward 20d returns: Q1: 0.00214  Q2: 0.00642  Q3: 0.00956  Q4: 0.00498  Q5: -0.00856
Q5-Q1 long-short (gross, monthly): mean -0.01070, ann -0.1339, Sharpe -0.933, MDD -0.3140
top-quintile turnover: 0.595

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0738 | -0.462 | 0.333 |
| 2023 | 12 | -0.0512 | -0.458 | 0.417 |

regime split: up-market IC -0.1097 (n=13) / down-market IC -0.0067 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.999
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0023 | 0.1350 | 0.0171 | 0.500 | -0.0205 | -0.1273 | 0.500 |
| 5 | -0.0001 | 0.1121 | -0.0012 | 0.542 | -0.0305 | -0.2397 | 0.375 |
| 10 | -0.0073 | 0.1150 | -0.0633 | 0.375 | -0.0408 | -0.2911 | 0.250 |
| 20 | -0.0310 | 0.0973 | -0.3190 | 0.417 | -0.0715 | -0.5607 | 0.167 |
| 40 | -0.0212 | 0.0975 | -0.2177 | 0.500 | -0.0630 | -0.4851 | 0.333 |
| 60 | -0.0117 | 0.0917 | -0.1281 | 0.458 | -0.0527 | -0.4532 | 0.375 |

quantile mean forward 20d returns: Q1: 0.03768  Q2: 0.03416  Q3: 0.04159  Q4: 0.03040  Q5: 0.02689
Q5-Q1 long-short (gross, monthly): mean -0.01079, ann -0.1086, Sharpe -0.846, MDD -0.2383
top-quintile turnover: 0.592

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0475 | -0.314 | 0.333 |
| 2025 | 12 | -0.0955 | -1.035 | 0.000 |

regime split: up-market IC -0.0982 (n=15) / down-market IC -0.0269 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0061 | 0.1390 | -0.0439 | 0.500 | -0.0205 | -0.1274 | 0.500 |
| 5 | -0.0113 | 0.1256 | -0.0897 | 0.500 | -0.0305 | -0.2398 | 0.375 |
| 10 | -0.0165 | 0.1134 | -0.1457 | 0.333 | -0.0408 | -0.2911 | 0.250 |
| 20 | -0.0427 | 0.0995 | -0.4288 | 0.417 | -0.0715 | -0.5608 | 0.167 |
| 40 | -0.0348 | 0.1033 | -0.3373 | 0.375 | -0.0630 | -0.4852 | 0.333 |
| 60 | -0.0275 | 0.1005 | -0.2738 | 0.417 | -0.0527 | -0.4532 | 0.375 |

quantile mean forward 20d returns: Q1: 0.03768  Q2: 0.03416  Q3: 0.04158  Q4: 0.03041  Q5: 0.02689
Q5-Q1 long-short (gross, monthly): mean -0.01080, ann -0.1087, Sharpe -0.847, MDD -0.2383
top-quintile turnover: 0.592

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0475 | -0.314 | 0.333 |
| 2025 | 12 | -0.0955 | -1.036 | 0.000 |

regime split: up-market IC -0.0982 (n=15) / down-market IC -0.0269 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`momentum_120`: 0.651  `high_52w_proximity`: 0.604  `momentum_20`: 0.507  `max_return_20`: 0.393  `amount_20`: 0.284

## redundancy cluster

cluster members: `momentum_60`, `price_vs_ma120`, `price_vs_ma60`

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.