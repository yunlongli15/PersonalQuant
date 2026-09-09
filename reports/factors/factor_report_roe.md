# factor_report_roe.md

## definition

- factor: `roe`  ·  category: quality  ·  version 1.0
- formula: `disclosed ROE, fallback net_profit/net_assets (year-end)`
- source: financial  ·  PIT: True
- required fields: roe, net_profit, net_assets
- description: return on equity, latest PIT annual report
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.019
- empirical direction: positive

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0618 | 0.1795 | 0.3444 | 0.600 | 0.0535 | 0.2911 | 0.600 |
| 5 | 0.0427 | 0.1965 | 0.2175 | 0.578 | 0.0554 | 0.2819 | 0.689 |
| 10 | 0.0548 | 0.1721 | 0.3185 | 0.578 | 0.0736 | 0.4083 | 0.622 |
| 20 | 0.0654 | 0.1737 | 0.3766 | 0.622 | 0.0853 | 0.4737 | 0.667 |
| 40 | 0.0672 | 0.1862 | 0.3611 | 0.689 | 0.0906 | 0.4626 | 0.733 |
| 60 | 0.0660 | 0.1943 | 0.3394 | 0.689 | 0.0830 | 0.3782 | 0.711 |

quantile mean forward 20d returns: Q1: 0.01143  Q2: 0.00988  Q3: 0.01161  Q4: 0.01249  Q5: 0.02509
Q5-Q1 long-short (gross, monthly): mean 0.01366, ann 0.1404, Sharpe 0.761, MDD -0.3310
top-quintile turnover: 0.078

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 9 | 0.0674 | 0.296 | 0.556 |
| 2019 | 12 | 0.1496 | 0.957 | 0.833 |
| 2020 | 12 | 0.1677 | 1.456 | 0.917 |
| 2021 | 12 | -0.0479 | -0.377 | 0.333 |

regime split: up-market IC 0.0852 (n=27) / down-market IC 0.0855 (n=18)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0351 | 0.1071 | 0.3280 | 0.533 | 0.0535 | 0.2911 | 0.600 |
| 5 | 0.0239 | 0.0934 | 0.2556 | 0.556 | 0.0554 | 0.2819 | 0.689 |
| 10 | 0.0140 | 0.0867 | 0.1617 | 0.578 | 0.0736 | 0.4083 | 0.622 |
| 20 | 0.0074 | 0.0900 | 0.0820 | 0.400 | 0.0853 | 0.4737 | 0.667 |
| 40 | 0.0105 | 0.0954 | 0.1096 | 0.489 | 0.0906 | 0.4626 | 0.733 |
| 60 | 0.0097 | 0.0976 | 0.0991 | 0.422 | 0.0830 | 0.3782 | 0.711 |

quantile mean forward 20d returns: Q1: 0.01143  Q2: 0.00988  Q3: 0.01161  Q4: 0.01249  Q5: 0.02509
Q5-Q1 long-short (gross, monthly): mean 0.01366, ann 0.1404, Sharpe 0.761, MDD -0.3310
top-quintile turnover: 0.078

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 9 | 0.0674 | 0.296 | 0.556 |
| 2019 | 12 | 0.1496 | 0.957 | 0.833 |
| 2020 | 12 | 0.1677 | 1.456 | 0.917 |
| 2021 | 12 | -0.0479 | -0.377 | 0.333 |

regime split: up-market IC 0.0852 (n=27) / down-market IC 0.0855 (n=18)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.018
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0857 | 0.2040 | -0.4201 | 0.375 | -0.0707 | -0.3362 | 0.333 |
| 5 | -0.0950 | 0.2153 | -0.4411 | 0.375 | -0.0917 | -0.3908 | 0.417 |
| 10 | -0.0505 | 0.2111 | -0.2392 | 0.417 | -0.0305 | -0.1385 | 0.458 |
| 20 | -0.0403 | 0.1906 | -0.2113 | 0.417 | -0.0525 | -0.2381 | 0.458 |
| 40 | -0.0418 | 0.1927 | -0.2169 | 0.500 | -0.0485 | -0.2093 | 0.542 |
| 60 | -0.0433 | 0.1958 | -0.2213 | 0.458 | -0.0437 | -0.1883 | 0.542 |

quantile mean forward 20d returns: Q1: 0.00643  Q2: 0.00995  Q3: 0.01186  Q4: -0.00241  Q5: -0.00447
Q5-Q1 long-short (gross, monthly): mean -0.01090, ann -0.0959, Sharpe -0.580, MDD -0.2985
top-quintile turnover: 0.064

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0551 | -0.237 | 0.333 |
| 2023 | 12 | -0.0500 | -0.240 | 0.583 |

regime split: up-market IC -0.0383 (n=13) / down-market IC -0.0693 (n=11)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0238 | 0.1404 | -0.1696 | 0.375 | -0.0707 | -0.3361 | 0.333 |
| 5 | -0.0483 | 0.1175 | -0.4116 | 0.292 | -0.0917 | -0.3908 | 0.417 |
| 10 | -0.0415 | 0.1164 | -0.3565 | 0.375 | -0.0305 | -0.1385 | 0.458 |
| 20 | -0.0379 | 0.1498 | -0.2528 | 0.458 | -0.0525 | -0.2381 | 0.458 |
| 40 | -0.0369 | 0.1539 | -0.2400 | 0.458 | -0.0485 | -0.2093 | 0.542 |
| 60 | -0.0345 | 0.1297 | -0.2658 | 0.458 | -0.0437 | -0.1884 | 0.542 |

quantile mean forward 20d returns: Q1: 0.00643  Q2: 0.00995  Q3: 0.01186  Q4: -0.00241  Q5: -0.00447
Q5-Q1 long-short (gross, monthly): mean -0.01090, ann -0.0959, Sharpe -0.580, MDD -0.2985
top-quintile turnover: 0.064

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0551 | -0.237 | 0.333 |
| 2023 | 12 | -0.0500 | -0.240 | 0.583 |

regime split: up-market IC -0.0383 (n=13) / down-market IC -0.0693 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.017
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0124 | 0.1491 | -0.0832 | 0.500 | -0.0103 | -0.0694 | 0.500 |
| 5 | -0.0108 | 0.1630 | -0.0663 | 0.375 | -0.0250 | -0.1656 | 0.333 |
| 10 | 0.0100 | 0.1422 | 0.0705 | 0.542 | 0.0182 | 0.1193 | 0.583 |
| 20 | -0.0271 | 0.1214 | -0.2231 | 0.417 | -0.0165 | -0.1189 | 0.458 |
| 40 | -0.0326 | 0.1256 | -0.2597 | 0.375 | -0.0184 | -0.1318 | 0.500 |
| 60 | -0.0439 | 0.1256 | -0.3497 | 0.375 | -0.0215 | -0.1683 | 0.458 |

quantile mean forward 20d returns: Q1: 0.03713  Q2: 0.02481  Q3: 0.03411  Q4: 0.03233  Q5: 0.02291
Q5-Q1 long-short (gross, monthly): mean -0.01422, ann -0.1668, Sharpe -1.224, MDD -0.3397
top-quintile turnover: 0.059

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0366 | -0.258 | 0.417 |
| 2025 | 12 | 0.0035 | 0.026 | 0.500 |

regime split: up-market IC -0.0401 (n=15) / down-market IC 0.0227 (n=9)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0304 | 0.1500 | -0.2029 | 0.500 | -0.0103 | -0.0695 | 0.500 |
| 5 | -0.0133 | 0.1746 | -0.0763 | 0.375 | -0.0250 | -0.1656 | 0.333 |
| 10 | -0.0079 | 0.1583 | -0.0498 | 0.500 | 0.0182 | 0.1194 | 0.583 |
| 20 | -0.0405 | 0.1332 | -0.3043 | 0.333 | -0.0166 | -0.1194 | 0.458 |
| 40 | -0.0650 | 0.1598 | -0.4070 | 0.292 | -0.0185 | -0.1319 | 0.500 |
| 60 | -0.0826 | 0.1647 | -0.5015 | 0.333 | -0.0216 | -0.1685 | 0.458 |

quantile mean forward 20d returns: Q1: 0.03713  Q2: 0.02481  Q3: 0.03411  Q4: 0.03233  Q5: 0.02291
Q5-Q1 long-short (gross, monthly): mean -0.01422, ann -0.1668, Sharpe -1.224, MDD -0.3397
top-quintile turnover: 0.059

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0367 | -0.259 | 0.417 |
| 2025 | 12 | 0.0034 | 0.026 | 0.500 |

regime split: up-market IC -0.0401 (n=15) / down-market IC 0.0226 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`roa`: 0.695  `net_margin`: 0.594  `gross_margin`: 0.473  `ocf_to_net_profit`: -0.432  `amount_20`: 0.340

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.