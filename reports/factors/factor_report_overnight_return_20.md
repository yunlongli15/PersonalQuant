# factor_report_overnight_return_20.md

## definition

- factor: `overnight_return_20`  ·  category: microstructure  ·  version 1.0
- formula: `mean(open[t]/adj_close[t-1]-1, 20d)`
- source: market  ·  PIT: True
- required fields: open, close, factor
- description: 20 日平均隔夜收益（开盘/昨收-1）—— A 股隔夜部分常反转
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 1.000
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0120 | 0.0530 | 0.2261 | 0.625 | 0.0129 | 0.2001 | 0.583 |
| 5 | 0.0022 | 0.0762 | 0.0290 | 0.583 | 0.0031 | 0.0324 | 0.604 |
| 10 | 0.0060 | 0.0734 | 0.0820 | 0.562 | 0.0048 | 0.0513 | 0.542 |
| 20 | 0.0120 | 0.0780 | 0.1534 | 0.562 | 0.0088 | 0.0873 | 0.542 |
| 40 | 0.0153 | 0.0816 | 0.1878 | 0.625 | 0.0090 | 0.0868 | 0.521 |
| 60 | 0.0176 | 0.0864 | 0.2040 | 0.604 | 0.0088 | 0.0827 | 0.583 |

quantile mean forward 20d returns: Q1: 0.00885  Q2: 0.00937  Q3: 0.01130  Q4: 0.01375  Q5: 0.01245
Q5-Q1 long-short (gross, monthly): mean 0.00360, ann 0.0376, Sharpe 0.393, MDD -0.1246
top-quintile turnover: 0.072

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0129 | 0.116 | 0.583 |
| 2019 | 12 | 0.0362 | 0.474 | 0.667 |
| 2020 | 12 | -0.0055 | -0.059 | 0.500 |
| 2021 | 12 | -0.0082 | -0.072 | 0.417 |

regime split: up-market IC 0.0214 (n=28) / down-market IC -0.0087 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0021 | 0.0427 | 0.0488 | 0.604 | 0.0129 | 0.2002 | 0.583 |
| 5 | -0.0086 | 0.0602 | -0.1430 | 0.521 | 0.0031 | 0.0323 | 0.604 |
| 10 | -0.0036 | 0.0636 | -0.0561 | 0.562 | 0.0048 | 0.0512 | 0.542 |
| 20 | 0.0061 | 0.0663 | 0.0924 | 0.583 | 0.0088 | 0.0871 | 0.542 |
| 40 | 0.0082 | 0.0735 | 0.1119 | 0.583 | 0.0090 | 0.0866 | 0.521 |
| 60 | 0.0119 | 0.0777 | 0.1532 | 0.583 | 0.0088 | 0.0825 | 0.583 |

quantile mean forward 20d returns: Q1: 0.00885  Q2: 0.00936  Q3: 0.01131  Q4: 0.01375  Q5: 0.01245
Q5-Q1 long-short (gross, monthly): mean 0.00360, ann 0.0376, Sharpe 0.393, MDD -0.1247
top-quintile turnover: 0.072

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0128 | 0.116 | 0.583 |
| 2019 | 12 | 0.0362 | 0.474 | 0.667 |
| 2020 | 12 | -0.0055 | -0.059 | 0.500 |
| 2021 | 12 | -0.0083 | -0.072 | 0.417 |

regime split: up-market IC 0.0214 (n=28) / down-market IC -0.0088 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0129 | 0.0873 | -0.1476 | 0.458 | -0.0236 | -0.2128 | 0.375 |
| 5 | -0.0040 | 0.1184 | -0.0337 | 0.500 | -0.0166 | -0.1141 | 0.417 |
| 10 | -0.0041 | 0.0955 | -0.0426 | 0.500 | -0.0198 | -0.1612 | 0.458 |
| 20 | -0.0151 | 0.1173 | -0.1291 | 0.500 | -0.0250 | -0.1763 | 0.500 |
| 40 | -0.0145 | 0.1196 | -0.1212 | 0.583 | -0.0268 | -0.1871 | 0.542 |
| 60 | -0.0199 | 0.0995 | -0.1996 | 0.583 | -0.0385 | -0.3103 | 0.458 |

quantile mean forward 20d returns: Q1: 0.00135  Q2: 0.00391  Q3: 0.00834  Q4: 0.00315  Q5: -0.00220
Q5-Q1 long-short (gross, monthly): mean -0.00355, ann -0.0275, Sharpe -0.197, MDD -0.1518
top-quintile turnover: 0.058

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0008 | -0.005 | 0.500 |
| 2023 | 12 | -0.0493 | -0.352 | 0.500 |

regime split: up-market IC 0.0370 (n=13) / down-market IC -0.0984 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0192 | 0.0847 | -0.2268 | 0.375 | -0.0236 | -0.2127 | 0.375 |
| 5 | -0.0081 | 0.1145 | -0.0710 | 0.500 | -0.0166 | -0.1141 | 0.417 |
| 10 | -0.0113 | 0.0863 | -0.1308 | 0.417 | -0.0198 | -0.1611 | 0.458 |
| 20 | -0.0300 | 0.0924 | -0.3241 | 0.458 | -0.0250 | -0.1761 | 0.500 |
| 40 | -0.0322 | 0.0926 | -0.3478 | 0.458 | -0.0268 | -0.1870 | 0.542 |
| 60 | -0.0438 | 0.0779 | -0.5627 | 0.333 | -0.0385 | -0.3101 | 0.458 |

quantile mean forward 20d returns: Q1: 0.00133  Q2: 0.00393  Q3: 0.00834  Q4: 0.00316  Q5: -0.00221
Q5-Q1 long-short (gross, monthly): mean -0.00354, ann -0.0276, Sharpe -0.198, MDD -0.1518
top-quintile turnover: 0.058

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0007 | -0.005 | 0.500 |
| 2023 | 12 | -0.0493 | -0.352 | 0.500 |

regime split: up-market IC 0.0370 (n=13) / down-market IC -0.0983 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 1.000
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0255 | 0.1086 | 0.2348 | 0.625 | 0.0228 | 0.1758 | 0.625 |
| 5 | -0.0430 | 0.1088 | -0.3948 | 0.375 | -0.0559 | -0.3903 | 0.333 |
| 10 | -0.0078 | 0.0998 | -0.0776 | 0.500 | -0.0083 | -0.0632 | 0.458 |
| 20 | 0.0212 | 0.0776 | 0.2737 | 0.708 | 0.0187 | 0.1787 | 0.500 |
| 40 | 0.0166 | 0.0873 | 0.1900 | 0.583 | 0.0147 | 0.1279 | 0.625 |
| 60 | 0.0289 | 0.0860 | 0.3361 | 0.708 | 0.0296 | 0.2668 | 0.708 |

quantile mean forward 20d returns: Q1: 0.02760  Q2: 0.03080  Q3: 0.04061  Q4: 0.03375  Q5: 0.03796
Q5-Q1 long-short (gross, monthly): mean 0.01036, ann 0.1221, Sharpe 1.141, MDD -0.0686
top-quintile turnover: 0.028

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0082 | 0.073 | 0.417 |
| 2025 | 12 | 0.0291 | 0.307 | 0.583 |

regime split: up-market IC 0.0590 (n=15) / down-market IC -0.0485 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0192 | 0.1028 | 0.1873 | 0.625 | 0.0228 | 0.1759 | 0.625 |
| 5 | -0.0407 | 0.0832 | -0.4890 | 0.250 | -0.0559 | -0.3902 | 0.333 |
| 10 | -0.0128 | 0.0845 | -0.1518 | 0.500 | -0.0083 | -0.0631 | 0.458 |
| 20 | 0.0120 | 0.0755 | 0.1586 | 0.542 | 0.0187 | 0.1787 | 0.500 |
| 40 | 0.0061 | 0.0806 | 0.0762 | 0.500 | 0.0147 | 0.1279 | 0.625 |
| 60 | 0.0147 | 0.0789 | 0.1857 | 0.583 | 0.0296 | 0.2667 | 0.708 |

quantile mean forward 20d returns: Q1: 0.02760  Q2: 0.03080  Q3: 0.04062  Q4: 0.03374  Q5: 0.03796
Q5-Q1 long-short (gross, monthly): mean 0.01036, ann 0.1221, Sharpe 1.141, MDD -0.0686
top-quintile turnover: 0.028

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0082 | 0.073 | 0.417 |
| 2025 | 12 | 0.0291 | 0.308 | 0.583 |

regime split: up-market IC 0.0590 (n=15) / down-market IC -0.0485 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`intraday_return_20`: -1.000  `gap_count_20`: 0.147  `downside_volatility_60`: 0.144  `amihud_20`: 0.107  `max_return_20`: 0.088

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.