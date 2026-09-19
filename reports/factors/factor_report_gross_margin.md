# factor_report_gross_margin.md

## definition

- factor: `gross_margin`  ·  category: quality  ·  version 1.0
- formula: `(revenue-cost_of_revenue)/revenue`
- source: financial  ·  PIT: True
- required fields: revenue, cost_of_revenue
- description: gross margin, latest PIT annual report (MISSING for banks/insurers: no cost_of_revenue)
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.017
- empirical direction: positive

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0266 | 0.2146 | 0.1238 | 0.556 | 0.0164 | 0.0756 | 0.556 |
| 5 | -0.0230 | 0.1999 | -0.1152 | 0.378 | 0.0052 | 0.0251 | 0.511 |
| 10 | 0.0115 | 0.1951 | 0.0591 | 0.556 | 0.0438 | 0.2135 | 0.578 |
| 20 | 0.0380 | 0.2093 | 0.1814 | 0.622 | 0.0726 | 0.3365 | 0.622 |
| 40 | 0.0240 | 0.1892 | 0.1270 | 0.556 | 0.0560 | 0.2934 | 0.600 |
| 60 | 0.0201 | 0.1774 | 0.1131 | 0.556 | 0.0529 | 0.2900 | 0.600 |

quantile mean forward 20d returns: Q1: 0.01723  Q2: 0.01577  Q3: 0.01329  Q4: 0.01770  Q5: 0.01776
Q5-Q1 long-short (gross, monthly): mean 0.00053, ann -0.0400, Sharpe -0.162, MDD -0.5279
top-quintile turnover: 0.076

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 9 | 0.1505 | 0.773 | 0.667 |
| 2019 | 12 | 0.1457 | 0.674 | 0.750 |
| 2020 | 12 | 0.0302 | 0.162 | 0.667 |
| 2021 | 12 | -0.0166 | -0.078 | 0.417 |

regime split: up-market IC 0.0479 (n=27) / down-market IC 0.1096 (n=18)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0060 | 0.1235 | 0.0485 | 0.622 | 0.0164 | 0.0756 | 0.556 |
| 5 | 0.0065 | 0.1274 | 0.0511 | 0.622 | 0.0053 | 0.0254 | 0.511 |
| 10 | 0.0129 | 0.1189 | 0.1087 | 0.556 | 0.0438 | 0.2135 | 0.578 |
| 20 | 0.0071 | 0.1174 | 0.0606 | 0.600 | 0.0725 | 0.3361 | 0.622 |
| 40 | -0.0002 | 0.1056 | -0.0021 | 0.556 | 0.0559 | 0.2929 | 0.600 |
| 60 | -0.0020 | 0.1021 | -0.0198 | 0.489 | 0.0529 | 0.2897 | 0.600 |

quantile mean forward 20d returns: Q1: 0.01723  Q2: 0.01577  Q3: 0.01329  Q4: 0.01770  Q5: 0.01776
Q5-Q1 long-short (gross, monthly): mean 0.00053, ann -0.0400, Sharpe -0.162, MDD -0.5279
top-quintile turnover: 0.076

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 9 | 0.1502 | 0.772 | 0.667 |
| 2019 | 12 | 0.1457 | 0.673 | 0.750 |
| 2020 | 12 | 0.0302 | 0.162 | 0.667 |
| 2021 | 12 | -0.0167 | -0.079 | 0.417 |

regime split: up-market IC 0.0477 (n=27) / down-market IC 0.1096 (n=18)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.016
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0464 | 0.1310 | -0.3538 | 0.333 | -0.0445 | -0.3332 | 0.333 |
| 5 | -0.0368 | 0.1542 | -0.2386 | 0.375 | -0.0392 | -0.2442 | 0.458 |
| 10 | -0.0005 | 0.1611 | -0.0029 | 0.542 | 0.0123 | 0.0769 | 0.625 |
| 20 | -0.0206 | 0.1590 | -0.1297 | 0.417 | -0.0100 | -0.0601 | 0.542 |
| 40 | -0.0194 | 0.1474 | -0.1313 | 0.417 | -0.0152 | -0.0911 | 0.500 |
| 60 | -0.0248 | 0.1464 | -0.1692 | 0.458 | -0.0184 | -0.1105 | 0.500 |

quantile mean forward 20d returns: Q1: 0.01179  Q2: 0.00492  Q3: 0.00765  Q4: -0.00134  Q5: 0.00291
Q5-Q1 long-short (gross, monthly): mean -0.00888, ann -0.0733, Sharpe -0.484, MDD -0.2565
top-quintile turnover: 0.068

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0311 | -0.149 | 0.583 |
| 2023 | 12 | 0.0112 | 0.109 | 0.500 |

regime split: up-market IC -0.0672 (n=13) / down-market IC 0.0576 (n=11)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0180 | 0.0977 | -0.1838 | 0.458 | -0.0445 | -0.3334 | 0.333 |
| 5 | 0.0013 | 0.1039 | 0.0128 | 0.583 | -0.0391 | -0.2433 | 0.458 |
| 10 | 0.0249 | 0.1119 | 0.2227 | 0.583 | 0.0125 | 0.0785 | 0.625 |
| 20 | 0.0188 | 0.0684 | 0.2751 | 0.542 | -0.0099 | -0.0594 | 0.542 |
| 40 | 0.0241 | 0.0513 | 0.4691 | 0.625 | -0.0150 | -0.0903 | 0.500 |
| 60 | 0.0249 | 0.0379 | 0.6588 | 0.792 | -0.0181 | -0.1088 | 0.500 |

quantile mean forward 20d returns: Q1: 0.01179  Q2: 0.00492  Q3: 0.00765  Q4: -0.00134  Q5: 0.00291
Q5-Q1 long-short (gross, monthly): mean -0.00888, ann -0.0733, Sharpe -0.484, MDD -0.2565
top-quintile turnover: 0.068

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0309 | -0.148 | 0.583 |
| 2023 | 12 | 0.0112 | 0.110 | 0.500 |

regime split: up-market IC -0.0669 (n=13) / down-market IC 0.0576 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.015
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0398 | 0.1570 | -0.2538 | 0.417 | -0.0596 | -0.3480 | 0.333 |
| 5 | -0.0524 | 0.1630 | -0.3213 | 0.417 | -0.0594 | -0.3337 | 0.375 |
| 10 | -0.0177 | 0.1415 | -0.1252 | 0.458 | -0.0278 | -0.1833 | 0.458 |
| 20 | -0.0369 | 0.1371 | -0.2690 | 0.458 | -0.0510 | -0.3015 | 0.417 |
| 40 | -0.0601 | 0.1491 | -0.4030 | 0.417 | -0.0781 | -0.4358 | 0.417 |
| 60 | -0.0643 | 0.1515 | -0.4242 | 0.292 | -0.0900 | -0.5045 | 0.375 |

quantile mean forward 20d returns: Q1: 0.02707  Q2: 0.04730  Q3: 0.03822  Q4: 0.02404  Q5: 0.01454
Q5-Q1 long-short (gross, monthly): mean -0.01253, ann -0.1586, Sharpe -1.217, MDD -0.3617
top-quintile turnover: 0.081

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0459 | -0.325 | 0.333 |
| 2025 | 12 | -0.0560 | -0.291 | 0.500 |

regime split: up-market IC -0.1285 (n=15) / down-market IC 0.0783 (n=9)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0269 | 0.1166 | 0.2305 | 0.667 | -0.0596 | -0.3480 | 0.333 |
| 5 | -0.0062 | 0.1109 | -0.0562 | 0.542 | -0.0594 | -0.3337 | 0.375 |
| 10 | 0.0223 | 0.0987 | 0.2257 | 0.542 | -0.0278 | -0.1833 | 0.458 |
| 20 | 0.0035 | 0.0952 | 0.0364 | 0.625 | -0.0510 | -0.3015 | 0.417 |
| 40 | 0.0024 | 0.1047 | 0.0225 | 0.667 | -0.0781 | -0.4358 | 0.417 |
| 60 | 0.0059 | 0.1164 | 0.0506 | 0.708 | -0.0900 | -0.5045 | 0.375 |

quantile mean forward 20d returns: Q1: 0.02707  Q2: 0.04730  Q3: 0.03822  Q4: 0.02404  Q5: 0.01454
Q5-Q1 long-short (gross, monthly): mean -0.01253, ann -0.1586, Sharpe -1.217, MDD -0.3617
top-quintile turnover: 0.081

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0459 | -0.325 | 0.333 |
| 2025 | 12 | -0.0560 | -0.291 | 0.500 |

regime split: up-market IC -0.1285 (n=15) / down-market IC 0.0783 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`net_margin`: 0.583  `earnings_yield`: 0.228  `high_52w_proximity`: 0.227  `net_profit_growth`: 0.222  `amihud_20`: -0.187

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.