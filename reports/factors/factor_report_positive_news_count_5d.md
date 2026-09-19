# factor_report_positive_news_count_5d.md

## definition

- factor: `positive_news_count_5d`  ·  category: news  ·  version 1.0
- formula: `count(rule-direction-positive events in 5d)`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: positive announcement count (rule direction), 5d
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.401
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0054 | 0.0534 | 0.1009 | 0.500 | 0.0043 | 0.0697 | 0.479 |
| 5 | -0.0018 | 0.0339 | -0.0528 | 0.396 | -0.0023 | -0.0555 | 0.479 |
| 10 | 0.0055 | 0.0391 | 0.1410 | 0.542 | 0.0043 | 0.0960 | 0.583 |
| 20 | 0.0029 | 0.0505 | 0.0566 | 0.396 | -0.0014 | -0.0261 | 0.458 |
| 40 | 0.0018 | 0.0478 | 0.0369 | 0.479 | -0.0039 | -0.0747 | 0.479 |
| 60 | 0.0003 | 0.0373 | 0.0072 | 0.562 | -0.0055 | -0.1300 | 0.500 |

quantile mean forward 20d returns: Q1: 0.00924  Q2: 0.01233  Q3: 0.01559  Q4: 0.00826  Q5: 0.01047
Q5-Q1 long-short (gross, monthly): mean 0.00124, ann 0.0135, Sharpe 0.139, MDD -0.1298
top-quintile turnover: 0.118

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0032 | 0.052 | 0.333 |
| 2019 | 12 | 0.0027 | 0.075 | 0.583 |
| 2020 | 12 | -0.0119 | -0.233 | 0.417 |
| 2021 | 12 | 0.0002 | 0.004 | 0.500 |

regime split: up-market IC -0.0033 (n=28) / down-market IC 0.0011 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0054 | 0.0534 | 0.1011 | 0.500 | 0.0042 | 0.0692 | 0.479 |
| 5 | -0.0018 | 0.0339 | -0.0525 | 0.396 | -0.0023 | -0.0554 | 0.479 |
| 10 | 0.0055 | 0.0391 | 0.1411 | 0.542 | 0.0043 | 0.0953 | 0.583 |
| 20 | 0.0029 | 0.0505 | 0.0567 | 0.396 | -0.0014 | -0.0263 | 0.458 |
| 40 | 0.0018 | 0.0478 | 0.0371 | 0.479 | -0.0039 | -0.0749 | 0.479 |
| 60 | 0.0003 | 0.0373 | 0.0072 | 0.562 | -0.0055 | -0.1297 | 0.500 |

quantile mean forward 20d returns: Q1: 0.00924  Q2: 0.01233  Q3: 0.01559  Q4: 0.00826  Q5: 0.01047
Q5-Q1 long-short (gross, monthly): mean 0.00124, ann 0.0135, Sharpe 0.139, MDD -0.1298
top-quintile turnover: 0.118

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0032 | 0.051 | 0.333 |
| 2019 | 12 | 0.0027 | 0.075 | 0.583 |
| 2020 | 12 | -0.0119 | -0.232 | 0.417 |
| 2021 | 12 | 0.0002 | 0.003 | 0.500 |

regime split: up-market IC -0.0033 (n=28) / down-market IC 0.0011 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.455
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0014 | 0.0521 | 0.0261 | 0.583 | 0.0014 | 0.0210 | 0.583 |
| 5 | -0.0017 | 0.0296 | -0.0560 | 0.458 | -0.0004 | -0.0103 | 0.583 |
| 10 | -0.0106 | 0.0360 | -0.2948 | 0.417 | -0.0147 | -0.3123 | 0.500 |
| 20 | -0.0082 | 0.0346 | -0.2361 | 0.500 | -0.0124 | -0.2684 | 0.542 |
| 40 | 0.0084 | 0.0448 | 0.1880 | 0.625 | 0.0118 | 0.2339 | 0.667 |
| 60 | 0.0077 | 0.0507 | 0.1509 | 0.542 | 0.0056 | 0.0978 | 0.500 |

quantile mean forward 20d returns: Q1: 0.00358  Q2: 0.00338  Q3: 0.00157  Q4: 0.00374  Q5: -0.00274
Q5-Q1 long-short (gross, monthly): mean -0.00632, ann -0.0629, Sharpe -0.571, MDD -0.1590
top-quintile turnover: 0.196

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0201 | -0.551 | 0.417 |
| 2023 | 12 | -0.0047 | -0.089 | 0.667 |

regime split: up-market IC -0.0147 (n=13) / down-market IC -0.0097 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0014 | 0.0522 | 0.0259 | 0.583 | 0.0014 | 0.0210 | 0.583 |
| 5 | -0.0017 | 0.0296 | -0.0561 | 0.458 | -0.0004 | -0.0099 | 0.583 |
| 10 | -0.0106 | 0.0360 | -0.2949 | 0.417 | -0.0147 | -0.3122 | 0.500 |
| 20 | -0.0082 | 0.0346 | -0.2363 | 0.500 | -0.0124 | -0.2682 | 0.542 |
| 40 | 0.0084 | 0.0448 | 0.1878 | 0.625 | 0.0118 | 0.2341 | 0.667 |
| 60 | 0.0076 | 0.0507 | 0.1505 | 0.542 | 0.0056 | 0.0979 | 0.500 |

quantile mean forward 20d returns: Q1: 0.00358  Q2: 0.00338  Q3: 0.00157  Q4: 0.00374  Q5: -0.00274
Q5-Q1 long-short (gross, monthly): mean -0.00632, ann -0.0629, Sharpe -0.571, MDD -0.1590
top-quintile turnover: 0.196

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0201 | -0.551 | 0.417 |
| 2023 | 12 | -0.0047 | -0.088 | 0.667 |

regime split: up-market IC -0.0147 (n=13) / down-market IC -0.0097 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.457
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0152 | 0.0518 | 0.2929 | 0.500 | 0.0176 | 0.3186 | 0.500 |
| 5 | 0.0161 | 0.0544 | 0.2950 | 0.500 | 0.0184 | 0.2894 | 0.667 |
| 10 | 0.0169 | 0.0495 | 0.3411 | 0.500 | 0.0209 | 0.3474 | 0.625 |
| 20 | 0.0127 | 0.0556 | 0.2292 | 0.542 | 0.0109 | 0.1974 | 0.625 |
| 40 | 0.0050 | 0.0384 | 0.1310 | 0.500 | 0.0016 | 0.0333 | 0.500 |
| 60 | 0.0013 | 0.0404 | 0.0328 | 0.375 | -0.0017 | -0.0337 | 0.458 |

quantile mean forward 20d returns: Q1: 0.02865  Q2: 0.03593  Q3: 0.03348  Q4: 0.02544  Q5: 0.03937
Q5-Q1 long-short (gross, monthly): mean 0.01072, ann 0.1179, Sharpe 0.840, MDD -0.0761
top-quintile turnover: 0.118

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0321 | 0.554 | 0.833 |
| 2025 | 12 | -0.0103 | -0.241 | 0.417 |

regime split: up-market IC 0.0088 (n=15) / down-market IC 0.0144 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0152 | 0.0518 | 0.2930 | 0.500 | 0.0176 | 0.3180 | 0.500 |
| 5 | 0.0160 | 0.0544 | 0.2947 | 0.500 | 0.0184 | 0.2890 | 0.667 |
| 10 | 0.0169 | 0.0495 | 0.3410 | 0.500 | 0.0209 | 0.3471 | 0.625 |
| 20 | 0.0127 | 0.0556 | 0.2291 | 0.542 | 0.0109 | 0.1970 | 0.625 |
| 40 | 0.0050 | 0.0384 | 0.1307 | 0.500 | 0.0016 | 0.0319 | 0.500 |
| 60 | 0.0013 | 0.0404 | 0.0328 | 0.375 | -0.0018 | -0.0346 | 0.458 |

quantile mean forward 20d returns: Q1: 0.02865  Q2: 0.03593  Q3: 0.03348  Q4: 0.02544  Q5: 0.03937
Q5-Q1 long-short (gross, monthly): mean 0.01072, ann 0.1179, Sharpe 0.840, MDD -0.0761
top-quintile turnover: 0.118

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0322 | 0.554 | 0.833 |
| 2025 | 12 | -0.0104 | -0.242 | 0.417 |

regime split: up-market IC 0.0088 (n=15) / down-market IC 0.0144 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`buyback_event_count_20d`: 0.393  `major_event_count_20d`: 0.299  `announcement_count_5d`: 0.296  `news_count_5d`: 0.296  `event_sentiment_shock`: 0.259

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.