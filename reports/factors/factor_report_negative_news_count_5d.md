# factor_report_negative_news_count_5d.md

## definition

- factor: `negative_news_count_5d`  ·  category: news  ·  version 1.0
- formula: `count(rule-direction-negative events in 5d)`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: negative announcement count (rule direction), 5d
- declared (economic) direction: **negative**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.401
- empirical direction: positive  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0121 | 0.0446 | 0.2719 | 0.562 | 0.0133 | 0.2443 | 0.562 |
| 5 | 0.0088 | 0.0321 | 0.2746 | 0.542 | 0.0112 | 0.2566 | 0.604 |
| 10 | 0.0144 | 0.0387 | 0.3713 | 0.562 | 0.0150 | 0.3193 | 0.604 |
| 20 | 0.0072 | 0.0414 | 0.1732 | 0.542 | 0.0077 | 0.1521 | 0.521 |
| 40 | 0.0133 | 0.0445 | 0.2995 | 0.583 | 0.0118 | 0.2263 | 0.542 |
| 60 | 0.0097 | 0.0444 | 0.2190 | 0.562 | 0.0064 | 0.1138 | 0.542 |

quantile mean forward 20d returns: Q1: 0.00915  Q2: 0.01189  Q3: 0.01431  Q4: 0.00888  Q5: 0.01166
Q5-Q1 long-short (gross, monthly): mean 0.00251, ann 0.0287, Sharpe 0.284, MDD -0.1425
top-quintile turnover: 0.168

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0068 | 0.341 | 0.583 |
| 2019 | 12 | 0.0447 | 0.652 | 0.583 |
| 2020 | 12 | -0.0125 | -0.289 | 0.500 |
| 2021 | 12 | -0.0083 | -0.239 | 0.417 |

regime split: up-market IC 0.0060 (n=28) / down-market IC 0.0100 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0121 | 0.0446 | 0.2719 | 0.562 | 0.0132 | 0.2433 | 0.562 |
| 5 | 0.0088 | 0.0321 | 0.2746 | 0.542 | 0.0112 | 0.2562 | 0.604 |
| 10 | 0.0144 | 0.0387 | 0.3713 | 0.562 | 0.0150 | 0.3187 | 0.604 |
| 20 | 0.0072 | 0.0414 | 0.1732 | 0.542 | 0.0077 | 0.1519 | 0.521 |
| 40 | 0.0133 | 0.0445 | 0.2995 | 0.583 | 0.0118 | 0.2264 | 0.542 |
| 60 | 0.0097 | 0.0444 | 0.2192 | 0.562 | 0.0064 | 0.1138 | 0.542 |

quantile mean forward 20d returns: Q1: 0.00915  Q2: 0.01189  Q3: 0.01431  Q4: 0.00888  Q5: 0.01166
Q5-Q1 long-short (gross, monthly): mean 0.00251, ann 0.0287, Sharpe 0.284, MDD -0.1425
top-quintile turnover: 0.168

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0068 | 0.341 | 0.583 |
| 2019 | 12 | 0.0447 | 0.651 | 0.583 |
| 2020 | 12 | -0.0125 | -0.289 | 0.500 |
| 2021 | 12 | -0.0083 | -0.240 | 0.417 |

regime split: up-market IC 0.0060 (n=28) / down-market IC 0.0100 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.455
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0008 | 0.0433 | -0.0186 | 0.435 | -0.0072 | -0.1506 | 0.348 |
| 5 | -0.0008 | 0.0410 | -0.0206 | 0.417 | 0.0009 | 0.0154 | 0.583 |
| 10 | -0.0063 | 0.0366 | -0.1728 | 0.435 | -0.0071 | -0.1434 | 0.435 |
| 20 | -0.0080 | 0.0317 | -0.2531 | 0.292 | -0.0073 | -0.1766 | 0.333 |
| 40 | -0.0089 | 0.0338 | -0.2616 | 0.391 | -0.0091 | -0.2086 | 0.435 |
| 60 | -0.0081 | 0.0281 | -0.2883 | 0.261 | -0.0098 | -0.2909 | 0.348 |

quantile mean forward 20d returns: Q1: 0.00343  Q2: 0.00396  Q3: -0.00020  Q4: 0.00492  Q5: -0.00257
Q5-Q1 long-short (gross, monthly): mean -0.00601, ann -0.0590, Sharpe -0.512, MDD -0.1571
top-quintile turnover: 0.093

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0097 | -0.227 | 0.333 |
| 2023 | 12 | -0.0047 | -0.118 | 0.333 |

regime split: up-market IC -0.0174 (n=13) / down-market IC 0.0058 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0008 | 0.0433 | -0.0187 | 0.435 | -0.0072 | -0.1506 | 0.348 |
| 5 | -0.0009 | 0.0418 | -0.0212 | 0.435 | 0.0009 | 0.0154 | 0.609 |
| 10 | -0.0063 | 0.0366 | -0.1730 | 0.435 | -0.0071 | -0.1434 | 0.435 |
| 20 | -0.0084 | 0.0324 | -0.2590 | 0.304 | -0.0073 | -0.1766 | 0.348 |
| 40 | -0.0088 | 0.0338 | -0.2617 | 0.391 | -0.0091 | -0.2086 | 0.435 |
| 60 | -0.0081 | 0.0281 | -0.2883 | 0.261 | -0.0098 | -0.2909 | 0.348 |

quantile mean forward 20d returns: Q1: 0.00474  Q2: 0.00425  Q3: -0.00003  Q4: 0.00593  Q5: -0.00196
Q5-Q1 long-short (gross, monthly): mean -0.00669, ann -0.0662, Sharpe -0.565, MDD -0.1638
top-quintile turnover: 0.101

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0098 | -0.227 | 0.333 |
| 2023 | 11 | -0.0047 | -0.119 | 0.364 |

regime split: up-market IC -0.0174 (n=13) / down-market IC 0.0058 (n=10)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.457
- empirical direction: positive  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0206 | 0.0496 | 0.4153 | 0.739 | 0.0174 | 0.3339 | 0.609 |
| 5 | 0.0134 | 0.0484 | 0.2771 | 0.583 | 0.0143 | 0.2800 | 0.542 |
| 10 | 0.0173 | 0.0454 | 0.3802 | 0.542 | 0.0148 | 0.3222 | 0.542 |
| 20 | 0.0119 | 0.0348 | 0.3416 | 0.583 | 0.0074 | 0.2185 | 0.500 |
| 40 | 0.0105 | 0.0245 | 0.4310 | 0.625 | 0.0054 | 0.2782 | 0.542 |
| 60 | 0.0118 | 0.0275 | 0.4290 | 0.625 | 0.0053 | 0.2308 | 0.542 |

quantile mean forward 20d returns: Q1: 0.02856  Q2: 0.03597  Q3: 0.03517  Q4: 0.02615  Q5: 0.03702
Q5-Q1 long-short (gross, monthly): mean 0.00847, ann 0.0922, Sharpe 0.831, MDD -0.0765
top-quintile turnover: 0.032

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0022 | 0.085 | 0.417 |
| 2025 | 12 | 0.0117 | 0.303 | 0.583 |

regime split: up-market IC 0.0120 (n=15) / down-market IC -0.0007 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0215 | 0.0505 | 0.4263 | 0.727 | 0.0174 | 0.3339 | 0.636 |
| 5 | 0.0146 | 0.0503 | 0.2904 | 0.591 | 0.0143 | 0.2800 | 0.591 |
| 10 | 0.0188 | 0.0471 | 0.3998 | 0.545 | 0.0148 | 0.3222 | 0.591 |
| 20 | 0.0130 | 0.0362 | 0.3587 | 0.591 | 0.0074 | 0.2186 | 0.545 |
| 40 | 0.0115 | 0.0253 | 0.4541 | 0.636 | 0.0054 | 0.2782 | 0.591 |
| 60 | 0.0129 | 0.0285 | 0.4519 | 0.636 | 0.0053 | 0.2308 | 0.591 |

quantile mean forward 20d returns: Q1: 0.02981  Q2: 0.03890  Q3: 0.03758  Q4: 0.02778  Q5: 0.03882
Q5-Q1 long-short (gross, monthly): mean 0.00902, ann 0.0981, Sharpe 0.850, MDD -0.0765
top-quintile turnover: 0.037

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 10 | 0.0022 | 0.085 | 0.500 |
| 2025 | 12 | 0.0117 | 0.303 | 0.583 |

regime split: up-market IC 0.0120 (n=14) / down-market IC -0.0007 (n=8)

---

## correlation with other factors (avg cross-sectional spearman, research)

`announcement_count_5d`: 0.293  `news_count_5d`: 0.293  `event_sentiment_shock`: -0.292  `news_importance_5d`: 0.273  `major_event_count_20d`: 0.272

## interpretation & limitations

- declared direction `negative` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.