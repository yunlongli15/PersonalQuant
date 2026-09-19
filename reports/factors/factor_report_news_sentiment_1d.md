# factor_report_news_sentiment_1d.md

## definition

- factor: `news_sentiment_1d`  ·  category: news  ·  version 1.0
- formula: `mean sentiment of events in 1d`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: 1-day mean event sentiment
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.401
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0018 | 0.0282 | 0.0623 | 0.458 | 0.0000 | 0.0005 | 0.375 |
| 5 | -0.0022 | 0.0240 | -0.0925 | 0.458 | -0.0023 | -0.0744 | 0.438 |
| 10 | -0.0017 | 0.0310 | -0.0551 | 0.542 | -0.0019 | -0.0621 | 0.479 |
| 20 | 0.0021 | 0.0311 | 0.0669 | 0.542 | 0.0029 | 0.0851 | 0.542 |
| 40 | 0.0018 | 0.0267 | 0.0692 | 0.583 | 0.0022 | 0.0703 | 0.479 |
| 60 | 0.0016 | 0.0244 | 0.0665 | 0.458 | 0.0022 | 0.0736 | 0.458 |

quantile mean forward 20d returns: Q1: 0.00914  Q2: 0.01138  Q3: 0.01650  Q4: 0.00866  Q5: 0.01020
Q5-Q1 long-short (gross, monthly): mean 0.00105, ann 0.0120, Sharpe 0.132, MDD -0.1091
top-quintile turnover: 0.048

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0013 | -0.055 | 0.583 |
| 2019 | 12 | 0.0053 | 0.195 | 0.583 |
| 2020 | 12 | 0.0042 | 0.202 | 0.750 |
| 2021 | 12 | 0.0028 | 0.052 | 0.250 |

regime split: up-market IC 0.0060 (n=28) / down-market IC -0.0021 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0022 | 0.0296 | 0.0756 | 0.455 | 0.0000 | 0.0008 | 0.409 |
| 5 | -0.0025 | 0.0252 | -0.1010 | 0.432 | -0.0023 | -0.0744 | 0.477 |
| 10 | -0.0019 | 0.0324 | -0.0583 | 0.568 | -0.0019 | -0.0623 | 0.523 |
| 20 | 0.0023 | 0.0326 | 0.0722 | 0.568 | 0.0029 | 0.0850 | 0.591 |
| 40 | 0.0018 | 0.0282 | 0.0641 | 0.591 | 0.0022 | 0.0702 | 0.523 |
| 60 | 0.0016 | 0.0257 | 0.0609 | 0.500 | 0.0021 | 0.0735 | 0.500 |

quantile mean forward 20d returns: Q1: 0.01015  Q2: 0.01378  Q3: 0.02000  Q4: 0.00984  Q5: 0.01294
Q5-Q1 long-short (gross, monthly): mean 0.00279, ann 0.0336, Sharpe 0.362, MDD -0.0885
top-quintile turnover: 0.056

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 10 | -0.0013 | -0.055 | 0.700 |
| 2019 | 11 | 0.0053 | 0.195 | 0.636 |
| 2020 | 12 | 0.0042 | 0.202 | 0.750 |
| 2021 | 11 | 0.0027 | 0.052 | 0.273 |

regime split: up-market IC 0.0060 (n=27) / down-market IC -0.0021 (n=17)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.455
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0025 | 0.0441 | 0.0575 | 0.542 | 0.0064 | 0.1260 | 0.583 |
| 5 | -0.0046 | 0.0355 | -0.1282 | 0.391 | -0.0047 | -0.1038 | 0.478 |
| 10 | -0.0024 | 0.0356 | -0.0675 | 0.478 | -0.0013 | -0.0303 | 0.435 |
| 20 | -0.0011 | 0.0267 | -0.0394 | 0.333 | -0.0004 | -0.0127 | 0.375 |
| 40 | 0.0085 | 0.0513 | 0.1650 | 0.458 | 0.0112 | 0.1881 | 0.417 |
| 60 | 0.0111 | 0.0522 | 0.2125 | 0.478 | 0.0123 | 0.1966 | 0.478 |

quantile mean forward 20d returns: Q1: 0.00346  Q2: 0.00256  Q3: 0.00111  Q4: 0.00401  Q5: -0.00161
Q5-Q1 long-short (gross, monthly): mean -0.00507, ann -0.0487, Sharpe -0.449, MDD -0.1320
top-quintile turnover: 0.075

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0110 | -0.597 | 0.250 |
| 2023 | 12 | 0.0093 | 0.223 | 0.500 |

regime split: up-market IC -0.0011 (n=13) / down-market IC 0.0003 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0041 | 0.0458 | 0.0904 | 0.522 | 0.0064 | 0.1259 | 0.609 |
| 5 | -0.0038 | 0.0358 | -0.1049 | 0.391 | -0.0046 | -0.1029 | 0.478 |
| 10 | -0.0019 | 0.0361 | -0.0533 | 0.478 | -0.0013 | -0.0293 | 0.435 |
| 20 | -0.0005 | 0.0275 | -0.0187 | 0.391 | -0.0004 | -0.0116 | 0.391 |
| 40 | 0.0092 | 0.0522 | 0.1759 | 0.478 | 0.0112 | 0.1879 | 0.435 |
| 60 | 0.0114 | 0.0526 | 0.2171 | 0.478 | 0.0123 | 0.1962 | 0.478 |

quantile mean forward 20d returns: Q1: 0.00083  Q2: -0.00097  Q3: -0.00220  Q4: 0.00244  Q5: -0.00577
Q5-Q1 long-short (gross, monthly): mean -0.00661, ann -0.0654, Sharpe -0.607, MDD -0.1320
top-quintile turnover: 0.081

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 11 | -0.0109 | -0.591 | 0.273 |
| 2023 | 12 | 0.0093 | 0.223 | 0.500 |

regime split: up-market IC -0.0011 (n=12) / down-market IC 0.0004 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.457
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0135 | 0.0557 | -0.2427 | 0.391 | -0.0092 | -0.1564 | 0.478 |
| 5 | -0.0071 | 0.0563 | -0.1266 | 0.565 | -0.0040 | -0.0662 | 0.522 |
| 10 | -0.0100 | 0.0512 | -0.1949 | 0.522 | -0.0061 | -0.1150 | 0.565 |
| 20 | -0.0076 | 0.0363 | -0.2082 | 0.478 | -0.0047 | -0.1316 | 0.522 |
| 40 | -0.0041 | 0.0179 | -0.2303 | 0.391 | -0.0032 | -0.1692 | 0.522 |
| 60 | -0.0032 | 0.0142 | -0.2287 | 0.304 | -0.0042 | -0.2065 | 0.348 |

quantile mean forward 20d returns: Q1: 0.02981  Q2: 0.03570  Q3: 0.03548  Q4: 0.02602  Q5: 0.03587
Q5-Q1 long-short (gross, monthly): mean 0.00606, ann 0.0625, Sharpe 0.632, MDD -0.0769
top-quintile turnover: 0.046

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 11 | 0.0055 | 0.249 | 0.636 |
| 2025 | 12 | -0.0132 | -0.316 | 0.417 |

regime split: up-market IC -0.0161 (n=15) / down-market IC 0.0152 (n=8)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0139 | 0.0565 | -0.2457 | 0.364 | -0.0092 | -0.1564 | 0.500 |
| 5 | -0.0070 | 0.0575 | -0.1224 | 0.545 | -0.0040 | -0.0662 | 0.545 |
| 10 | -0.0101 | 0.0519 | -0.1948 | 0.545 | -0.0061 | -0.1150 | 0.591 |
| 20 | -0.0077 | 0.0371 | -0.2087 | 0.455 | -0.0047 | -0.1317 | 0.545 |
| 40 | -0.0046 | 0.0183 | -0.2492 | 0.409 | -0.0032 | -0.1692 | 0.545 |
| 60 | -0.0037 | 0.0145 | -0.2571 | 0.318 | -0.0042 | -0.2063 | 0.364 |

quantile mean forward 20d returns: Q1: 0.03519  Q2: 0.04050  Q3: 0.04111  Q4: 0.03160  Q5: 0.04134
Q5-Q1 long-short (gross, monthly): mean 0.00615, ann 0.0633, Sharpe 0.662, MDD -0.0769
top-quintile turnover: 0.049

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 10 | 0.0055 | 0.249 | 0.700 |
| 2025 | 12 | -0.0132 | -0.316 | 0.417 |

regime split: up-market IC -0.0161 (n=14) / down-market IC 0.0152 (n=8)

---

## correlation with other factors (avg cross-sectional spearman, research)

`negative_news_count_5d`: -0.272  `event_sentiment_shock`: 0.183  `buyback_event_count_20d`: 0.068  `earnings_event_count_60d`: -0.025  `news_attention_1d`: 0.018

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.