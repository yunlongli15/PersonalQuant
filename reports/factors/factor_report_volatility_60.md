# factor_report_volatility_60.md

## definition

- factor: `volatility_60`  ·  category: volatility  ·  version 1.0
- formula: `std(ret_daily, 60)`
- source: market  ·  PIT: True
- required fields: close, factor
- description: 60-day daily-return volatility
- declared (economic) direction: **negative**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.969
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0467 | 0.1597 | 0.2926 | 0.708 | 0.0330 | 0.1706 | 0.667 |
| 5 | 0.0195 | 0.1366 | 0.1428 | 0.521 | -0.0050 | -0.0284 | 0.458 |
| 10 | 0.0161 | 0.1201 | 0.1337 | 0.521 | -0.0173 | -0.1068 | 0.438 |
| 20 | -0.0223 | 0.1271 | -0.1750 | 0.438 | -0.0692 | -0.4395 | 0.312 |
| 40 | -0.0338 | 0.1212 | -0.2790 | 0.417 | -0.0858 | -0.5786 | 0.292 |
| 60 | -0.0388 | 0.1120 | -0.3464 | 0.333 | -0.0930 | -0.6840 | 0.271 |

quantile mean forward 20d returns: Q1: 0.00911  Q2: 0.01442  Q3: 0.01333  Q4: 0.01376  Q5: 0.00510
Q5-Q1 long-short (gross, monthly): mean -0.00401, ann -0.0707, Sharpe -0.394, MDD -0.3373
top-quintile turnover: 0.368

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0717 | -0.691 | 0.250 |
| 2019 | 12 | -0.0166 | -0.093 | 0.333 |
| 2020 | 12 | -0.0872 | -0.567 | 0.333 |
| 2021 | 12 | -0.1014 | -0.601 | 0.333 |

regime split: up-market IC -0.0266 (n=28) / down-market IC -0.1289 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0459 | 0.1596 | 0.2875 | 0.708 | 0.0330 | 0.1706 | 0.667 |
| 5 | 0.0169 | 0.1399 | 0.1208 | 0.500 | -0.0050 | -0.0283 | 0.458 |
| 10 | 0.0126 | 0.1227 | 0.1027 | 0.521 | -0.0173 | -0.1068 | 0.438 |
| 20 | -0.0294 | 0.1274 | -0.2309 | 0.396 | -0.0692 | -0.4394 | 0.312 |
| 40 | -0.0430 | 0.1187 | -0.3623 | 0.396 | -0.0858 | -0.5786 | 0.292 |
| 60 | -0.0482 | 0.1097 | -0.4391 | 0.292 | -0.0930 | -0.6838 | 0.271 |

quantile mean forward 20d returns: Q1: 0.00911  Q2: 0.01442  Q3: 0.01332  Q4: 0.01376  Q5: 0.00511
Q5-Q1 long-short (gross, monthly): mean -0.00400, ann -0.0706, Sharpe -0.393, MDD -0.3372
top-quintile turnover: 0.368

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0717 | -0.691 | 0.250 |
| 2019 | 12 | -0.0166 | -0.092 | 0.333 |
| 2020 | 12 | -0.0871 | -0.567 | 0.333 |
| 2021 | 12 | -0.1014 | -0.601 | 0.333 |

regime split: up-market IC -0.0266 (n=28) / down-market IC -0.1289 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.988
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0081 | 0.1249 | -0.0647 | 0.500 | -0.0434 | -0.2972 | 0.458 |
| 5 | 0.0061 | 0.1495 | 0.0410 | 0.500 | -0.0370 | -0.1927 | 0.375 |
| 10 | -0.0377 | 0.1262 | -0.2986 | 0.292 | -0.0877 | -0.5375 | 0.250 |
| 20 | -0.0636 | 0.1367 | -0.4648 | 0.375 | -0.1185 | -0.7194 | 0.208 |
| 40 | -0.0855 | 0.1202 | -0.7108 | 0.208 | -0.1422 | -0.9906 | 0.208 |
| 60 | -0.1068 | 0.0898 | -1.1891 | 0.125 | -0.1749 | -1.6674 | 0.042 |

quantile mean forward 20d returns: Q1: 0.00957  Q2: 0.00676  Q3: 0.00722  Q4: -0.00038  Q5: -0.00863
Q5-Q1 long-short (gross, monthly): mean -0.01820, ann -0.2049, Sharpe -1.320, MDD -0.3714
top-quintile turnover: 0.384

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0638 | -0.495 | 0.250 |
| 2023 | 12 | -0.1732 | -0.973 | 0.167 |

regime split: up-market IC -0.0590 (n=13) / down-market IC -0.1889 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0075 | 0.1353 | -0.0558 | 0.500 | -0.0434 | -0.2972 | 0.458 |
| 5 | 0.0079 | 0.1514 | 0.0524 | 0.500 | -0.0370 | -0.1927 | 0.375 |
| 10 | -0.0402 | 0.1263 | -0.3184 | 0.292 | -0.0877 | -0.5374 | 0.250 |
| 20 | -0.0658 | 0.1327 | -0.4957 | 0.333 | -0.1185 | -0.7193 | 0.208 |
| 40 | -0.0893 | 0.1173 | -0.7610 | 0.250 | -0.1422 | -0.9904 | 0.208 |
| 60 | -0.1113 | 0.0833 | -1.3354 | 0.042 | -0.1749 | -1.6670 | 0.042 |

quantile mean forward 20d returns: Q1: 0.00957  Q2: 0.00675  Q3: 0.00724  Q4: -0.00039  Q5: -0.00863
Q5-Q1 long-short (gross, monthly): mean -0.01820, ann -0.2049, Sharpe -1.320, MDD -0.3713
top-quintile turnover: 0.384

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0638 | -0.495 | 0.250 |
| 2023 | 12 | -0.1731 | -0.973 | 0.167 |

regime split: up-market IC -0.0589 (n=13) / down-market IC -0.1888 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.988
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0458 | 0.1773 | 0.2581 | 0.500 | 0.0243 | 0.1079 | 0.500 |
| 5 | -0.0413 | 0.1835 | -0.2253 | 0.375 | -0.0864 | -0.3642 | 0.375 |
| 10 | -0.0116 | 0.1834 | -0.0634 | 0.500 | -0.0469 | -0.2027 | 0.458 |
| 20 | -0.0027 | 0.1491 | -0.0182 | 0.417 | -0.0545 | -0.2713 | 0.375 |
| 40 | -0.0080 | 0.1257 | -0.0636 | 0.542 | -0.0575 | -0.3257 | 0.333 |
| 60 | 0.0071 | 0.1026 | 0.0691 | 0.583 | -0.0427 | -0.3069 | 0.417 |

quantile mean forward 20d returns: Q1: 0.02604  Q2: 0.03343  Q3: 0.04256  Q4: 0.03731  Q5: 0.03138
Q5-Q1 long-short (gross, monthly): mean 0.00534, ann 0.0248, Sharpe 0.120, MDD -0.1697
top-quintile turnover: 0.398

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0407 | -0.194 | 0.417 |
| 2025 | 12 | -0.0683 | -0.358 | 0.333 |

regime split: up-market IC 0.0313 (n=15) / down-market IC -0.1975 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0412 | 0.1745 | 0.2363 | 0.542 | 0.0243 | 0.1079 | 0.500 |
| 5 | -0.0450 | 0.1764 | -0.2551 | 0.375 | -0.0864 | -0.3642 | 0.375 |
| 10 | -0.0167 | 0.1773 | -0.0940 | 0.500 | -0.0469 | -0.2027 | 0.458 |
| 20 | -0.0128 | 0.1430 | -0.0892 | 0.417 | -0.0545 | -0.2714 | 0.375 |
| 40 | -0.0211 | 0.1204 | -0.1752 | 0.500 | -0.0575 | -0.3257 | 0.333 |
| 60 | -0.0087 | 0.1001 | -0.0867 | 0.458 | -0.0427 | -0.3068 | 0.417 |

quantile mean forward 20d returns: Q1: 0.02604  Q2: 0.03343  Q3: 0.04257  Q4: 0.03730  Q5: 0.03138
Q5-Q1 long-short (gross, monthly): mean 0.00534, ann 0.0248, Sharpe 0.120, MDD -0.1697
top-quintile turnover: 0.398

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0407 | -0.194 | 0.417 |
| 2025 | 12 | -0.0683 | -0.358 | 0.333 |

regime split: up-market IC 0.0313 (n=15) / down-market IC -0.1974 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`downside_volatility_60`: 0.913  `volatility_20`: 0.810  `earnings_yield`: -0.525  `pe`: 0.501  `amount_60`: 0.473

## redundancy cluster

cluster members: `downside_volatility_60`, `volatility_20`, `volatility_60`

## interpretation & limitations

- declared direction `negative` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.