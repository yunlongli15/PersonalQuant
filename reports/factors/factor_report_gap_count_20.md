# factor_report_gap_count_20.md

## definition

- factor: `gap_count_20`  ·  category: microstructure  ·  version 1.0
- formula: `count(|open/prev_close-1| > 3%, 20d) / 20`
- source: market  ·  PIT: True
- required fields: open, close, factor
- description: 跳空频率（信息冲击的连续性 / 情绪化交易程度）
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 1.000
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0081 | 0.0187 | 0.4335 | 0.667 | 0.0085 | 0.4045 | 0.604 |
| 5 | 0.0020 | 0.0217 | 0.0916 | 0.521 | 0.0032 | 0.1300 | 0.542 |
| 10 | 0.0038 | 0.0188 | 0.2032 | 0.542 | 0.0034 | 0.1558 | 0.521 |
| 20 | 0.0035 | 0.0190 | 0.1834 | 0.562 | 0.0017 | 0.0826 | 0.521 |
| 40 | 0.0057 | 0.0201 | 0.2827 | 0.583 | 0.0036 | 0.1612 | 0.500 |
| 60 | 0.0079 | 0.0198 | 0.4008 | 0.708 | 0.0051 | 0.2247 | 0.583 |

quantile mean forward 20d returns: Q1: 0.00898  Q2: 0.01157  Q3: 0.01677  Q4: 0.00853  Q5: 0.00987
Q5-Q1 long-short (gross, monthly): mean 0.00089, ann 0.0098, Sharpe 0.104, MDD -0.1189
top-quintile turnover: 0.007

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0023 | -0.086 | 0.333 |
| 2019 | 12 | 0.0053 | 0.393 | 0.667 |
| 2020 | 12 | 0.0056 | 0.287 | 0.667 |
| 2021 | 12 | -0.0017 | -0.082 | 0.417 |

regime split: up-market IC 0.0046 (n=28) / down-market IC -0.0022 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0054 | 0.0175 | 0.3087 | 0.646 | 0.0085 | 0.4051 | 0.604 |
| 5 | 0.0009 | 0.0180 | 0.0525 | 0.604 | 0.0032 | 0.1301 | 0.542 |
| 10 | 0.0027 | 0.0168 | 0.1607 | 0.604 | 0.0034 | 0.1561 | 0.521 |
| 20 | 0.0028 | 0.0185 | 0.1488 | 0.583 | 0.0017 | 0.0831 | 0.521 |
| 40 | 0.0035 | 0.0192 | 0.1836 | 0.562 | 0.0036 | 0.1615 | 0.500 |
| 60 | 0.0052 | 0.0185 | 0.2832 | 0.625 | 0.0051 | 0.2250 | 0.583 |

quantile mean forward 20d returns: Q1: 0.00898  Q2: 0.01157  Q3: 0.01677  Q4: 0.00853  Q5: 0.00987
Q5-Q1 long-short (gross, monthly): mean 0.00089, ann 0.0098, Sharpe 0.104, MDD -0.1189
top-quintile turnover: 0.007

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0023 | -0.085 | 0.333 |
| 2019 | 12 | 0.0053 | 0.392 | 0.667 |
| 2020 | 12 | 0.0056 | 0.288 | 0.667 |
| 2021 | 12 | -0.0017 | -0.082 | 0.417 |

regime split: up-market IC 0.0046 (n=28) / down-market IC -0.0022 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0007 | 0.0163 | 0.0399 | 0.458 | -0.0006 | -0.0288 | 0.500 |
| 5 | 0.0018 | 0.0222 | 0.0816 | 0.583 | 0.0030 | 0.1112 | 0.500 |
| 10 | 0.0015 | 0.0200 | 0.0757 | 0.542 | 0.0015 | 0.0633 | 0.417 |
| 20 | 0.0025 | 0.0219 | 0.1154 | 0.542 | -0.0009 | -0.0340 | 0.458 |
| 40 | 0.0040 | 0.0241 | 0.1665 | 0.583 | 0.0025 | 0.0960 | 0.583 |
| 60 | 0.0021 | 0.0210 | 0.1021 | 0.625 | 0.0000 | 0.0018 | 0.583 |

quantile mean forward 20d returns: Q1: 0.00305  Q2: 0.00352  Q3: 0.00039  Q4: 0.00419  Q5: 0.00339
Q5-Q1 long-short (gross, monthly): mean 0.00034, ann 0.0158, Sharpe 0.101, MDD -0.0948
top-quintile turnover: 0.005

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0059 | 0.249 | 0.583 |
| 2023 | 12 | -0.0076 | -0.293 | 0.333 |

regime split: up-market IC 0.0076 (n=13) / down-market IC -0.0109 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0017 | 0.0151 | 0.1103 | 0.458 | -0.0006 | -0.0288 | 0.500 |
| 5 | 0.0049 | 0.0204 | 0.2422 | 0.708 | 0.0030 | 0.1115 | 0.500 |
| 10 | 0.0039 | 0.0191 | 0.2054 | 0.625 | 0.0016 | 0.0637 | 0.417 |
| 20 | 0.0030 | 0.0210 | 0.1426 | 0.583 | -0.0009 | -0.0335 | 0.458 |
| 40 | 0.0041 | 0.0238 | 0.1730 | 0.625 | 0.0025 | 0.0966 | 0.583 |
| 60 | 0.0027 | 0.0198 | 0.1371 | 0.667 | 0.0001 | 0.0027 | 0.583 |

quantile mean forward 20d returns: Q1: 0.00305  Q2: 0.00352  Q3: 0.00039  Q4: 0.00419  Q5: 0.00339
Q5-Q1 long-short (gross, monthly): mean 0.00034, ann 0.0158, Sharpe 0.101, MDD -0.0948
top-quintile turnover: 0.005

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0059 | 0.249 | 0.583 |
| 2023 | 12 | -0.0076 | -0.292 | 0.333 |

regime split: up-market IC 0.0076 (n=13) / down-market IC -0.0109 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 1.000
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0063 | 0.0286 | 0.2213 | 0.583 | 0.0050 | 0.1644 | 0.583 |
| 5 | -0.0014 | 0.0218 | -0.0620 | 0.417 | -0.0057 | -0.2298 | 0.333 |
| 10 | 0.0036 | 0.0237 | 0.1499 | 0.625 | 0.0021 | 0.0799 | 0.625 |
| 20 | 0.0092 | 0.0173 | 0.5316 | 0.667 | 0.0074 | 0.3494 | 0.542 |
| 40 | 0.0042 | 0.0164 | 0.2535 | 0.625 | 0.0037 | 0.1751 | 0.500 |
| 60 | 0.0059 | 0.0196 | 0.3016 | 0.625 | 0.0061 | 0.2791 | 0.542 |

quantile mean forward 20d returns: Q1: 0.02873  Q2: 0.03668  Q3: 0.03504  Q4: 0.02630  Q5: 0.04397
Q5-Q1 long-short (gross, monthly): mean 0.01524, ann 0.1816, Sharpe 1.029, MDD -0.0985
top-quintile turnover: 0.009

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0070 | 0.333 | 0.417 |
| 2025 | 12 | 0.0078 | 0.366 | 0.667 |

regime split: up-market IC 0.0108 (n=15) / down-market IC 0.0017 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0034 | 0.0228 | 0.1507 | 0.542 | 0.0050 | 0.1645 | 0.583 |
| 5 | -0.0043 | 0.0178 | -0.2402 | 0.417 | -0.0057 | -0.2299 | 0.333 |
| 10 | 0.0021 | 0.0212 | 0.0967 | 0.583 | 0.0021 | 0.0797 | 0.625 |
| 20 | 0.0072 | 0.0137 | 0.5235 | 0.667 | 0.0074 | 0.3497 | 0.542 |
| 40 | 0.0055 | 0.0140 | 0.3903 | 0.583 | 0.0037 | 0.1752 | 0.500 |
| 60 | 0.0078 | 0.0160 | 0.4890 | 0.625 | 0.0060 | 0.2788 | 0.542 |

quantile mean forward 20d returns: Q1: 0.02873  Q2: 0.03668  Q3: 0.03504  Q4: 0.02630  Q5: 0.04397
Q5-Q1 long-short (gross, monthly): mean 0.01524, ann 0.1816, Sharpe 1.029, MDD -0.0985
top-quintile turnover: 0.009

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0070 | 0.333 | 0.417 |
| 2025 | 12 | 0.0078 | 0.367 | 0.667 |

regime split: up-market IC 0.0108 (n=15) / down-market IC 0.0017 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`overnight_intraday_ratio_20`: 0.148  `overnight_return_20`: 0.147  `intraday_return_20`: -0.147  `operating_cash_flow`: 0.094  `pe`: -0.083

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.