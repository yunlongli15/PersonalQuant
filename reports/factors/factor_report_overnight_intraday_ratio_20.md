# factor_report_overnight_intraday_ratio_20.md

## definition

- factor: `overnight_intraday_ratio_20`  ·  category: microstructure  ·  version 1.0
- formula: `sum(overnight,20d) / sum(intraday,20d)`
- source: market  ·  PIT: True
- required fields: open, close, factor
- description: 隔夜与日内累计收益之比（口径相对化，跨股可比）
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 1.000
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0120 | 0.0530 | 0.2266 | 0.625 | 0.0128 | 0.1989 | 0.583 |
| 5 | 0.0022 | 0.0762 | 0.0285 | 0.583 | 0.0030 | 0.0313 | 0.604 |
| 10 | 0.0059 | 0.0734 | 0.0807 | 0.562 | 0.0047 | 0.0499 | 0.542 |
| 20 | 0.0118 | 0.0781 | 0.1510 | 0.562 | 0.0086 | 0.0850 | 0.542 |
| 40 | 0.0151 | 0.0815 | 0.1853 | 0.625 | 0.0087 | 0.0842 | 0.521 |
| 60 | 0.0174 | 0.0863 | 0.2015 | 0.604 | 0.0086 | 0.0802 | 0.583 |

quantile mean forward 20d returns: Q1: 0.00882  Q2: 0.00947  Q3: 0.01129  Q4: 0.01370  Q5: 0.01244
Q5-Q1 long-short (gross, monthly): mean 0.00363, ann 0.0379, Sharpe 0.395, MDD -0.1241
top-quintile turnover: 0.072

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0127 | 0.115 | 0.583 |
| 2019 | 12 | 0.0361 | 0.471 | 0.667 |
| 2020 | 12 | -0.0058 | -0.062 | 0.500 |
| 2021 | 12 | -0.0086 | -0.075 | 0.417 |

regime split: up-market IC 0.0211 (n=28) / down-market IC -0.0089 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0024 | 0.0429 | 0.0563 | 0.604 | 0.0128 | 0.1990 | 0.583 |
| 5 | -0.0082 | 0.0605 | -0.1350 | 0.521 | 0.0030 | 0.0313 | 0.604 |
| 10 | -0.0033 | 0.0637 | -0.0511 | 0.562 | 0.0047 | 0.0499 | 0.542 |
| 20 | 0.0062 | 0.0665 | 0.0936 | 0.583 | 0.0086 | 0.0848 | 0.542 |
| 40 | 0.0080 | 0.0736 | 0.1086 | 0.583 | 0.0087 | 0.0840 | 0.521 |
| 60 | 0.0116 | 0.0777 | 0.1490 | 0.583 | 0.0085 | 0.0800 | 0.583 |

quantile mean forward 20d returns: Q1: 0.00881  Q2: 0.00945  Q3: 0.01133  Q4: 0.01368  Q5: 0.01244
Q5-Q1 long-short (gross, monthly): mean 0.00363, ann 0.0379, Sharpe 0.394, MDD -0.1243
top-quintile turnover: 0.072

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0127 | 0.114 | 0.583 |
| 2019 | 12 | 0.0360 | 0.471 | 0.667 |
| 2020 | 12 | -0.0058 | -0.062 | 0.500 |
| 2021 | 12 | -0.0086 | -0.075 | 0.417 |

regime split: up-market IC 0.0211 (n=28) / down-market IC -0.0090 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0129 | 0.0873 | -0.1483 | 0.458 | -0.0237 | -0.2139 | 0.375 |
| 5 | -0.0041 | 0.1183 | -0.0349 | 0.500 | -0.0168 | -0.1153 | 0.417 |
| 10 | -0.0043 | 0.0954 | -0.0447 | 0.500 | -0.0200 | -0.1630 | 0.458 |
| 20 | -0.0152 | 0.1173 | -0.1300 | 0.500 | -0.0252 | -0.1774 | 0.500 |
| 40 | -0.0146 | 0.1195 | -0.1222 | 0.583 | -0.0270 | -0.1885 | 0.542 |
| 60 | -0.0200 | 0.0993 | -0.2012 | 0.583 | -0.0387 | -0.3121 | 0.458 |

quantile mean forward 20d returns: Q1: 0.00132  Q2: 0.00397  Q3: 0.00820  Q4: 0.00324  Q5: -0.00218
Q5-Q1 long-short (gross, monthly): mean -0.00350, ann -0.0270, Sharpe -0.194, MDD -0.1515
top-quintile turnover: 0.059

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0010 | -0.007 | 0.500 |
| 2023 | 12 | -0.0495 | -0.353 | 0.500 |

regime split: up-market IC 0.0368 (n=13) / down-market IC -0.0985 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0192 | 0.0849 | -0.2260 | 0.375 | -0.0237 | -0.2138 | 0.375 |
| 5 | -0.0081 | 0.1147 | -0.0703 | 0.500 | -0.0168 | -0.1153 | 0.417 |
| 10 | -0.0113 | 0.0865 | -0.1302 | 0.417 | -0.0200 | -0.1630 | 0.458 |
| 20 | -0.0299 | 0.0928 | -0.3223 | 0.458 | -0.0252 | -0.1774 | 0.500 |
| 40 | -0.0321 | 0.0928 | -0.3461 | 0.458 | -0.0270 | -0.1885 | 0.542 |
| 60 | -0.0438 | 0.0781 | -0.5608 | 0.333 | -0.0387 | -0.3121 | 0.458 |

quantile mean forward 20d returns: Q1: 0.00132  Q2: 0.00399  Q3: 0.00818  Q4: 0.00325  Q5: -0.00219
Q5-Q1 long-short (gross, monthly): mean -0.00351, ann -0.0271, Sharpe -0.195, MDD -0.1515
top-quintile turnover: 0.059

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0010 | -0.007 | 0.500 |
| 2023 | 12 | -0.0495 | -0.353 | 0.500 |

regime split: up-market IC 0.0368 (n=13) / down-market IC -0.0985 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 1.000
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0256 | 0.1088 | 0.2348 | 0.625 | 0.0227 | 0.1749 | 0.625 |
| 5 | -0.0429 | 0.1089 | -0.3944 | 0.375 | -0.0559 | -0.3904 | 0.333 |
| 10 | -0.0079 | 0.0999 | -0.0786 | 0.500 | -0.0085 | -0.0645 | 0.458 |
| 20 | 0.0211 | 0.0776 | 0.2724 | 0.667 | 0.0185 | 0.1767 | 0.500 |
| 40 | 0.0165 | 0.0873 | 0.1886 | 0.583 | 0.0145 | 0.1259 | 0.625 |
| 60 | 0.0288 | 0.0860 | 0.3352 | 0.708 | 0.0295 | 0.2657 | 0.667 |

quantile mean forward 20d returns: Q1: 0.02761  Q2: 0.03091  Q3: 0.04049  Q4: 0.03375  Q5: 0.03795
Q5-Q1 long-short (gross, monthly): mean 0.01034, ann 0.1218, Sharpe 1.137, MDD -0.0690
top-quintile turnover: 0.029

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0080 | 0.071 | 0.417 |
| 2025 | 12 | 0.0289 | 0.305 | 0.583 |

regime split: up-market IC 0.0587 (n=15) / down-market IC -0.0486 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0193 | 0.1029 | 0.1875 | 0.625 | 0.0227 | 0.1750 | 0.625 |
| 5 | -0.0407 | 0.0834 | -0.4885 | 0.250 | -0.0559 | -0.3904 | 0.333 |
| 10 | -0.0128 | 0.0845 | -0.1518 | 0.500 | -0.0085 | -0.0645 | 0.458 |
| 20 | 0.0120 | 0.0755 | 0.1594 | 0.542 | 0.0185 | 0.1767 | 0.500 |
| 40 | 0.0062 | 0.0807 | 0.0764 | 0.500 | 0.0145 | 0.1259 | 0.625 |
| 60 | 0.0147 | 0.0789 | 0.1869 | 0.583 | 0.0295 | 0.2655 | 0.667 |

quantile mean forward 20d returns: Q1: 0.02761  Q2: 0.03092  Q3: 0.04049  Q4: 0.03374  Q5: 0.03795
Q5-Q1 long-short (gross, monthly): mean 0.01034, ann 0.1218, Sharpe 1.137, MDD -0.0690
top-quintile turnover: 0.029

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0080 | 0.071 | 0.417 |
| 2025 | 12 | 0.0289 | 0.305 | 0.583 |

regime split: up-market IC 0.0587 (n=15) / down-market IC -0.0486 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`intraday_return_20`: -1.000  `gap_count_20`: 0.148  `downside_volatility_60`: 0.144  `amihud_20`: 0.106  `max_return_20`: 0.089

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.