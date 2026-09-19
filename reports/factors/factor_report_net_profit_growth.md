# factor_report_net_profit_growth.md

## definition

- factor: `net_profit_growth`  ·  category: growth  ·  version 1.0
- formula: `net_profit[t]/net_profit[t-1]-1 (same report, prior-year column)`
- source: financial  ·  PIT: True
- required fields: net_profit
- description: annual net-profit growth, latest PIT annual report
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.022
- empirical direction: positive

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0006 | 0.1284 | -0.0044 | 0.522 | 0.0064 | 0.0521 | 0.522 |
| 5 | 0.0079 | 0.1457 | 0.0543 | 0.565 | 0.0226 | 0.1625 | 0.543 |
| 10 | 0.0019 | 0.1543 | 0.0123 | 0.565 | 0.0184 | 0.1260 | 0.609 |
| 20 | -0.0017 | 0.1404 | -0.0121 | 0.522 | 0.0084 | 0.0609 | 0.500 |
| 40 | -0.0050 | 0.1487 | -0.0337 | 0.522 | 0.0104 | 0.0671 | 0.609 |
| 60 | -0.0133 | 0.1640 | -0.0812 | 0.522 | -0.0026 | -0.0153 | 0.565 |

quantile mean forward 20d returns: Q1: 0.01771  Q2: 0.00900  Q3: 0.00765  Q4: 0.01474  Q5: 0.01466
Q5-Q1 long-short (gross, monthly): mean -0.00304, ann -0.0331, Sharpe -0.254, MDD -0.2017
top-quintile turnover: 0.105

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 10 | -0.0238 | -0.112 | 0.400 |
| 2019 | 12 | 0.0468 | 0.563 | 0.667 |
| 2020 | 12 | 0.0577 | 0.684 | 0.583 |
| 2021 | 12 | -0.0525 | -0.468 | 0.333 |

regime split: up-market IC 0.0120 (n=27) / down-market IC 0.0032 (n=19)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0030 | 0.1107 | 0.0269 | 0.457 | 0.0064 | 0.0521 | 0.522 |
| 5 | 0.0090 | 0.0966 | 0.0929 | 0.435 | 0.0226 | 0.1625 | 0.543 |
| 10 | 0.0039 | 0.0963 | 0.0409 | 0.391 | 0.0184 | 0.1260 | 0.609 |
| 20 | -0.0051 | 0.0902 | -0.0568 | 0.457 | 0.0084 | 0.0609 | 0.500 |
| 40 | -0.0114 | 0.0757 | -0.1501 | 0.370 | 0.0104 | 0.0671 | 0.609 |
| 60 | -0.0162 | 0.0775 | -0.2089 | 0.348 | -0.0026 | -0.0153 | 0.565 |

quantile mean forward 20d returns: Q1: 0.01771  Q2: 0.00900  Q3: 0.00765  Q4: 0.01474  Q5: 0.01466
Q5-Q1 long-short (gross, monthly): mean -0.00304, ann -0.0331, Sharpe -0.254, MDD -0.2017
top-quintile turnover: 0.105

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 10 | -0.0238 | -0.112 | 0.400 |
| 2019 | 12 | 0.0468 | 0.563 | 0.667 |
| 2020 | 12 | 0.0577 | 0.684 | 0.583 |
| 2021 | 12 | -0.0525 | -0.468 | 0.333 |

regime split: up-market IC 0.0120 (n=27) / down-market IC 0.0032 (n=19)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.021
- empirical direction: positive

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0033 | 0.1211 | -0.0275 | 0.500 | -0.0065 | -0.0603 | 0.458 |
| 5 | 0.0064 | 0.1188 | 0.0543 | 0.542 | 0.0079 | 0.0687 | 0.583 |
| 10 | 0.0095 | 0.1455 | 0.0651 | 0.583 | 0.0225 | 0.1654 | 0.583 |
| 20 | 0.0055 | 0.1201 | 0.0455 | 0.542 | 0.0138 | 0.1155 | 0.625 |
| 40 | 0.0213 | 0.1355 | 0.1570 | 0.542 | 0.0165 | 0.1175 | 0.583 |
| 60 | 0.0253 | 0.1411 | 0.1791 | 0.583 | 0.0177 | 0.1209 | 0.583 |

quantile mean forward 20d returns: Q1: 0.00538  Q2: 0.00496  Q3: 0.00470  Q4: 0.00305  Q5: 0.00549
Q5-Q1 long-short (gross, monthly): mean 0.00011, ann 0.0237, Sharpe 0.240, MDD -0.0925
top-quintile turnover: 0.113

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0042 | -0.032 | 0.583 |
| 2023 | 12 | 0.0318 | 0.302 | 0.667 |

regime split: up-market IC -0.0066 (n=13) / down-market IC 0.0379 (n=11)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0112 | 0.0444 | -0.2525 | 0.417 | -0.0065 | -0.0603 | 0.458 |
| 5 | 0.0010 | 0.0557 | 0.0183 | 0.375 | 0.0079 | 0.0687 | 0.583 |
| 10 | 0.0002 | 0.0500 | 0.0041 | 0.458 | 0.0225 | 0.1654 | 0.583 |
| 20 | 0.0034 | 0.0542 | 0.0624 | 0.542 | 0.0138 | 0.1155 | 0.625 |
| 40 | 0.0045 | 0.0413 | 0.1088 | 0.583 | 0.0165 | 0.1175 | 0.583 |
| 60 | 0.0007 | 0.0385 | 0.0173 | 0.625 | 0.0177 | 0.1209 | 0.583 |

quantile mean forward 20d returns: Q1: 0.00538  Q2: 0.00496  Q3: 0.00470  Q4: 0.00305  Q5: 0.00549
Q5-Q1 long-short (gross, monthly): mean 0.00011, ann 0.0237, Sharpe 0.240, MDD -0.0925
top-quintile turnover: 0.113

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0042 | -0.032 | 0.583 |
| 2023 | 12 | 0.0318 | 0.302 | 0.667 |

regime split: up-market IC -0.0066 (n=13) / down-market IC 0.0379 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.020
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0039 | 0.0865 | -0.0454 | 0.458 | -0.0016 | -0.0181 | 0.417 |
| 5 | 0.0037 | 0.0855 | 0.0432 | 0.542 | -0.0028 | -0.0374 | 0.583 |
| 10 | 0.0014 | 0.1173 | 0.0117 | 0.500 | 0.0076 | 0.0700 | 0.542 |
| 20 | -0.0129 | 0.1226 | -0.1049 | 0.292 | -0.0002 | -0.0017 | 0.417 |
| 40 | -0.0248 | 0.1283 | -0.1933 | 0.458 | -0.0037 | -0.0346 | 0.542 |
| 60 | -0.0417 | 0.1234 | -0.3379 | 0.417 | -0.0246 | -0.2428 | 0.375 |

quantile mean forward 20d returns: Q1: 0.04337  Q2: 0.01618  Q3: 0.02593  Q4: 0.03135  Q5: 0.02747
Q5-Q1 long-short (gross, monthly): mean -0.01590, ann -0.1961, Sharpe -1.521, MDD -0.3542
top-quintile turnover: 0.107

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0009 | 0.009 | 0.417 |
| 2025 | 12 | -0.0013 | -0.011 | 0.417 |

regime split: up-market IC -0.0142 (n=15) / down-market IC 0.0232 (n=9)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0274 | 0.0530 | -0.5172 | 0.250 | -0.0016 | -0.0181 | 0.417 |
| 5 | -0.0056 | 0.0538 | -0.1032 | 0.417 | -0.0028 | -0.0374 | 0.583 |
| 10 | -0.0039 | 0.0517 | -0.0762 | 0.417 | 0.0076 | 0.0700 | 0.542 |
| 20 | -0.0032 | 0.0626 | -0.0505 | 0.500 | -0.0002 | -0.0017 | 0.417 |
| 40 | -0.0089 | 0.0613 | -0.1455 | 0.542 | -0.0037 | -0.0346 | 0.542 |
| 60 | -0.0084 | 0.0606 | -0.1381 | 0.417 | -0.0246 | -0.2428 | 0.375 |

quantile mean forward 20d returns: Q1: 0.04337  Q2: 0.01618  Q3: 0.02593  Q4: 0.03135  Q5: 0.02747
Q5-Q1 long-short (gross, monthly): mean -0.01590, ann -0.1961, Sharpe -1.521, MDD -0.3542
top-quintile turnover: 0.107

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0009 | 0.009 | 0.417 |
| 2025 | 12 | -0.0013 | -0.011 | 0.417 |

regime split: up-market IC -0.0142 (n=15) / down-market IC 0.0232 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`gross_margin`: 0.222  `amount_60`: 0.217  `amount_20`: 0.209  `amihud_20`: -0.189  `debt_to_asset`: -0.164

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.