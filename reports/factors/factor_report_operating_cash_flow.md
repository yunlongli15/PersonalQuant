# factor_report_operating_cash_flow.md

## definition

- factor: `operating_cash_flow`  ·  category: cash_flow  ·  version 1.0
- formula: `operating cash flow (absolute, latest PIT annual report)`
- source: financial  ·  PIT: True
- required fields: operating_cash_flow
- description: operating cash flow level (a size proxy; the ratio forms below are the comparable cash-flow factors)
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.023
- empirical direction: negative

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0473 | 0.1545 | -0.3065 | 0.326 | -0.0469 | -0.2659 | 0.391 |
| 5 | -0.0432 | 0.1719 | -0.2512 | 0.326 | -0.0240 | -0.1317 | 0.413 |
| 10 | -0.0369 | 0.1827 | -0.2017 | 0.457 | -0.0126 | -0.0680 | 0.435 |
| 20 | -0.0378 | 0.1903 | -0.1987 | 0.435 | -0.0153 | -0.0776 | 0.478 |
| 40 | -0.0450 | 0.1917 | -0.2345 | 0.435 | -0.0097 | -0.0507 | 0.522 |
| 60 | -0.0685 | 0.1894 | -0.3620 | 0.348 | -0.0244 | -0.1239 | 0.370 |

quantile mean forward 20d returns: Q1: 0.01747  Q2: 0.01947  Q3: 0.01291  Q4: 0.00815  Q5: 0.00550
Q5-Q1 long-short (gross, monthly): mean -0.01197, ann -0.1581, Sharpe -0.823, MDD -0.5671
top-quintile turnover: 0.085

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 10 | 0.0201 | 0.117 | 0.600 |
| 2019 | 12 | -0.0822 | -0.534 | 0.333 |
| 2020 | 12 | -0.0006 | -0.003 | 0.333 |
| 2021 | 12 | 0.0075 | 0.030 | 0.667 |

regime split: up-market IC -0.0393 (n=27) / down-market IC 0.0189 (n=19)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0388 | 0.0965 | -0.4020 | 0.370 | -0.0470 | -0.2667 | 0.370 |
| 5 | -0.0242 | 0.0949 | -0.2552 | 0.370 | -0.0241 | -0.1323 | 0.413 |
| 10 | -0.0148 | 0.0945 | -0.1566 | 0.478 | -0.0127 | -0.0688 | 0.435 |
| 20 | -0.0209 | 0.1034 | -0.2021 | 0.457 | -0.0154 | -0.0784 | 0.478 |
| 40 | -0.0275 | 0.1087 | -0.2530 | 0.413 | -0.0099 | -0.0519 | 0.522 |
| 60 | -0.0423 | 0.1047 | -0.4039 | 0.304 | -0.0246 | -0.1253 | 0.370 |

quantile mean forward 20d returns: Q1: 0.01747  Q2: 0.01947  Q3: 0.01291  Q4: 0.00815  Q5: 0.00550
Q5-Q1 long-short (gross, monthly): mean -0.01197, ann -0.1581, Sharpe -0.823, MDD -0.5671
top-quintile turnover: 0.085

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 10 | 0.0201 | 0.117 | 0.600 |
| 2019 | 12 | -0.0825 | -0.537 | 0.333 |
| 2020 | 12 | -0.0008 | -0.005 | 0.333 |
| 2021 | 12 | 0.0074 | 0.030 | 0.667 |

regime split: up-market IC -0.0394 (n=27) / down-market IC 0.0186 (n=19)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.021
- empirical direction: positive

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0612 | 0.1447 | 0.4232 | 0.625 | 0.0613 | 0.3615 | 0.625 |
| 5 | 0.0573 | 0.1947 | 0.2940 | 0.542 | 0.0718 | 0.3457 | 0.625 |
| 10 | 0.0632 | 0.1578 | 0.4006 | 0.667 | 0.0868 | 0.5550 | 0.667 |
| 20 | 0.0739 | 0.2249 | 0.3287 | 0.583 | 0.0981 | 0.4459 | 0.625 |
| 40 | 0.0877 | 0.2052 | 0.4277 | 0.667 | 0.1174 | 0.5907 | 0.708 |
| 60 | 0.1056 | 0.1638 | 0.6446 | 0.792 | 0.1421 | 0.8928 | 0.792 |

quantile mean forward 20d returns: Q1: -0.00127  Q2: -0.00201  Q3: 0.00597  Q4: 0.01101  Q5: 0.01171
Q5-Q1 long-short (gross, monthly): mean 0.01299, ann 0.1565, Sharpe 0.803, MDD -0.1888
top-quintile turnover: 0.049

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0549 | 0.254 | 0.583 |
| 2023 | 12 | 0.1412 | 0.657 | 0.667 |

regime split: up-market IC -0.0366 (n=13) / down-market IC 0.2573 (n=11)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0356 | 0.1011 | 0.3526 | 0.667 | 0.0616 | 0.3638 | 0.625 |
| 5 | 0.0261 | 0.1135 | 0.2301 | 0.542 | 0.0718 | 0.3461 | 0.625 |
| 10 | 0.0227 | 0.1005 | 0.2254 | 0.583 | 0.0868 | 0.5553 | 0.667 |
| 20 | 0.0418 | 0.1336 | 0.3133 | 0.625 | 0.0981 | 0.4464 | 0.625 |
| 40 | 0.0551 | 0.1248 | 0.4418 | 0.583 | 0.1174 | 0.5913 | 0.708 |
| 60 | 0.0722 | 0.0999 | 0.7229 | 0.792 | 0.1421 | 0.8947 | 0.792 |

quantile mean forward 20d returns: Q1: -0.00127  Q2: -0.00201  Q3: 0.00597  Q4: 0.01101  Q5: 0.01171
Q5-Q1 long-short (gross, monthly): mean 0.01299, ann 0.1565, Sharpe 0.803, MDD -0.1888
top-quintile turnover: 0.049

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0550 | 0.254 | 0.583 |
| 2023 | 12 | 0.1412 | 0.657 | 0.667 |

regime split: up-market IC -0.0365 (n=13) / down-market IC 0.2571 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.020
- empirical direction: negative

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0985 | 0.2019 | -0.4879 | 0.292 | -0.0813 | -0.3703 | 0.375 |
| 5 | -0.0199 | 0.1948 | -0.1022 | 0.500 | -0.0038 | -0.0179 | 0.542 |
| 10 | -0.0289 | 0.2210 | -0.1310 | 0.333 | -0.0123 | -0.0529 | 0.417 |
| 20 | -0.0653 | 0.2503 | -0.2608 | 0.458 | -0.0405 | -0.1519 | 0.458 |
| 40 | -0.0911 | 0.2359 | -0.3864 | 0.333 | -0.0542 | -0.2094 | 0.458 |
| 60 | -0.1227 | 0.2180 | -0.5627 | 0.333 | -0.0802 | -0.3364 | 0.375 |

quantile mean forward 20d returns: Q1: 0.04958  Q2: 0.03282  Q3: 0.02239  Q4: 0.01672  Q5: 0.02114
Q5-Q1 long-short (gross, monthly): mean -0.02844, ann -0.2820, Sharpe -1.202, MDD -0.5388
top-quintile turnover: 0.057

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0253 | -0.105 | 0.500 |
| 2025 | 12 | -0.0557 | -0.193 | 0.417 |

regime split: up-market IC -0.1478 (n=15) / down-market IC 0.1383 (n=9)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0482 | 0.1321 | -0.3648 | 0.375 | -0.0813 | -0.3707 | 0.375 |
| 5 | -0.0164 | 0.1044 | -0.1575 | 0.417 | -0.0038 | -0.0178 | 0.542 |
| 10 | -0.0109 | 0.1418 | -0.0771 | 0.375 | -0.0121 | -0.0523 | 0.417 |
| 20 | -0.0450 | 0.1400 | -0.3215 | 0.375 | -0.0403 | -0.1514 | 0.458 |
| 40 | -0.0623 | 0.1284 | -0.4847 | 0.375 | -0.0541 | -0.2091 | 0.458 |
| 60 | -0.0684 | 0.1161 | -0.5890 | 0.208 | -0.0801 | -0.3362 | 0.375 |

quantile mean forward 20d returns: Q1: 0.04958  Q2: 0.03282  Q3: 0.02239  Q4: 0.01672  Q5: 0.02114
Q5-Q1 long-short (gross, monthly): mean -0.02844, ann -0.2820, Sharpe -1.202, MDD -0.5388
top-quintile turnover: 0.057

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0253 | -0.105 | 0.500 |
| 2025 | 12 | -0.0554 | -0.192 | 0.417 |

regime split: up-market IC -0.1475 (n=15) / down-market IC 0.1383 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`downside_volatility_60`: -0.291  `amihud_20`: -0.278  `earnings_yield`: 0.246  `max_return_20`: -0.207  `gross_margin`: 0.204

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.