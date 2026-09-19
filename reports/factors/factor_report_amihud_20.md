# factor_report_amihud_20.md

## definition

- factor: `amihud_20`  ·  category: liquidity  ·  version 1.0
- formula: `mean(|ret| / amount_cny, 20d) * 1e9`
- source: market  ·  PIT: True
- required fields: close, factor, amount
- description: Amihud 非流动性（单位成交额的价格冲击，放大 1e9）
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 1.000
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0032 | 0.1111 | -0.0292 | 0.458 | 0.0009 | 0.0067 | 0.438 |
| 5 | 0.0172 | 0.1201 | 0.1430 | 0.542 | 0.0270 | 0.1863 | 0.583 |
| 10 | 0.0243 | 0.1137 | 0.2137 | 0.604 | 0.0377 | 0.2624 | 0.583 |
| 20 | 0.0292 | 0.1164 | 0.2511 | 0.562 | 0.0390 | 0.2832 | 0.521 |
| 40 | 0.0387 | 0.1132 | 0.3418 | 0.604 | 0.0527 | 0.4014 | 0.646 |
| 60 | 0.0395 | 0.1139 | 0.3466 | 0.583 | 0.0592 | 0.4481 | 0.667 |

quantile mean forward 20d returns: Q1: 0.00714  Q2: 0.00874  Q3: 0.01088  Q4: 0.01212  Q5: 0.01684
Q5-Q1 long-short (gross, monthly): mean 0.00970, ann 0.1164, Sharpe 0.814, MDD -0.2263
top-quintile turnover: 0.316

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0453 | 0.333 | 0.500 |
| 2019 | 12 | -0.0037 | -0.040 | 0.333 |
| 2020 | 12 | -0.0069 | -0.044 | 0.500 |
| 2021 | 12 | 0.1215 | 1.033 | 0.750 |

regime split: up-market IC 0.0660 (n=28) / down-market IC 0.0012 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0102 | 0.0889 | -0.1152 | 0.396 | 0.0008 | 0.0067 | 0.438 |
| 5 | 0.0044 | 0.0974 | 0.0449 | 0.542 | 0.0270 | 0.1863 | 0.583 |
| 10 | 0.0169 | 0.0929 | 0.1818 | 0.542 | 0.0377 | 0.2624 | 0.583 |
| 20 | 0.0280 | 0.0906 | 0.3092 | 0.667 | 0.0390 | 0.2833 | 0.521 |
| 40 | 0.0366 | 0.0899 | 0.4068 | 0.729 | 0.0528 | 0.4015 | 0.646 |
| 60 | 0.0408 | 0.0938 | 0.4348 | 0.625 | 0.0592 | 0.4482 | 0.667 |

quantile mean forward 20d returns: Q1: 0.00714  Q2: 0.00877  Q3: 0.01084  Q4: 0.01212  Q5: 0.01684
Q5-Q1 long-short (gross, monthly): mean 0.00970, ann 0.1165, Sharpe 0.814, MDD -0.2263
top-quintile turnover: 0.317

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0453 | 0.333 | 0.500 |
| 2019 | 12 | -0.0037 | -0.040 | 0.333 |
| 2020 | 12 | -0.0069 | -0.044 | 0.500 |
| 2021 | 12 | 0.1215 | 1.033 | 0.750 |

regime split: up-market IC 0.0660 (n=28) / down-market IC 0.0013 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 1.000
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0287 | 0.0992 | 0.2897 | 0.542 | 0.0460 | 0.3737 | 0.583 |
| 5 | 0.0228 | 0.1257 | 0.1812 | 0.542 | 0.0386 | 0.2553 | 0.625 |
| 10 | 0.0504 | 0.1047 | 0.4814 | 0.750 | 0.0664 | 0.5305 | 0.750 |
| 20 | 0.0820 | 0.0709 | 1.1568 | 0.875 | 0.1147 | 1.3380 | 0.917 |
| 40 | 0.0807 | 0.1131 | 0.7136 | 0.833 | 0.1203 | 0.9437 | 0.875 |
| 60 | 0.0943 | 0.1113 | 0.8478 | 0.833 | 0.1383 | 1.0768 | 0.917 |

quantile mean forward 20d returns: Q1: -0.01002  Q2: -0.00499  Q3: 0.00624  Q4: 0.00799  Q5: 0.01532
Q5-Q1 long-short (gross, monthly): mean 0.02534, ann 0.3154, Sharpe 4.062, MDD -0.0211
top-quintile turnover: 0.344

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0810 | 0.874 | 0.833 |
| 2023 | 12 | 0.1483 | 2.397 | 1.000 |

regime split: up-market IC 0.1412 (n=13) / down-market IC 0.0834 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0220 | 0.0799 | 0.2750 | 0.500 | 0.0460 | 0.3736 | 0.583 |
| 5 | 0.0223 | 0.1028 | 0.2170 | 0.625 | 0.0386 | 0.2553 | 0.625 |
| 10 | 0.0477 | 0.0880 | 0.5420 | 0.750 | 0.0664 | 0.5305 | 0.750 |
| 20 | 0.0669 | 0.0600 | 1.1149 | 0.917 | 0.1147 | 1.3381 | 0.917 |
| 40 | 0.0631 | 0.1012 | 0.6241 | 0.833 | 0.1203 | 0.9438 | 0.875 |
| 60 | 0.0759 | 0.1048 | 0.7242 | 0.875 | 0.1383 | 1.0769 | 0.917 |

quantile mean forward 20d returns: Q1: -0.01002  Q2: -0.00498  Q3: 0.00624  Q4: 0.00798  Q5: 0.01532
Q5-Q1 long-short (gross, monthly): mean 0.02534, ann 0.3154, Sharpe 4.062, MDD -0.0211
top-quintile turnover: 0.344

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0810 | 0.874 | 0.833 |
| 2023 | 12 | 0.1483 | 2.396 | 1.000 |

regime split: up-market IC 0.1412 (n=13) / down-market IC 0.0834 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 1.000
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0062 | 0.1401 | 0.0443 | 0.625 | 0.0195 | 0.1107 | 0.708 |
| 5 | 0.0212 | 0.1715 | 0.1235 | 0.667 | 0.0404 | 0.2054 | 0.667 |
| 10 | 0.0286 | 0.1838 | 0.1554 | 0.625 | 0.0515 | 0.2251 | 0.625 |
| 20 | 0.0229 | 0.1472 | 0.1554 | 0.500 | 0.0428 | 0.2327 | 0.625 |
| 40 | 0.0366 | 0.1161 | 0.3148 | 0.583 | 0.0634 | 0.4527 | 0.667 |
| 60 | 0.0439 | 0.1060 | 0.4139 | 0.667 | 0.0820 | 0.6434 | 0.708 |

quantile mean forward 20d returns: Q1: 0.03441  Q2: 0.02759  Q3: 0.03805  Q4: 0.03307  Q5: 0.03760
Q5-Q1 long-short (gross, monthly): mean 0.00319, ann 0.0880, Sharpe 0.468, MDD -0.1107
top-quintile turnover: 0.354

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0108 | 0.055 | 0.500 |
| 2025 | 12 | 0.0748 | 0.459 | 0.750 |

regime split: up-market IC 0.0247 (n=15) / down-market IC 0.0731 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0040 | 0.1142 | -0.0350 | 0.583 | 0.0195 | 0.1107 | 0.708 |
| 5 | 0.0164 | 0.1397 | 0.1174 | 0.667 | 0.0404 | 0.2054 | 0.667 |
| 10 | 0.0311 | 0.1538 | 0.2021 | 0.625 | 0.0515 | 0.2251 | 0.625 |
| 20 | 0.0274 | 0.1356 | 0.2022 | 0.500 | 0.0428 | 0.2327 | 0.625 |
| 40 | 0.0431 | 0.1155 | 0.3734 | 0.583 | 0.0634 | 0.4527 | 0.667 |
| 60 | 0.0538 | 0.1077 | 0.4999 | 0.708 | 0.0820 | 0.6434 | 0.708 |

quantile mean forward 20d returns: Q1: 0.03441  Q2: 0.02759  Q3: 0.03806  Q4: 0.03306  Q5: 0.03760
Q5-Q1 long-short (gross, monthly): mean 0.00319, ann 0.0880, Sharpe 0.468, MDD -0.1107
top-quintile turnover: 0.354

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0108 | 0.055 | 0.500 |
| 2025 | 12 | 0.0748 | 0.459 | 0.750 |

regime split: up-market IC 0.0247 (n=15) / down-market IC 0.0731 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`amount_60`: -0.914  `amount_20`: -0.910  `momentum_120`: -0.291  `high_52w_proximity`: -0.253  `net_margin`: -0.239

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.