# factor_report_high_52w_proximity.md

## definition

- factor: `high_52w_proximity`  ·  category: price_position  ·  version 1.0
- formula: `close / max(close, 250d)`
- source: market  ·  PIT: True
- required fields: close, factor
- description: 距 52 周高点比例（接近高点者后续更强，George-Hwang）
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.997
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0118 | 0.1258 | -0.0935 | 0.479 | -0.0277 | -0.1873 | 0.417 |
| 5 | -0.0364 | 0.1420 | -0.2564 | 0.375 | -0.0505 | -0.2888 | 0.312 |
| 10 | -0.0190 | 0.1251 | -0.1522 | 0.417 | -0.0294 | -0.1824 | 0.479 |
| 20 | -0.0051 | 0.1204 | -0.0427 | 0.479 | -0.0078 | -0.0516 | 0.500 |
| 40 | 0.0022 | 0.1036 | 0.0216 | 0.604 | -0.0038 | -0.0309 | 0.542 |
| 60 | 0.0165 | 0.1009 | 0.1631 | 0.604 | 0.0124 | 0.1080 | 0.625 |

quantile mean forward 20d returns: Q1: 0.01344  Q2: 0.01002  Q3: 0.01103  Q4: 0.01078  Q5: 0.01044
Q5-Q1 long-short (gross, monthly): mean -0.00299, ann -0.0537, Sharpe -0.294, MDD -0.3520
top-quintile turnover: 0.405

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0142 | -0.087 | 0.667 |
| 2019 | 12 | 0.0011 | 0.006 | 0.583 |
| 2020 | 12 | 0.0507 | 0.427 | 0.500 |
| 2021 | 12 | -0.0687 | -0.595 | 0.250 |

regime split: up-market IC -0.0514 (n=28) / down-market IC 0.0533 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0104 | 0.1256 | -0.0829 | 0.500 | -0.0277 | -0.1873 | 0.417 |
| 5 | -0.0370 | 0.1430 | -0.2586 | 0.375 | -0.0505 | -0.2888 | 0.312 |
| 10 | -0.0192 | 0.1265 | -0.1516 | 0.458 | -0.0294 | -0.1824 | 0.479 |
| 20 | -0.0056 | 0.1226 | -0.0461 | 0.500 | -0.0078 | -0.0516 | 0.500 |
| 40 | 0.0021 | 0.1075 | 0.0199 | 0.583 | -0.0038 | -0.0309 | 0.542 |
| 60 | 0.0165 | 0.1040 | 0.1589 | 0.583 | 0.0124 | 0.1080 | 0.625 |

quantile mean forward 20d returns: Q1: 0.01344  Q2: 0.01002  Q3: 0.01102  Q4: 0.01079  Q5: 0.01044
Q5-Q1 long-short (gross, monthly): mean -0.00299, ann -0.0537, Sharpe -0.294, MDD -0.3520
top-quintile turnover: 0.405

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0142 | -0.087 | 0.667 |
| 2019 | 12 | 0.0011 | 0.006 | 0.583 |
| 2020 | 12 | 0.0507 | 0.427 | 0.500 |
| 2021 | 12 | -0.0687 | -0.595 | 0.250 |

regime split: up-market IC -0.0514 (n=28) / down-market IC 0.0534 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 1.000
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0128 | 0.1171 | -0.1095 | 0.458 | -0.0161 | -0.1141 | 0.500 |
| 5 | -0.0352 | 0.1268 | -0.2773 | 0.417 | -0.0462 | -0.2932 | 0.458 |
| 10 | -0.0346 | 0.1083 | -0.3194 | 0.500 | -0.0357 | -0.2550 | 0.500 |
| 20 | -0.0094 | 0.1256 | -0.0746 | 0.583 | -0.0132 | -0.0873 | 0.542 |
| 40 | -0.0196 | 0.1268 | -0.1546 | 0.458 | -0.0212 | -0.1433 | 0.458 |
| 60 | -0.0132 | 0.1112 | -0.1188 | 0.500 | -0.0091 | -0.0702 | 0.417 |

quantile mean forward 20d returns: Q1: 0.00305  Q2: 0.00341  Q3: 0.00642  Q4: 0.00373  Q5: -0.00207
Q5-Q1 long-short (gross, monthly): mean -0.00512, ann -0.0715, Sharpe -0.485, MDD -0.2927
top-quintile turnover: 0.443

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0661 | -0.397 | 0.417 |
| 2023 | 12 | 0.0398 | 0.358 | 0.667 |

regime split: up-market IC -0.1125 (n=13) / down-market IC 0.1041 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0129 | 0.1185 | -0.1090 | 0.458 | -0.0161 | -0.1141 | 0.500 |
| 5 | -0.0358 | 0.1279 | -0.2798 | 0.417 | -0.0462 | -0.2932 | 0.458 |
| 10 | -0.0360 | 0.1089 | -0.3306 | 0.500 | -0.0357 | -0.2551 | 0.500 |
| 20 | -0.0106 | 0.1274 | -0.0829 | 0.625 | -0.0132 | -0.0874 | 0.542 |
| 40 | -0.0191 | 0.1296 | -0.1473 | 0.500 | -0.0212 | -0.1434 | 0.458 |
| 60 | -0.0109 | 0.1139 | -0.0961 | 0.500 | -0.0091 | -0.0703 | 0.417 |

quantile mean forward 20d returns: Q1: 0.00305  Q2: 0.00338  Q3: 0.00644  Q4: 0.00373  Q5: -0.00207
Q5-Q1 long-short (gross, monthly): mean -0.00512, ann -0.0715, Sharpe -0.485, MDD -0.2927
top-quintile turnover: 0.443

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0661 | -0.397 | 0.417 |
| 2023 | 12 | 0.0397 | 0.358 | 0.667 |

regime split: up-market IC -0.1125 (n=13) / down-market IC 0.1041 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 1.000
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0371 | 0.1131 | -0.3278 | 0.417 | -0.0516 | -0.3502 | 0.375 |
| 5 | 0.0080 | 0.1152 | 0.0694 | 0.500 | 0.0059 | 0.0390 | 0.500 |
| 10 | -0.0218 | 0.1055 | -0.2062 | 0.375 | -0.0391 | -0.2942 | 0.292 |
| 20 | -0.0210 | 0.1105 | -0.1897 | 0.500 | -0.0388 | -0.2687 | 0.458 |
| 40 | -0.0060 | 0.0973 | -0.0619 | 0.458 | -0.0255 | -0.1936 | 0.417 |
| 60 | -0.0078 | 0.0948 | -0.0825 | 0.500 | -0.0258 | -0.1999 | 0.333 |

quantile mean forward 20d returns: Q1: 0.03778  Q2: 0.03766  Q3: 0.03926  Q4: 0.02897  Q5: 0.02705
Q5-Q1 long-short (gross, monthly): mean -0.01073, ann -0.1097, Sharpe -0.656, MDD -0.3410
top-quintile turnover: 0.513

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0464 | -0.259 | 0.417 |
| 2025 | 12 | -0.0312 | -0.319 | 0.500 |

regime split: up-market IC -0.1071 (n=15) / down-market IC 0.0750 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0337 | 0.1119 | -0.3009 | 0.417 | -0.0516 | -0.3503 | 0.375 |
| 5 | 0.0111 | 0.1162 | 0.0956 | 0.542 | 0.0059 | 0.0390 | 0.500 |
| 10 | -0.0184 | 0.1043 | -0.1765 | 0.375 | -0.0391 | -0.2943 | 0.292 |
| 20 | -0.0180 | 0.1097 | -0.1637 | 0.458 | -0.0388 | -0.2687 | 0.458 |
| 40 | -0.0034 | 0.0990 | -0.0346 | 0.458 | -0.0255 | -0.1937 | 0.417 |
| 60 | -0.0048 | 0.0990 | -0.0487 | 0.500 | -0.0258 | -0.2000 | 0.333 |

quantile mean forward 20d returns: Q1: 0.03778  Q2: 0.03766  Q3: 0.03926  Q4: 0.02897  Q5: 0.02705
Q5-Q1 long-short (gross, monthly): mean -0.01073, ann -0.1096, Sharpe -0.656, MDD -0.3410
top-quintile turnover: 0.513

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0464 | -0.259 | 0.417 |
| 2025 | 12 | -0.0312 | -0.319 | 0.500 |

regime split: up-market IC -0.1071 (n=15) / down-market IC 0.0750 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`momentum_120`: 0.699  `momentum_60`: 0.604  `momentum_20`: 0.420  `downside_volatility_60`: -0.283  `amihud_20`: -0.253

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.