# factor_report_reversal_5.md

## definition

- factor: `reversal_5`  ·  category: reversal  ·  version 1.0
- formula: `-(adj_close[t]/adj_close[t-5]-1)`
- source: market  ·  PIT: True
- required fields: close, factor
- description: negative 5-trading-day return (short-term reversal)
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 1.000
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0056 | 0.1113 | 0.0505 | 0.562 | 0.0441 | 0.3287 | 0.625 |
| 5 | 0.0157 | 0.1197 | 0.1314 | 0.583 | 0.0419 | 0.2760 | 0.583 |
| 10 | 0.0149 | 0.1005 | 0.1478 | 0.521 | 0.0302 | 0.2310 | 0.583 |
| 20 | 0.0110 | 0.0817 | 0.1348 | 0.562 | 0.0206 | 0.1946 | 0.521 |
| 40 | 0.0103 | 0.0860 | 0.1203 | 0.562 | 0.0256 | 0.2463 | 0.604 |
| 60 | 0.0026 | 0.0758 | 0.0341 | 0.521 | 0.0158 | 0.1831 | 0.562 |

quantile mean forward 20d returns: Q1: 0.00593  Q2: 0.01177  Q3: 0.01271  Q4: 0.01380  Q5: 0.01152
Q5-Q1 long-short (gross, monthly): mean 0.00560, ann 0.0511, Sharpe 0.365, MDD -0.1146
top-quintile turnover: 0.801

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0086 | -0.114 | 0.417 |
| 2019 | 12 | 0.0623 | 0.389 | 0.500 |
| 2020 | 12 | 0.0076 | 0.105 | 0.583 |
| 2021 | 12 | 0.0209 | 0.287 | 0.583 |

regime split: up-market IC 0.0409 (n=28) / down-market IC -0.0080 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0085 | 0.1125 | -0.0752 | 0.396 | 0.0441 | 0.3287 | 0.625 |
| 5 | 0.0126 | 0.1164 | 0.1082 | 0.542 | 0.0419 | 0.2760 | 0.583 |
| 10 | 0.0147 | 0.0972 | 0.1509 | 0.521 | 0.0302 | 0.2310 | 0.583 |
| 20 | 0.0165 | 0.0855 | 0.1935 | 0.583 | 0.0206 | 0.1944 | 0.521 |
| 40 | 0.0139 | 0.0846 | 0.1645 | 0.583 | 0.0255 | 0.2461 | 0.604 |
| 60 | 0.0063 | 0.0756 | 0.0828 | 0.500 | 0.0158 | 0.1830 | 0.562 |

quantile mean forward 20d returns: Q1: 0.00594  Q2: 0.01175  Q3: 0.01271  Q4: 0.01380  Q5: 0.01152
Q5-Q1 long-short (gross, monthly): mean 0.00558, ann 0.0510, Sharpe 0.364, MDD -0.1148
top-quintile turnover: 0.801

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0086 | -0.114 | 0.417 |
| 2019 | 12 | 0.0623 | 0.389 | 0.500 |
| 2020 | 12 | 0.0077 | 0.106 | 0.583 |
| 2021 | 12 | 0.0209 | 0.286 | 0.583 |

regime split: up-market IC 0.0409 (n=28) / down-market IC -0.0080 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 1.000
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0280 | 0.1268 | 0.2208 | 0.667 | 0.0551 | 0.3633 | 0.667 |
| 5 | 0.0430 | 0.1301 | 0.3304 | 0.667 | 0.0604 | 0.3855 | 0.750 |
| 10 | 0.0314 | 0.0909 | 0.3451 | 0.625 | 0.0497 | 0.4245 | 0.667 |
| 20 | 0.0462 | 0.0908 | 0.5086 | 0.542 | 0.0585 | 0.5283 | 0.583 |
| 40 | 0.0567 | 0.0930 | 0.6102 | 0.750 | 0.0722 | 0.6774 | 0.667 |
| 60 | 0.0383 | 0.0774 | 0.4951 | 0.625 | 0.0492 | 0.4806 | 0.667 |

quantile mean forward 20d returns: Q1: -0.01052  Q2: 0.00267  Q3: 0.00892  Q4: 0.00712  Q5: 0.00636
Q5-Q1 long-short (gross, monthly): mean 0.01688, ann 0.2101, Sharpe 2.041, MDD -0.0356
top-quintile turnover: 0.851

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0823 | 0.790 | 0.750 |
| 2023 | 12 | 0.0347 | 0.310 | 0.417 |

regime split: up-market IC 0.0783 (n=13) / down-market IC 0.0351 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0243 | 0.1281 | 0.1894 | 0.583 | 0.0551 | 0.3633 | 0.667 |
| 5 | 0.0471 | 0.1253 | 0.3755 | 0.625 | 0.0604 | 0.3854 | 0.750 |
| 10 | 0.0377 | 0.0815 | 0.4627 | 0.625 | 0.0497 | 0.4243 | 0.667 |
| 20 | 0.0538 | 0.0811 | 0.6628 | 0.708 | 0.0585 | 0.5281 | 0.583 |
| 40 | 0.0668 | 0.0935 | 0.7137 | 0.750 | 0.0722 | 0.6772 | 0.667 |
| 60 | 0.0519 | 0.0747 | 0.6940 | 0.583 | 0.0492 | 0.4804 | 0.667 |

quantile mean forward 20d returns: Q1: -0.01052  Q2: 0.00267  Q3: 0.00891  Q4: 0.00713  Q5: 0.00636
Q5-Q1 long-short (gross, monthly): mean 0.01688, ann 0.2101, Sharpe 2.041, MDD -0.0356
top-quintile turnover: 0.851

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0823 | 0.790 | 0.750 |
| 2023 | 12 | 0.0347 | 0.310 | 0.417 |

regime split: up-market IC 0.0783 (n=13) / down-market IC 0.0351 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 1.000
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0231 | 0.1351 | -0.1713 | 0.458 | 0.0055 | 0.0343 | 0.583 |
| 5 | -0.0110 | 0.1076 | -0.1027 | 0.458 | 0.0191 | 0.1383 | 0.625 |
| 10 | -0.0184 | 0.0948 | -0.1936 | 0.333 | 0.0015 | 0.0130 | 0.500 |
| 20 | -0.0050 | 0.0770 | -0.0647 | 0.458 | 0.0112 | 0.1219 | 0.542 |
| 40 | -0.0171 | 0.0799 | -0.2142 | 0.375 | -0.0065 | -0.0609 | 0.542 |
| 60 | -0.0080 | 0.0750 | -0.1073 | 0.458 | 0.0032 | 0.0306 | 0.417 |

quantile mean forward 20d returns: Q1: 0.03033  Q2: 0.03648  Q3: 0.04145  Q4: 0.03337  Q5: 0.02910
Q5-Q1 long-short (gross, monthly): mean -0.00123, ann -0.0402, Sharpe -0.405, MDD -0.1372
top-quintile turnover: 0.867

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0113 | 0.100 | 0.500 |
| 2025 | 12 | 0.0110 | 0.173 | 0.583 |

regime split: up-market IC 0.0321 (n=15) / down-market IC -0.0238 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0209 | 0.1329 | -0.1572 | 0.458 | 0.0055 | 0.0344 | 0.583 |
| 5 | -0.0006 | 0.1016 | -0.0056 | 0.583 | 0.0191 | 0.1383 | 0.625 |
| 10 | -0.0050 | 0.0947 | -0.0526 | 0.375 | 0.0015 | 0.0129 | 0.500 |
| 20 | 0.0083 | 0.0757 | 0.1091 | 0.583 | 0.0112 | 0.1218 | 0.542 |
| 40 | -0.0046 | 0.0785 | -0.0584 | 0.458 | -0.0066 | -0.0610 | 0.542 |
| 60 | 0.0024 | 0.0792 | 0.0302 | 0.458 | 0.0031 | 0.0305 | 0.417 |

quantile mean forward 20d returns: Q1: 0.03031  Q2: 0.03650  Q3: 0.04145  Q4: 0.03337  Q5: 0.02910
Q5-Q1 long-short (gross, monthly): mean -0.00121, ann -0.0400, Sharpe -0.403, MDD -0.1368
top-quintile turnover: 0.867

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0113 | 0.100 | 0.500 |
| 2025 | 12 | 0.0110 | 0.172 | 0.583 |

regime split: up-market IC 0.0321 (n=15) / down-market IC -0.0237 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`price_vs_ma20`: -0.725  `momentum_20`: -0.448  `reversal_20`: 0.448  `price_vs_ma60`: -0.434  `volume_ratio_5_20`: -0.319

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.