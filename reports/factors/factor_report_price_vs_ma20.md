# factor_report_price_vs_ma20.md

## definition

- factor: `price_vs_ma20`  ·  category: price_position  ·  version 1.0
- formula: `adj_close/MA(adj_close,20)-1`
- source: market  ·  PIT: True
- required fields: close, factor
- description: close relative to its 20-day moving average
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 1.000
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0045 | 0.1235 | 0.0365 | 0.500 | -0.0371 | -0.2536 | 0.458 |
| 5 | -0.0124 | 0.1417 | -0.0873 | 0.438 | -0.0445 | -0.2541 | 0.417 |
| 10 | -0.0161 | 0.1062 | -0.1518 | 0.417 | -0.0404 | -0.2990 | 0.354 |
| 20 | -0.0227 | 0.0904 | -0.2507 | 0.333 | -0.0402 | -0.3579 | 0.333 |
| 40 | -0.0196 | 0.0925 | -0.2119 | 0.417 | -0.0426 | -0.3770 | 0.354 |
| 60 | -0.0085 | 0.0805 | -0.1057 | 0.521 | -0.0293 | -0.3032 | 0.438 |

quantile mean forward 20d returns: Q1: 0.01252  Q2: 0.01409  Q3: 0.01350  Q4: 0.01181  Q5: 0.00379
Q5-Q1 long-short (gross, monthly): mean -0.00873, ann -0.1016, Sharpe -0.686, MDD -0.3897
top-quintile turnover: 0.798

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0444 | -0.579 | 0.250 |
| 2019 | 12 | -0.0746 | -0.478 | 0.333 |
| 2020 | 12 | 0.0033 | 0.038 | 0.417 |
| 2021 | 12 | -0.0452 | -0.462 | 0.333 |

regime split: up-market IC -0.0642 (n=28) / down-market IC -0.0066 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0147 | 0.1282 | 0.1149 | 0.583 | -0.0371 | -0.2537 | 0.458 |
| 5 | -0.0141 | 0.1419 | -0.0991 | 0.417 | -0.0445 | -0.2541 | 0.417 |
| 10 | -0.0195 | 0.1075 | -0.1817 | 0.417 | -0.0404 | -0.2989 | 0.354 |
| 20 | -0.0302 | 0.0926 | -0.3261 | 0.333 | -0.0402 | -0.3577 | 0.333 |
| 40 | -0.0257 | 0.0899 | -0.2859 | 0.417 | -0.0426 | -0.3768 | 0.354 |
| 60 | -0.0135 | 0.0792 | -0.1711 | 0.458 | -0.0293 | -0.3030 | 0.438 |

quantile mean forward 20d returns: Q1: 0.01252  Q2: 0.01411  Q3: 0.01349  Q4: 0.01179  Q5: 0.00381
Q5-Q1 long-short (gross, monthly): mean -0.00872, ann -0.1014, Sharpe -0.685, MDD -0.3894
top-quintile turnover: 0.798

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0444 | -0.578 | 0.250 |
| 2019 | 12 | -0.0746 | -0.478 | 0.333 |
| 2020 | 12 | 0.0033 | 0.038 | 0.417 |
| 2021 | 12 | -0.0452 | -0.462 | 0.333 |

regime split: up-market IC -0.0642 (n=28) / down-market IC -0.0066 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 1.000
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0281 | 0.1361 | -0.2063 | 0.375 | -0.0524 | -0.3283 | 0.417 |
| 5 | -0.0488 | 0.1216 | -0.4014 | 0.250 | -0.0729 | -0.4866 | 0.250 |
| 10 | -0.0390 | 0.0901 | -0.4325 | 0.458 | -0.0611 | -0.5167 | 0.375 |
| 20 | -0.0469 | 0.0977 | -0.4796 | 0.458 | -0.0688 | -0.5843 | 0.250 |
| 40 | -0.0681 | 0.1184 | -0.5753 | 0.375 | -0.0938 | -0.6844 | 0.333 |
| 60 | -0.0452 | 0.1010 | -0.4474 | 0.292 | -0.0651 | -0.5207 | 0.292 |

quantile mean forward 20d returns: Q1: 0.00517  Q2: 0.00828  Q3: 0.00940  Q4: 0.00338  Q5: -0.01168
Q5-Q1 long-short (gross, monthly): mean -0.01685, ann -0.1894, Sharpe -1.813, MDD -0.3430
top-quintile turnover: 0.857

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0987 | -0.789 | 0.250 |
| 2023 | 12 | -0.0389 | -0.384 | 0.250 |

regime split: up-market IC -0.1168 (n=13) / down-market IC -0.0121 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0232 | 0.1446 | -0.1602 | 0.375 | -0.0525 | -0.3284 | 0.417 |
| 5 | -0.0537 | 0.1201 | -0.4469 | 0.292 | -0.0729 | -0.4865 | 0.250 |
| 10 | -0.0490 | 0.0843 | -0.5819 | 0.333 | -0.0611 | -0.5165 | 0.375 |
| 20 | -0.0564 | 0.0923 | -0.6110 | 0.208 | -0.0688 | -0.5841 | 0.250 |
| 40 | -0.0773 | 0.1176 | -0.6571 | 0.292 | -0.0938 | -0.6844 | 0.333 |
| 60 | -0.0581 | 0.1002 | -0.5803 | 0.292 | -0.0651 | -0.5206 | 0.292 |

quantile mean forward 20d returns: Q1: 0.00517  Q2: 0.00828  Q3: 0.00939  Q4: 0.00339  Q5: -0.01169
Q5-Q1 long-short (gross, monthly): mean -0.01686, ann -0.1895, Sharpe -1.814, MDD -0.3431
top-quintile turnover: 0.857

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0987 | -0.789 | 0.250 |
| 2023 | 12 | -0.0389 | -0.384 | 0.250 |

regime split: up-market IC -0.1167 (n=13) / down-market IC -0.0121 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 1.000
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0269 | 0.1483 | 0.1814 | 0.458 | -0.0014 | -0.0081 | 0.417 |
| 5 | 0.0172 | 0.1295 | 0.1330 | 0.458 | -0.0149 | -0.0963 | 0.417 |
| 10 | 0.0050 | 0.1058 | 0.0471 | 0.542 | -0.0257 | -0.1873 | 0.375 |
| 20 | -0.0141 | 0.0863 | -0.1634 | 0.417 | -0.0472 | -0.4393 | 0.292 |
| 40 | 0.0017 | 0.0751 | 0.0223 | 0.542 | -0.0249 | -0.2329 | 0.417 |
| 60 | -0.0082 | 0.0745 | -0.1096 | 0.542 | -0.0349 | -0.3346 | 0.417 |

quantile mean forward 20d returns: Q1: 0.03271  Q2: 0.03439  Q3: 0.04111  Q4: 0.03572  Q5: 0.02679
Q5-Q1 long-short (gross, monthly): mean -0.00592, ann -0.0685, Sharpe -0.654, MDD -0.1955
top-quintile turnover: 0.858

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0465 | -0.389 | 0.333 |
| 2025 | 12 | -0.0479 | -0.510 | 0.250 |

regime split: up-market IC -0.0872 (n=15) / down-market IC 0.0195 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0232 | 0.1464 | 0.1585 | 0.458 | -0.0014 | -0.0081 | 0.417 |
| 5 | 0.0050 | 0.1285 | 0.0387 | 0.375 | -0.0149 | -0.0963 | 0.417 |
| 10 | -0.0080 | 0.1091 | -0.0731 | 0.542 | -0.0257 | -0.1873 | 0.375 |
| 20 | -0.0287 | 0.0868 | -0.3300 | 0.375 | -0.0472 | -0.4391 | 0.292 |
| 40 | -0.0126 | 0.0761 | -0.1657 | 0.500 | -0.0249 | -0.2327 | 0.417 |
| 60 | -0.0200 | 0.0771 | -0.2596 | 0.375 | -0.0349 | -0.3344 | 0.417 |

quantile mean forward 20d returns: Q1: 0.03271  Q2: 0.03439  Q3: 0.04112  Q4: 0.03572  Q5: 0.02679
Q5-Q1 long-short (gross, monthly): mean -0.00592, ann -0.0685, Sharpe -0.654, MDD -0.1955
top-quintile turnover: 0.858

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0464 | -0.389 | 0.333 |
| 2025 | 12 | -0.0479 | -0.510 | 0.250 |

regime split: up-market IC -0.0872 (n=15) / down-market IC 0.0196 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`momentum_20`: 0.798  `amount_share_20`: 0.488  `momentum_60`: 0.417  `high_52w_proximity`: 0.396  `momentum_120`: 0.306

## redundancy cluster

cluster members: `price_vs_ma20`

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.