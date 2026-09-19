# factor_report_kurtosis_60.md

## definition

- factor: `kurtosis_60`  ·  category: microstructure  ·  version 1.0
- formula: `kurt(returns, 60d)`
- source: market  ·  PIT: True
- required fields: close, factor
- description: 收益峰度（尾部厚度 / 极端波动频率）
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 1.000
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0025 | 0.0643 | 0.0383 | 0.458 | 0.0029 | 0.0412 | 0.417 |
| 5 | 0.0005 | 0.0718 | 0.0071 | 0.417 | 0.0072 | 0.0836 | 0.542 |
| 10 | 0.0039 | 0.0628 | 0.0614 | 0.396 | 0.0147 | 0.1875 | 0.479 |
| 20 | 0.0100 | 0.0688 | 0.1457 | 0.479 | 0.0236 | 0.2832 | 0.562 |
| 40 | 0.0071 | 0.0658 | 0.1079 | 0.458 | 0.0185 | 0.2288 | 0.521 |
| 60 | 0.0050 | 0.0716 | 0.0700 | 0.458 | 0.0175 | 0.2065 | 0.479 |

quantile mean forward 20d returns: Q1: 0.00797  Q2: 0.01098  Q3: 0.01358  Q4: 0.01297  Q5: 0.01023
Q5-Q1 long-short (gross, monthly): mean 0.00226, ann 0.0291, Sharpe 0.362, MDD -0.1621
top-quintile turnover: 0.546

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0402 | 0.432 | 0.583 |
| 2019 | 12 | 0.0127 | 0.218 | 0.500 |
| 2020 | 12 | 0.0351 | 0.322 | 0.667 |
| 2021 | 12 | 0.0063 | 0.116 | 0.500 |

regime split: up-market IC 0.0190 (n=28) / down-market IC 0.0300 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0002 | 0.0654 | -0.0035 | 0.438 | 0.0029 | 0.0413 | 0.417 |
| 5 | -0.0048 | 0.0680 | -0.0706 | 0.396 | 0.0072 | 0.0835 | 0.542 |
| 10 | -0.0013 | 0.0599 | -0.0218 | 0.438 | 0.0147 | 0.1874 | 0.479 |
| 20 | 0.0060 | 0.0618 | 0.0977 | 0.458 | 0.0235 | 0.2830 | 0.562 |
| 40 | 0.0039 | 0.0616 | 0.0632 | 0.417 | 0.0184 | 0.2287 | 0.521 |
| 60 | 0.0033 | 0.0675 | 0.0485 | 0.417 | 0.0175 | 0.2065 | 0.479 |

quantile mean forward 20d returns: Q1: 0.00797  Q2: 0.01098  Q3: 0.01357  Q4: 0.01300  Q5: 0.01021
Q5-Q1 long-short (gross, monthly): mean 0.00224, ann 0.0288, Sharpe 0.359, MDD -0.1621
top-quintile turnover: 0.546

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0401 | 0.431 | 0.583 |
| 2019 | 12 | 0.0126 | 0.218 | 0.500 |
| 2020 | 12 | 0.0351 | 0.322 | 0.667 |
| 2021 | 12 | 0.0063 | 0.116 | 0.500 |

regime split: up-market IC 0.0190 (n=28) / down-market IC 0.0300 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 1.000
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0047 | 0.0345 | 0.1362 | 0.625 | 0.0020 | 0.0477 | 0.458 |
| 5 | 0.0012 | 0.0425 | 0.0284 | 0.458 | -0.0002 | -0.0043 | 0.458 |
| 10 | 0.0114 | 0.0340 | 0.3356 | 0.542 | 0.0118 | 0.2667 | 0.625 |
| 20 | 0.0051 | 0.0233 | 0.2207 | 0.542 | 0.0040 | 0.1165 | 0.417 |
| 40 | 0.0020 | 0.0280 | 0.0721 | 0.458 | 0.0049 | 0.1270 | 0.500 |
| 60 | 0.0023 | 0.0312 | 0.0740 | 0.417 | 0.0070 | 0.1614 | 0.542 |

quantile mean forward 20d returns: Q1: 0.00183  Q2: 0.00027  Q3: 0.00630  Q4: 0.00317  Q5: 0.00298
Q5-Q1 long-short (gross, monthly): mean 0.00115, ann 0.0044, Sharpe 0.163, MDD -0.0388
top-quintile turnover: 0.559

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0245 | 0.691 | 0.667 |
| 2023 | 12 | -0.0164 | -0.923 | 0.167 |

regime split: up-market IC 0.0048 (n=13) / down-market IC 0.0032 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0067 | 0.0304 | 0.2205 | 0.625 | 0.0020 | 0.0478 | 0.458 |
| 5 | 0.0018 | 0.0374 | 0.0493 | 0.500 | -0.0002 | -0.0042 | 0.458 |
| 10 | 0.0097 | 0.0328 | 0.2962 | 0.625 | 0.0117 | 0.2666 | 0.625 |
| 20 | 0.0038 | 0.0266 | 0.1439 | 0.583 | 0.0040 | 0.1167 | 0.417 |
| 40 | -0.0008 | 0.0274 | -0.0308 | 0.417 | 0.0049 | 0.1272 | 0.500 |
| 60 | -0.0016 | 0.0302 | -0.0526 | 0.417 | 0.0070 | 0.1614 | 0.542 |

quantile mean forward 20d returns: Q1: 0.00183  Q2: 0.00026  Q3: 0.00632  Q4: 0.00316  Q5: 0.00298
Q5-Q1 long-short (gross, monthly): mean 0.00115, ann 0.0044, Sharpe 0.163, MDD -0.0388
top-quintile turnover: 0.559

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0245 | 0.691 | 0.667 |
| 2023 | 12 | -0.0164 | -0.922 | 0.167 |

regime split: up-market IC 0.0048 (n=13) / down-market IC 0.0032 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 1.000
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0051 | 0.1012 | 0.0508 | 0.458 | -0.0001 | -0.0009 | 0.458 |
| 5 | 0.0050 | 0.0567 | 0.0880 | 0.625 | 0.0157 | 0.2409 | 0.625 |
| 10 | -0.0012 | 0.0639 | -0.0189 | 0.542 | 0.0117 | 0.1376 | 0.542 |
| 20 | 0.0087 | 0.0711 | 0.1223 | 0.625 | 0.0208 | 0.2199 | 0.625 |
| 40 | 0.0238 | 0.0575 | 0.4139 | 0.708 | 0.0397 | 0.4930 | 0.625 |
| 60 | 0.0276 | 0.0499 | 0.5532 | 0.708 | 0.0449 | 0.6341 | 0.667 |

quantile mean forward 20d returns: Q1: 0.03057  Q2: 0.03278  Q3: 0.04059  Q4: 0.03145  Q5: 0.03532
Q5-Q1 long-short (gross, monthly): mean 0.00475, ann 0.0876, Sharpe 0.905, MDD -0.0386
top-quintile turnover: 0.596

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0016 | -0.015 | 0.417 |
| 2025 | 12 | 0.0433 | 0.574 | 0.833 |

regime split: up-market IC 0.0192 (n=15) / down-market IC 0.0235 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0075 | 0.0933 | 0.0802 | 0.500 | -0.0001 | -0.0009 | 0.458 |
| 5 | 0.0037 | 0.0519 | 0.0721 | 0.542 | 0.0157 | 0.2410 | 0.625 |
| 10 | -0.0036 | 0.0559 | -0.0636 | 0.458 | 0.0117 | 0.1376 | 0.542 |
| 20 | 0.0077 | 0.0630 | 0.1228 | 0.583 | 0.0208 | 0.2199 | 0.625 |
| 40 | 0.0166 | 0.0544 | 0.3060 | 0.625 | 0.0397 | 0.4930 | 0.625 |
| 60 | 0.0175 | 0.0485 | 0.3607 | 0.542 | 0.0449 | 0.6342 | 0.667 |

quantile mean forward 20d returns: Q1: 0.03057  Q2: 0.03279  Q3: 0.04059  Q4: 0.03145  Q5: 0.03532
Q5-Q1 long-short (gross, monthly): mean 0.00475, ann 0.0876, Sharpe 0.905, MDD -0.0386
top-quintile turnover: 0.596

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0016 | -0.015 | 0.417 |
| 2025 | 12 | 0.0433 | 0.574 | 0.833 |

regime split: up-market IC 0.0192 (n=15) / down-market IC 0.0235 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`amount_60`: -0.175  `momentum_120`: -0.158  `amount_20`: -0.158  `downside_volatility_60`: -0.145  `max_return_20`: -0.117

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.