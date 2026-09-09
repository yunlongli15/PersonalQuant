# factor_report_volume_ratio_5_20.md

## definition

- factor: `volume_ratio_5_20`  ·  category: volume  ·  version 1.0
- formula: `MA(volume,5)/MA(volume,20)`
- source: market  ·  PIT: True
- required fields: volume
- description: 5-day vs 20-day average volume (activity acceleration)
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0123 | 0.0811 | 0.1517 | 0.479 | -0.0182 | -0.1989 | 0.375 |
| 5 | -0.0008 | 0.0928 | -0.0091 | 0.438 | -0.0219 | -0.2074 | 0.417 |
| 10 | -0.0060 | 0.0722 | -0.0827 | 0.417 | -0.0229 | -0.2608 | 0.354 |
| 20 | -0.0140 | 0.0588 | -0.2378 | 0.417 | -0.0263 | -0.3668 | 0.354 |
| 40 | -0.0069 | 0.0580 | -0.1191 | 0.438 | -0.0229 | -0.3480 | 0.417 |
| 60 | -0.0048 | 0.0479 | -0.1009 | 0.521 | -0.0170 | -0.3134 | 0.438 |

quantile mean forward 20d returns: Q1: 0.01112  Q2: 0.01303  Q3: 0.01282  Q4: 0.01222  Q5: 0.00652
Q5-Q1 long-short (gross, monthly): mean -0.00460, ann -0.0534, Sharpe -0.678, MDD -0.2594
top-quintile turnover: 0.842

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0361 | -0.484 | 0.333 |
| 2019 | 12 | -0.0506 | -0.888 | 0.250 |
| 2020 | 12 | -0.0042 | -0.051 | 0.417 |
| 2021 | 12 | -0.0144 | -0.238 | 0.417 |

regime split: up-market IC -0.0321 (n=28) / down-market IC -0.0183 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0171 | 0.0934 | 0.1828 | 0.458 | -0.0182 | -0.1988 | 0.375 |
| 5 | -0.0052 | 0.1032 | -0.0503 | 0.417 | -0.0218 | -0.2072 | 0.417 |
| 10 | -0.0114 | 0.0792 | -0.1438 | 0.396 | -0.0228 | -0.2605 | 0.354 |
| 20 | -0.0235 | 0.0617 | -0.3799 | 0.354 | -0.0263 | -0.3663 | 0.354 |
| 40 | -0.0146 | 0.0623 | -0.2344 | 0.396 | -0.0229 | -0.3477 | 0.417 |
| 60 | -0.0114 | 0.0486 | -0.2342 | 0.458 | -0.0169 | -0.3132 | 0.438 |

quantile mean forward 20d returns: Q1: 0.01112  Q2: 0.01302  Q3: 0.01283  Q4: 0.01223  Q5: 0.00652
Q5-Q1 long-short (gross, monthly): mean -0.00460, ann -0.0534, Sharpe -0.678, MDD -0.2593
top-quintile turnover: 0.842

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0361 | -0.483 | 0.333 |
| 2019 | 12 | -0.0506 | -0.887 | 0.250 |
| 2020 | 12 | -0.0042 | -0.051 | 0.417 |
| 2021 | 12 | -0.0143 | -0.237 | 0.417 |

regime split: up-market IC -0.0320 (n=28) / down-market IC -0.0182 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0199 | 0.0870 | -0.2285 | 0.375 | -0.0380 | -0.3987 | 0.333 |
| 5 | -0.0184 | 0.0690 | -0.2659 | 0.375 | -0.0348 | -0.3975 | 0.375 |
| 10 | -0.0246 | 0.0460 | -0.5352 | 0.208 | -0.0384 | -0.6747 | 0.208 |
| 20 | -0.0269 | 0.0629 | -0.4268 | 0.292 | -0.0363 | -0.4789 | 0.250 |
| 40 | -0.0406 | 0.0769 | -0.5282 | 0.167 | -0.0577 | -0.6559 | 0.125 |
| 60 | -0.0328 | 0.0590 | -0.5564 | 0.250 | -0.0499 | -0.7009 | 0.167 |

quantile mean forward 20d returns: Q1: 0.00647  Q2: 0.00337  Q3: 0.00634  Q4: 0.00222  Q5: -0.00385
Q5-Q1 long-short (gross, monthly): mean -0.01031, ann -0.1196, Sharpe -1.846, MDD -0.2249
top-quintile turnover: 0.885

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0400 | -0.579 | 0.250 |
| 2023 | 12 | -0.0326 | -0.398 | 0.250 |

regime split: up-market IC -0.0362 (n=13) / down-market IC -0.0364 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0217 | 0.0901 | -0.2412 | 0.417 | -0.0380 | -0.3986 | 0.333 |
| 5 | -0.0222 | 0.0730 | -0.3045 | 0.375 | -0.0348 | -0.3971 | 0.375 |
| 10 | -0.0308 | 0.0499 | -0.6183 | 0.167 | -0.0384 | -0.6740 | 0.208 |
| 20 | -0.0319 | 0.0661 | -0.4834 | 0.292 | -0.0362 | -0.4783 | 0.250 |
| 40 | -0.0464 | 0.0722 | -0.6433 | 0.208 | -0.0577 | -0.6555 | 0.125 |
| 60 | -0.0409 | 0.0553 | -0.7386 | 0.167 | -0.0498 | -0.7004 | 0.167 |

quantile mean forward 20d returns: Q1: 0.00647  Q2: 0.00336  Q3: 0.00634  Q4: 0.00220  Q5: -0.00382
Q5-Q1 long-short (gross, monthly): mean -0.01029, ann -0.1194, Sharpe -1.841, MDD -0.2245
top-quintile turnover: 0.885

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0399 | -0.579 | 0.250 |
| 2023 | 12 | -0.0326 | -0.398 | 0.250 |

regime split: up-market IC -0.0362 (n=13) / down-market IC -0.0363 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0018 | 0.0797 | 0.0225 | 0.500 | -0.0202 | -0.1991 | 0.375 |
| 5 | -0.0141 | 0.0756 | -0.1864 | 0.333 | -0.0343 | -0.3698 | 0.292 |
| 10 | -0.0092 | 0.0749 | -0.1227 | 0.417 | -0.0313 | -0.3382 | 0.375 |
| 20 | -0.0171 | 0.0549 | -0.3124 | 0.292 | -0.0368 | -0.5425 | 0.250 |
| 40 | -0.0165 | 0.0538 | -0.3066 | 0.333 | -0.0352 | -0.4965 | 0.292 |
| 60 | -0.0243 | 0.0470 | -0.5177 | 0.375 | -0.0415 | -0.6576 | 0.292 |

quantile mean forward 20d returns: Q1: 0.03383  Q2: 0.03455  Q3: 0.04284  Q4: 0.03292  Q5: 0.02659
Q5-Q1 long-short (gross, monthly): mean -0.00724, ann -0.0728, Sharpe -0.969, MDD -0.1851
top-quintile turnover: 0.894

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0571 | -1.050 | 0.167 |
| 2025 | 12 | -0.0164 | -0.223 | 0.333 |

regime split: up-market IC -0.0580 (n=15) / down-market IC -0.0014 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0031 | 0.0800 | -0.0392 | 0.500 | -0.0202 | -0.1991 | 0.375 |
| 5 | -0.0213 | 0.0727 | -0.2924 | 0.292 | -0.0343 | -0.3698 | 0.292 |
| 10 | -0.0184 | 0.0761 | -0.2423 | 0.417 | -0.0313 | -0.3382 | 0.375 |
| 20 | -0.0281 | 0.0556 | -0.5049 | 0.292 | -0.0368 | -0.5425 | 0.250 |
| 40 | -0.0250 | 0.0561 | -0.4463 | 0.375 | -0.0352 | -0.4966 | 0.292 |
| 60 | -0.0321 | 0.0486 | -0.6605 | 0.250 | -0.0415 | -0.6576 | 0.292 |

quantile mean forward 20d returns: Q1: 0.03383  Q2: 0.03456  Q3: 0.04285  Q4: 0.03292  Q5: 0.02657
Q5-Q1 long-short (gross, monthly): mean -0.00726, ann -0.0731, Sharpe -0.973, MDD -0.1851
top-quintile turnover: 0.894

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0571 | -1.050 | 0.167 |
| 2025 | 12 | -0.0164 | -0.223 | 0.333 |

regime split: up-market IC -0.0580 (n=15) / down-market IC -0.0014 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`price_vs_ma20`: 0.433  `reversal_5`: -0.319  `momentum_20`: 0.290  `reversal_20`: -0.290  `price_vs_ma60`: 0.205

## redundancy cluster

cluster members: `volume_ratio_5_20`

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.