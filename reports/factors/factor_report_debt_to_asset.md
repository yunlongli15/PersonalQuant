# factor_report_debt_to_asset.md

## definition

- factor: `debt_to_asset`  ·  category: quality  ·  version 1.0
- formula: `total_liabilities/total_assets`
- source: financial  ·  PIT: True
- required fields: total_liabilities, total_assets
- description: leverage, latest PIT annual report (banks structurally ~0.9 — handled as real data, not an error)
- declared (economic) direction: **negative**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.023
- empirical direction: negative

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0118 | 0.1102 | -0.1072 | 0.435 | -0.0162 | -0.1230 | 0.435 |
| 5 | -0.0209 | 0.1292 | -0.1617 | 0.413 | -0.0180 | -0.1211 | 0.413 |
| 10 | -0.0343 | 0.1221 | -0.2809 | 0.413 | -0.0348 | -0.2744 | 0.435 |
| 20 | -0.0231 | 0.1170 | -0.1976 | 0.348 | -0.0179 | -0.1506 | 0.435 |
| 40 | -0.0269 | 0.1175 | -0.2287 | 0.413 | -0.0119 | -0.1001 | 0.370 |
| 60 | -0.0281 | 0.1203 | -0.2333 | 0.391 | -0.0034 | -0.0292 | 0.413 |

quantile mean forward 20d returns: Q1: 0.01269  Q2: 0.01727  Q3: 0.01387  Q4: 0.01403  Q5: 0.00680
Q5-Q1 long-short (gross, monthly): mean -0.00589, ann -0.0633, Sharpe -0.533, MDD -0.3363
top-quintile turnover: 0.067

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 10 | -0.0217 | -0.179 | 0.400 |
| 2019 | 12 | -0.0337 | -0.291 | 0.583 |
| 2020 | 12 | -0.0234 | -0.212 | 0.250 |
| 2021 | 12 | 0.0067 | 0.054 | 0.500 |

regime split: up-market IC -0.0251 (n=27) / down-market IC -0.0076 (n=19)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0008 | 0.0961 | -0.0078 | 0.435 | -0.0162 | -0.1230 | 0.435 |
| 5 | -0.0043 | 0.1028 | -0.0415 | 0.413 | -0.0180 | -0.1211 | 0.413 |
| 10 | 0.0073 | 0.1135 | 0.0646 | 0.500 | -0.0348 | -0.2744 | 0.435 |
| 20 | 0.0064 | 0.0981 | 0.0649 | 0.457 | -0.0179 | -0.1506 | 0.435 |
| 40 | 0.0195 | 0.0873 | 0.2231 | 0.500 | -0.0119 | -0.1001 | 0.370 |
| 60 | 0.0154 | 0.0806 | 0.1913 | 0.478 | -0.0034 | -0.0292 | 0.413 |

quantile mean forward 20d returns: Q1: 0.01269  Q2: 0.01727  Q3: 0.01387  Q4: 0.01403  Q5: 0.00680
Q5-Q1 long-short (gross, monthly): mean -0.00589, ann -0.0633, Sharpe -0.533, MDD -0.3363
top-quintile turnover: 0.067

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 10 | -0.0217 | -0.179 | 0.400 |
| 2019 | 12 | -0.0337 | -0.291 | 0.583 |
| 2020 | 12 | -0.0234 | -0.212 | 0.250 |
| 2021 | 12 | 0.0067 | 0.054 | 0.500 |

regime split: up-market IC -0.0251 (n=27) / down-market IC -0.0076 (n=19)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.022
- empirical direction: positive  ⚠️ disagrees with declared direction

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0220 | 0.1208 | -0.1821 | 0.458 | -0.0080 | -0.0566 | 0.500 |
| 5 | 0.0079 | 0.1159 | 0.0682 | 0.417 | 0.0160 | 0.1457 | 0.542 |
| 10 | -0.0097 | 0.1034 | -0.0942 | 0.500 | -0.0087 | -0.0791 | 0.417 |
| 20 | 0.0018 | 0.1031 | 0.0170 | 0.417 | 0.0092 | 0.0800 | 0.458 |
| 40 | -0.0072 | 0.0954 | -0.0756 | 0.500 | 0.0084 | 0.0838 | 0.583 |
| 60 | -0.0010 | 0.0865 | -0.0116 | 0.458 | 0.0165 | 0.1959 | 0.625 |

quantile mean forward 20d returns: Q1: 0.00478  Q2: 0.00188  Q3: 0.00523  Q4: 0.01023  Q5: 0.00335
Q5-Q1 long-short (gross, monthly): mean -0.00143, ann -0.0048, Sharpe -0.049, MDD -0.1484
top-quintile turnover: 0.033

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0266 | -0.257 | 0.333 |
| 2023 | 12 | 0.0449 | 0.394 | 0.583 |

regime split: up-market IC -0.0303 (n=13) / down-market IC 0.0558 (n=11)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0140 | 0.0616 | -0.2266 | 0.417 | -0.0080 | -0.0566 | 0.500 |
| 5 | -0.0093 | 0.0739 | -0.1257 | 0.542 | 0.0160 | 0.1457 | 0.542 |
| 10 | -0.0022 | 0.0643 | -0.0339 | 0.583 | -0.0087 | -0.0791 | 0.417 |
| 20 | -0.0025 | 0.0493 | -0.0516 | 0.583 | 0.0092 | 0.0800 | 0.458 |
| 40 | -0.0011 | 0.0511 | -0.0219 | 0.458 | 0.0084 | 0.0838 | 0.583 |
| 60 | 0.0140 | 0.0526 | 0.2666 | 0.417 | 0.0165 | 0.1959 | 0.625 |

quantile mean forward 20d returns: Q1: 0.00478  Q2: 0.00188  Q3: 0.00523  Q4: 0.01023  Q5: 0.00335
Q5-Q1 long-short (gross, monthly): mean -0.00143, ann -0.0048, Sharpe -0.049, MDD -0.1484
top-quintile turnover: 0.033

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0266 | -0.257 | 0.333 |
| 2023 | 12 | 0.0449 | 0.394 | 0.583 |

regime split: up-market IC -0.0303 (n=13) / down-market IC 0.0558 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.021
- empirical direction: positive  ⚠️ disagrees with declared direction

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0238 | 0.1264 | -0.1884 | 0.375 | -0.0132 | -0.0840 | 0.458 |
| 5 | 0.0245 | 0.1404 | 0.1747 | 0.583 | 0.0352 | 0.2205 | 0.500 |
| 10 | 0.0114 | 0.1358 | 0.0843 | 0.542 | 0.0240 | 0.1586 | 0.625 |
| 20 | 0.0130 | 0.1434 | 0.0904 | 0.542 | 0.0276 | 0.1706 | 0.708 |
| 40 | 0.0192 | 0.1459 | 0.1314 | 0.542 | 0.0413 | 0.2381 | 0.708 |
| 60 | 0.0133 | 0.1412 | 0.0942 | 0.458 | 0.0402 | 0.2368 | 0.667 |

quantile mean forward 20d returns: Q1: 0.02060  Q2: 0.04044  Q3: 0.03538  Q4: 0.02134  Q5: 0.02728
Q5-Q1 long-short (gross, monthly): mean 0.00668, ann 0.1057, Sharpe 0.892, MDD -0.0847
top-quintile turnover: 0.033

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0548 | 0.362 | 0.750 |
| 2025 | 12 | 0.0003 | 0.002 | 0.667 |

regime split: up-market IC 0.0085 (n=15) / down-market IC 0.0595 (n=9)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0277 | 0.0966 | 0.2867 | 0.667 | -0.0132 | -0.0840 | 0.458 |
| 5 | 0.0295 | 0.1105 | 0.2666 | 0.625 | 0.0352 | 0.2205 | 0.500 |
| 10 | 0.0129 | 0.0876 | 0.1473 | 0.417 | 0.0240 | 0.1586 | 0.625 |
| 20 | 0.0124 | 0.0968 | 0.1279 | 0.500 | 0.0276 | 0.1706 | 0.708 |
| 40 | 0.0259 | 0.1090 | 0.2373 | 0.542 | 0.0413 | 0.2381 | 0.708 |
| 60 | 0.0270 | 0.1136 | 0.2381 | 0.500 | 0.0402 | 0.2368 | 0.667 |

quantile mean forward 20d returns: Q1: 0.02060  Q2: 0.04044  Q3: 0.03538  Q4: 0.02134  Q5: 0.02728
Q5-Q1 long-short (gross, monthly): mean 0.00668, ann 0.1057, Sharpe 0.892, MDD -0.0847
top-quintile turnover: 0.033

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0548 | 0.362 | 0.750 |
| 2025 | 12 | 0.0003 | 0.002 | 0.667 |

regime split: up-market IC 0.0085 (n=15) / down-market IC 0.0595 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`gross_margin`: -0.465  `roa`: -0.430  `ocf_to_assets`: -0.305  `roe`: -0.258  `net_profit_growth`: -0.164

## interpretation & limitations

- declared direction `negative` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.