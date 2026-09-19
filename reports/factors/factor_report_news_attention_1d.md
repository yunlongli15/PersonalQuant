# factor_report_news_attention_1d.md

## definition

- factor: `news_attention_1d`  ·  category: news  ·  version 1.0
- formula: `count(1d) / mean_count(60d)`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: 1-day attention vs 60d baseline
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.201
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0069 | 0.0430 | 0.1593 | 0.604 | 0.0036 | 0.0707 | 0.542 |
| 5 | 0.0055 | 0.0419 | 0.1308 | 0.542 | 0.0043 | 0.0874 | 0.521 |
| 10 | 0.0062 | 0.0342 | 0.1821 | 0.500 | 0.0061 | 0.1423 | 0.500 |
| 20 | 0.0114 | 0.0363 | 0.3145 | 0.604 | 0.0099 | 0.1945 | 0.562 |
| 40 | 0.0108 | 0.0396 | 0.2722 | 0.583 | 0.0081 | 0.1767 | 0.500 |
| 60 | 0.0022 | 0.0271 | 0.0810 | 0.521 | 0.0002 | 0.0046 | 0.583 |

quantile mean forward 20d returns: Q1: 0.00918  Q2: 0.01205  Q3: 0.01326  Q4: 0.01017  Q5: 0.01122
Q5-Q1 long-short (gross, monthly): mean 0.00205, ann 0.0220, Sharpe 0.264, MDD -0.1197
top-quintile turnover: 0.417

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0167 | 0.425 | 0.583 |
| 2019 | 12 | 0.0238 | 0.501 | 0.583 |
| 2020 | 12 | 0.0065 | 0.122 | 0.583 |
| 2021 | 12 | -0.0075 | -0.136 | 0.500 |

regime split: up-market IC 0.0131 (n=28) / down-market IC 0.0053 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0040 | 0.0366 | 0.1098 | 0.542 | 0.0038 | 0.0745 | 0.542 |
| 5 | 0.0028 | 0.0299 | 0.0945 | 0.521 | 0.0043 | 0.0883 | 0.521 |
| 10 | 0.0030 | 0.0270 | 0.1100 | 0.458 | 0.0063 | 0.1449 | 0.500 |
| 20 | 0.0092 | 0.0304 | 0.3020 | 0.604 | 0.0100 | 0.1959 | 0.562 |
| 40 | 0.0059 | 0.0342 | 0.1730 | 0.542 | 0.0082 | 0.1798 | 0.521 |
| 60 | -0.0009 | 0.0264 | -0.0354 | 0.479 | 0.0003 | 0.0090 | 0.583 |

quantile mean forward 20d returns: Q1: 0.00918  Q2: 0.01205  Q3: 0.01326  Q4: 0.01019  Q5: 0.01120
Q5-Q1 long-short (gross, monthly): mean 0.00202, ann 0.0219, Sharpe 0.263, MDD -0.1196
top-quintile turnover: 0.417

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0170 | 0.426 | 0.583 |
| 2019 | 12 | 0.0238 | 0.502 | 0.583 |
| 2020 | 12 | 0.0065 | 0.122 | 0.583 |
| 2021 | 12 | -0.0075 | -0.135 | 0.500 |

regime split: up-market IC 0.0133 (n=28) / down-market IC 0.0053 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.188
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0171 | 0.0657 | 0.2596 | 0.542 | 0.0200 | 0.2622 | 0.542 |
| 5 | 0.0191 | 0.0685 | 0.2784 | 0.542 | 0.0261 | 0.3142 | 0.583 |
| 10 | 0.0139 | 0.0592 | 0.2351 | 0.542 | 0.0204 | 0.2804 | 0.500 |
| 20 | -0.0035 | 0.0600 | -0.0579 | 0.458 | -0.0049 | -0.0694 | 0.417 |
| 40 | 0.0031 | 0.0543 | 0.0569 | 0.500 | 0.0017 | 0.0249 | 0.458 |
| 60 | 0.0182 | 0.0687 | 0.2651 | 0.458 | 0.0161 | 0.2058 | 0.458 |

quantile mean forward 20d returns: Q1: 0.00305  Q2: 0.00371  Q3: 0.00110  Q4: 0.00355  Q5: -0.00188
Q5-Q1 long-short (gross, monthly): mean -0.00492, ann -0.0523, Sharpe -0.459, MDD -0.1618
top-quintile turnover: 0.608

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0026 | 0.035 | 0.500 |
| 2023 | 12 | -0.0124 | -0.194 | 0.333 |

regime split: up-market IC -0.0134 (n=13) / down-market IC 0.0052 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0127 | 0.0635 | 0.2005 | 0.542 | 0.0201 | 0.2627 | 0.542 |
| 5 | 0.0147 | 0.0644 | 0.2281 | 0.500 | 0.0259 | 0.3108 | 0.583 |
| 10 | 0.0139 | 0.0570 | 0.2430 | 0.542 | 0.0204 | 0.2805 | 0.500 |
| 20 | -0.0040 | 0.0567 | -0.0699 | 0.500 | -0.0049 | -0.0692 | 0.417 |
| 40 | 0.0047 | 0.0539 | 0.0880 | 0.500 | 0.0016 | 0.0236 | 0.458 |
| 60 | 0.0173 | 0.0641 | 0.2690 | 0.500 | 0.0161 | 0.2064 | 0.458 |

quantile mean forward 20d returns: Q1: 0.00305  Q2: 0.00371  Q3: 0.00113  Q4: 0.00354  Q5: -0.00189
Q5-Q1 long-short (gross, monthly): mean -0.00494, ann -0.0525, Sharpe -0.461, MDD -0.1618
top-quintile turnover: 0.607

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0031 | 0.041 | 0.500 |
| 2023 | 12 | -0.0128 | -0.199 | 0.333 |

regime split: up-market IC -0.0133 (n=13) / down-market IC 0.0051 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.203
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0072 | 0.0508 | 0.1413 | 0.458 | 0.0081 | 0.1385 | 0.458 |
| 5 | 0.0161 | 0.0507 | 0.3171 | 0.583 | 0.0161 | 0.2699 | 0.500 |
| 10 | 0.0161 | 0.0551 | 0.2930 | 0.500 | 0.0175 | 0.2743 | 0.500 |
| 20 | -0.0014 | 0.0416 | -0.0333 | 0.375 | 0.0023 | 0.0467 | 0.417 |
| 40 | -0.0156 | 0.0346 | -0.4513 | 0.375 | -0.0147 | -0.3316 | 0.417 |
| 60 | -0.0140 | 0.0285 | -0.4923 | 0.250 | -0.0157 | -0.4293 | 0.292 |

quantile mean forward 20d returns: Q1: 0.02885  Q2: 0.03605  Q3: 0.03354  Q4: 0.02660  Q5: 0.03782
Q5-Q1 long-short (gross, monthly): mean 0.00897, ann 0.0876, Sharpe 0.809, MDD -0.0726
top-quintile turnover: 0.675

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0012 | -0.023 | 0.417 |
| 2025 | 12 | 0.0058 | 0.132 | 0.417 |

regime split: up-market IC -0.0057 (n=15) / down-market IC 0.0156 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0076 | 0.0515 | 0.1470 | 0.417 | 0.0082 | 0.1401 | 0.458 |
| 5 | 0.0145 | 0.0460 | 0.3160 | 0.542 | 0.0161 | 0.2674 | 0.500 |
| 10 | 0.0142 | 0.0525 | 0.2705 | 0.500 | 0.0175 | 0.2733 | 0.500 |
| 20 | -0.0022 | 0.0394 | -0.0558 | 0.375 | 0.0023 | 0.0480 | 0.417 |
| 40 | -0.0156 | 0.0341 | -0.4576 | 0.375 | -0.0147 | -0.3325 | 0.417 |
| 60 | -0.0140 | 0.0277 | -0.5040 | 0.250 | -0.0156 | -0.4295 | 0.292 |

quantile mean forward 20d returns: Q1: 0.02885  Q2: 0.03605  Q3: 0.03354  Q4: 0.02658  Q5: 0.03784
Q5-Q1 long-short (gross, monthly): mean 0.00899, ann 0.0879, Sharpe 0.812, MDD -0.0721
top-quintile turnover: 0.677

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0012 | -0.023 | 0.417 |
| 2025 | 12 | 0.0059 | 0.134 | 0.417 |

regime split: up-market IC -0.0056 (n=15) / down-market IC 0.0156 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`news_count_1d`: 0.994  `announcement_attention_5d`: 0.506  `news_attention_5d`: 0.506  `announcement_count_5d`: 0.494  `news_count_5d`: 0.494

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.