# factor_report_pe.md

## definition

- factor: `pe`  ·  category: valuation  ·  version 1.0
- formula: `close / eps_latest_annual (eps=基本每股收益; negative EPS kept)`
- source: financial  ·  PIT: True
- required fields: close, eps
- description: price-to-earnings on the latest PIT annual report
- declared (economic) direction: **negative**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.020
- empirical direction: negative

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0180 | 0.2178 | 0.0828 | 0.511 | 0.0159 | 0.0663 | 0.533 |
| 5 | 0.0252 | 0.2039 | 0.1236 | 0.556 | 0.0010 | 0.0040 | 0.578 |
| 10 | 0.0085 | 0.2113 | 0.0401 | 0.489 | -0.0196 | -0.0860 | 0.422 |
| 20 | 0.0050 | 0.2145 | 0.0234 | 0.489 | -0.0353 | -0.1563 | 0.444 |
| 40 | 0.0156 | 0.2117 | 0.0737 | 0.556 | -0.0255 | -0.1156 | 0.489 |
| 60 | 0.0323 | 0.2207 | 0.1462 | 0.622 | -0.0211 | -0.0905 | 0.533 |

quantile mean forward 20d returns: Q1: 0.00914  Q2: 0.01500  Q3: 0.01365  Q4: 0.01434  Q5: 0.01376
Q5-Q1 long-short (gross, monthly): mean 0.00462, ann 0.0437, Sharpe 0.214, MDD -0.2599
top-quintile turnover: 0.193

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 9 | -0.0552 | -0.656 | 0.222 |
| 2019 | 12 | 0.0222 | 0.089 | 0.583 |
| 2020 | 12 | 0.0108 | 0.057 | 0.500 |
| 2021 | 12 | -0.1241 | -0.458 | 0.417 |

regime split: up-market IC -0.0056 (n=27) / down-market IC -0.0800 (n=18)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0356 | 0.1935 | 0.1840 | 0.533 | 0.0159 | 0.0662 | 0.533 |
| 5 | 0.0315 | 0.1853 | 0.1702 | 0.444 | 0.0009 | 0.0039 | 0.578 |
| 10 | 0.0237 | 0.1980 | 0.1197 | 0.489 | -0.0196 | -0.0861 | 0.422 |
| 20 | 0.0124 | 0.1938 | 0.0638 | 0.556 | -0.0354 | -0.1565 | 0.444 |
| 40 | 0.0257 | 0.1726 | 0.1491 | 0.511 | -0.0255 | -0.1159 | 0.489 |
| 60 | 0.0506 | 0.1582 | 0.3200 | 0.644 | -0.0212 | -0.0908 | 0.533 |

quantile mean forward 20d returns: Q1: 0.00914  Q2: 0.01500  Q3: 0.01365  Q4: 0.01434  Q5: 0.01376
Q5-Q1 long-short (gross, monthly): mean 0.00462, ann 0.0437, Sharpe 0.214, MDD -0.2599
top-quintile turnover: 0.193

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 9 | -0.0552 | -0.656 | 0.222 |
| 2019 | 12 | 0.0220 | 0.088 | 0.583 |
| 2020 | 12 | 0.0108 | 0.057 | 0.500 |
| 2021 | 12 | -0.1241 | -0.457 | 0.417 |

regime split: up-market IC -0.0056 (n=27) / down-market IC -0.0800 (n=18)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.018
- empirical direction: negative

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0201 | 0.1486 | -0.1351 | 0.458 | -0.0304 | -0.1877 | 0.417 |
| 5 | -0.0517 | 0.2247 | -0.2301 | 0.458 | -0.0666 | -0.2681 | 0.500 |
| 10 | -0.0651 | 0.1914 | -0.3402 | 0.458 | -0.0765 | -0.4045 | 0.333 |
| 20 | -0.0570 | 0.2321 | -0.2456 | 0.458 | -0.0742 | -0.3188 | 0.375 |
| 40 | -0.0632 | 0.2392 | -0.2643 | 0.375 | -0.0814 | -0.3304 | 0.292 |
| 60 | -0.0860 | 0.2149 | -0.4002 | 0.375 | -0.1053 | -0.4327 | 0.375 |

quantile mean forward 20d returns: Q1: 0.01012  Q2: 0.00985  Q3: 0.00407  Q4: -0.00079  Q5: -0.00297
Q5-Q1 long-short (gross, monthly): mean -0.01309, ann -0.1717, Sharpe -0.919, MDD -0.3190
top-quintile turnover: 0.134

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0338 | -0.133 | 0.500 |
| 2023 | 12 | -0.1145 | -0.567 | 0.250 |

regime split: up-market IC 0.0238 (n=13) / down-market IC -0.1899 (n=11)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0006 | 0.1202 | -0.0050 | 0.458 | -0.0304 | -0.1878 | 0.417 |
| 5 | -0.0265 | 0.1467 | -0.1808 | 0.417 | -0.0666 | -0.2682 | 0.500 |
| 10 | -0.0282 | 0.1593 | -0.1771 | 0.417 | -0.0765 | -0.4051 | 0.333 |
| 20 | -0.0087 | 0.1761 | -0.0497 | 0.583 | -0.0741 | -0.3187 | 0.375 |
| 40 | -0.0100 | 0.1748 | -0.0572 | 0.500 | -0.0814 | -0.3306 | 0.292 |
| 60 | -0.0292 | 0.1670 | -0.1748 | 0.500 | -0.1054 | -0.4329 | 0.375 |

quantile mean forward 20d returns: Q1: 0.01012  Q2: 0.00985  Q3: 0.00407  Q4: -0.00079  Q5: -0.00297
Q5-Q1 long-short (gross, monthly): mean -0.01309, ann -0.1717, Sharpe -0.919, MDD -0.3190
top-quintile turnover: 0.134

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0338 | -0.133 | 0.500 |
| 2023 | 12 | -0.1145 | -0.567 | 0.250 |

regime split: up-market IC 0.0238 (n=13) / down-market IC -0.1899 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.017
- empirical direction: negative

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0430 | 0.2210 | 0.1945 | 0.583 | 0.0249 | 0.0985 | 0.583 |
| 5 | -0.0118 | 0.2074 | -0.0570 | 0.500 | -0.0446 | -0.1874 | 0.458 |
| 10 | 0.0075 | 0.2299 | 0.0325 | 0.458 | -0.0112 | -0.0445 | 0.458 |
| 20 | 0.0413 | 0.2378 | 0.1737 | 0.625 | -0.0004 | -0.0018 | 0.542 |
| 40 | 0.0201 | 0.2111 | 0.0950 | 0.500 | -0.0071 | -0.0320 | 0.500 |
| 60 | 0.0239 | 0.1705 | 0.1400 | 0.458 | -0.0068 | -0.0370 | 0.375 |

quantile mean forward 20d returns: Q1: 0.01990  Q2: 0.02314  Q3: 0.03069  Q4: 0.02396  Q5: 0.04423
Q5-Q1 long-short (gross, monthly): mean 0.02432, ann 0.2533, Sharpe 1.081, MDD -0.1910
top-quintile turnover: 0.131

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0026 | -0.013 | 0.500 |
| 2025 | 12 | 0.0018 | 0.006 | 0.583 |

regime split: up-market IC 0.0848 (n=15) / down-market IC -0.1424 (n=9)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0442 | 0.1700 | 0.2597 | 0.625 | 0.0248 | 0.0982 | 0.583 |
| 5 | 0.0176 | 0.1627 | 0.1084 | 0.542 | -0.0445 | -0.1872 | 0.458 |
| 10 | 0.0461 | 0.1356 | 0.3400 | 0.625 | -0.0112 | -0.0443 | 0.458 |
| 20 | 0.0725 | 0.1783 | 0.4069 | 0.708 | -0.0004 | -0.0016 | 0.542 |
| 40 | 0.0612 | 0.1697 | 0.3604 | 0.625 | -0.0071 | -0.0319 | 0.500 |
| 60 | 0.0689 | 0.1618 | 0.4256 | 0.708 | -0.0069 | -0.0372 | 0.375 |

quantile mean forward 20d returns: Q1: 0.01990  Q2: 0.02314  Q3: 0.03069  Q4: 0.02396  Q5: 0.04423
Q5-Q1 long-short (gross, monthly): mean 0.02432, ann 0.2533, Sharpe 1.081, MDD -0.1910
top-quintile turnover: 0.131

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0026 | -0.014 | 0.500 |
| 2025 | 12 | 0.0019 | 0.007 | 0.583 |

regime split: up-market IC 0.0848 (n=15) / down-market IC -0.1423 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`earnings_yield`: -0.938  `downside_volatility_60`: 0.497  `max_return_20`: 0.395  `net_margin`: -0.293  `momentum_120`: 0.187

## interpretation & limitations

- declared direction `negative` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.