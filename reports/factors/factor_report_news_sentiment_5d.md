# factor_report_news_sentiment_5d.md

## definition

- factor: `news_sentiment_5d`  ·  category: news  ·  version 1.0
- formula: `mean sentiment of events in 5d`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: 5-day mean event sentiment
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.401
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0086 | 0.0567 | -0.1516 | 0.375 | -0.0132 | -0.1964 | 0.396 |
| 5 | -0.0096 | 0.0358 | -0.2668 | 0.312 | -0.0117 | -0.2407 | 0.417 |
| 10 | -0.0100 | 0.0444 | -0.2258 | 0.396 | -0.0135 | -0.2481 | 0.375 |
| 20 | -0.0076 | 0.0479 | -0.1587 | 0.396 | -0.0085 | -0.1399 | 0.521 |
| 40 | -0.0095 | 0.0492 | -0.1937 | 0.375 | -0.0109 | -0.1797 | 0.396 |
| 60 | -0.0077 | 0.0431 | -0.1781 | 0.396 | -0.0094 | -0.1714 | 0.521 |

quantile mean forward 20d returns: Q1: 0.01037  Q2: 0.01118  Q3: 0.01540  Q4: 0.00828  Q5: 0.01065
Q5-Q1 long-short (gross, monthly): mean 0.00028, ann 0.0020, Sharpe 0.021, MDD -0.1307
top-quintile turnover: 0.143

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0016 | -0.024 | 0.417 |
| 2019 | 12 | -0.0328 | -0.461 | 0.500 |
| 2020 | 12 | -0.0078 | -0.162 | 0.583 |
| 2021 | 12 | 0.0081 | 0.163 | 0.583 |

regime split: up-market IC -0.0067 (n=28) / down-market IC -0.0111 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0075 | 0.0545 | -0.1385 | 0.396 | -0.0124 | -0.1844 | 0.417 |
| 5 | -0.0088 | 0.0364 | -0.2406 | 0.333 | -0.0128 | -0.2662 | 0.396 |
| 10 | -0.0094 | 0.0439 | -0.2139 | 0.417 | -0.0146 | -0.2695 | 0.354 |
| 20 | -0.0066 | 0.0460 | -0.1443 | 0.417 | -0.0109 | -0.1810 | 0.500 |
| 40 | -0.0089 | 0.0495 | -0.1802 | 0.354 | -0.0103 | -0.1690 | 0.438 |
| 60 | -0.0074 | 0.0443 | -0.1663 | 0.375 | -0.0102 | -0.1868 | 0.500 |

quantile mean forward 20d returns: Q1: 0.01060  Q2: 0.01106  Q3: 0.01544  Q4: 0.00817  Q5: 0.01062
Q5-Q1 long-short (gross, monthly): mean 0.00002, ann -0.0011, Sharpe -0.011, MDD -0.1314
top-quintile turnover: 0.134

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0016 | -0.024 | 0.417 |
| 2019 | 12 | -0.0424 | -0.649 | 0.417 |
| 2020 | 12 | -0.0078 | -0.162 | 0.583 |
| 2021 | 12 | 0.0081 | 0.163 | 0.583 |

regime split: up-market IC -0.0109 (n=28) / down-market IC -0.0110 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.455
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0001 | 0.0579 | -0.0021 | 0.500 | 0.0045 | 0.0602 | 0.625 |
| 5 | -0.0024 | 0.0455 | -0.0519 | 0.458 | -0.0012 | -0.0185 | 0.458 |
| 10 | -0.0079 | 0.0424 | -0.1858 | 0.417 | -0.0103 | -0.1780 | 0.458 |
| 20 | -0.0019 | 0.0396 | -0.0475 | 0.542 | -0.0060 | -0.1119 | 0.500 |
| 40 | 0.0152 | 0.0528 | 0.2875 | 0.667 | 0.0168 | 0.2678 | 0.583 |
| 60 | 0.0137 | 0.0478 | 0.2876 | 0.667 | 0.0132 | 0.2267 | 0.542 |

quantile mean forward 20d returns: Q1: 0.00265  Q2: 0.00384  Q3: 0.00268  Q4: 0.00358  Q5: -0.00321
Q5-Q1 long-short (gross, monthly): mean -0.00586, ann -0.0575, Sharpe -0.529, MDD -0.1561
top-quintile turnover: 0.195

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0053 | -0.099 | 0.500 |
| 2023 | 12 | -0.0068 | -0.125 | 0.500 |

regime split: up-market IC 0.0002 (n=13) / down-market IC -0.0135 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0007 | 0.0576 | 0.0118 | 0.500 | -0.0004 | -0.0049 | 0.583 |
| 5 | 0.0005 | 0.0446 | 0.0111 | 0.458 | -0.0046 | -0.0726 | 0.417 |
| 10 | -0.0059 | 0.0424 | -0.1392 | 0.417 | -0.0127 | -0.2232 | 0.417 |
| 20 | 0.0010 | 0.0377 | 0.0254 | 0.542 | -0.0075 | -0.1398 | 0.458 |
| 40 | 0.0139 | 0.0489 | 0.2849 | 0.667 | 0.0166 | 0.2642 | 0.583 |
| 60 | 0.0134 | 0.0464 | 0.2880 | 0.667 | 0.0124 | 0.2135 | 0.500 |

quantile mean forward 20d returns: Q1: 0.00264  Q2: 0.00394  Q3: 0.00258  Q4: 0.00363  Q5: -0.00325
Q5-Q1 long-short (gross, monthly): mean -0.00589, ann -0.0578, Sharpe -0.532, MDD -0.1561
top-quintile turnover: 0.196

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0082 | -0.157 | 0.417 |
| 2023 | 12 | -0.0067 | -0.123 | 0.500 |

regime split: up-market IC -0.0025 (n=13) / down-market IC -0.0134 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.457
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0025 | 0.0680 | 0.0363 | 0.542 | 0.0052 | 0.0717 | 0.458 |
| 5 | 0.0069 | 0.0695 | 0.0993 | 0.542 | 0.0090 | 0.1126 | 0.625 |
| 10 | 0.0070 | 0.0643 | 0.1087 | 0.542 | 0.0124 | 0.1651 | 0.625 |
| 20 | 0.0066 | 0.0634 | 0.1038 | 0.667 | 0.0073 | 0.1175 | 0.667 |
| 40 | 0.0023 | 0.0405 | 0.0577 | 0.542 | 0.0016 | 0.0333 | 0.542 |
| 60 | -0.0018 | 0.0409 | -0.0439 | 0.375 | -0.0027 | -0.0527 | 0.417 |

quantile mean forward 20d returns: Q1: 0.02952  Q2: 0.03530  Q3: 0.03322  Q4: 0.02549  Q5: 0.03933
Q5-Q1 long-short (gross, monthly): mean 0.00981, ann 0.1063, Sharpe 0.769, MDD -0.0766
top-quintile turnover: 0.128

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0320 | 0.548 | 0.833 |
| 2025 | 12 | -0.0175 | -0.319 | 0.500 |

regime split: up-market IC 0.0018 (n=15) / down-market IC 0.0163 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0032 | 0.0678 | 0.0473 | 0.500 | 0.0053 | 0.0727 | 0.458 |
| 5 | 0.0064 | 0.0704 | 0.0904 | 0.542 | 0.0090 | 0.1130 | 0.625 |
| 10 | 0.0066 | 0.0645 | 0.1024 | 0.542 | 0.0124 | 0.1655 | 0.625 |
| 20 | 0.0052 | 0.0588 | 0.0884 | 0.667 | 0.0073 | 0.1175 | 0.667 |
| 40 | 0.0018 | 0.0385 | 0.0469 | 0.542 | 0.0016 | 0.0335 | 0.542 |
| 60 | -0.0024 | 0.0384 | -0.0621 | 0.375 | -0.0026 | -0.0523 | 0.417 |

quantile mean forward 20d returns: Q1: 0.02952  Q2: 0.03530  Q3: 0.03322  Q4: 0.02549  Q5: 0.03933
Q5-Q1 long-short (gross, monthly): mean 0.00981, ann 0.1063, Sharpe 0.769, MDD -0.0766
top-quintile turnover: 0.128

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0320 | 0.548 | 0.833 |
| 2025 | 12 | -0.0175 | -0.318 | 0.500 |

regime split: up-market IC 0.0018 (n=15) / down-market IC 0.0163 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`negative_news_count_5d`: -0.581  `event_sentiment_shock`: 0.446  `buyback_event_count_20d`: 0.238  `event_shock`: 0.049  `major_event_count_20d`: 0.035

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.