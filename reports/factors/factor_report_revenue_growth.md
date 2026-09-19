# factor_report_revenue_growth.md

## definition

- factor: `revenue_growth`  ·  category: growth  ·  version 1.0
- formula: `revenue[t]/revenue[t-1]-1 (same report, prior-year column)`
- source: financial  ·  PIT: True
- required fields: revenue
- description: annual revenue growth, latest PIT annual report
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.024
- empirical direction: positive

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0430 | 0.1204 | 0.3571 | 0.609 | 0.0439 | 0.3630 | 0.587 |
| 5 | 0.0288 | 0.1595 | 0.1805 | 0.565 | 0.0341 | 0.2065 | 0.543 |
| 10 | 0.0416 | 0.1613 | 0.2578 | 0.674 | 0.0375 | 0.2272 | 0.674 |
| 20 | 0.0325 | 0.1546 | 0.2101 | 0.652 | 0.0286 | 0.1905 | 0.630 |
| 40 | 0.0344 | 0.1829 | 0.1880 | 0.630 | 0.0297 | 0.1565 | 0.674 |
| 60 | 0.0384 | 0.2038 | 0.1885 | 0.696 | 0.0290 | 0.1398 | 0.630 |

quantile mean forward 20d returns: Q1: 0.01280  Q2: 0.00820  Q3: 0.00964  Q4: 0.01728  Q5: 0.01577
Q5-Q1 long-short (gross, monthly): mean 0.00297, ann 0.0269, Sharpe 0.216, MDD -0.1915
top-quintile turnover: 0.119

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 10 | -0.0164 | -0.073 | 0.400 |
| 2019 | 12 | 0.1033 | 1.131 | 0.917 |
| 2020 | 12 | 0.0685 | 0.695 | 0.750 |
| 2021 | 12 | -0.0486 | -0.445 | 0.417 |

regime split: up-market IC 0.0480 (n=27) / down-market IC 0.0009 (n=19)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0203 | 0.1269 | 0.1601 | 0.500 | 0.0438 | 0.3629 | 0.587 |
| 5 | 0.0120 | 0.1523 | 0.0787 | 0.522 | 0.0341 | 0.2064 | 0.543 |
| 10 | 0.0192 | 0.1538 | 0.1245 | 0.522 | 0.0375 | 0.2272 | 0.674 |
| 20 | 0.0067 | 0.1431 | 0.0465 | 0.457 | 0.0286 | 0.1905 | 0.630 |
| 40 | 0.0055 | 0.1517 | 0.0361 | 0.543 | 0.0297 | 0.1565 | 0.674 |
| 60 | 0.0098 | 0.1710 | 0.0575 | 0.543 | 0.0289 | 0.1398 | 0.630 |

quantile mean forward 20d returns: Q1: 0.01280  Q2: 0.00820  Q3: 0.00964  Q4: 0.01728  Q5: 0.01577
Q5-Q1 long-short (gross, monthly): mean 0.00297, ann 0.0269, Sharpe 0.216, MDD -0.1915
top-quintile turnover: 0.119

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 10 | -0.0164 | -0.073 | 0.400 |
| 2019 | 12 | 0.1033 | 1.131 | 0.917 |
| 2020 | 12 | 0.0685 | 0.695 | 0.750 |
| 2021 | 12 | -0.0486 | -0.445 | 0.417 |

regime split: up-market IC 0.0480 (n=27) / down-market IC 0.0009 (n=19)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.021
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0084 | 0.1060 | 0.0795 | 0.542 | 0.0124 | 0.1194 | 0.542 |
| 5 | -0.0089 | 0.1240 | -0.0719 | 0.417 | -0.0027 | -0.0196 | 0.375 |
| 10 | 0.0106 | 0.1296 | 0.0815 | 0.500 | 0.0193 | 0.1539 | 0.542 |
| 20 | -0.0180 | 0.1076 | -0.1673 | 0.417 | -0.0155 | -0.1232 | 0.500 |
| 40 | -0.0118 | 0.1357 | -0.0869 | 0.417 | -0.0063 | -0.0444 | 0.458 |
| 60 | -0.0251 | 0.1505 | -0.1665 | 0.500 | -0.0230 | -0.1388 | 0.500 |

quantile mean forward 20d returns: Q1: 0.00976  Q2: 0.00595  Q3: 0.00363  Q4: 0.00733  Q5: 0.00037
Q5-Q1 long-short (gross, monthly): mean -0.00939, ann -0.0889, Sharpe -0.775, MDD -0.2238
top-quintile turnover: 0.105

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0084 | -0.062 | 0.583 |
| 2023 | 12 | -0.0225 | -0.198 | 0.417 |

regime split: up-market IC -0.0029 (n=13) / down-market IC -0.0303 (n=11)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0381 | 0.0809 | 0.4706 | 0.667 | 0.0124 | 0.1195 | 0.542 |
| 5 | -0.0096 | 0.0762 | -0.1260 | 0.458 | -0.0027 | -0.0197 | 0.375 |
| 10 | 0.0154 | 0.0994 | 0.1554 | 0.500 | 0.0193 | 0.1539 | 0.542 |
| 20 | 0.0100 | 0.1171 | 0.0857 | 0.500 | -0.0155 | -0.1232 | 0.500 |
| 40 | 0.0201 | 0.1035 | 0.1937 | 0.583 | -0.0063 | -0.0445 | 0.458 |
| 60 | 0.0175 | 0.0989 | 0.1766 | 0.625 | -0.0230 | -0.1389 | 0.500 |

quantile mean forward 20d returns: Q1: 0.00976  Q2: 0.00595  Q3: 0.00363  Q4: 0.00733  Q5: 0.00037
Q5-Q1 long-short (gross, monthly): mean -0.00939, ann -0.0889, Sharpe -0.775, MDD -0.2238
top-quintile turnover: 0.105

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0084 | -0.062 | 0.583 |
| 2023 | 12 | -0.0225 | -0.199 | 0.417 |

regime split: up-market IC -0.0029 (n=13) / down-market IC -0.0303 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.020
- empirical direction: positive

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0052 | 0.1083 | 0.0479 | 0.542 | -0.0069 | -0.0623 | 0.500 |
| 5 | 0.0199 | 0.0994 | 0.2003 | 0.542 | -0.0036 | -0.0306 | 0.542 |
| 10 | 0.0215 | 0.1178 | 0.1827 | 0.500 | 0.0116 | 0.0947 | 0.583 |
| 20 | 0.0379 | 0.1335 | 0.2842 | 0.542 | 0.0263 | 0.1868 | 0.542 |
| 40 | 0.0483 | 0.1407 | 0.3433 | 0.708 | 0.0349 | 0.2635 | 0.625 |
| 60 | 0.0403 | 0.1420 | 0.2837 | 0.667 | 0.0304 | 0.2202 | 0.583 |

quantile mean forward 20d returns: Q1: 0.02553  Q2: 0.03144  Q3: 0.01952  Q4: 0.02771  Q5: 0.03938
Q5-Q1 long-short (gross, monthly): mean 0.01385, ann 0.1367, Sharpe 0.995, MDD -0.1400
top-quintile turnover: 0.106

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0061 | 0.041 | 0.500 |
| 2025 | 12 | 0.0465 | 0.358 | 0.583 |

regime split: up-market IC 0.0595 (n=15) / down-market IC -0.0291 (n=9)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0018 | 0.1119 | 0.0160 | 0.583 | -0.0068 | -0.0621 | 0.500 |
| 5 | 0.0145 | 0.1089 | 0.1328 | 0.583 | -0.0035 | -0.0303 | 0.583 |
| 10 | 0.0287 | 0.1327 | 0.2161 | 0.542 | 0.0116 | 0.0950 | 0.583 |
| 20 | 0.0392 | 0.1315 | 0.2978 | 0.625 | 0.0263 | 0.1868 | 0.542 |
| 40 | 0.0581 | 0.1246 | 0.4665 | 0.750 | 0.0350 | 0.2636 | 0.625 |
| 60 | 0.0563 | 0.1141 | 0.4939 | 0.667 | 0.0304 | 0.2203 | 0.583 |

quantile mean forward 20d returns: Q1: 0.02553  Q2: 0.03144  Q3: 0.01952  Q4: 0.02771  Q5: 0.03938
Q5-Q1 long-short (gross, monthly): mean 0.01385, ann 0.1367, Sharpe 0.995, MDD -0.1400
top-quintile turnover: 0.106

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0062 | 0.042 | 0.500 |
| 2025 | 12 | 0.0464 | 0.358 | 0.583 |

regime split: up-market IC 0.0595 (n=15) / down-market IC -0.0291 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`net_profit_growth`: 0.581  `downside_volatility_60`: 0.226  `max_return_20`: 0.176  `amount_60`: 0.170  `amount_20`: 0.164

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.