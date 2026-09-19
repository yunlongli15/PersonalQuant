# factor_report_major_event_count_20d.md

## definition

- factor: `major_event_count_20d`  ·  category: news  ·  version 1.0
- formula: `count(importance >= 0.6 events in 20d)`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: major event count, 20d
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.401
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0291 | 0.0606 | 0.4798 | 0.708 | 0.0355 | 0.4859 | 0.771 |
| 5 | 0.0176 | 0.0493 | 0.3571 | 0.583 | 0.0179 | 0.2915 | 0.583 |
| 10 | 0.0173 | 0.0489 | 0.3547 | 0.583 | 0.0187 | 0.2886 | 0.583 |
| 20 | 0.0084 | 0.0552 | 0.1513 | 0.500 | 0.0081 | 0.1150 | 0.438 |
| 40 | 0.0105 | 0.0609 | 0.1724 | 0.479 | 0.0097 | 0.1354 | 0.479 |
| 60 | 0.0175 | 0.0504 | 0.3467 | 0.625 | 0.0151 | 0.2541 | 0.583 |

quantile mean forward 20d returns: Q1: 0.01033  Q2: 0.00792  Q3: 0.01144  Q4: 0.01219  Q5: 0.01401
Q5-Q1 long-short (gross, monthly): mean 0.00368, ann 0.0375, Sharpe 0.398, MDD -0.1726
top-quintile turnover: 0.418

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0127 | 0.201 | 0.417 |
| 2019 | 12 | 0.0349 | 0.494 | 0.583 |
| 2020 | 12 | -0.0009 | -0.012 | 0.333 |
| 2021 | 12 | -0.0142 | -0.211 | 0.417 |

regime split: up-market IC 0.0261 (n=28) / down-market IC -0.0170 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0296 | 0.0590 | 0.5012 | 0.667 | 0.0376 | 0.5368 | 0.771 |
| 5 | 0.0171 | 0.0479 | 0.3574 | 0.583 | 0.0187 | 0.3065 | 0.583 |
| 10 | 0.0179 | 0.0492 | 0.3650 | 0.625 | 0.0198 | 0.3076 | 0.583 |
| 20 | 0.0083 | 0.0523 | 0.1585 | 0.500 | 0.0096 | 0.1387 | 0.438 |
| 40 | 0.0109 | 0.0605 | 0.1807 | 0.500 | 0.0106 | 0.1482 | 0.479 |
| 60 | 0.0175 | 0.0512 | 0.3415 | 0.625 | 0.0158 | 0.2660 | 0.604 |

quantile mean forward 20d returns: Q1: 0.01033  Q2: 0.00792  Q3: 0.01110  Q4: 0.01182  Q5: 0.01472
Q5-Q1 long-short (gross, monthly): mean 0.00439, ann 0.0463, Sharpe 0.492, MDD -0.1650
top-quintile turnover: 0.418

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0172 | 0.287 | 0.417 |
| 2019 | 12 | 0.0350 | 0.494 | 0.583 |
| 2020 | 12 | -0.0017 | -0.024 | 0.333 |
| 2021 | 12 | -0.0120 | -0.186 | 0.417 |

regime split: up-market IC 0.0279 (n=28) / down-market IC -0.0160 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.455
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0298 | 0.0908 | 0.3280 | 0.583 | 0.0277 | 0.2834 | 0.542 |
| 5 | 0.0280 | 0.0639 | 0.4390 | 0.583 | 0.0362 | 0.4308 | 0.583 |
| 10 | 0.0262 | 0.0692 | 0.3783 | 0.625 | 0.0308 | 0.3529 | 0.583 |
| 20 | 0.0111 | 0.0703 | 0.1576 | 0.458 | 0.0044 | 0.0567 | 0.417 |
| 40 | 0.0121 | 0.0625 | 0.1945 | 0.583 | 0.0118 | 0.1586 | 0.625 |
| 60 | 0.0121 | 0.0519 | 0.2337 | 0.583 | 0.0043 | 0.0657 | 0.542 |

quantile mean forward 20d returns: Q1: 0.00170  Q2: 0.00180  Q3: 0.00213  Q4: 0.00423  Q5: -0.00033
Q5-Q1 long-short (gross, monthly): mean -0.00202, ann -0.0188, Sharpe -0.144, MDD -0.1388
top-quintile turnover: 0.366

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0091 | -0.195 | 0.500 |
| 2023 | 12 | 0.0180 | 0.183 | 0.333 |

regime split: up-market IC -0.0034 (n=13) / down-market IC 0.0136 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0302 | 0.0920 | 0.3286 | 0.583 | 0.0278 | 0.2837 | 0.542 |
| 5 | 0.0281 | 0.0638 | 0.4410 | 0.583 | 0.0362 | 0.4305 | 0.583 |
| 10 | 0.0253 | 0.0690 | 0.3671 | 0.583 | 0.0308 | 0.3534 | 0.583 |
| 20 | 0.0117 | 0.0719 | 0.1631 | 0.458 | 0.0044 | 0.0562 | 0.417 |
| 40 | 0.0124 | 0.0639 | 0.1943 | 0.583 | 0.0119 | 0.1598 | 0.625 |
| 60 | 0.0114 | 0.0530 | 0.2142 | 0.583 | 0.0044 | 0.0671 | 0.542 |

quantile mean forward 20d returns: Q1: 0.00170  Q2: 0.00180  Q3: 0.00212  Q4: 0.00423  Q5: -0.00031
Q5-Q1 long-short (gross, monthly): mean -0.00201, ann -0.0186, Sharpe -0.143, MDD -0.1388
top-quintile turnover: 0.366

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0093 | -0.198 | 0.500 |
| 2023 | 12 | 0.0181 | 0.184 | 0.333 |

regime split: up-market IC -0.0035 (n=13) / down-market IC 0.0137 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.457
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0234 | 0.0551 | 0.4245 | 0.667 | 0.0240 | 0.3211 | 0.583 |
| 5 | 0.0256 | 0.0540 | 0.4731 | 0.708 | 0.0299 | 0.4276 | 0.625 |
| 10 | 0.0304 | 0.0469 | 0.6473 | 0.708 | 0.0319 | 0.5497 | 0.750 |
| 20 | 0.0353 | 0.0496 | 0.7105 | 0.875 | 0.0374 | 0.7008 | 0.708 |
| 40 | 0.0206 | 0.0398 | 0.5163 | 0.500 | 0.0160 | 0.3203 | 0.542 |
| 60 | 0.0108 | 0.0359 | 0.2996 | 0.542 | 0.0048 | 0.1034 | 0.375 |

quantile mean forward 20d returns: Q1: 0.02814  Q2: 0.03512  Q3: 0.02751  Q4: 0.02695  Q5: 0.04514
Q5-Q1 long-short (gross, monthly): mean 0.01699, ann 0.1879, Sharpe 1.240, MDD -0.0784
top-quintile turnover: 0.232

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0453 | 0.683 | 0.583 |
| 2025 | 12 | 0.0296 | 0.860 | 0.833 |

regime split: up-market IC 0.0457 (n=15) / down-market IC 0.0236 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0220 | 0.0539 | 0.4074 | 0.667 | 0.0210 | 0.2847 | 0.583 |
| 5 | 0.0220 | 0.0504 | 0.4372 | 0.708 | 0.0267 | 0.3689 | 0.583 |
| 10 | 0.0274 | 0.0462 | 0.5929 | 0.667 | 0.0294 | 0.4842 | 0.708 |
| 20 | 0.0330 | 0.0490 | 0.6746 | 0.875 | 0.0353 | 0.6600 | 0.708 |
| 40 | 0.0193 | 0.0383 | 0.5045 | 0.500 | 0.0151 | 0.3031 | 0.542 |
| 60 | 0.0104 | 0.0356 | 0.2913 | 0.542 | 0.0044 | 0.0953 | 0.375 |

quantile mean forward 20d returns: Q1: 0.02814  Q2: 0.03512  Q3: 0.02788  Q4: 0.02710  Q5: 0.04462
Q5-Q1 long-short (gross, monthly): mean 0.01648, ann 0.1809, Sharpe 1.197, MDD -0.0784
top-quintile turnover: 0.228

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0408 | 0.612 | 0.583 |
| 2025 | 12 | 0.0297 | 0.860 | 0.833 |

regime split: up-market IC 0.0458 (n=15) / down-market IC 0.0177 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`event_shock`: 0.537  `announcement_count_20d`: 0.503  `news_count_20d`: 0.503  `announcement_count_5d`: 0.413  `news_count_5d`: 0.413

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.