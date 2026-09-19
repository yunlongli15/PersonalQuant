# factor_report_announcement_count_20d.md

## definition

- factor: `announcement_count_20d`  ·  category: news  ·  version 1.0
- formula: `count(all announcements in 20d)`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: announcement count, 20-day window
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.401
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0365 | 0.0627 | 0.5822 | 0.729 | 0.0452 | 0.5200 | 0.729 |
| 5 | 0.0254 | 0.0566 | 0.4498 | 0.625 | 0.0281 | 0.4055 | 0.625 |
| 10 | 0.0259 | 0.0523 | 0.4950 | 0.604 | 0.0301 | 0.4477 | 0.604 |
| 20 | 0.0108 | 0.0547 | 0.1977 | 0.604 | 0.0100 | 0.1379 | 0.500 |
| 40 | 0.0121 | 0.0535 | 0.2271 | 0.562 | 0.0144 | 0.2018 | 0.542 |
| 60 | 0.0144 | 0.0594 | 0.2421 | 0.542 | 0.0178 | 0.2422 | 0.646 |

quantile mean forward 20d returns: Q1: 0.00913  Q2: 0.01034  Q3: 0.00906  Q4: 0.01216  Q5: 0.01519
Q5-Q1 long-short (gross, monthly): mean 0.00606, ann 0.0650, Sharpe 0.545, MDD -0.2112
top-quintile turnover: 0.308

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0052 | 0.077 | 0.417 |
| 2019 | 12 | 0.0427 | 0.689 | 0.667 |
| 2020 | 12 | -0.0018 | -0.022 | 0.583 |
| 2021 | 12 | -0.0062 | -0.103 | 0.333 |

regime split: up-market IC 0.0290 (n=28) / down-market IC -0.0167 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0349 | 0.0692 | 0.5050 | 0.729 | 0.0436 | 0.5076 | 0.708 |
| 5 | 0.0270 | 0.0573 | 0.4707 | 0.729 | 0.0306 | 0.4409 | 0.667 |
| 10 | 0.0272 | 0.0503 | 0.5408 | 0.583 | 0.0312 | 0.4639 | 0.604 |
| 20 | 0.0116 | 0.0540 | 0.2142 | 0.542 | 0.0112 | 0.1545 | 0.521 |
| 40 | 0.0166 | 0.0559 | 0.2978 | 0.583 | 0.0160 | 0.2207 | 0.542 |
| 60 | 0.0215 | 0.0599 | 0.3589 | 0.646 | 0.0191 | 0.2605 | 0.646 |

quantile mean forward 20d returns: Q1: 0.00908  Q2: 0.01029  Q3: 0.00926  Q4: 0.01144  Q5: 0.01580
Q5-Q1 long-short (gross, monthly): mean 0.00672, ann 0.0731, Sharpe 0.602, MDD -0.2156
top-quintile turnover: 0.289

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0051 | 0.073 | 0.417 |
| 2019 | 12 | 0.0474 | 0.805 | 0.667 |
| 2020 | 12 | -0.0015 | -0.018 | 0.583 |
| 2021 | 12 | -0.0064 | -0.100 | 0.417 |

regime split: up-market IC 0.0295 (n=28) / down-market IC -0.0146 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.455
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0047 | 0.0489 | 0.0969 | 0.583 | 0.0132 | 0.1922 | 0.542 |
| 5 | 0.0016 | 0.0574 | 0.0278 | 0.542 | 0.0071 | 0.0965 | 0.500 |
| 10 | -0.0002 | 0.0545 | -0.0033 | 0.542 | 0.0003 | 0.0038 | 0.458 |
| 20 | 0.0044 | 0.0493 | 0.0901 | 0.500 | 0.0029 | 0.0363 | 0.417 |
| 40 | -0.0047 | 0.0622 | -0.0762 | 0.542 | 0.0013 | 0.0153 | 0.500 |
| 60 | -0.0026 | 0.0542 | -0.0479 | 0.542 | 0.0006 | 0.0082 | 0.458 |

quantile mean forward 20d returns: Q1: 0.00429  Q2: -0.00229  Q3: 0.00288  Q4: 0.00348  Q5: 0.00118
Q5-Q1 long-short (gross, monthly): mean -0.00310, ann -0.0304, Sharpe -0.198, MDD -0.1530
top-quintile turnover: 0.314

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0112 | 0.128 | 0.417 |
| 2023 | 12 | -0.0055 | -0.079 | 0.417 |

regime split: up-market IC 0.0460 (n=13) / down-market IC -0.0481 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0167 | 0.0587 | 0.2843 | 0.625 | 0.0136 | 0.1926 | 0.542 |
| 5 | 0.0068 | 0.0608 | 0.1125 | 0.500 | 0.0066 | 0.0920 | 0.500 |
| 10 | 0.0040 | 0.0559 | 0.0720 | 0.542 | 0.0015 | 0.0224 | 0.458 |
| 20 | 0.0097 | 0.0678 | 0.1424 | 0.500 | 0.0070 | 0.0837 | 0.458 |
| 40 | 0.0049 | 0.0719 | 0.0681 | 0.500 | 0.0027 | 0.0325 | 0.500 |
| 60 | 0.0065 | 0.0649 | 0.1001 | 0.542 | -0.0012 | -0.0153 | 0.458 |

quantile mean forward 20d returns: Q1: 0.00410  Q2: -0.00147  Q3: 0.00131  Q4: 0.00298  Q5: 0.00262
Q5-Q1 long-short (gross, monthly): mean -0.00148, ann -0.0094, Sharpe -0.060, MDD -0.1495
top-quintile turnover: 0.241

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0040 | 0.045 | 0.417 |
| 2023 | 12 | 0.0101 | 0.126 | 0.500 |

regime split: up-market IC 0.0484 (n=13) / down-market IC -0.0419 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.457
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0260 | 0.0615 | 0.4230 | 0.708 | 0.0362 | 0.4505 | 0.625 |
| 5 | 0.0042 | 0.0660 | 0.0631 | 0.542 | 0.0086 | 0.1061 | 0.542 |
| 10 | 0.0129 | 0.0538 | 0.2407 | 0.583 | 0.0212 | 0.3144 | 0.667 |
| 20 | 0.0142 | 0.0376 | 0.3772 | 0.625 | 0.0217 | 0.4207 | 0.625 |
| 40 | 0.0128 | 0.0370 | 0.3468 | 0.583 | 0.0189 | 0.3677 | 0.667 |
| 60 | 0.0125 | 0.0314 | 0.3984 | 0.667 | 0.0170 | 0.4828 | 0.708 |

quantile mean forward 20d returns: Q1: 0.02622  Q2: 0.02989  Q3: 0.03462  Q4: 0.03168  Q5: 0.04047
Q5-Q1 long-short (gross, monthly): mean 0.01426, ann 0.1605, Sharpe 1.476, MDD -0.0459
top-quintile turnover: 0.347

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0286 | 0.557 | 0.667 |
| 2025 | 12 | 0.0148 | 0.291 | 0.583 |

regime split: up-market IC 0.0397 (n=15) / down-market IC -0.0083 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0290 | 0.0600 | 0.4834 | 0.750 | 0.0367 | 0.4808 | 0.708 |
| 5 | 0.0039 | 0.0587 | 0.0663 | 0.500 | 0.0034 | 0.0432 | 0.583 |
| 10 | 0.0131 | 0.0439 | 0.2987 | 0.583 | 0.0160 | 0.2500 | 0.625 |
| 20 | 0.0207 | 0.0374 | 0.5526 | 0.708 | 0.0179 | 0.3427 | 0.625 |
| 40 | 0.0163 | 0.0356 | 0.4579 | 0.708 | 0.0110 | 0.2384 | 0.625 |
| 60 | 0.0158 | 0.0250 | 0.6298 | 0.708 | 0.0131 | 0.3974 | 0.667 |

quantile mean forward 20d returns: Q1: 0.02624  Q2: 0.03081  Q3: 0.03473  Q4: 0.03070  Q5: 0.04039
Q5-Q1 long-short (gross, monthly): mean 0.01415, ann 0.1592, Sharpe 1.472, MDD -0.0438
top-quintile turnover: 0.286

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0224 | 0.469 | 0.667 |
| 2025 | 12 | 0.0134 | 0.239 | 0.583 |

regime split: up-market IC 0.0368 (n=15) / down-market IC -0.0136 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`news_count_20d`: 1.000  `announcement_count_5d`: 0.702  `news_count_5d`: 0.702  `news_importance_5d`: 0.652  `news_novelty_5d`: 0.623

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.