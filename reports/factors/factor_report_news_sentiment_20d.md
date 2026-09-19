# factor_report_news_sentiment_20d.md

## definition

- factor: `news_sentiment_20d`  ·  category: news  ·  version 1.0
- formula: `mean sentiment of events in 20d`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: 20-day mean event sentiment
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.401
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0116 | 0.0482 | -0.2399 | 0.417 | -0.0197 | -0.2791 | 0.396 |
| 5 | -0.0066 | 0.0421 | -0.1563 | 0.458 | -0.0110 | -0.1872 | 0.396 |
| 10 | -0.0128 | 0.0457 | -0.2805 | 0.417 | -0.0213 | -0.3495 | 0.354 |
| 20 | 0.0005 | 0.0532 | 0.0089 | 0.417 | -0.0091 | -0.1317 | 0.396 |
| 40 | -0.0015 | 0.0567 | -0.0257 | 0.458 | -0.0051 | -0.0708 | 0.438 |
| 60 | -0.0013 | 0.0557 | -0.0239 | 0.417 | -0.0045 | -0.0665 | 0.438 |

quantile mean forward 20d returns: Q1: 0.00992  Q2: 0.01166  Q3: 0.01581  Q4: 0.00867  Q5: 0.00982
Q5-Q1 long-short (gross, monthly): mean -0.00010, ann -0.0078, Sharpe -0.095, MDD -0.1184
top-quintile turnover: 0.196

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0167 | -0.229 | 0.333 |
| 2019 | 12 | -0.0133 | -0.184 | 0.333 |
| 2020 | 12 | -0.0067 | -0.088 | 0.333 |
| 2021 | 12 | 0.0001 | 0.003 | 0.583 |

regime split: up-market IC -0.0192 (n=28) / down-market IC 0.0049 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0162 | 0.0523 | -0.3099 | 0.354 | -0.0191 | -0.2583 | 0.396 |
| 5 | -0.0075 | 0.0438 | -0.1707 | 0.500 | -0.0103 | -0.1733 | 0.417 |
| 10 | -0.0151 | 0.0460 | -0.3284 | 0.438 | -0.0193 | -0.3131 | 0.375 |
| 20 | -0.0035 | 0.0535 | -0.0654 | 0.396 | -0.0069 | -0.1003 | 0.438 |
| 40 | -0.0053 | 0.0585 | -0.0913 | 0.375 | -0.0030 | -0.0417 | 0.458 |
| 60 | -0.0025 | 0.0546 | -0.0463 | 0.438 | 0.0011 | 0.0158 | 0.479 |

quantile mean forward 20d returns: Q1: 0.00977  Q2: 0.01178  Q3: 0.01570  Q4: 0.00874  Q5: 0.00990
Q5-Q1 long-short (gross, monthly): mean 0.00013, ann -0.0052, Sharpe -0.061, MDD -0.1184
top-quintile turnover: 0.209

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0167 | -0.229 | 0.333 |
| 2019 | 12 | -0.0132 | -0.182 | 0.333 |
| 2020 | 12 | 0.0008 | 0.011 | 0.417 |
| 2021 | 12 | 0.0015 | 0.029 | 0.667 |

regime split: up-market IC -0.0159 (n=28) / down-market IC 0.0057 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.455
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0052 | 0.0640 | 0.0813 | 0.500 | 0.0063 | 0.0766 | 0.583 |
| 5 | -0.0134 | 0.0573 | -0.2340 | 0.375 | -0.0176 | -0.2146 | 0.458 |
| 10 | -0.0159 | 0.0521 | -0.3046 | 0.333 | -0.0229 | -0.3067 | 0.292 |
| 20 | -0.0096 | 0.0421 | -0.2279 | 0.333 | -0.0234 | -0.3748 | 0.250 |
| 40 | 0.0055 | 0.0494 | 0.1110 | 0.625 | -0.0052 | -0.0754 | 0.458 |
| 60 | 0.0063 | 0.0628 | 0.0997 | 0.542 | 0.0012 | 0.0147 | 0.458 |

quantile mean forward 20d returns: Q1: 0.00241  Q2: 0.00326  Q3: 0.00479  Q4: 0.00522  Q5: -0.00614
Q5-Q1 long-short (gross, monthly): mean -0.00855, ann -0.0858, Sharpe -0.752, MDD -0.1731
top-quintile turnover: 0.237

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0303 | -0.558 | 0.333 |
| 2023 | 12 | -0.0164 | -0.239 | 0.167 |

regime split: up-market IC -0.0194 (n=13) / down-market IC -0.0281 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0025 | 0.0642 | 0.0389 | 0.500 | 0.0017 | 0.0214 | 0.542 |
| 5 | -0.0139 | 0.0495 | -0.2818 | 0.417 | -0.0205 | -0.2560 | 0.417 |
| 10 | -0.0161 | 0.0425 | -0.3798 | 0.417 | -0.0249 | -0.3429 | 0.250 |
| 20 | -0.0101 | 0.0368 | -0.2752 | 0.250 | -0.0262 | -0.4334 | 0.208 |
| 40 | -0.0037 | 0.0403 | -0.0916 | 0.583 | -0.0066 | -0.0972 | 0.458 |
| 60 | -0.0016 | 0.0551 | -0.0291 | 0.500 | -0.0006 | -0.0071 | 0.417 |

quantile mean forward 20d returns: Q1: 0.00242  Q2: 0.00337  Q3: 0.00525  Q4: 0.00482  Q5: -0.00632
Q5-Q1 long-short (gross, monthly): mean -0.00874, ann -0.0879, Sharpe -0.773, MDD -0.1735
top-quintile turnover: 0.229

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0360 | -0.737 | 0.250 |
| 2023 | 12 | -0.0164 | -0.239 | 0.167 |

regime split: up-market IC -0.0232 (n=13) / down-market IC -0.0297 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.457
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0140 | 0.0639 | 0.2195 | 0.708 | 0.0112 | 0.1319 | 0.625 |
| 5 | 0.0137 | 0.0677 | 0.2017 | 0.542 | 0.0092 | 0.1127 | 0.542 |
| 10 | 0.0059 | 0.0577 | 0.1029 | 0.542 | 0.0048 | 0.0645 | 0.458 |
| 20 | 0.0078 | 0.0418 | 0.1857 | 0.625 | 0.0156 | 0.2442 | 0.625 |
| 40 | 0.0028 | 0.0343 | 0.0826 | 0.458 | 0.0081 | 0.1645 | 0.542 |
| 60 | -0.0102 | 0.0327 | -0.3122 | 0.333 | -0.0081 | -0.1454 | 0.417 |

quantile mean forward 20d returns: Q1: 0.02999  Q2: 0.03355  Q3: 0.03012  Q4: 0.02634  Q5: 0.04287
Q5-Q1 long-short (gross, monthly): mean 0.01288, ann 0.1370, Sharpe 0.982, MDD -0.0812
top-quintile turnover: 0.233

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0426 | 0.706 | 0.833 |
| 2025 | 12 | -0.0115 | -0.209 | 0.417 |

regime split: up-market IC 0.0127 (n=15) / down-market IC 0.0203 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0124 | 0.0567 | 0.2187 | 0.708 | 0.0191 | 0.2281 | 0.667 |
| 5 | 0.0070 | 0.0635 | 0.1099 | 0.583 | 0.0065 | 0.0797 | 0.500 |
| 10 | -0.0015 | 0.0523 | -0.0293 | 0.500 | -0.0003 | -0.0040 | 0.417 |
| 20 | -0.0018 | 0.0501 | -0.0367 | 0.625 | -0.0023 | -0.0337 | 0.583 |
| 40 | -0.0038 | 0.0344 | -0.1097 | 0.458 | -0.0039 | -0.0764 | 0.500 |
| 60 | -0.0169 | 0.0347 | -0.4878 | 0.292 | -0.0217 | -0.4106 | 0.375 |

quantile mean forward 20d returns: Q1: 0.03295  Q2: 0.03184  Q3: 0.03179  Q4: 0.02658  Q5: 0.03970
Q5-Q1 long-short (gross, monthly): mean 0.00675, ann 0.0627, Sharpe 0.720, MDD -0.0812
top-quintile turnover: 0.239

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0070 | 0.090 | 0.750 |
| 2025 | 12 | -0.0116 | -0.211 | 0.417 |

regime split: up-market IC -0.0159 (n=15) / down-market IC 0.0203 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`news_positive_negative_ratio`: 1.000  `buyback_event_count_20d`: 0.433  `negative_news_count_5d`: -0.272  `event_sentiment_shock`: -0.104  `major_event_count_20d`: 0.104

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.