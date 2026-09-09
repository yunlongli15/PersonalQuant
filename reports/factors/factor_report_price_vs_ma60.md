# factor_report_price_vs_ma60.md

## definition

- factor: `price_vs_ma60`  ·  category: price_position  ·  version 1.0
- formula: `adj_close/MA(adj_close,60)-1`
- source: market  ·  PIT: True
- required fields: close, factor
- description: close relative to its 60-day moving average
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.969
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0049 | 0.1388 | -0.0356 | 0.500 | -0.0439 | -0.2802 | 0.417 |
| 5 | -0.0265 | 0.1492 | -0.1773 | 0.396 | -0.0644 | -0.3561 | 0.354 |
| 10 | -0.0211 | 0.1132 | -0.1862 | 0.396 | -0.0556 | -0.3777 | 0.354 |
| 20 | -0.0345 | 0.1194 | -0.2886 | 0.438 | -0.0652 | -0.4547 | 0.333 |
| 40 | -0.0257 | 0.1032 | -0.2495 | 0.438 | -0.0586 | -0.4803 | 0.375 |
| 60 | -0.0145 | 0.0899 | -0.1613 | 0.479 | -0.0459 | -0.4281 | 0.354 |

quantile mean forward 20d returns: Q1: 0.01549  Q2: 0.01386  Q3: 0.01258  Q4: 0.01098  Q5: 0.00280
Q5-Q1 long-short (gross, monthly): mean -0.01268, ann -0.1472, Sharpe -0.861, MDD -0.4710
top-quintile turnover: 0.631

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0586 | -0.469 | 0.417 |
| 2019 | 12 | -0.0770 | -0.542 | 0.333 |
| 2020 | 12 | -0.0011 | -0.008 | 0.417 |
| 2021 | 12 | -0.1240 | -0.941 | 0.167 |

regime split: up-market IC -0.0932 (n=28) / down-market IC -0.0259 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0017 | 0.1482 | 0.0115 | 0.479 | -0.0439 | -0.2802 | 0.417 |
| 5 | -0.0307 | 0.1534 | -0.1999 | 0.438 | -0.0644 | -0.3561 | 0.354 |
| 10 | -0.0256 | 0.1152 | -0.2225 | 0.396 | -0.0556 | -0.3777 | 0.354 |
| 20 | -0.0409 | 0.1231 | -0.3322 | 0.396 | -0.0651 | -0.4545 | 0.333 |
| 40 | -0.0330 | 0.1041 | -0.3165 | 0.396 | -0.0586 | -0.4801 | 0.375 |
| 60 | -0.0194 | 0.0878 | -0.2215 | 0.479 | -0.0459 | -0.4280 | 0.354 |

quantile mean forward 20d returns: Q1: 0.01549  Q2: 0.01386  Q3: 0.01260  Q4: 0.01096  Q5: 0.00281
Q5-Q1 long-short (gross, monthly): mean -0.01268, ann -0.1471, Sharpe -0.861, MDD -0.4709
top-quintile turnover: 0.631

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0586 | -0.469 | 0.417 |
| 2019 | 12 | -0.0769 | -0.542 | 0.333 |
| 2020 | 12 | -0.0011 | -0.008 | 0.417 |
| 2021 | 12 | -0.1239 | -0.940 | 0.167 |

regime split: up-market IC -0.0932 (n=28) / down-market IC -0.0259 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.989
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0082 | 0.1337 | -0.0617 | 0.458 | -0.0297 | -0.1887 | 0.375 |
| 5 | -0.0239 | 0.1386 | -0.1723 | 0.458 | -0.0579 | -0.3465 | 0.375 |
| 10 | -0.0308 | 0.1078 | -0.2861 | 0.417 | -0.0591 | -0.4399 | 0.375 |
| 20 | -0.0316 | 0.1359 | -0.2326 | 0.500 | -0.0628 | -0.4047 | 0.333 |
| 40 | -0.0494 | 0.1383 | -0.3569 | 0.375 | -0.0808 | -0.5078 | 0.250 |
| 60 | -0.0468 | 0.1195 | -0.3916 | 0.292 | -0.0763 | -0.5311 | 0.250 |

quantile mean forward 20d returns: Q1: 0.00263  Q2: 0.00604  Q3: 0.00930  Q4: 0.00648  Q5: -0.00989
Q5-Q1 long-short (gross, monthly): mean -0.01252, ann -0.1604, Sharpe -1.020, MDD -0.3384
top-quintile turnover: 0.693

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.1079 | -0.637 | 0.333 |
| 2023 | 12 | -0.0177 | -0.142 | 0.333 |

regime split: up-market IC -0.1360 (n=13) / down-market IC 0.0238 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0103 | 0.1439 | -0.0715 | 0.417 | -0.0297 | -0.1887 | 0.375 |
| 5 | -0.0331 | 0.1392 | -0.2380 | 0.375 | -0.0579 | -0.3465 | 0.375 |
| 10 | -0.0481 | 0.1075 | -0.4476 | 0.375 | -0.0591 | -0.4398 | 0.375 |
| 20 | -0.0489 | 0.1385 | -0.3531 | 0.375 | -0.0628 | -0.4046 | 0.333 |
| 40 | -0.0643 | 0.1423 | -0.4519 | 0.292 | -0.0808 | -0.5078 | 0.250 |
| 60 | -0.0644 | 0.1215 | -0.5301 | 0.250 | -0.0763 | -0.5310 | 0.250 |

quantile mean forward 20d returns: Q1: 0.00263  Q2: 0.00604  Q3: 0.00930  Q4: 0.00647  Q5: -0.00989
Q5-Q1 long-short (gross, monthly): mean -0.01252, ann -0.1603, Sharpe -1.020, MDD -0.3384
top-quintile turnover: 0.693

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.1079 | -0.637 | 0.333 |
| 2023 | 12 | -0.0177 | -0.142 | 0.333 |

regime split: up-market IC -0.1360 (n=13) / down-market IC 0.0238 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.988
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0002 | 0.1560 | -0.0014 | 0.542 | -0.0338 | -0.1813 | 0.375 |
| 5 | 0.0032 | 0.1326 | 0.0243 | 0.417 | -0.0351 | -0.2224 | 0.333 |
| 10 | -0.0032 | 0.1024 | -0.0313 | 0.500 | -0.0419 | -0.3056 | 0.333 |
| 20 | -0.0264 | 0.1007 | -0.2618 | 0.458 | -0.0739 | -0.5626 | 0.250 |
| 40 | -0.0150 | 0.0869 | -0.1732 | 0.375 | -0.0593 | -0.4945 | 0.250 |
| 60 | -0.0098 | 0.0789 | -0.1237 | 0.417 | -0.0539 | -0.5093 | 0.250 |

quantile mean forward 20d returns: Q1: 0.03681  Q2: 0.03387  Q3: 0.04167  Q4: 0.03248  Q5: 0.02591
Q5-Q1 long-short (gross, monthly): mean -0.01090, ann -0.1077, Sharpe -0.800, MDD -0.2207
top-quintile turnover: 0.683

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0598 | -0.382 | 0.333 |
| 2025 | 12 | -0.0881 | -0.899 | 0.167 |

regime split: up-market IC -0.1178 (n=15) / down-market IC -0.0009 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0045 | 0.1565 | -0.0286 | 0.500 | -0.0338 | -0.1813 | 0.375 |
| 5 | -0.0067 | 0.1400 | -0.0480 | 0.458 | -0.0351 | -0.2223 | 0.333 |
| 10 | -0.0131 | 0.1045 | -0.1256 | 0.500 | -0.0419 | -0.3056 | 0.333 |
| 20 | -0.0371 | 0.1027 | -0.3610 | 0.458 | -0.0739 | -0.5626 | 0.250 |
| 40 | -0.0249 | 0.0905 | -0.2751 | 0.417 | -0.0593 | -0.4945 | 0.250 |
| 60 | -0.0211 | 0.0858 | -0.2463 | 0.458 | -0.0539 | -0.5093 | 0.250 |

quantile mean forward 20d returns: Q1: 0.03681  Q2: 0.03388  Q3: 0.04165  Q4: 0.03250  Q5: 0.02589
Q5-Q1 long-short (gross, monthly): mean -0.01092, ann -0.1079, Sharpe -0.801, MDD -0.2207
top-quintile turnover: 0.682

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0598 | -0.382 | 0.333 |
| 2025 | 12 | -0.0881 | -0.899 | 0.167 |

regime split: up-market IC -0.1178 (n=15) / down-market IC -0.0009 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`price_vs_ma120`: 0.846  `momentum_60`: 0.809  `momentum_20`: 0.792  `reversal_20`: -0.792  `price_vs_ma20`: 0.700

## redundancy cluster

cluster members: `momentum_60`, `price_vs_ma120`, `price_vs_ma60`

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.