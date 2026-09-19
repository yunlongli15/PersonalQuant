# factor_report_news_importance_5d.md

## definition

- factor: `news_importance_5d`  ·  category: news  ·  version 1.0
- formula: `mean importance of events in 5d`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: 5-day mean event importance
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.401
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0285 | 0.0539 | 0.5293 | 0.792 | 0.0323 | 0.4725 | 0.729 |
| 5 | 0.0201 | 0.0440 | 0.4562 | 0.688 | 0.0198 | 0.3583 | 0.688 |
| 10 | 0.0256 | 0.0428 | 0.5980 | 0.688 | 0.0265 | 0.4748 | 0.625 |
| 20 | 0.0215 | 0.0494 | 0.4363 | 0.667 | 0.0216 | 0.3480 | 0.646 |
| 40 | 0.0253 | 0.0522 | 0.4839 | 0.688 | 0.0235 | 0.3594 | 0.625 |
| 60 | 0.0221 | 0.0581 | 0.3803 | 0.667 | 0.0195 | 0.2653 | 0.583 |

quantile mean forward 20d returns: Q1: 0.00758  Q2: 0.00822  Q3: 0.01178  Q4: 0.01290  Q5: 0.01541
Q5-Q1 long-short (gross, monthly): mean 0.00783, ann 0.0901, Sharpe 0.946, MDD -0.0958
top-quintile turnover: 0.687

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0261 | 0.613 | 0.750 |
| 2019 | 12 | 0.0423 | 0.695 | 0.667 |
| 2020 | 12 | 0.0072 | 0.089 | 0.500 |
| 2021 | 12 | 0.0106 | 0.209 | 0.667 |

regime split: up-market IC 0.0379 (n=28) / down-market IC -0.0012 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0296 | 0.0568 | 0.5214 | 0.792 | 0.0326 | 0.4821 | 0.729 |
| 5 | 0.0195 | 0.0437 | 0.4452 | 0.688 | 0.0200 | 0.3632 | 0.667 |
| 10 | 0.0261 | 0.0432 | 0.6026 | 0.667 | 0.0271 | 0.4907 | 0.646 |
| 20 | 0.0223 | 0.0500 | 0.4468 | 0.688 | 0.0218 | 0.3526 | 0.625 |
| 40 | 0.0245 | 0.0526 | 0.4667 | 0.708 | 0.0239 | 0.3719 | 0.625 |
| 60 | 0.0213 | 0.0569 | 0.3741 | 0.667 | 0.0192 | 0.2674 | 0.583 |

quantile mean forward 20d returns: Q1: 0.00752  Q2: 0.00826  Q3: 0.01144  Q4: 0.01319  Q5: 0.01547
Q5-Q1 long-short (gross, monthly): mean 0.00795, ann 0.0913, Sharpe 0.956, MDD -0.0976
top-quintile turnover: 0.689

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0270 | 0.632 | 0.750 |
| 2019 | 12 | 0.0438 | 0.723 | 0.667 |
| 2020 | 12 | 0.0075 | 0.093 | 0.500 |
| 2021 | 12 | 0.0090 | 0.182 | 0.583 |

regime split: up-market IC 0.0376 (n=28) / down-market IC -0.0004 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.455
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0144 | 0.0736 | 0.1951 | 0.625 | 0.0185 | 0.2183 | 0.625 |
| 5 | 0.0025 | 0.0765 | 0.0333 | 0.417 | 0.0088 | 0.1032 | 0.458 |
| 10 | 0.0114 | 0.0695 | 0.1636 | 0.542 | 0.0165 | 0.1990 | 0.500 |
| 20 | 0.0201 | 0.0776 | 0.2595 | 0.542 | 0.0275 | 0.3076 | 0.625 |
| 40 | 0.0028 | 0.0670 | 0.0425 | 0.542 | 0.0085 | 0.1029 | 0.500 |
| 60 | 0.0073 | 0.0603 | 0.1202 | 0.583 | 0.0125 | 0.1651 | 0.500 |

quantile mean forward 20d returns: Q1: 0.00036  Q2: 0.00276  Q3: 0.00020  Q4: 0.00261  Q5: 0.00362
Q5-Q1 long-short (gross, monthly): mean 0.00326, ann 0.0472, Sharpe 0.360, MDD -0.1248
top-quintile turnover: 0.698

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0405 | 0.580 | 0.583 |
| 2023 | 12 | 0.0145 | 0.140 | 0.667 |

regime split: up-market IC 0.0422 (n=13) / down-market IC 0.0102 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0211 | 0.0689 | 0.3069 | 0.667 | 0.0231 | 0.2687 | 0.625 |
| 5 | 0.0113 | 0.0735 | 0.1533 | 0.542 | 0.0127 | 0.1465 | 0.500 |
| 10 | 0.0204 | 0.0663 | 0.3079 | 0.708 | 0.0196 | 0.2383 | 0.500 |
| 20 | 0.0283 | 0.0771 | 0.3676 | 0.667 | 0.0307 | 0.3380 | 0.667 |
| 40 | 0.0068 | 0.0689 | 0.0984 | 0.583 | 0.0091 | 0.1072 | 0.542 |
| 60 | 0.0097 | 0.0602 | 0.1618 | 0.583 | 0.0126 | 0.1647 | 0.500 |

quantile mean forward 20d returns: Q1: 0.00034  Q2: 0.00211  Q3: 0.00042  Q4: 0.00239  Q5: 0.00428
Q5-Q1 long-short (gross, monthly): mean 0.00395, ann 0.0560, Sharpe 0.408, MDD -0.1342
top-quintile turnover: 0.687

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0469 | 0.670 | 0.667 |
| 2023 | 12 | 0.0144 | 0.137 | 0.667 |

regime split: up-market IC 0.0475 (n=13) / down-market IC 0.0108 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.457
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0215 | 0.0490 | 0.4392 | 0.625 | 0.0276 | 0.4824 | 0.750 |
| 5 | 0.0171 | 0.0498 | 0.3438 | 0.583 | 0.0252 | 0.3749 | 0.667 |
| 10 | 0.0167 | 0.0508 | 0.3293 | 0.625 | 0.0270 | 0.4909 | 0.708 |
| 20 | 0.0107 | 0.0329 | 0.3242 | 0.708 | 0.0170 | 0.3750 | 0.708 |
| 40 | -0.0015 | 0.0243 | -0.0605 | 0.458 | 0.0010 | 0.0223 | 0.583 |
| 60 | -0.0094 | 0.0313 | -0.3002 | 0.458 | -0.0136 | -0.3035 | 0.375 |

quantile mean forward 20d returns: Q1: 0.02858  Q2: 0.03261  Q3: 0.03269  Q4: 0.03288  Q5: 0.03611
Q5-Q1 long-short (gross, monthly): mean 0.00753, ann 0.0717, Sharpe 0.763, MDD -0.0827
top-quintile turnover: 0.697

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0129 | 0.301 | 0.583 |
| 2025 | 12 | 0.0210 | 0.447 | 0.833 |

regime split: up-market IC 0.0213 (n=15) / down-market IC 0.0097 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0194 | 0.0468 | 0.4138 | 0.583 | 0.0271 | 0.4708 | 0.708 |
| 5 | 0.0163 | 0.0483 | 0.3378 | 0.667 | 0.0224 | 0.3323 | 0.625 |
| 10 | 0.0209 | 0.0432 | 0.4847 | 0.667 | 0.0240 | 0.4310 | 0.667 |
| 20 | 0.0128 | 0.0289 | 0.4427 | 0.708 | 0.0147 | 0.3150 | 0.667 |
| 40 | -0.0010 | 0.0229 | -0.0416 | 0.500 | -0.0010 | -0.0246 | 0.542 |
| 60 | -0.0089 | 0.0314 | -0.2848 | 0.458 | -0.0156 | -0.3569 | 0.292 |

quantile mean forward 20d returns: Q1: 0.02858  Q2: 0.03316  Q3: 0.03257  Q4: 0.03247  Q5: 0.03609
Q5-Q1 long-short (gross, monthly): mean 0.00751, ann 0.0715, Sharpe 0.759, MDD -0.0831
top-quintile turnover: 0.697

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0122 | 0.278 | 0.583 |
| 2025 | 12 | 0.0172 | 0.349 | 0.750 |

regime split: up-market IC 0.0213 (n=15) / down-market IC 0.0036 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`announcement_count_5d`: 0.960  `news_count_5d`: 0.960  `news_novelty_5d`: 0.958  `announcement_attention_5d`: 0.920  `news_attention_5d`: 0.920

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.