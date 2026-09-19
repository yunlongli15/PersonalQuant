# factor_report_skewness_60.md

## definition

- factor: `skewness_60`  ·  category: microstructure  ·  version 1.0
- formula: `skew(returns, 60d)`
- source: market  ·  PIT: True
- required fields: close, factor
- description: 收益偏度（负偏度溢价：高偏度股票后续较弱）
- declared (economic) direction: **negative**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0143 | 0.0506 | 0.2824 | 0.646 | -0.0014 | -0.0240 | 0.438 |
| 5 | -0.0010 | 0.0561 | -0.0171 | 0.458 | -0.0168 | -0.2510 | 0.312 |
| 10 | -0.0065 | 0.0580 | -0.1118 | 0.438 | -0.0195 | -0.2675 | 0.417 |
| 20 | -0.0179 | 0.0537 | -0.3333 | 0.312 | -0.0326 | -0.5015 | 0.333 |
| 40 | -0.0164 | 0.0432 | -0.3806 | 0.354 | -0.0323 | -0.5558 | 0.271 |
| 60 | -0.0166 | 0.0507 | -0.3266 | 0.333 | -0.0312 | -0.4625 | 0.271 |

quantile mean forward 20d returns: Q1: 0.01301  Q2: 0.01265  Q3: 0.01178  Q4: 0.00990  Q5: 0.00839
Q5-Q1 long-short (gross, monthly): mean -0.00462, ann -0.0537, Sharpe -0.832, MDD -0.2269
top-quintile turnover: 0.541

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0613 | -0.980 | 0.167 |
| 2019 | 12 | -0.0209 | -0.595 | 0.500 |
| 2020 | 12 | -0.0141 | -0.156 | 0.417 |
| 2021 | 12 | -0.0339 | -0.721 | 0.250 |

regime split: up-market IC -0.0373 (n=28) / down-market IC -0.0259 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0144 | 0.0496 | 0.2912 | 0.625 | -0.0014 | -0.0240 | 0.438 |
| 5 | -0.0014 | 0.0545 | -0.0254 | 0.458 | -0.0168 | -0.2510 | 0.312 |
| 10 | -0.0070 | 0.0558 | -0.1257 | 0.458 | -0.0195 | -0.2675 | 0.417 |
| 20 | -0.0185 | 0.0531 | -0.3479 | 0.333 | -0.0326 | -0.5016 | 0.333 |
| 40 | -0.0166 | 0.0435 | -0.3812 | 0.292 | -0.0323 | -0.5560 | 0.271 |
| 60 | -0.0159 | 0.0512 | -0.3116 | 0.396 | -0.0312 | -0.4626 | 0.271 |

quantile mean forward 20d returns: Q1: 0.01301  Q2: 0.01270  Q3: 0.01175  Q4: 0.00987  Q5: 0.00839
Q5-Q1 long-short (gross, monthly): mean -0.00462, ann -0.0537, Sharpe -0.832, MDD -0.2269
top-quintile turnover: 0.541

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0613 | -0.981 | 0.167 |
| 2019 | 12 | -0.0210 | -0.596 | 0.500 |
| 2020 | 12 | -0.0141 | -0.156 | 0.417 |
| 2021 | 12 | -0.0339 | -0.721 | 0.250 |

regime split: up-market IC -0.0373 (n=28) / down-market IC -0.0259 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0068 | 0.0429 | 0.1593 | 0.500 | -0.0093 | -0.1771 | 0.458 |
| 5 | 0.0079 | 0.0512 | 0.1546 | 0.542 | -0.0102 | -0.1634 | 0.375 |
| 10 | -0.0100 | 0.0559 | -0.1781 | 0.542 | -0.0319 | -0.4879 | 0.333 |
| 20 | -0.0214 | 0.0517 | -0.4140 | 0.375 | -0.0444 | -0.7316 | 0.167 |
| 40 | -0.0287 | 0.0442 | -0.6483 | 0.292 | -0.0504 | -1.0098 | 0.125 |
| 60 | -0.0326 | 0.0364 | -0.8958 | 0.208 | -0.0581 | -1.3947 | 0.125 |

quantile mean forward 20d returns: Q1: 0.00556  Q2: 0.00414  Q3: 0.00430  Q4: 0.00215  Q5: -0.00161
Q5-Q1 long-short (gross, monthly): mean -0.00717, ann -0.0754, Sharpe -1.312, MDD -0.1451
top-quintile turnover: 0.555

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0387 | -0.597 | 0.167 |
| 2023 | 12 | -0.0502 | -0.898 | 0.167 |

regime split: up-market IC -0.0296 (n=13) / down-market IC -0.0620 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0075 | 0.0438 | 0.1725 | 0.500 | -0.0093 | -0.1770 | 0.458 |
| 5 | 0.0072 | 0.0498 | 0.1454 | 0.542 | -0.0102 | -0.1634 | 0.375 |
| 10 | -0.0078 | 0.0543 | -0.1446 | 0.500 | -0.0319 | -0.4880 | 0.333 |
| 20 | -0.0200 | 0.0495 | -0.4043 | 0.333 | -0.0445 | -0.7318 | 0.167 |
| 40 | -0.0271 | 0.0430 | -0.6307 | 0.292 | -0.0505 | -1.0101 | 0.125 |
| 60 | -0.0307 | 0.0351 | -0.8732 | 0.208 | -0.0581 | -1.3949 | 0.125 |

quantile mean forward 20d returns: Q1: 0.00556  Q2: 0.00417  Q3: 0.00430  Q4: 0.00213  Q5: -0.00161
Q5-Q1 long-short (gross, monthly): mean -0.00717, ann -0.0754, Sharpe -1.312, MDD -0.1451
top-quintile turnover: 0.555

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0387 | -0.598 | 0.167 |
| 2023 | 12 | -0.0502 | -0.899 | 0.167 |

regime split: up-market IC -0.0296 (n=13) / down-market IC -0.0620 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0248 | 0.0931 | 0.2661 | 0.542 | 0.0123 | 0.1144 | 0.417 |
| 5 | -0.0025 | 0.0646 | -0.0387 | 0.417 | -0.0235 | -0.2969 | 0.292 |
| 10 | 0.0019 | 0.0841 | 0.0228 | 0.458 | -0.0171 | -0.1529 | 0.458 |
| 20 | -0.0185 | 0.0766 | -0.2414 | 0.458 | -0.0473 | -0.4529 | 0.333 |
| 40 | -0.0203 | 0.0549 | -0.3698 | 0.417 | -0.0483 | -0.5882 | 0.333 |
| 60 | -0.0286 | 0.0503 | -0.5686 | 0.292 | -0.0595 | -0.8100 | 0.167 |

quantile mean forward 20d returns: Q1: 0.03653  Q2: 0.03476  Q3: 0.03844  Q4: 0.02995  Q5: 0.03103
Q5-Q1 long-short (gross, monthly): mean -0.00550, ann -0.0939, Sharpe -0.856, MDD -0.1820
top-quintile turnover: 0.569

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0224 | -0.182 | 0.417 |
| 2025 | 12 | -0.0722 | -0.977 | 0.250 |

regime split: up-market IC -0.0567 (n=15) / down-market IC -0.0316 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0253 | 0.0914 | 0.2770 | 0.542 | 0.0123 | 0.1145 | 0.417 |
| 5 | -0.0012 | 0.0589 | -0.0203 | 0.375 | -0.0235 | -0.2968 | 0.292 |
| 10 | 0.0033 | 0.0829 | 0.0396 | 0.458 | -0.0171 | -0.1529 | 0.458 |
| 20 | -0.0155 | 0.0740 | -0.2100 | 0.458 | -0.0473 | -0.4529 | 0.333 |
| 40 | -0.0174 | 0.0518 | -0.3351 | 0.417 | -0.0483 | -0.5881 | 0.333 |
| 60 | -0.0264 | 0.0486 | -0.5419 | 0.250 | -0.0595 | -0.8099 | 0.167 |

quantile mean forward 20d returns: Q1: 0.03653  Q2: 0.03476  Q3: 0.03844  Q4: 0.02995  Q5: 0.03103
Q5-Q1 long-short (gross, monthly): mean -0.00550, ann -0.0939, Sharpe -0.856, MDD -0.1820
top-quintile turnover: 0.569

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0224 | -0.182 | 0.417 |
| 2025 | 12 | -0.0722 | -0.977 | 0.250 |

regime split: up-market IC -0.0567 (n=15) / down-market IC -0.0316 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`max_return_20`: 0.308  `limit_up_count_20`: 0.301  `momentum_60`: 0.285  `kurtosis_60`: 0.192  `momentum_120`: 0.172

## redundancy cluster

cluster members: `skewness_60`

## interpretation & limitations

- declared direction `negative` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.