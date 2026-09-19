# factor_report_roa.md

## definition

- factor: `roa`  ·  category: quality  ·  version 1.0
- formula: `net_profit/total_assets (derived, stored)`
- source: financial  ·  PIT: True
- required fields: net_profit, total_assets
- description: return on assets, latest PIT annual report
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.023
- empirical direction: positive

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0313 | 0.1568 | 0.1999 | 0.630 | 0.0231 | 0.1349 | 0.587 |
| 5 | 0.0231 | 0.1893 | 0.1218 | 0.587 | 0.0149 | 0.0707 | 0.587 |
| 10 | 0.0435 | 0.1688 | 0.2575 | 0.630 | 0.0425 | 0.2404 | 0.630 |
| 20 | 0.0462 | 0.1766 | 0.2617 | 0.652 | 0.0472 | 0.2728 | 0.630 |
| 40 | 0.0461 | 0.1766 | 0.2612 | 0.696 | 0.0426 | 0.2440 | 0.652 |
| 60 | 0.0484 | 0.1874 | 0.2580 | 0.674 | 0.0337 | 0.1791 | 0.652 |

quantile mean forward 20d returns: Q1: 0.00954  Q2: 0.00792  Q3: 0.01211  Q4: 0.01865  Q5: 0.01647
Q5-Q1 long-short (gross, monthly): mean 0.00692, ann 0.0631, Sharpe 0.383, MDD -0.2760
top-quintile turnover: 0.086

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 10 | 0.0226 | 0.112 | 0.600 |
| 2019 | 12 | 0.0951 | 0.749 | 0.833 |
| 2020 | 12 | 0.1139 | 0.681 | 0.667 |
| 2021 | 12 | -0.0468 | -0.323 | 0.417 |

regime split: up-market IC 0.0374 (n=27) / down-market IC 0.0612 (n=19)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0333 | 0.0710 | -0.4688 | 0.370 | 0.0231 | 0.1349 | 0.587 |
| 5 | -0.0253 | 0.0735 | -0.3440 | 0.326 | 0.0149 | 0.0707 | 0.587 |
| 10 | -0.0253 | 0.0755 | -0.3356 | 0.348 | 0.0425 | 0.2403 | 0.630 |
| 20 | -0.0258 | 0.0733 | -0.3513 | 0.304 | 0.0472 | 0.2727 | 0.630 |
| 40 | -0.0324 | 0.0730 | -0.4438 | 0.217 | 0.0426 | 0.2439 | 0.652 |
| 60 | -0.0402 | 0.0806 | -0.4985 | 0.239 | 0.0337 | 0.1790 | 0.652 |

quantile mean forward 20d returns: Q1: 0.00954  Q2: 0.00792  Q3: 0.01211  Q4: 0.01865  Q5: 0.01647
Q5-Q1 long-short (gross, monthly): mean 0.00692, ann 0.0631, Sharpe 0.383, MDD -0.2760
top-quintile turnover: 0.086

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 10 | 0.0226 | 0.112 | 0.600 |
| 2019 | 12 | 0.0951 | 0.749 | 0.833 |
| 2020 | 12 | 0.1139 | 0.681 | 0.667 |
| 2021 | 12 | -0.0469 | -0.323 | 0.417 |

regime split: up-market IC 0.0373 (n=27) / down-market IC 0.0612 (n=19)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.022
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0299 | 0.1833 | -0.1632 | 0.500 | -0.0323 | -0.1701 | 0.500 |
| 5 | -0.0409 | 0.2158 | -0.1894 | 0.417 | -0.0441 | -0.2005 | 0.417 |
| 10 | -0.0051 | 0.1928 | -0.0267 | 0.500 | 0.0063 | 0.0322 | 0.500 |
| 20 | -0.0190 | 0.1652 | -0.1153 | 0.542 | -0.0215 | -0.1196 | 0.542 |
| 40 | -0.0038 | 0.1671 | -0.0225 | 0.500 | -0.0096 | -0.0500 | 0.417 |
| 60 | -0.0099 | 0.1684 | -0.0590 | 0.542 | -0.0103 | -0.0514 | 0.458 |

quantile mean forward 20d returns: Q1: 0.00874  Q2: 0.00488  Q3: 0.00707  Q4: 0.00644  Q5: -0.00159
Q5-Q1 long-short (gross, monthly): mean -0.01034, ann -0.0912, Sharpe -0.601, MDD -0.2142
top-quintile turnover: 0.052

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0117 | -0.075 | 0.583 |
| 2023 | 12 | -0.0313 | -0.156 | 0.500 |

regime split: up-market IC 0.0385 (n=13) / down-market IC -0.0924 (n=11)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0007 | 0.0522 | -0.0137 | 0.417 | -0.0323 | -0.1701 | 0.500 |
| 5 | 0.0117 | 0.0610 | 0.1916 | 0.500 | -0.0441 | -0.2006 | 0.417 |
| 10 | 0.0049 | 0.0499 | 0.0975 | 0.500 | 0.0063 | 0.0322 | 0.500 |
| 20 | 0.0221 | 0.0683 | 0.3238 | 0.708 | -0.0215 | -0.1196 | 0.542 |
| 40 | 0.0322 | 0.0704 | 0.4573 | 0.667 | -0.0096 | -0.0500 | 0.417 |
| 60 | 0.0370 | 0.0669 | 0.5532 | 0.625 | -0.0103 | -0.0515 | 0.458 |

quantile mean forward 20d returns: Q1: 0.00874  Q2: 0.00488  Q3: 0.00707  Q4: 0.00644  Q5: -0.00159
Q5-Q1 long-short (gross, monthly): mean -0.01034, ann -0.0912, Sharpe -0.601, MDD -0.2142
top-quintile turnover: 0.052

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0117 | -0.076 | 0.583 |
| 2023 | 12 | -0.0313 | -0.156 | 0.500 |

regime split: up-market IC 0.0385 (n=13) / down-market IC -0.0924 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.021
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0190 | 0.1377 | 0.1382 | 0.625 | 0.0174 | 0.1229 | 0.583 |
| 5 | -0.0303 | 0.1576 | -0.1925 | 0.458 | -0.0476 | -0.2901 | 0.417 |
| 10 | -0.0208 | 0.1803 | -0.1152 | 0.333 | -0.0153 | -0.0815 | 0.375 |
| 20 | -0.0245 | 0.1604 | -0.1527 | 0.417 | -0.0319 | -0.1787 | 0.375 |
| 40 | -0.0404 | 0.1515 | -0.2666 | 0.375 | -0.0412 | -0.2480 | 0.417 |
| 60 | -0.0492 | 0.1668 | -0.2950 | 0.417 | -0.0591 | -0.3353 | 0.333 |

quantile mean forward 20d returns: Q1: 0.02978  Q2: 0.02443  Q3: 0.03467  Q4: 0.03543  Q5: 0.01946
Q5-Q1 long-short (gross, monthly): mean -0.01032, ann -0.1489, Sharpe -1.047, MDD -0.2895
top-quintile turnover: 0.068

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0408 | -0.244 | 0.333 |
| 2025 | 12 | -0.0230 | -0.122 | 0.417 |

regime split: up-market IC -0.0179 (n=15) / down-market IC -0.0553 (n=9)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0273 | 0.0915 | -0.2985 | 0.333 | 0.0174 | 0.1231 | 0.583 |
| 5 | -0.0145 | 0.0673 | -0.2150 | 0.417 | -0.0476 | -0.2900 | 0.417 |
| 10 | -0.0199 | 0.0716 | -0.2777 | 0.375 | -0.0153 | -0.0814 | 0.375 |
| 20 | -0.0107 | 0.0747 | -0.1438 | 0.417 | -0.0319 | -0.1787 | 0.375 |
| 40 | -0.0166 | 0.0646 | -0.2565 | 0.333 | -0.0412 | -0.2481 | 0.417 |
| 60 | -0.0232 | 0.0602 | -0.3854 | 0.208 | -0.0591 | -0.3354 | 0.333 |

quantile mean forward 20d returns: Q1: 0.02978  Q2: 0.02443  Q3: 0.03467  Q4: 0.03543  Q5: 0.01946
Q5-Q1 long-short (gross, monthly): mean -0.01032, ann -0.1489, Sharpe -1.047, MDD -0.2895
top-quintile turnover: 0.068

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0408 | -0.244 | 0.333 |
| 2025 | 12 | -0.0230 | -0.122 | 0.417 |

regime split: up-market IC -0.0178 (n=15) / down-market IC -0.0553 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`gross_margin`: 0.520  `debt_to_asset`: -0.430  `net_margin`: 0.366  `net_profit_growth`: 0.255  `intraday_return_20`: 0.244

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.