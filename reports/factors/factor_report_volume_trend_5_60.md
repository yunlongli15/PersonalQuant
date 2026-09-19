# factor_report_volume_trend_5_60.md

## definition

- factor: `volume_trend_5_60`  ·  category: volume  ·  version 1.0
- formula: `mean(volume,5d) / mean(volume,60d)`
- source: market  ·  PIT: True
- required fields: volume
- description: 短期/长期成交量之比（量能趋势，两窗口比值抵消源缩放）
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.998
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0135 | 0.0936 | 0.1442 | 0.500 | -0.0223 | -0.2146 | 0.375 |
| 5 | -0.0020 | 0.1071 | -0.0185 | 0.438 | -0.0340 | -0.2779 | 0.333 |
| 10 | -0.0099 | 0.0793 | -0.1252 | 0.396 | -0.0386 | -0.4064 | 0.292 |
| 20 | -0.0234 | 0.0729 | -0.3203 | 0.354 | -0.0473 | -0.5433 | 0.250 |
| 40 | -0.0201 | 0.0788 | -0.2552 | 0.333 | -0.0467 | -0.4936 | 0.292 |
| 60 | -0.0173 | 0.0705 | -0.2451 | 0.354 | -0.0406 | -0.4780 | 0.271 |

quantile mean forward 20d returns: Q1: 0.01243  Q2: 0.01257  Q3: 0.01378  Q4: 0.01299  Q5: 0.00395
Q5-Q1 long-short (gross, monthly): mean -0.00848, ann -0.0942, Sharpe -0.999, MDD -0.3316
top-quintile turnover: 0.781

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0552 | -1.003 | 0.167 |
| 2019 | 12 | -0.0642 | -1.395 | 0.167 |
| 2020 | 12 | 0.0059 | 0.053 | 0.333 |
| 2021 | 12 | -0.0756 | -0.809 | 0.333 |

regime split: up-market IC -0.0543 (n=28) / down-market IC -0.0374 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0192 | 0.1090 | 0.1765 | 0.542 | -0.0223 | -0.2144 | 0.375 |
| 5 | -0.0087 | 0.1184 | -0.0734 | 0.438 | -0.0340 | -0.2777 | 0.333 |
| 10 | -0.0194 | 0.0892 | -0.2178 | 0.333 | -0.0386 | -0.4062 | 0.292 |
| 20 | -0.0382 | 0.0726 | -0.5254 | 0.208 | -0.0472 | -0.5431 | 0.250 |
| 40 | -0.0328 | 0.0759 | -0.4326 | 0.250 | -0.0467 | -0.4934 | 0.292 |
| 60 | -0.0281 | 0.0642 | -0.4383 | 0.271 | -0.0406 | -0.4777 | 0.271 |

quantile mean forward 20d returns: Q1: 0.01243  Q2: 0.01258  Q3: 0.01376  Q4: 0.01299  Q5: 0.00396
Q5-Q1 long-short (gross, monthly): mean -0.00847, ann -0.0941, Sharpe -0.997, MDD -0.3312
top-quintile turnover: 0.781

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0551 | -1.003 | 0.167 |
| 2019 | 12 | -0.0642 | -1.394 | 0.167 |
| 2020 | 12 | 0.0059 | 0.053 | 0.333 |
| 2021 | 12 | -0.0755 | -0.808 | 0.333 |

regime split: up-market IC -0.0543 (n=28) / down-market IC -0.0374 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0141 | 0.0900 | -0.1566 | 0.417 | -0.0404 | -0.4081 | 0.333 |
| 5 | -0.0126 | 0.0870 | -0.1449 | 0.458 | -0.0396 | -0.3768 | 0.375 |
| 10 | -0.0237 | 0.0744 | -0.3184 | 0.417 | -0.0471 | -0.5372 | 0.250 |
| 20 | -0.0203 | 0.0865 | -0.2346 | 0.458 | -0.0432 | -0.4555 | 0.333 |
| 40 | -0.0353 | 0.0796 | -0.4432 | 0.375 | -0.0622 | -0.6812 | 0.292 |
| 60 | -0.0387 | 0.0691 | -0.5604 | 0.333 | -0.0657 | -0.7954 | 0.292 |

quantile mean forward 20d returns: Q1: 0.00451  Q2: 0.00323  Q3: 0.00765  Q4: 0.00287  Q5: -0.00371
Q5-Q1 long-short (gross, monthly): mean -0.00822, ann -0.1067, Sharpe -1.100, MDD -0.2114
top-quintile turnover: 0.829

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0693 | -0.666 | 0.250 |
| 2023 | 12 | -0.0171 | -0.224 | 0.417 |

regime split: up-market IC -0.0721 (n=13) / down-market IC -0.0090 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0157 | 0.1033 | -0.1519 | 0.417 | -0.0404 | -0.4081 | 0.333 |
| 5 | -0.0166 | 0.0972 | -0.1713 | 0.458 | -0.0396 | -0.3764 | 0.375 |
| 10 | -0.0338 | 0.0815 | -0.4151 | 0.333 | -0.0471 | -0.5368 | 0.250 |
| 20 | -0.0303 | 0.0917 | -0.3303 | 0.333 | -0.0431 | -0.4550 | 0.333 |
| 40 | -0.0476 | 0.0819 | -0.5816 | 0.250 | -0.0622 | -0.6806 | 0.292 |
| 60 | -0.0518 | 0.0671 | -0.7714 | 0.250 | -0.0657 | -0.7950 | 0.292 |

quantile mean forward 20d returns: Q1: 0.00451  Q2: 0.00323  Q3: 0.00765  Q4: 0.00285  Q5: -0.00369
Q5-Q1 long-short (gross, monthly): mean -0.00820, ann -0.1065, Sharpe -1.097, MDD -0.2114
top-quintile turnover: 0.829

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0692 | -0.666 | 0.250 |
| 2023 | 12 | -0.0170 | -0.224 | 0.417 |

regime split: up-market IC -0.0720 (n=13) / down-market IC -0.0090 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0079 | 0.0931 | -0.0854 | 0.458 | -0.0358 | -0.3122 | 0.375 |
| 5 | -0.0106 | 0.1013 | -0.1043 | 0.375 | -0.0453 | -0.3530 | 0.292 |
| 10 | -0.0194 | 0.0861 | -0.2252 | 0.375 | -0.0575 | -0.5281 | 0.333 |
| 20 | -0.0254 | 0.0683 | -0.3714 | 0.333 | -0.0597 | -0.6653 | 0.250 |
| 40 | -0.0241 | 0.0665 | -0.3622 | 0.375 | -0.0545 | -0.6256 | 0.208 |
| 60 | -0.0272 | 0.0506 | -0.5376 | 0.333 | -0.0583 | -0.8568 | 0.208 |

quantile mean forward 20d returns: Q1: 0.03587  Q2: 0.03482  Q3: 0.04231  Q4: 0.03278  Q5: 0.02494
Q5-Q1 long-short (gross, monthly): mean -0.01093, ann -0.1065, Sharpe -1.249, MDD -0.2017
top-quintile turnover: 0.844

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0700 | -0.948 | 0.167 |
| 2025 | 12 | -0.0493 | -0.483 | 0.333 |

regime split: up-market IC -0.0894 (n=15) / down-market IC -0.0102 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0130 | 0.0931 | -0.1399 | 0.417 | -0.0358 | -0.3122 | 0.375 |
| 5 | -0.0204 | 0.0933 | -0.2191 | 0.333 | -0.0453 | -0.3529 | 0.292 |
| 10 | -0.0295 | 0.0928 | -0.3179 | 0.333 | -0.0575 | -0.5280 | 0.333 |
| 20 | -0.0394 | 0.0726 | -0.5421 | 0.292 | -0.0596 | -0.6648 | 0.250 |
| 40 | -0.0366 | 0.0667 | -0.5486 | 0.292 | -0.0545 | -0.6251 | 0.208 |
| 60 | -0.0424 | 0.0486 | -0.8732 | 0.208 | -0.0583 | -0.8561 | 0.208 |

quantile mean forward 20d returns: Q1: 0.03587  Q2: 0.03482  Q3: 0.04231  Q4: 0.03278  Q5: 0.02494
Q5-Q1 long-short (gross, monthly): mean -0.01094, ann -0.1066, Sharpe -1.250, MDD -0.2018
top-quintile turnover: 0.844

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0700 | -0.948 | 0.167 |
| 2025 | 12 | -0.0493 | -0.483 | 0.333 |

regime split: up-market IC -0.0894 (n=15) / down-market IC -0.0101 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`amount_share_20`: 0.478  `momentum_20`: 0.459  `max_return_20`: 0.372  `limit_up_count_20`: 0.295  `momentum_60`: 0.237

## redundancy cluster

cluster members: `volume_trend_5_60`

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.