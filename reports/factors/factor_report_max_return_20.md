# factor_report_max_return_20.md

## definition

- factor: `max_return_20`  ·  category: microstructure  ·  version 1.0
- formula: `mean(largest 3 daily returns in 20d)`
- source: market  ·  PIT: True
- required fields: close, factor
- description: 彩票效应：极端正收益（MAX）越强，后续越容易跑输
- declared (economic) direction: **negative**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0397 | 0.1353 | 0.2933 | 0.667 | 0.0076 | 0.0489 | 0.562 |
| 5 | 0.0127 | 0.1199 | 0.1059 | 0.542 | -0.0267 | -0.1862 | 0.417 |
| 10 | 0.0067 | 0.1053 | 0.0640 | 0.458 | -0.0376 | -0.2847 | 0.354 |
| 20 | -0.0299 | 0.1131 | -0.2640 | 0.333 | -0.0807 | -0.6099 | 0.250 |
| 40 | -0.0371 | 0.1015 | -0.3652 | 0.375 | -0.0918 | -0.7698 | 0.229 |
| 60 | -0.0356 | 0.0957 | -0.3716 | 0.458 | -0.0906 | -0.8189 | 0.229 |

quantile mean forward 20d returns: Q1: 0.01062  Q2: 0.01396  Q3: 0.01487  Q4: 0.01351  Q5: 0.00276
Q5-Q1 long-short (gross, monthly): mean -0.00785, ann -0.1022, Sharpe -0.664, MDD -0.3569
top-quintile turnover: 0.683

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0914 | -1.328 | 0.083 |
| 2019 | 12 | -0.0445 | -0.337 | 0.333 |
| 2020 | 12 | -0.0586 | -0.363 | 0.417 |
| 2021 | 12 | -0.1282 | -0.966 | 0.167 |

regime split: up-market IC -0.0516 (n=28) / down-market IC -0.1214 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0437 | 0.1403 | 0.3113 | 0.667 | 0.0076 | 0.0489 | 0.562 |
| 5 | 0.0053 | 0.1259 | 0.0417 | 0.562 | -0.0267 | -0.1861 | 0.417 |
| 10 | -0.0018 | 0.1088 | -0.0162 | 0.438 | -0.0376 | -0.2846 | 0.354 |
| 20 | -0.0421 | 0.1117 | -0.3773 | 0.312 | -0.0807 | -0.6097 | 0.250 |
| 40 | -0.0505 | 0.0948 | -0.5327 | 0.292 | -0.0918 | -0.7695 | 0.229 |
| 60 | -0.0488 | 0.0864 | -0.5646 | 0.312 | -0.0906 | -0.8185 | 0.229 |

quantile mean forward 20d returns: Q1: 0.01062  Q2: 0.01396  Q3: 0.01484  Q4: 0.01353  Q5: 0.00276
Q5-Q1 long-short (gross, monthly): mean -0.00785, ann -0.1022, Sharpe -0.664, MDD -0.3569
top-quintile turnover: 0.683

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0914 | -1.328 | 0.083 |
| 2019 | 12 | -0.0445 | -0.337 | 0.333 |
| 2020 | 12 | -0.0586 | -0.363 | 0.417 |
| 2021 | 12 | -0.1282 | -0.966 | 0.167 |

regime split: up-market IC -0.0516 (n=28) / down-market IC -0.1214 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0100 | 0.1075 | -0.0929 | 0.417 | -0.0558 | -0.4939 | 0.375 |
| 5 | -0.0014 | 0.1104 | -0.0125 | 0.458 | -0.0506 | -0.3886 | 0.375 |
| 10 | -0.0386 | 0.0955 | -0.4037 | 0.333 | -0.0934 | -0.8261 | 0.208 |
| 20 | -0.0454 | 0.1133 | -0.4006 | 0.458 | -0.1028 | -0.8327 | 0.250 |
| 40 | -0.0655 | 0.1142 | -0.5737 | 0.417 | -0.1208 | -0.8991 | 0.167 |
| 60 | -0.0828 | 0.0864 | -0.9588 | 0.208 | -0.1449 | -1.4426 | 0.083 |

quantile mean forward 20d returns: Q1: 0.00684  Q2: 0.00546  Q3: 0.00724  Q4: 0.00120  Q5: -0.00620
Q5-Q1 long-short (gross, monthly): mean -0.01304, ann -0.1552, Sharpe -1.226, MDD -0.2917
top-quintile turnover: 0.709

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0891 | -0.888 | 0.167 |
| 2023 | 12 | -0.1165 | -0.823 | 0.333 |

regime split: up-market IC -0.0853 (n=13) / down-market IC -0.1235 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0047 | 0.1264 | -0.0372 | 0.417 | -0.0558 | -0.4940 | 0.375 |
| 5 | -0.0020 | 0.1155 | -0.0173 | 0.458 | -0.0506 | -0.3886 | 0.375 |
| 10 | -0.0464 | 0.0981 | -0.4727 | 0.333 | -0.0934 | -0.8259 | 0.208 |
| 20 | -0.0530 | 0.1136 | -0.4662 | 0.417 | -0.1028 | -0.8326 | 0.250 |
| 40 | -0.0741 | 0.1132 | -0.6548 | 0.333 | -0.1208 | -0.8989 | 0.167 |
| 60 | -0.0938 | 0.0861 | -1.0889 | 0.083 | -0.1448 | -1.4424 | 0.083 |

quantile mean forward 20d returns: Q1: 0.00684  Q2: 0.00546  Q3: 0.00723  Q4: 0.00119  Q5: -0.00618
Q5-Q1 long-short (gross, monthly): mean -0.01303, ann -0.1550, Sharpe -1.226, MDD -0.2914
top-quintile turnover: 0.709

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0891 | -0.888 | 0.167 |
| 2023 | 12 | -0.1165 | -0.823 | 0.333 |

regime split: up-market IC -0.0853 (n=13) / down-market IC -0.1235 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0390 | 0.1675 | 0.2326 | 0.583 | 0.0055 | 0.0270 | 0.417 |
| 5 | -0.0227 | 0.1331 | -0.1706 | 0.375 | -0.0771 | -0.4541 | 0.333 |
| 10 | -0.0065 | 0.1405 | -0.0464 | 0.625 | -0.0539 | -0.3077 | 0.417 |
| 20 | -0.0164 | 0.1188 | -0.1384 | 0.500 | -0.0757 | -0.4920 | 0.375 |
| 40 | -0.0177 | 0.1059 | -0.1670 | 0.500 | -0.0745 | -0.5396 | 0.333 |
| 60 | -0.0078 | 0.0931 | -0.0834 | 0.542 | -0.0647 | -0.5320 | 0.292 |

quantile mean forward 20d returns: Q1: 0.02918  Q2: 0.03569  Q3: 0.04275  Q4: 0.03550  Q5: 0.02759
Q5-Q1 long-short (gross, monthly): mean -0.00159, ann -0.0297, Sharpe -0.190, MDD -0.1513
top-quintile turnover: 0.731

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0676 | -0.437 | 0.417 |
| 2025 | 12 | -0.0839 | -0.550 | 0.333 |

regime split: up-market IC -0.0317 (n=15) / down-market IC -0.1491 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0350 | 0.1681 | 0.2080 | 0.500 | 0.0055 | 0.0270 | 0.417 |
| 5 | -0.0273 | 0.1294 | -0.2109 | 0.458 | -0.0771 | -0.4541 | 0.333 |
| 10 | -0.0129 | 0.1349 | -0.0956 | 0.500 | -0.0539 | -0.3078 | 0.417 |
| 20 | -0.0303 | 0.1087 | -0.2787 | 0.458 | -0.0757 | -0.4920 | 0.375 |
| 40 | -0.0311 | 0.0960 | -0.3239 | 0.458 | -0.0745 | -0.5395 | 0.333 |
| 60 | -0.0245 | 0.0851 | -0.2873 | 0.458 | -0.0646 | -0.5320 | 0.292 |

quantile mean forward 20d returns: Q1: 0.02918  Q2: 0.03569  Q3: 0.04276  Q4: 0.03549  Q5: 0.02760
Q5-Q1 long-short (gross, monthly): mean -0.00159, ann -0.0297, Sharpe -0.190, MDD -0.1513
top-quintile turnover: 0.731

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0675 | -0.436 | 0.417 |
| 2025 | 12 | -0.0839 | -0.550 | 0.333 |

regime split: up-market IC -0.0317 (n=15) / down-market IC -0.1491 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`limit_up_count_20`: 0.624  `downside_volatility_60`: 0.509  `amount_20`: 0.463  `momentum_20`: 0.452  `earnings_yield`: -0.412

## redundancy cluster

cluster members: `downside_volatility_60`, `max_return_20`, `parkinson_vol_20`, `volatility_20`, `volatility_60`

## interpretation & limitations

- declared direction `negative` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.