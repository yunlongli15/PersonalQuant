# factor_report_net_margin.md

## definition

- factor: `net_margin`  ·  category: quality  ·  version 1.0
- formula: `net_profit/revenue`
- source: financial  ·  PIT: True
- required fields: net_profit, revenue
- description: net margin, latest PIT annual report
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.023
- empirical direction: positive

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0093 | 0.1792 | 0.0516 | 0.478 | 0.0048 | 0.0245 | 0.522 |
| 5 | -0.0014 | 0.1492 | -0.0094 | 0.457 | 0.0168 | 0.1083 | 0.522 |
| 10 | -0.0072 | 0.1440 | -0.0498 | 0.413 | 0.0197 | 0.1180 | 0.543 |
| 20 | 0.0235 | 0.1401 | 0.1674 | 0.609 | 0.0509 | 0.3250 | 0.630 |
| 40 | 0.0058 | 0.1247 | 0.0468 | 0.543 | 0.0508 | 0.3478 | 0.652 |
| 60 | -0.0020 | 0.1158 | -0.0174 | 0.543 | 0.0474 | 0.3309 | 0.674 |

quantile mean forward 20d returns: Q1: 0.00732  Q2: 0.01884  Q3: 0.01087  Q4: 0.01966  Q5: 0.00803
Q5-Q1 long-short (gross, monthly): mean 0.00071, ann 0.0014, Sharpe 0.011, MDD -0.2257
top-quintile turnover: 0.064

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 10 | 0.0738 | 0.554 | 0.700 |
| 2019 | 12 | 0.0999 | 0.597 | 0.667 |
| 2020 | 12 | 0.0655 | 0.456 | 0.750 |
| 2021 | 12 | -0.0320 | -0.224 | 0.417 |

regime split: up-market IC 0.0292 (n=27) / down-market IC 0.0816 (n=19)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0005 | 0.0758 | -0.0063 | 0.435 | 0.0048 | 0.0245 | 0.522 |
| 5 | -0.0002 | 0.0654 | -0.0023 | 0.413 | 0.0168 | 0.1083 | 0.522 |
| 10 | -0.0030 | 0.0614 | -0.0490 | 0.391 | 0.0197 | 0.1180 | 0.543 |
| 20 | -0.0089 | 0.0682 | -0.1302 | 0.391 | 0.0509 | 0.3250 | 0.630 |
| 40 | -0.0096 | 0.0654 | -0.1468 | 0.391 | 0.0508 | 0.3478 | 0.652 |
| 60 | -0.0109 | 0.0599 | -0.1828 | 0.348 | 0.0474 | 0.3309 | 0.674 |

quantile mean forward 20d returns: Q1: 0.00732  Q2: 0.01884  Q3: 0.01087  Q4: 0.01966  Q5: 0.00803
Q5-Q1 long-short (gross, monthly): mean 0.00071, ann 0.0014, Sharpe 0.011, MDD -0.2257
top-quintile turnover: 0.064

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 10 | 0.0738 | 0.554 | 0.700 |
| 2019 | 12 | 0.0999 | 0.597 | 0.667 |
| 2020 | 12 | 0.0655 | 0.456 | 0.750 |
| 2021 | 12 | -0.0320 | -0.224 | 0.417 |

regime split: up-market IC 0.0292 (n=27) / down-market IC 0.0816 (n=19)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.021
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0640 | 0.1490 | -0.4293 | 0.292 | -0.0650 | -0.4247 | 0.333 |
| 5 | -0.0451 | 0.1718 | -0.2628 | 0.375 | -0.0360 | -0.1983 | 0.417 |
| 10 | -0.0236 | 0.1772 | -0.1331 | 0.417 | -0.0154 | -0.0884 | 0.500 |
| 20 | -0.0292 | 0.1623 | -0.1799 | 0.458 | -0.0123 | -0.0721 | 0.417 |
| 40 | -0.0213 | 0.1587 | -0.1340 | 0.375 | -0.0003 | -0.0017 | 0.417 |
| 60 | -0.0299 | 0.1628 | -0.1838 | 0.458 | -0.0023 | -0.0140 | 0.542 |

quantile mean forward 20d returns: Q1: 0.01344  Q2: 0.00863  Q3: 0.00329  Q4: -0.00074  Q5: 0.00110
Q5-Q1 long-short (gross, monthly): mean -0.01234, ann -0.1028, Sharpe -0.860, MDD -0.2825
top-quintile turnover: 0.046

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0548 | -0.298 | 0.333 |
| 2023 | 12 | 0.0302 | 0.209 | 0.500 |

regime split: up-market IC -0.0569 (n=13) / down-market IC 0.0404 (n=11)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0343 | 0.1029 | 0.3336 | 0.625 | -0.0650 | -0.4247 | 0.333 |
| 5 | 0.0282 | 0.1188 | 0.2372 | 0.583 | -0.0360 | -0.1983 | 0.417 |
| 10 | 0.0138 | 0.1133 | 0.1217 | 0.500 | -0.0154 | -0.0884 | 0.500 |
| 20 | 0.0019 | 0.0964 | 0.0195 | 0.500 | -0.0123 | -0.0721 | 0.417 |
| 40 | 0.0215 | 0.0970 | 0.2219 | 0.583 | -0.0003 | -0.0017 | 0.417 |
| 60 | 0.0305 | 0.0951 | 0.3212 | 0.583 | -0.0023 | -0.0140 | 0.542 |

quantile mean forward 20d returns: Q1: 0.01344  Q2: 0.00863  Q3: 0.00329  Q4: -0.00074  Q5: 0.00110
Q5-Q1 long-short (gross, monthly): mean -0.01234, ann -0.1028, Sharpe -0.860, MDD -0.2825
top-quintile turnover: 0.046

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0548 | -0.298 | 0.333 |
| 2023 | 12 | 0.0302 | 0.209 | 0.500 |

regime split: up-market IC -0.0569 (n=13) / down-market IC 0.0404 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.020
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0402 | 0.1532 | -0.2621 | 0.417 | -0.0382 | -0.2224 | 0.458 |
| 5 | -0.0206 | 0.1409 | -0.1460 | 0.333 | -0.0216 | -0.1460 | 0.417 |
| 10 | -0.0240 | 0.1268 | -0.1895 | 0.542 | 0.0016 | 0.0114 | 0.583 |
| 20 | -0.0330 | 0.1568 | -0.2106 | 0.417 | -0.0186 | -0.1051 | 0.500 |
| 40 | -0.0608 | 0.1776 | -0.3422 | 0.375 | -0.0415 | -0.2099 | 0.458 |
| 60 | -0.0684 | 0.1824 | -0.3749 | 0.333 | -0.0394 | -0.1922 | 0.417 |

quantile mean forward 20d returns: Q1: 0.03181  Q2: 0.04169  Q3: 0.02842  Q4: 0.02400  Q5: 0.01782
Q5-Q1 long-short (gross, monthly): mean -0.01399, ann -0.1617, Sharpe -1.065, MDD -0.3721
top-quintile turnover: 0.041

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0260 | 0.207 | 0.583 |
| 2025 | 12 | -0.0632 | -0.306 | 0.417 |

regime split: up-market IC -0.0927 (n=15) / down-market IC 0.1049 (n=9)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0151 | 0.1449 | -0.1040 | 0.542 | -0.0382 | -0.2224 | 0.458 |
| 5 | -0.0026 | 0.1262 | -0.0209 | 0.417 | -0.0216 | -0.1460 | 0.417 |
| 10 | -0.0035 | 0.1369 | -0.0256 | 0.542 | 0.0016 | 0.0114 | 0.583 |
| 20 | -0.0384 | 0.1548 | -0.2478 | 0.417 | -0.0186 | -0.1051 | 0.500 |
| 40 | -0.0631 | 0.1576 | -0.4005 | 0.375 | -0.0415 | -0.2099 | 0.458 |
| 60 | -0.0745 | 0.1543 | -0.4831 | 0.292 | -0.0394 | -0.1922 | 0.417 |

quantile mean forward 20d returns: Q1: 0.03181  Q2: 0.04169  Q3: 0.02842  Q4: 0.02400  Q5: 0.01782
Q5-Q1 long-short (gross, monthly): mean -0.01399, ann -0.1617, Sharpe -1.065, MDD -0.3721
top-quintile turnover: 0.041

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0260 | 0.207 | 0.583 |
| 2025 | 12 | -0.0632 | -0.306 | 0.417 |

regime split: up-market IC -0.0927 (n=15) / down-market IC 0.1049 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`roe`: 0.594  `gross_margin`: 0.583  `roa`: 0.366  `earnings_yield`: 0.358  `ocf_to_net_profit`: -0.312

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.