# factor_report_news_attention_20d.md

## definition

- factor: `news_attention_20d`  ·  category: news  ·  version 1.0
- formula: `count(20d) / mean_count(60d)`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: 20-day attention vs 60d baseline
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.201
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0031 | 0.0676 | 0.0459 | 0.521 | 0.0013 | 0.0151 | 0.479 |
| 5 | 0.0003 | 0.0580 | 0.0043 | 0.458 | -0.0002 | -0.0023 | 0.417 |
| 10 | 0.0009 | 0.0506 | 0.0184 | 0.500 | 0.0009 | 0.0141 | 0.500 |
| 20 | 0.0053 | 0.0521 | 0.1018 | 0.479 | 0.0062 | 0.0970 | 0.542 |
| 40 | 0.0019 | 0.0537 | 0.0348 | 0.521 | 0.0018 | 0.0260 | 0.479 |
| 60 | 0.0067 | 0.0568 | 0.1186 | 0.500 | 0.0037 | 0.0507 | 0.438 |

quantile mean forward 20d returns: Q1: 0.01026  Q2: 0.00751  Q3: 0.01295  Q4: 0.01139  Q5: 0.01377
Q5-Q1 long-short (gross, monthly): mean 0.00352, ann 0.0418, Sharpe 0.378, MDD -0.1395
top-quintile turnover: 0.742

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0288 | -0.540 | 0.417 |
| 2019 | 12 | 0.0158 | 0.270 | 0.500 |
| 2020 | 12 | 0.0263 | 0.328 | 0.667 |
| 2021 | 12 | 0.0114 | 0.274 | 0.583 |

regime split: up-market IC 0.0152 (n=28) / down-market IC -0.0065 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0001 | 0.0687 | 0.0009 | 0.500 | -0.0015 | -0.0183 | 0.458 |
| 5 | 0.0010 | 0.0564 | 0.0176 | 0.500 | -0.0010 | -0.0139 | 0.438 |
| 10 | 0.0008 | 0.0479 | 0.0163 | 0.500 | -0.0002 | -0.0026 | 0.479 |
| 20 | 0.0021 | 0.0505 | 0.0415 | 0.500 | 0.0042 | 0.0662 | 0.521 |
| 40 | -0.0016 | 0.0534 | -0.0291 | 0.479 | -0.0015 | -0.0221 | 0.458 |
| 60 | 0.0025 | 0.0577 | 0.0438 | 0.542 | 0.0015 | 0.0210 | 0.438 |

quantile mean forward 20d returns: Q1: 0.01099  Q2: 0.00789  Q3: 0.01228  Q4: 0.01087  Q5: 0.01385
Q5-Q1 long-short (gross, monthly): mean 0.00286, ann 0.0332, Sharpe 0.291, MDD -0.1568
top-quintile turnover: 0.738

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0269 | -0.511 | 0.417 |
| 2019 | 12 | 0.0169 | 0.288 | 0.500 |
| 2020 | 12 | 0.0197 | 0.252 | 0.667 |
| 2021 | 12 | 0.0070 | 0.147 | 0.500 |

regime split: up-market IC 0.0105 (n=28) / down-market IC -0.0047 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.188
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0006 | 0.0611 | 0.0090 | 0.500 | 0.0105 | 0.1603 | 0.500 |
| 5 | -0.0077 | 0.0642 | -0.1195 | 0.458 | 0.0062 | 0.0845 | 0.500 |
| 10 | -0.0042 | 0.0600 | -0.0702 | 0.458 | 0.0118 | 0.1719 | 0.542 |
| 20 | 0.0043 | 0.0637 | 0.0676 | 0.625 | 0.0269 | 0.3819 | 0.667 |
| 40 | -0.0026 | 0.0732 | -0.0349 | 0.542 | 0.0118 | 0.1598 | 0.583 |
| 60 | 0.0015 | 0.0638 | 0.0231 | 0.583 | 0.0099 | 0.1488 | 0.542 |

quantile mean forward 20d returns: Q1: -0.00320  Q2: -0.00181  Q3: 0.00987  Q4: 0.00703  Q5: -0.00235
Q5-Q1 long-short (gross, monthly): mean 0.00085, ann 0.0207, Sharpe 0.182, MDD -0.1180
top-quintile turnover: 0.753

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0514 | 0.881 | 0.833 |
| 2023 | 12 | 0.0025 | 0.034 | 0.500 |

regime split: up-market IC 0.0313 (n=13) / down-market IC 0.0217 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0005 | 0.0598 | 0.0088 | 0.500 | 0.0087 | 0.1284 | 0.542 |
| 5 | -0.0035 | 0.0618 | -0.0564 | 0.458 | 0.0075 | 0.1048 | 0.458 |
| 10 | 0.0006 | 0.0589 | 0.0100 | 0.500 | 0.0129 | 0.1884 | 0.542 |
| 20 | 0.0123 | 0.0661 | 0.1858 | 0.708 | 0.0287 | 0.4194 | 0.708 |
| 40 | 0.0042 | 0.0705 | 0.0597 | 0.583 | 0.0112 | 0.1493 | 0.583 |
| 60 | 0.0077 | 0.0649 | 0.1183 | 0.500 | 0.0081 | 0.1172 | 0.583 |

quantile mean forward 20d returns: Q1: -0.00303  Q2: -0.00204  Q3: 0.00827  Q4: 0.00824  Q5: -0.00190
Q5-Q1 long-short (gross, monthly): mean 0.00113, ann 0.0236, Sharpe 0.199, MDD -0.1180
top-quintile turnover: 0.754

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0497 | 0.858 | 0.833 |
| 2023 | 12 | 0.0078 | 0.108 | 0.583 |

regime split: up-market IC 0.0329 (n=13) / down-market IC 0.0238 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.203
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0066 | 0.0646 | 0.1021 | 0.375 | 0.0179 | 0.2258 | 0.542 |
| 5 | 0.0033 | 0.0489 | 0.0679 | 0.542 | 0.0120 | 0.1729 | 0.542 |
| 10 | 0.0131 | 0.0535 | 0.2440 | 0.500 | 0.0234 | 0.3331 | 0.583 |
| 20 | -0.0061 | 0.0523 | -0.1162 | 0.458 | 0.0033 | 0.0479 | 0.500 |
| 40 | -0.0099 | 0.0499 | -0.1991 | 0.500 | -0.0020 | -0.0346 | 0.625 |
| 60 | -0.0139 | 0.0475 | -0.2935 | 0.417 | -0.0137 | -0.2430 | 0.458 |

quantile mean forward 20d returns: Q1: 0.02998  Q2: 0.03553  Q3: 0.03083  Q4: 0.03186  Q5: 0.03467
Q5-Q1 long-short (gross, monthly): mean 0.00470, ann 0.0401, Sharpe 0.552, MDD -0.0550
top-quintile turnover: 0.730

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0050 | -0.071 | 0.583 |
| 2025 | 12 | 0.0116 | 0.179 | 0.417 |

regime split: up-market IC -0.0068 (n=15) / down-market IC 0.0200 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0158 | 0.0643 | 0.2457 | 0.583 | 0.0158 | 0.2305 | 0.542 |
| 5 | 0.0085 | 0.0442 | 0.1920 | 0.625 | 0.0077 | 0.1168 | 0.458 |
| 10 | 0.0159 | 0.0497 | 0.3203 | 0.625 | 0.0188 | 0.2891 | 0.583 |
| 20 | -0.0024 | 0.0515 | -0.0459 | 0.583 | 0.0001 | 0.0018 | 0.500 |
| 40 | -0.0063 | 0.0471 | -0.1333 | 0.583 | -0.0044 | -0.0775 | 0.583 |
| 60 | -0.0136 | 0.0455 | -0.2994 | 0.375 | -0.0157 | -0.2825 | 0.458 |

quantile mean forward 20d returns: Q1: 0.03097  Q2: 0.03510  Q3: 0.03090  Q4: 0.03068  Q5: 0.03521
Q5-Q1 long-short (gross, monthly): mean 0.00424, ann 0.0347, Sharpe 0.515, MDD -0.0550
top-quintile turnover: 0.730

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0074 | -0.105 | 0.583 |
| 2025 | 12 | 0.0076 | 0.129 | 0.417 |

regime split: up-market IC -0.0082 (n=15) / down-market IC 0.0139 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`announcement_count_20d`: 0.580  `news_count_20d`: 0.580  `announcement_attention_5d`: 0.541  `news_attention_5d`: 0.541  `news_importance_5d`: 0.460

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.