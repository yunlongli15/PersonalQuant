# factor_report_earnings_yield.md

## definition

- factor: `earnings_yield`  ·  category: valuation  ·  version 1.0
- formula: `eps_latest_annual / close`
- source: financial  ·  PIT: True
- required fields: close, eps
- description: inverse of PE (EPS/price) on the latest PIT annual report
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.020
- empirical direction: positive

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0264 | 0.2214 | -0.1191 | 0.467 | -0.0218 | -0.0887 | 0.467 |
| 5 | -0.0290 | 0.2253 | -0.1289 | 0.467 | -0.0044 | -0.0168 | 0.422 |
| 10 | -0.0236 | 0.2367 | -0.0995 | 0.467 | 0.0052 | 0.0211 | 0.556 |
| 20 | -0.0219 | 0.2293 | -0.0954 | 0.489 | 0.0213 | 0.0889 | 0.511 |
| 40 | -0.0403 | 0.2226 | -0.1809 | 0.444 | 0.0089 | 0.0398 | 0.489 |
| 60 | -0.0648 | 0.2299 | -0.2817 | 0.356 | -0.0045 | -0.0188 | 0.444 |

quantile mean forward 20d returns: Q1: 0.01566  Q2: 0.01460  Q3: 0.01341  Q4: 0.01703  Q5: 0.00527
Q5-Q1 long-short (gross, monthly): mean -0.01039, ann -0.1463, Sharpe -0.665, MDD -0.6131
top-quintile turnover: 0.117

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 9 | 0.0479 | 0.394 | 0.556 |
| 2019 | 12 | -0.0649 | -0.240 | 0.417 |
| 2020 | 12 | -0.0152 | -0.078 | 0.500 |
| 2021 | 12 | 0.1241 | 0.458 | 0.583 |

regime split: up-market IC -0.0138 (n=27) / down-market IC 0.0740 (n=18)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0318 | 0.2051 | -0.1550 | 0.422 | -0.0218 | -0.0887 | 0.467 |
| 5 | -0.0289 | 0.2051 | -0.1409 | 0.444 | -0.0044 | -0.0168 | 0.422 |
| 10 | -0.0353 | 0.2106 | -0.1677 | 0.422 | 0.0052 | 0.0211 | 0.556 |
| 20 | -0.0348 | 0.2056 | -0.1692 | 0.400 | 0.0213 | 0.0888 | 0.511 |
| 40 | -0.0522 | 0.1970 | -0.2651 | 0.467 | 0.0089 | 0.0398 | 0.489 |
| 60 | -0.0744 | 0.2019 | -0.3687 | 0.333 | -0.0045 | -0.0188 | 0.444 |

quantile mean forward 20d returns: Q1: 0.01566  Q2: 0.01460  Q3: 0.01341  Q4: 0.01703  Q5: 0.00527
Q5-Q1 long-short (gross, monthly): mean -0.01039, ann -0.1463, Sharpe -0.665, MDD -0.6131
top-quintile turnover: 0.117

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 9 | 0.0479 | 0.394 | 0.556 |
| 2019 | 12 | -0.0649 | -0.240 | 0.417 |
| 2020 | 12 | -0.0152 | -0.078 | 0.500 |
| 2021 | 12 | 0.1241 | 0.457 | 0.583 |

regime split: up-market IC -0.0138 (n=27) / down-market IC 0.0740 (n=18)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.018
- empirical direction: positive

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0270 | 0.1463 | 0.1846 | 0.542 | 0.0434 | 0.2662 | 0.708 |
| 5 | 0.0404 | 0.2320 | 0.1741 | 0.625 | 0.0622 | 0.2448 | 0.458 |
| 10 | 0.0481 | 0.2029 | 0.2371 | 0.542 | 0.0815 | 0.3980 | 0.667 |
| 20 | 0.0508 | 0.2680 | 0.1894 | 0.500 | 0.0876 | 0.3261 | 0.583 |
| 40 | 0.0705 | 0.2737 | 0.2577 | 0.625 | 0.0995 | 0.3581 | 0.708 |
| 60 | 0.0879 | 0.2456 | 0.3579 | 0.667 | 0.1210 | 0.4580 | 0.625 |

quantile mean forward 20d returns: Q1: -0.00057  Q2: 0.00057  Q3: 0.00338  Q4: 0.00806  Q5: 0.00937
Q5-Q1 long-short (gross, monthly): mean 0.00994, ann 0.1111, Sharpe 0.485, MDD -0.3319
top-quintile turnover: 0.114

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0260 | 0.088 | 0.333 |
| 2023 | 12 | 0.1492 | 0.678 | 0.833 |

regime split: up-market IC -0.0418 (n=13) / down-market IC 0.2405 (n=11)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0099 | 0.1301 | 0.0760 | 0.500 | 0.0434 | 0.2663 | 0.708 |
| 5 | 0.0159 | 0.2080 | 0.0765 | 0.458 | 0.0622 | 0.2448 | 0.458 |
| 10 | 0.0229 | 0.1810 | 0.1268 | 0.542 | 0.0815 | 0.3980 | 0.667 |
| 20 | 0.0352 | 0.2392 | 0.1470 | 0.500 | 0.0876 | 0.3261 | 0.583 |
| 40 | 0.0573 | 0.2298 | 0.2493 | 0.625 | 0.0995 | 0.3580 | 0.708 |
| 60 | 0.0594 | 0.2043 | 0.2907 | 0.667 | 0.1210 | 0.4580 | 0.625 |

quantile mean forward 20d returns: Q1: -0.00057  Q2: 0.00057  Q3: 0.00338  Q4: 0.00806  Q5: 0.00937
Q5-Q1 long-short (gross, monthly): mean 0.00994, ann 0.1111, Sharpe 0.485, MDD -0.3319
top-quintile turnover: 0.114

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0260 | 0.088 | 0.333 |
| 2023 | 12 | 0.1492 | 0.678 | 0.833 |

regime split: up-market IC -0.0418 (n=13) / down-market IC 0.2405 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.017
- empirical direction: positive

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0525 | 0.2279 | -0.2305 | 0.417 | -0.0289 | -0.1119 | 0.458 |
| 5 | 0.0079 | 0.2051 | 0.0383 | 0.667 | 0.0356 | 0.1620 | 0.625 |
| 10 | -0.0093 | 0.2344 | -0.0397 | 0.375 | 0.0128 | 0.0524 | 0.500 |
| 20 | -0.0312 | 0.2568 | -0.1214 | 0.458 | 0.0045 | 0.0168 | 0.458 |
| 40 | -0.0533 | 0.2424 | -0.2199 | 0.417 | -0.0039 | -0.0150 | 0.500 |
| 60 | -0.0745 | 0.2129 | -0.3500 | 0.333 | -0.0213 | -0.0961 | 0.500 |

quantile mean forward 20d returns: Q1: 0.04251  Q2: 0.02815  Q3: 0.02873  Q4: 0.02183  Q5: 0.02023
Q5-Q1 long-short (gross, monthly): mean -0.02228, ann -0.2513, Sharpe -0.944, MDD -0.5340
top-quintile turnover: 0.098

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0395 | 0.179 | 0.500 |
| 2025 | 12 | -0.0306 | -0.103 | 0.417 |

regime split: up-market IC -0.1085 (n=15) / down-market IC 0.1926 (n=9)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0440 | 0.1769 | -0.2489 | 0.417 | -0.0289 | -0.1119 | 0.458 |
| 5 | 0.0022 | 0.1579 | 0.0142 | 0.583 | 0.0356 | 0.1620 | 0.625 |
| 10 | 0.0012 | 0.2004 | 0.0062 | 0.417 | 0.0128 | 0.0524 | 0.500 |
| 20 | -0.0389 | 0.2155 | -0.1805 | 0.458 | 0.0045 | 0.0168 | 0.458 |
| 40 | -0.0597 | 0.2125 | -0.2810 | 0.333 | -0.0039 | -0.0150 | 0.500 |
| 60 | -0.0670 | 0.1888 | -0.3550 | 0.333 | -0.0213 | -0.0961 | 0.500 |

quantile mean forward 20d returns: Q1: 0.04251  Q2: 0.02815  Q3: 0.02873  Q4: 0.02183  Q5: 0.02023
Q5-Q1 long-short (gross, monthly): mean -0.02228, ann -0.2513, Sharpe -0.944, MDD -0.5340
top-quintile turnover: 0.098

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0395 | 0.179 | 0.500 |
| 2025 | 12 | -0.0306 | -0.103 | 0.417 |

regime split: up-market IC -0.1085 (n=15) / down-market IC 0.1926 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`downside_volatility_60`: -0.526  `max_return_20`: -0.412  `net_margin`: 0.358  `gross_margin`: 0.228  `momentum_120`: -0.203

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.