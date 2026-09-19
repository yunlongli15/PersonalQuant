# factor_report_earnings_event_count_60d.md

## definition

- factor: `earnings_event_count_60d`  ·  category: news  ·  version 1.0
- formula: `count(earnings/forecast/revision events in 60d)`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: earnings-related event count, 60d
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.401
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0202 | 0.0640 | 0.3156 | 0.604 | 0.0236 | 0.2870 | 0.583 |
| 5 | 0.0226 | 0.0601 | 0.3757 | 0.604 | 0.0286 | 0.3652 | 0.625 |
| 10 | 0.0219 | 0.0556 | 0.3944 | 0.625 | 0.0257 | 0.3344 | 0.604 |
| 20 | 0.0050 | 0.0511 | 0.0971 | 0.521 | 0.0040 | 0.0584 | 0.479 |
| 40 | 0.0006 | 0.0488 | 0.0122 | 0.479 | 0.0003 | 0.0050 | 0.438 |
| 60 | 0.0068 | 0.0482 | 0.1406 | 0.562 | 0.0081 | 0.1267 | 0.542 |

quantile mean forward 20d returns: Q1: 0.00899  Q2: 0.01250  Q3: 0.01075  Q4: 0.00974  Q5: 0.01390
Q5-Q1 long-short (gross, monthly): mean 0.00491, ann 0.0561, Sharpe 0.554, MDD -0.1333
top-quintile turnover: 0.488

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0136 | -0.242 | 0.500 |
| 2019 | 12 | 0.0369 | 0.563 | 0.583 |
| 2020 | 12 | 0.0093 | 0.130 | 0.417 |
| 2021 | 12 | -0.0166 | -0.252 | 0.417 |

regime split: up-market IC 0.0218 (n=28) / down-market IC -0.0210 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0202 | 0.0625 | 0.3239 | 0.604 | 0.0239 | 0.2828 | 0.583 |
| 5 | 0.0225 | 0.0583 | 0.3861 | 0.625 | 0.0293 | 0.3750 | 0.625 |
| 10 | 0.0220 | 0.0555 | 0.3960 | 0.604 | 0.0267 | 0.3480 | 0.604 |
| 20 | 0.0053 | 0.0505 | 0.1051 | 0.562 | 0.0040 | 0.0565 | 0.500 |
| 40 | 0.0014 | 0.0499 | 0.0288 | 0.500 | 0.0001 | 0.0011 | 0.438 |
| 60 | 0.0080 | 0.0494 | 0.1622 | 0.562 | 0.0085 | 0.1343 | 0.562 |

quantile mean forward 20d returns: Q1: 0.00961  Q2: 0.01185  Q3: 0.01054  Q4: 0.00889  Q5: 0.01499
Q5-Q1 long-short (gross, monthly): mean 0.00537, ann 0.0617, Sharpe 0.594, MDD -0.1319
top-quintile turnover: 0.489

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0138 | -0.216 | 0.583 |
| 2019 | 12 | 0.0352 | 0.536 | 0.583 |
| 2020 | 12 | 0.0111 | 0.151 | 0.417 |
| 2021 | 12 | -0.0167 | -0.262 | 0.417 |

regime split: up-market IC 0.0216 (n=28) / down-market IC -0.0207 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.455
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0195 | 0.0686 | 0.2835 | 0.542 | 0.0216 | 0.2467 | 0.583 |
| 5 | 0.0208 | 0.0723 | 0.2874 | 0.583 | 0.0309 | 0.3459 | 0.583 |
| 10 | 0.0077 | 0.0553 | 0.1391 | 0.542 | 0.0152 | 0.2210 | 0.583 |
| 20 | 0.0220 | 0.0539 | 0.4080 | 0.750 | 0.0279 | 0.4413 | 0.750 |
| 40 | 0.0153 | 0.0761 | 0.2012 | 0.542 | 0.0184 | 0.2042 | 0.542 |
| 60 | 0.0240 | 0.0740 | 0.3238 | 0.625 | 0.0230 | 0.2628 | 0.542 |

quantile mean forward 20d returns: Q1: 0.00320  Q2: -0.00045  Q3: 0.00119  Q4: 0.00137  Q5: 0.00422
Q5-Q1 long-short (gross, monthly): mean 0.00102, ann 0.0223, Sharpe 0.218, MDD -0.0739
top-quintile turnover: 0.477

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0276 | 0.395 | 0.667 |
| 2023 | 12 | 0.0281 | 0.507 | 0.833 |

regime split: up-market IC 0.0457 (n=13) / down-market IC 0.0068 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0189 | 0.0670 | 0.2816 | 0.500 | 0.0217 | 0.2487 | 0.583 |
| 5 | 0.0217 | 0.0702 | 0.3096 | 0.625 | 0.0295 | 0.3315 | 0.583 |
| 10 | 0.0104 | 0.0533 | 0.1947 | 0.583 | 0.0142 | 0.1981 | 0.583 |
| 20 | 0.0227 | 0.0521 | 0.4361 | 0.792 | 0.0257 | 0.3918 | 0.750 |
| 40 | 0.0144 | 0.0748 | 0.1924 | 0.542 | 0.0203 | 0.2247 | 0.583 |
| 60 | 0.0231 | 0.0737 | 0.3134 | 0.583 | 0.0245 | 0.2838 | 0.583 |

quantile mean forward 20d returns: Q1: 0.00358  Q2: -0.00047  Q3: 0.00087  Q4: 0.00136  Q5: 0.00419
Q5-Q1 long-short (gross, monthly): mean 0.00061, ann 0.0173, Sharpe 0.168, MDD -0.0755
top-quintile turnover: 0.480

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0240 | 0.321 | 0.667 |
| 2023 | 12 | 0.0274 | 0.498 | 0.833 |

regime split: up-market IC 0.0450 (n=13) / down-market IC 0.0029 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.457
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0302 | 0.0635 | 0.4755 | 0.750 | 0.0386 | 0.4761 | 0.708 |
| 5 | 0.0289 | 0.0597 | 0.4839 | 0.667 | 0.0375 | 0.4754 | 0.625 |
| 10 | 0.0383 | 0.0458 | 0.8366 | 0.792 | 0.0438 | 0.6997 | 0.750 |
| 20 | 0.0235 | 0.0413 | 0.5704 | 0.667 | 0.0257 | 0.4570 | 0.667 |
| 40 | 0.0096 | 0.0353 | 0.2727 | 0.625 | 0.0055 | 0.1206 | 0.542 |
| 60 | 0.0130 | 0.0366 | 0.3558 | 0.667 | 0.0057 | 0.1158 | 0.542 |

quantile mean forward 20d returns: Q1: 0.03188  Q2: 0.03009  Q3: 0.02760  Q4: 0.02889  Q5: 0.04441
Q5-Q1 long-short (gross, monthly): mean 0.01253, ann 0.1348, Sharpe 1.584, MDD -0.0304
top-quintile turnover: 0.426

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0228 | 0.396 | 0.583 |
| 2025 | 12 | 0.0286 | 0.522 | 0.750 |

regime split: up-market IC 0.0292 (n=15) / down-market IC 0.0199 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0265 | 0.0642 | 0.4131 | 0.708 | 0.0388 | 0.4767 | 0.708 |
| 5 | 0.0299 | 0.0573 | 0.5220 | 0.667 | 0.0378 | 0.4779 | 0.625 |
| 10 | 0.0407 | 0.0449 | 0.9066 | 0.833 | 0.0442 | 0.7005 | 0.750 |
| 20 | 0.0233 | 0.0411 | 0.5679 | 0.708 | 0.0255 | 0.4550 | 0.667 |
| 40 | 0.0095 | 0.0349 | 0.2723 | 0.625 | 0.0056 | 0.1204 | 0.542 |
| 60 | 0.0133 | 0.0374 | 0.3572 | 0.667 | 0.0056 | 0.1129 | 0.542 |

quantile mean forward 20d returns: Q1: 0.03152  Q2: 0.03049  Q3: 0.02772  Q4: 0.02896  Q5: 0.04417
Q5-Q1 long-short (gross, monthly): mean 0.01266, ann 0.1366, Sharpe 1.614, MDD -0.0304
top-quintile turnover: 0.429

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0232 | 0.399 | 0.583 |
| 2025 | 12 | 0.0278 | 0.517 | 0.750 |

regime split: up-market IC 0.0285 (n=15) / down-market IC 0.0205 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`announcement_count_20d`: 0.525  `news_count_20d`: 0.525  `announcement_count_5d`: 0.396  `news_count_5d`: 0.396  `news_importance_5d`: 0.379

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.