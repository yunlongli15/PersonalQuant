# factor_report_amount_share_20.md

## definition

- factor: `amount_share_20`  ·  category: liquidity  ·  version 1.0
- formula: `amount_cny[t] / mean(amount_cny, 20d)`
- source: market  ·  PIT: True
- required fields: amount, volume
- description: 当日成交额相对自身 20 日均值（放量倍数，单股内归一）
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0005 | 0.0875 | 0.0055 | 0.458 | -0.0390 | -0.3875 | 0.271 |
| 5 | -0.0116 | 0.0854 | -0.1354 | 0.438 | -0.0356 | -0.3441 | 0.333 |
| 10 | -0.0090 | 0.0687 | -0.1315 | 0.479 | -0.0253 | -0.2950 | 0.375 |
| 20 | -0.0036 | 0.0539 | -0.0664 | 0.458 | -0.0129 | -0.1921 | 0.417 |
| 40 | -0.0029 | 0.0583 | -0.0496 | 0.417 | -0.0159 | -0.2196 | 0.417 |
| 60 | -0.0024 | 0.0499 | -0.0482 | 0.500 | -0.0119 | -0.1982 | 0.438 |

quantile mean forward 20d returns: Q1: 0.00923  Q2: 0.01161  Q3: 0.01339  Q4: 0.01319  Q5: 0.00830
Q5-Q1 long-short (gross, monthly): mean -0.00093, ann -0.0086, Sharpe -0.117, MDD -0.1974
top-quintile turnover: 0.821

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0150 | -0.238 | 0.417 |
| 2019 | 12 | -0.0333 | -0.538 | 0.250 |
| 2020 | 12 | 0.0129 | 0.160 | 0.583 |
| 2021 | 12 | -0.0164 | -0.316 | 0.417 |

regime split: up-market IC -0.0281 (n=28) / down-market IC 0.0083 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0046 | 0.0965 | 0.0482 | 0.438 | -0.0390 | -0.3875 | 0.271 |
| 5 | -0.0190 | 0.0906 | -0.2094 | 0.417 | -0.0356 | -0.3437 | 0.333 |
| 10 | -0.0182 | 0.0714 | -0.2544 | 0.438 | -0.0252 | -0.2944 | 0.375 |
| 20 | -0.0172 | 0.0587 | -0.2925 | 0.396 | -0.0129 | -0.1914 | 0.417 |
| 40 | -0.0154 | 0.0580 | -0.2662 | 0.417 | -0.0159 | -0.2190 | 0.417 |
| 60 | -0.0138 | 0.0496 | -0.2779 | 0.417 | -0.0119 | -0.1975 | 0.438 |

quantile mean forward 20d returns: Q1: 0.00923  Q2: 0.01160  Q3: 0.01337  Q4: 0.01321  Q5: 0.00830
Q5-Q1 long-short (gross, monthly): mean -0.00093, ann -0.0085, Sharpe -0.117, MDD -0.1974
top-quintile turnover: 0.821

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0149 | -0.238 | 0.417 |
| 2019 | 12 | -0.0332 | -0.537 | 0.250 |
| 2020 | 12 | 0.0129 | 0.160 | 0.583 |
| 2021 | 12 | -0.0163 | -0.314 | 0.417 |

regime split: up-market IC -0.0280 (n=28) / down-market IC 0.0083 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0364 | 0.1032 | -0.3530 | 0.375 | -0.0622 | -0.5294 | 0.250 |
| 5 | -0.0312 | 0.0873 | -0.3577 | 0.500 | -0.0516 | -0.4776 | 0.333 |
| 10 | -0.0284 | 0.0564 | -0.5038 | 0.375 | -0.0438 | -0.6263 | 0.333 |
| 20 | -0.0321 | 0.0624 | -0.5141 | 0.375 | -0.0408 | -0.5339 | 0.250 |
| 40 | -0.0516 | 0.0732 | -0.7051 | 0.333 | -0.0693 | -0.8022 | 0.292 |
| 60 | -0.0359 | 0.0606 | -0.5920 | 0.292 | -0.0515 | -0.7062 | 0.250 |

quantile mean forward 20d returns: Q1: 0.00588  Q2: 0.00479  Q3: 0.00711  Q4: 0.00252  Q5: -0.00575
Q5-Q1 long-short (gross, monthly): mean -0.01163, ann -0.1344, Sharpe -1.953, MDD -0.2507
top-quintile turnover: 0.877

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0589 | -0.800 | 0.167 |
| 2023 | 12 | -0.0228 | -0.304 | 0.333 |

regime split: up-market IC -0.0584 (n=13) / down-market IC -0.0201 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0355 | 0.1039 | -0.3414 | 0.333 | -0.0622 | -0.5293 | 0.250 |
| 5 | -0.0342 | 0.0890 | -0.3845 | 0.417 | -0.0516 | -0.4775 | 0.333 |
| 10 | -0.0338 | 0.0609 | -0.5549 | 0.333 | -0.0438 | -0.6262 | 0.333 |
| 20 | -0.0411 | 0.0630 | -0.6529 | 0.250 | -0.0408 | -0.5337 | 0.250 |
| 40 | -0.0570 | 0.0664 | -0.8586 | 0.208 | -0.0693 | -0.8022 | 0.292 |
| 60 | -0.0427 | 0.0520 | -0.8212 | 0.250 | -0.0515 | -0.7062 | 0.250 |

quantile mean forward 20d returns: Q1: 0.00588  Q2: 0.00479  Q3: 0.00710  Q4: 0.00253  Q5: -0.00576
Q5-Q1 long-short (gross, monthly): mean -0.01163, ann -0.1344, Sharpe -1.954, MDD -0.2508
top-quintile turnover: 0.877

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0589 | -0.799 | 0.167 |
| 2023 | 12 | -0.0228 | -0.304 | 0.333 |

regime split: up-market IC -0.0584 (n=13) / down-market IC -0.0201 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0106 | 0.0744 | -0.1423 | 0.417 | -0.0397 | -0.4195 | 0.333 |
| 5 | -0.0200 | 0.0700 | -0.2855 | 0.250 | -0.0417 | -0.4588 | 0.250 |
| 10 | -0.0148 | 0.0759 | -0.1944 | 0.458 | -0.0370 | -0.4129 | 0.250 |
| 20 | -0.0226 | 0.0604 | -0.3747 | 0.375 | -0.0410 | -0.5837 | 0.250 |
| 40 | -0.0149 | 0.0495 | -0.3009 | 0.417 | -0.0306 | -0.4634 | 0.333 |
| 60 | -0.0217 | 0.0447 | -0.4863 | 0.292 | -0.0400 | -0.6776 | 0.250 |

quantile mean forward 20d returns: Q1: 0.03485  Q2: 0.03576  Q3: 0.04163  Q4: 0.03276  Q5: 0.02572
Q5-Q1 long-short (gross, monthly): mean -0.00912, ann -0.0890, Sharpe -1.112, MDD -0.2257
top-quintile turnover: 0.887

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0608 | -0.875 | 0.167 |
| 2025 | 12 | -0.0213 | -0.325 | 0.333 |

regime split: up-market IC -0.0711 (n=15) / down-market IC 0.0091 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0096 | 0.0669 | -0.1441 | 0.458 | -0.0397 | -0.4195 | 0.333 |
| 5 | -0.0280 | 0.0713 | -0.3927 | 0.333 | -0.0417 | -0.4586 | 0.250 |
| 10 | -0.0242 | 0.0753 | -0.3218 | 0.375 | -0.0370 | -0.4127 | 0.250 |
| 20 | -0.0329 | 0.0606 | -0.5434 | 0.292 | -0.0410 | -0.5834 | 0.250 |
| 40 | -0.0233 | 0.0490 | -0.4753 | 0.333 | -0.0306 | -0.4631 | 0.333 |
| 60 | -0.0303 | 0.0429 | -0.7046 | 0.250 | -0.0400 | -0.6775 | 0.250 |

quantile mean forward 20d returns: Q1: 0.03485  Q2: 0.03576  Q3: 0.04165  Q4: 0.03277  Q5: 0.02570
Q5-Q1 long-short (gross, monthly): mean -0.00915, ann -0.0893, Sharpe -1.115, MDD -0.2257
top-quintile turnover: 0.887

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0608 | -0.874 | 0.167 |
| 2025 | 12 | -0.0212 | -0.325 | 0.333 |

regime split: up-market IC -0.0711 (n=15) / down-market IC 0.0092 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`momentum_20`: 0.304  `high_52w_proximity`: 0.155  `downside_volatility_60`: -0.132  `momentum_60`: 0.103  `news_attention_1d`: 0.098

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.