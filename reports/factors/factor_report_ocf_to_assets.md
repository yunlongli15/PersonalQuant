# factor_report_ocf_to_assets.md

## definition

- factor: `ocf_to_assets`  ·  category: cash_flow  ·  version 1.0
- formula: `operating_cash_flow/total_assets`
- source: financial  ·  PIT: True
- required fields: operating_cash_flow, total_assets
- description: cash-flow yield on assets, latest PIT annual report
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.023
- empirical direction: positive

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0098 | 0.1176 | 0.0831 | 0.587 | -0.0031 | -0.0232 | 0.457 |
| 5 | 0.0057 | 0.1486 | 0.0385 | 0.543 | -0.0006 | -0.0040 | 0.543 |
| 10 | 0.0290 | 0.1408 | 0.2061 | 0.565 | 0.0233 | 0.1517 | 0.565 |
| 20 | 0.0331 | 0.1419 | 0.2332 | 0.674 | 0.0343 | 0.2275 | 0.630 |
| 40 | 0.0501 | 0.1423 | 0.3522 | 0.696 | 0.0536 | 0.3539 | 0.652 |
| 60 | 0.0430 | 0.1339 | 0.3209 | 0.652 | 0.0451 | 0.3174 | 0.609 |

quantile mean forward 20d returns: Q1: 0.01042  Q2: 0.01033  Q3: 0.01659  Q4: 0.01210  Q5: 0.01574
Q5-Q1 long-short (gross, monthly): mean 0.00532, ann 0.0378, Sharpe 0.258, MDD -0.1684
top-quintile turnover: 0.089

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 10 | 0.0420 | 0.240 | 0.600 |
| 2019 | 12 | 0.0486 | 0.331 | 0.667 |
| 2020 | 12 | 0.0898 | 0.783 | 0.833 |
| 2021 | 12 | -0.0419 | -0.316 | 0.417 |

regime split: up-market IC 0.0389 (n=27) / down-market IC 0.0277 (n=19)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0316 | 0.0573 | -0.5512 | 0.304 | -0.0031 | -0.0232 | 0.457 |
| 5 | -0.0127 | 0.0633 | -0.2002 | 0.370 | -0.0006 | -0.0040 | 0.543 |
| 10 | -0.0009 | 0.0703 | -0.0125 | 0.500 | 0.0233 | 0.1517 | 0.565 |
| 20 | 0.0002 | 0.0700 | 0.0025 | 0.457 | 0.0343 | 0.2275 | 0.630 |
| 40 | 0.0062 | 0.0634 | 0.0977 | 0.500 | 0.0536 | 0.3539 | 0.652 |
| 60 | 0.0040 | 0.0636 | 0.0627 | 0.500 | 0.0451 | 0.3174 | 0.609 |

quantile mean forward 20d returns: Q1: 0.01042  Q2: 0.01033  Q3: 0.01659  Q4: 0.01210  Q5: 0.01574
Q5-Q1 long-short (gross, monthly): mean 0.00532, ann 0.0378, Sharpe 0.258, MDD -0.1684
top-quintile turnover: 0.089

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 10 | 0.0420 | 0.240 | 0.600 |
| 2019 | 12 | 0.0486 | 0.331 | 0.667 |
| 2020 | 12 | 0.0898 | 0.783 | 0.833 |
| 2021 | 12 | -0.0419 | -0.316 | 0.417 |

regime split: up-market IC 0.0389 (n=27) / down-market IC 0.0277 (n=19)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.021
- empirical direction: positive

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0347 | 0.1014 | 0.3421 | 0.667 | 0.0260 | 0.2473 | 0.542 |
| 5 | 0.0291 | 0.1374 | 0.2119 | 0.500 | 0.0281 | 0.1922 | 0.417 |
| 10 | 0.0548 | 0.1315 | 0.4172 | 0.542 | 0.0654 | 0.4661 | 0.583 |
| 20 | 0.0515 | 0.1342 | 0.3835 | 0.708 | 0.0504 | 0.3270 | 0.792 |
| 40 | 0.0673 | 0.1650 | 0.4078 | 0.750 | 0.0676 | 0.3754 | 0.708 |
| 60 | 0.0737 | 0.1708 | 0.4313 | 0.708 | 0.0798 | 0.4274 | 0.583 |

quantile mean forward 20d returns: Q1: 0.00105  Q2: 0.00362  Q3: 0.00777  Q4: 0.00360  Q5: 0.00984
Q5-Q1 long-short (gross, monthly): mean 0.00879, ann 0.1081, Sharpe 0.847, MDD -0.1853
top-quintile turnover: 0.097

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0516 | 0.472 | 0.833 |
| 2023 | 12 | 0.0492 | 0.261 | 0.750 |

regime split: up-market IC 0.0710 (n=13) / down-market IC 0.0260 (n=11)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0124 | 0.0635 | -0.1950 | 0.333 | 0.0260 | 0.2475 | 0.542 |
| 5 | -0.0052 | 0.0874 | -0.0593 | 0.458 | 0.0281 | 0.1923 | 0.417 |
| 10 | 0.0045 | 0.0649 | 0.0687 | 0.500 | 0.0654 | 0.4662 | 0.583 |
| 20 | 0.0216 | 0.0731 | 0.2957 | 0.625 | 0.0504 | 0.3272 | 0.792 |
| 40 | 0.0306 | 0.0723 | 0.4231 | 0.750 | 0.0676 | 0.3755 | 0.708 |
| 60 | 0.0426 | 0.0619 | 0.6888 | 0.667 | 0.0798 | 0.4276 | 0.583 |

quantile mean forward 20d returns: Q1: 0.00105  Q2: 0.00362  Q3: 0.00777  Q4: 0.00360  Q5: 0.00984
Q5-Q1 long-short (gross, monthly): mean 0.00879, ann 0.1081, Sharpe 0.847, MDD -0.1853
top-quintile turnover: 0.097

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0516 | 0.472 | 0.833 |
| 2023 | 12 | 0.0492 | 0.261 | 0.750 |

regime split: up-market IC 0.0711 (n=13) / down-market IC 0.0260 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.020
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0130 | 0.0978 | -0.1328 | 0.458 | -0.0126 | -0.1212 | 0.500 |
| 5 | -0.0295 | 0.1172 | -0.2517 | 0.375 | -0.0387 | -0.3114 | 0.417 |
| 10 | -0.0010 | 0.1292 | -0.0074 | 0.542 | -0.0020 | -0.0146 | 0.500 |
| 20 | -0.0147 | 0.1023 | -0.1434 | 0.458 | -0.0126 | -0.0875 | 0.458 |
| 40 | -0.0229 | 0.1050 | -0.2180 | 0.458 | -0.0153 | -0.1173 | 0.583 |
| 60 | -0.0301 | 0.1139 | -0.2644 | 0.417 | -0.0211 | -0.1683 | 0.500 |

quantile mean forward 20d returns: Q1: 0.02640  Q2: 0.03681  Q3: 0.02883  Q4: 0.02683  Q5: 0.02440
Q5-Q1 long-short (gross, monthly): mean -0.00200, ann -0.0495, Sharpe -0.413, MDD -0.2004
top-quintile turnover: 0.067

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0199 | -0.126 | 0.417 |
| 2025 | 12 | -0.0053 | -0.041 | 0.500 |

regime split: up-market IC -0.0400 (n=15) / down-market IC 0.0330 (n=9)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0194 | 0.0958 | -0.2020 | 0.292 | -0.0126 | -0.1206 | 0.500 |
| 5 | 0.0052 | 0.0848 | 0.0612 | 0.500 | -0.0387 | -0.3115 | 0.417 |
| 10 | 0.0088 | 0.0839 | 0.1045 | 0.542 | -0.0021 | -0.0146 | 0.500 |
| 20 | 0.0089 | 0.0811 | 0.1092 | 0.542 | -0.0126 | -0.0875 | 0.458 |
| 40 | 0.0087 | 0.0825 | 0.1052 | 0.542 | -0.0153 | -0.1173 | 0.583 |
| 60 | 0.0027 | 0.0779 | 0.0345 | 0.500 | -0.0210 | -0.1680 | 0.500 |

quantile mean forward 20d returns: Q1: 0.02640  Q2: 0.03681  Q3: 0.02883  Q4: 0.02683  Q5: 0.02440
Q5-Q1 long-short (gross, monthly): mean -0.00200, ann -0.0495, Sharpe -0.413, MDD -0.2004
top-quintile turnover: 0.067

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0199 | -0.125 | 0.417 |
| 2025 | 12 | -0.0053 | -0.042 | 0.500 |

regime split: up-market IC -0.0400 (n=15) / down-market IC 0.0331 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`gross_margin`: 0.375  `debt_to_asset`: -0.305  `net_profit_growth`: 0.209  `earnings_yield`: -0.196  `amount_60`: 0.172

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.