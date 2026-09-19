# factor_report_intraday_return_20.md

## definition

- factor: `intraday_return_20`  ·  category: microstructure  ·  version 1.0
- formula: `mean(adj_close[t]/open[t]-1, 20d)`
- source: market  ·  PIT: True
- required fields: open, close, factor
- description: 20 日平均日内收益（收盘/开盘-1）—— A 股日内部分常延续
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0119 | 0.0529 | -0.2251 | 0.375 | -0.0131 | -0.2035 | 0.417 |
| 5 | -0.0023 | 0.0763 | -0.0304 | 0.438 | -0.0035 | -0.0360 | 0.396 |
| 10 | -0.0062 | 0.0734 | -0.0843 | 0.438 | -0.0052 | -0.0555 | 0.458 |
| 20 | -0.0123 | 0.0779 | -0.1578 | 0.438 | -0.0093 | -0.0924 | 0.458 |
| 40 | -0.0156 | 0.0815 | -0.1916 | 0.375 | -0.0095 | -0.0917 | 0.479 |
| 60 | -0.0178 | 0.0864 | -0.2063 | 0.396 | -0.0092 | -0.0865 | 0.417 |

quantile mean forward 20d returns: Q1: 0.01252  Q2: 0.01369  Q3: 0.01134  Q4: 0.00937  Q5: 0.00880
Q5-Q1 long-short (gross, monthly): mean -0.00372, ann -0.0464, Sharpe -0.485, MDD -0.2312
top-quintile turnover: 0.067

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0135 | -0.122 | 0.417 |
| 2019 | 12 | -0.0367 | -0.483 | 0.333 |
| 2020 | 12 | 0.0053 | 0.057 | 0.500 |
| 2021 | 12 | 0.0077 | 0.067 | 0.583 |

regime split: up-market IC -0.0219 (n=28) / down-market IC 0.0083 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0140 | 0.0557 | -0.2521 | 0.417 | -0.0131 | -0.2034 | 0.417 |
| 5 | -0.0070 | 0.0730 | -0.0959 | 0.417 | -0.0035 | -0.0360 | 0.396 |
| 10 | -0.0102 | 0.0667 | -0.1531 | 0.438 | -0.0052 | -0.0555 | 0.458 |
| 20 | -0.0104 | 0.0701 | -0.1491 | 0.438 | -0.0093 | -0.0923 | 0.458 |
| 40 | -0.0132 | 0.0720 | -0.1837 | 0.417 | -0.0095 | -0.0917 | 0.479 |
| 60 | -0.0132 | 0.0743 | -0.1783 | 0.375 | -0.0092 | -0.0865 | 0.417 |

quantile mean forward 20d returns: Q1: 0.01252  Q2: 0.01368  Q3: 0.01134  Q4: 0.00938  Q5: 0.00880
Q5-Q1 long-short (gross, monthly): mean -0.00372, ann -0.0464, Sharpe -0.486, MDD -0.2313
top-quintile turnover: 0.066

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0135 | -0.122 | 0.417 |
| 2019 | 12 | -0.0367 | -0.484 | 0.333 |
| 2020 | 12 | 0.0053 | 0.057 | 0.500 |
| 2021 | 12 | 0.0077 | 0.067 | 0.583 |

regime split: up-market IC -0.0219 (n=28) / down-market IC 0.0083 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 1.000
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0128 | 0.0874 | 0.1466 | 0.542 | 0.0234 | 0.2110 | 0.625 |
| 5 | 0.0038 | 0.1187 | 0.0321 | 0.500 | 0.0163 | 0.1114 | 0.583 |
| 10 | 0.0038 | 0.0956 | 0.0398 | 0.500 | 0.0194 | 0.1577 | 0.542 |
| 20 | 0.0149 | 0.1173 | 0.1271 | 0.500 | 0.0246 | 0.1734 | 0.500 |
| 40 | 0.0142 | 0.1196 | 0.1185 | 0.417 | 0.0263 | 0.1837 | 0.458 |
| 60 | 0.0196 | 0.0995 | 0.1964 | 0.417 | 0.0381 | 0.3066 | 0.500 |

quantile mean forward 20d returns: Q1: -0.00219  Q2: 0.00327  Q3: 0.00827  Q4: 0.00390  Q5: 0.00130
Q5-Q1 long-short (gross, monthly): mean 0.00349, ann 0.0087, Sharpe 0.062, MDD -0.1975
top-quintile turnover: 0.030

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0002 | 0.001 | 0.500 |
| 2023 | 12 | 0.0491 | 0.351 | 0.500 |

regime split: up-market IC -0.0376 (n=13) / down-market IC 0.0982 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0040 | 0.0735 | 0.0546 | 0.500 | 0.0234 | 0.2109 | 0.625 |
| 5 | -0.0045 | 0.0961 | -0.0466 | 0.500 | 0.0163 | 0.1114 | 0.583 |
| 10 | -0.0030 | 0.0831 | -0.0365 | 0.500 | 0.0194 | 0.1577 | 0.542 |
| 20 | 0.0036 | 0.1081 | 0.0334 | 0.458 | 0.0247 | 0.1734 | 0.500 |
| 40 | 0.0035 | 0.1091 | 0.0320 | 0.417 | 0.0263 | 0.1838 | 0.458 |
| 60 | 0.0073 | 0.0922 | 0.0796 | 0.417 | 0.0381 | 0.3065 | 0.500 |

quantile mean forward 20d returns: Q1: -0.00218  Q2: 0.00326  Q3: 0.00827  Q4: 0.00390  Q5: 0.00130
Q5-Q1 long-short (gross, monthly): mean 0.00348, ann 0.0086, Sharpe 0.062, MDD -0.1975
top-quintile turnover: 0.030

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0002 | 0.001 | 0.500 |
| 2023 | 12 | 0.0491 | 0.351 | 0.500 |

regime split: up-market IC -0.0376 (n=13) / down-market IC 0.0982 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0256 | 0.1083 | -0.2360 | 0.375 | -0.0230 | -0.1781 | 0.375 |
| 5 | 0.0429 | 0.1088 | 0.3945 | 0.625 | 0.0557 | 0.3886 | 0.667 |
| 10 | 0.0076 | 0.0998 | 0.0763 | 0.500 | 0.0080 | 0.0605 | 0.542 |
| 20 | -0.0215 | 0.0776 | -0.2771 | 0.292 | -0.0192 | -0.1833 | 0.458 |
| 40 | -0.0168 | 0.0871 | -0.1927 | 0.417 | -0.0152 | -0.1318 | 0.375 |
| 60 | -0.0291 | 0.0859 | -0.3393 | 0.292 | -0.0301 | -0.2709 | 0.292 |

quantile mean forward 20d returns: Q1: 0.03797  Q2: 0.03379  Q3: 0.04064  Q4: 0.03064  Q5: 0.02770
Q5-Q1 long-short (gross, monthly): mean -0.01027, ann -0.1195, Sharpe -1.111, MDD -0.2683
top-quintile turnover: 0.025

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0088 | -0.078 | 0.500 |
| 2025 | 12 | -0.0295 | -0.312 | 0.417 |

regime split: up-market IC -0.0596 (n=15) / down-market IC 0.0483 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0236 | 0.0911 | -0.2588 | 0.333 | -0.0230 | -0.1780 | 0.375 |
| 5 | 0.0320 | 0.1011 | 0.3164 | 0.625 | 0.0557 | 0.3886 | 0.667 |
| 10 | 0.0008 | 0.0901 | 0.0090 | 0.542 | 0.0080 | 0.0605 | 0.542 |
| 20 | -0.0217 | 0.0630 | -0.3440 | 0.333 | -0.0191 | -0.1833 | 0.458 |
| 40 | -0.0180 | 0.0651 | -0.2762 | 0.375 | -0.0152 | -0.1317 | 0.375 |
| 60 | -0.0296 | 0.0630 | -0.4700 | 0.292 | -0.0301 | -0.2709 | 0.292 |

quantile mean forward 20d returns: Q1: 0.03797  Q2: 0.03379  Q3: 0.04064  Q4: 0.03064  Q5: 0.02769
Q5-Q1 long-short (gross, monthly): mean -0.01028, ann -0.1195, Sharpe -1.112, MDD -0.2683
top-quintile turnover: 0.025

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0088 | -0.078 | 0.500 |
| 2025 | 12 | -0.0295 | -0.312 | 0.417 |

regime split: up-market IC -0.0596 (n=15) / down-market IC 0.0483 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`gap_count_20`: -0.147  `downside_volatility_60`: -0.145  `amihud_20`: -0.107  `max_return_20`: -0.085  `high_52w_proximity`: 0.061

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.