# factor_report_buyback_event_count_20d.md

## definition

- factor: `buyback_event_count_20d`  ·  category: news  ·  version 1.0
- formula: `count(share_buyback events in 20d)`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: buyback event count, 20d
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.401
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0006 | 0.0244 | -0.0259 | 0.438 | -0.0004 | -0.0124 | 0.458 |
| 5 | -0.0007 | 0.0222 | -0.0302 | 0.542 | -0.0018 | -0.0645 | 0.458 |
| 10 | 0.0020 | 0.0252 | 0.0793 | 0.562 | 0.0034 | 0.1051 | 0.583 |
| 20 | 0.0059 | 0.0251 | 0.2353 | 0.542 | 0.0072 | 0.2071 | 0.542 |
| 40 | 0.0085 | 0.0249 | 0.3424 | 0.604 | 0.0088 | 0.2812 | 0.604 |
| 60 | 0.0099 | 0.0248 | 0.4003 | 0.604 | 0.0083 | 0.3249 | 0.625 |

quantile mean forward 20d returns: Q1: 0.00913  Q2: 0.01155  Q3: 0.01581  Q4: 0.00879  Q5: 0.01060
Q5-Q1 long-short (gross, monthly): mean 0.00147, ann 0.0169, Sharpe 0.186, MDD -0.1229
top-quintile turnover: 0.043

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0005 | 0.016 | 0.500 |
| 2019 | 12 | 0.0190 | 0.404 | 0.583 |
| 2020 | 12 | 0.0104 | 0.489 | 0.667 |
| 2021 | 12 | -0.0011 | -0.033 | 0.417 |

regime split: up-market IC 0.0072 (n=28) / down-market IC 0.0072 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0006 | 0.0244 | -0.0259 | 0.438 | -0.0004 | -0.0127 | 0.458 |
| 5 | -0.0007 | 0.0222 | -0.0303 | 0.542 | -0.0018 | -0.0642 | 0.458 |
| 10 | 0.0020 | 0.0252 | 0.0793 | 0.562 | 0.0034 | 0.1050 | 0.583 |
| 20 | 0.0059 | 0.0251 | 0.2353 | 0.542 | 0.0072 | 0.2073 | 0.542 |
| 40 | 0.0085 | 0.0249 | 0.3425 | 0.604 | 0.0088 | 0.2811 | 0.604 |
| 60 | 0.0099 | 0.0248 | 0.4004 | 0.604 | 0.0083 | 0.3252 | 0.625 |

quantile mean forward 20d returns: Q1: 0.00913  Q2: 0.01155  Q3: 0.01581  Q4: 0.00879  Q5: 0.01060
Q5-Q1 long-short (gross, monthly): mean 0.00147, ann 0.0169, Sharpe 0.186, MDD -0.1229
top-quintile turnover: 0.043

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0005 | 0.018 | 0.500 |
| 2019 | 12 | 0.0190 | 0.404 | 0.583 |
| 2020 | 12 | 0.0104 | 0.489 | 0.667 |
| 2021 | 12 | -0.0011 | -0.033 | 0.417 |

regime split: up-market IC 0.0072 (n=28) / down-market IC 0.0072 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.455
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0115 | 0.0377 | -0.3035 | 0.375 | -0.0110 | -0.2354 | 0.417 |
| 5 | -0.0117 | 0.0375 | -0.3109 | 0.333 | -0.0157 | -0.3502 | 0.333 |
| 10 | -0.0059 | 0.0324 | -0.1826 | 0.375 | -0.0118 | -0.3064 | 0.292 |
| 20 | -0.0071 | 0.0337 | -0.2105 | 0.417 | -0.0097 | -0.2295 | 0.375 |
| 40 | -0.0064 | 0.0286 | -0.2236 | 0.500 | -0.0077 | -0.1976 | 0.417 |
| 60 | -0.0050 | 0.0308 | -0.1637 | 0.417 | -0.0080 | -0.1904 | 0.458 |

quantile mean forward 20d returns: Q1: 0.00336  Q2: 0.00328  Q3: 0.00210  Q4: 0.00335  Q5: -0.00255
Q5-Q1 long-short (gross, monthly): mean -0.00591, ann -0.0584, Sharpe -0.511, MDD -0.1497
top-quintile turnover: 0.086

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0105 | -0.212 | 0.250 |
| 2023 | 12 | -0.0088 | -0.268 | 0.500 |

regime split: up-market IC -0.0248 (n=13) / down-market IC 0.0082 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0115 | 0.0377 | -0.3035 | 0.375 | -0.0110 | -0.2354 | 0.417 |
| 5 | -0.0117 | 0.0375 | -0.3109 | 0.333 | -0.0157 | -0.3500 | 0.333 |
| 10 | -0.0059 | 0.0324 | -0.1827 | 0.375 | -0.0118 | -0.3065 | 0.292 |
| 20 | -0.0071 | 0.0337 | -0.2105 | 0.417 | -0.0097 | -0.2295 | 0.375 |
| 40 | -0.0064 | 0.0286 | -0.2239 | 0.500 | -0.0077 | -0.1977 | 0.417 |
| 60 | -0.0051 | 0.0308 | -0.1639 | 0.417 | -0.0080 | -0.1906 | 0.458 |

quantile mean forward 20d returns: Q1: 0.00336  Q2: 0.00328  Q3: 0.00210  Q4: 0.00335  Q5: -0.00255
Q5-Q1 long-short (gross, monthly): mean -0.00591, ann -0.0584, Sharpe -0.511, MDD -0.1497
top-quintile turnover: 0.086

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0105 | -0.212 | 0.250 |
| 2023 | 12 | -0.0088 | -0.268 | 0.500 |

regime split: up-market IC -0.0248 (n=13) / down-market IC 0.0082 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.457
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0052 | 0.0333 | 0.1573 | 0.542 | 0.0107 | 0.2278 | 0.583 |
| 5 | -0.0012 | 0.0342 | -0.0339 | 0.583 | -0.0007 | -0.0142 | 0.542 |
| 10 | 0.0041 | 0.0381 | 0.1076 | 0.417 | -0.0002 | -0.0049 | 0.500 |
| 20 | 0.0045 | 0.0324 | 0.1395 | 0.500 | 0.0008 | 0.0170 | 0.458 |
| 40 | -0.0012 | 0.0238 | -0.0509 | 0.417 | -0.0073 | -0.2426 | 0.458 |
| 60 | -0.0108 | 0.0260 | -0.4148 | 0.292 | -0.0193 | -0.5507 | 0.292 |

quantile mean forward 20d returns: Q1: 0.02873  Q2: 0.03690  Q3: 0.03489  Q4: 0.02577  Q5: 0.03657
Q5-Q1 long-short (gross, monthly): mean 0.00784, ann 0.0735, Sharpe 0.683, MDD -0.0795
top-quintile turnover: 0.076

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0084 | 0.229 | 0.500 |
| 2025 | 12 | -0.0069 | -0.133 | 0.417 |

regime split: up-market IC 0.0055 (n=15) / down-market IC -0.0071 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0052 | 0.0333 | 0.1570 | 0.542 | 0.0107 | 0.2278 | 0.583 |
| 5 | -0.0012 | 0.0342 | -0.0340 | 0.583 | -0.0007 | -0.0135 | 0.542 |
| 10 | 0.0041 | 0.0380 | 0.1077 | 0.417 | -0.0002 | -0.0039 | 0.500 |
| 20 | 0.0045 | 0.0324 | 0.1396 | 0.500 | 0.0008 | 0.0177 | 0.458 |
| 40 | -0.0012 | 0.0238 | -0.0509 | 0.417 | -0.0073 | -0.2422 | 0.458 |
| 60 | -0.0108 | 0.0260 | -0.4148 | 0.292 | -0.0192 | -0.5505 | 0.292 |

quantile mean forward 20d returns: Q1: 0.02873  Q2: 0.03690  Q3: 0.03489  Q4: 0.02577  Q5: 0.03657
Q5-Q1 long-short (gross, monthly): mean 0.00784, ann 0.0735, Sharpe 0.683, MDD -0.0795
top-quintile turnover: 0.076

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0084 | 0.229 | 0.500 |
| 2025 | 12 | -0.0068 | -0.132 | 0.417 |

regime split: up-market IC 0.0055 (n=15) / down-market IC -0.0070 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`announcement_count_20d`: 0.242  `news_count_20d`: 0.242  `major_event_count_20d`: 0.237  `announcement_count_5d`: 0.208  `news_count_5d`: 0.208

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.