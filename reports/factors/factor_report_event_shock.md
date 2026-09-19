# factor_report_event_shock.md

## definition

- factor: `event_shock`  ·  category: news  ·  version 1.0
- formula: `major_count(5d) / mean_major_count(120d)，极端值在归一化层处理`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: major-event shock vs 120d baseline
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.014
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0148 | 0.0482 | 0.3075 | 0.625 | 0.0176 | 0.3061 | 0.667 |
| 5 | 0.0049 | 0.0338 | 0.1445 | 0.542 | 0.0060 | 0.1469 | 0.583 |
| 10 | 0.0069 | 0.0388 | 0.1785 | 0.542 | 0.0078 | 0.1702 | 0.625 |
| 20 | 0.0030 | 0.0443 | 0.0678 | 0.521 | 0.0022 | 0.0383 | 0.521 |
| 40 | 0.0076 | 0.0438 | 0.1736 | 0.542 | 0.0065 | 0.1361 | 0.583 |
| 60 | 0.0120 | 0.0407 | 0.2948 | 0.583 | 0.0104 | 0.2118 | 0.625 |

quantile mean forward 20d returns: Q1: 0.00964  Q2: 0.01186  Q3: 0.01470  Q4: 0.00886  Q5: 0.01082
Q5-Q1 long-short (gross, monthly): mean 0.00118, ann 0.0074, Sharpe 0.082, MDD -0.1407
top-quintile turnover: 0.206

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0084 | -0.146 | 0.417 |
| 2019 | 12 | 0.0198 | 0.307 | 0.667 |
| 2020 | 12 | 0.0149 | 0.304 | 0.667 |
| 2021 | 12 | -0.0177 | -0.391 | 0.333 |

regime split: up-market IC 0.0134 (n=28) / down-market IC -0.0136 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0142 | 0.0478 | 0.2965 | 0.625 | 0.0176 | 0.3061 | 0.667 |
| 5 | 0.0046 | 0.0340 | 0.1365 | 0.542 | 0.0060 | 0.1460 | 0.583 |
| 10 | 0.0066 | 0.0389 | 0.1694 | 0.542 | 0.0077 | 0.1695 | 0.625 |
| 20 | 0.0028 | 0.0443 | 0.0635 | 0.521 | 0.0021 | 0.0373 | 0.521 |
| 40 | 0.0075 | 0.0440 | 0.1694 | 0.542 | 0.0065 | 0.1348 | 0.583 |
| 60 | 0.0119 | 0.0409 | 0.2911 | 0.583 | 0.0103 | 0.2111 | 0.625 |

quantile mean forward 20d returns: Q1: 0.00964  Q2: 0.01186  Q3: 0.01470  Q4: 0.00886  Q5: 0.01082
Q5-Q1 long-short (gross, monthly): mean 0.00118, ann 0.0074, Sharpe 0.082, MDD -0.1407
top-quintile turnover: 0.206

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0084 | -0.146 | 0.417 |
| 2019 | 12 | 0.0198 | 0.307 | 0.667 |
| 2020 | 12 | 0.0149 | 0.304 | 0.667 |
| 2021 | 12 | -0.0179 | -0.396 | 0.333 |

regime split: up-market IC 0.0134 (n=28) / down-market IC -0.0136 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.014
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0030 | 0.0726 | 0.0419 | 0.375 | -0.0016 | -0.0204 | 0.417 |
| 5 | -0.0031 | 0.0426 | -0.0724 | 0.458 | -0.0030 | -0.0535 | 0.500 |
| 10 | 0.0046 | 0.0585 | 0.0788 | 0.417 | 0.0024 | 0.0334 | 0.417 |
| 20 | 0.0007 | 0.0729 | 0.0091 | 0.417 | -0.0025 | -0.0301 | 0.458 |
| 40 | 0.0100 | 0.0640 | 0.1555 | 0.625 | 0.0078 | 0.1135 | 0.542 |
| 60 | 0.0099 | 0.0532 | 0.1865 | 0.500 | 0.0017 | 0.0294 | 0.458 |

quantile mean forward 20d returns: Q1: 0.00300  Q2: 0.00349  Q3: 0.00103  Q4: 0.00303  Q5: -0.00102
Q5-Q1 long-short (gross, monthly): mean -0.00402, ann -0.0403, Sharpe -0.315, MDD -0.1774
top-quintile turnover: 0.290

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0065 | -0.122 | 0.500 |
| 2023 | 12 | 0.0016 | 0.016 | 0.417 |

regime split: up-market IC -0.0243 (n=13) / down-market IC 0.0234 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0046 | 0.0716 | 0.0648 | 0.375 | -0.0016 | -0.0203 | 0.417 |
| 5 | -0.0042 | 0.0415 | -0.1013 | 0.458 | -0.0030 | -0.0535 | 0.500 |
| 10 | 0.0037 | 0.0587 | 0.0628 | 0.417 | 0.0024 | 0.0335 | 0.417 |
| 20 | 0.0003 | 0.0734 | 0.0042 | 0.375 | -0.0024 | -0.0301 | 0.458 |
| 40 | 0.0099 | 0.0642 | 0.1547 | 0.625 | 0.0078 | 0.1135 | 0.542 |
| 60 | 0.0109 | 0.0520 | 0.2099 | 0.500 | 0.0017 | 0.0295 | 0.458 |

quantile mean forward 20d returns: Q1: 0.00300  Q2: 0.00349  Q3: 0.00103  Q4: 0.00303  Q5: -0.00102
Q5-Q1 long-short (gross, monthly): mean -0.00402, ann -0.0403, Sharpe -0.315, MDD -0.1774
top-quintile turnover: 0.290

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0065 | -0.122 | 0.500 |
| 2023 | 12 | 0.0016 | 0.016 | 0.417 |

regime split: up-market IC -0.0243 (n=13) / down-market IC 0.0234 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.010
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0134 | 0.0512 | 0.2612 | 0.625 | 0.0140 | 0.2207 | 0.583 |
| 5 | 0.0117 | 0.0467 | 0.2502 | 0.667 | 0.0132 | 0.2189 | 0.625 |
| 10 | 0.0180 | 0.0454 | 0.3957 | 0.583 | 0.0201 | 0.3870 | 0.667 |
| 20 | 0.0265 | 0.0514 | 0.5158 | 0.667 | 0.0255 | 0.5113 | 0.667 |
| 40 | 0.0209 | 0.0394 | 0.5304 | 0.625 | 0.0177 | 0.4110 | 0.542 |
| 60 | 0.0139 | 0.0345 | 0.4037 | 0.625 | 0.0069 | 0.1803 | 0.417 |

quantile mean forward 20d returns: Q1: 0.02836  Q2: 0.03572  Q3: 0.03114  Q4: 0.02628  Q5: 0.04135
Q5-Q1 long-short (gross, monthly): mean 0.01298, ann 0.1355, Sharpe 0.923, MDD -0.0770
top-quintile turnover: 0.126

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0340 | 0.567 | 0.667 |
| 2025 | 12 | 0.0171 | 0.482 | 0.667 |

regime split: up-market IC 0.0302 (n=15) / down-market IC 0.0177 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0131 | 0.0511 | 0.2555 | 0.625 | 0.0140 | 0.2209 | 0.583 |
| 5 | 0.0115 | 0.0464 | 0.2475 | 0.667 | 0.0132 | 0.2188 | 0.625 |
| 10 | 0.0175 | 0.0453 | 0.3870 | 0.583 | 0.0202 | 0.3871 | 0.667 |
| 20 | 0.0267 | 0.0512 | 0.5217 | 0.667 | 0.0256 | 0.5117 | 0.667 |
| 40 | 0.0212 | 0.0394 | 0.5382 | 0.667 | 0.0177 | 0.4112 | 0.542 |
| 60 | 0.0144 | 0.0344 | 0.4183 | 0.625 | 0.0069 | 0.1802 | 0.417 |

quantile mean forward 20d returns: Q1: 0.02836  Q2: 0.03572  Q3: 0.03114  Q4: 0.02628  Q5: 0.04135
Q5-Q1 long-short (gross, monthly): mean 0.01298, ann 0.1355, Sharpe 0.923, MDD -0.0770
top-quintile turnover: 0.126

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0340 | 0.567 | 0.667 |
| 2025 | 12 | 0.0171 | 0.484 | 0.667 |

regime split: up-market IC 0.0302 (n=15) / down-market IC 0.0178 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`major_event_count_20d`: 0.537  `news_count_5d`: 0.504  `announcement_count_5d`: 0.504  `news_importance_5d`: 0.486  `announcement_attention_5d`: 0.463

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.