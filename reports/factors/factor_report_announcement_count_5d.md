# factor_report_announcement_count_5d.md

## definition

- factor: `announcement_count_5d`  ·  category: news  ·  version 1.0
- formula: `count(all announcements in 5d) — 与 news_count_5d 等价（v1 公告=全部文档；引入普通新闻后分开）`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: announcement count, 5-day window
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.401
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0283 | 0.0576 | 0.4916 | 0.729 | 0.0320 | 0.4297 | 0.708 |
| 5 | 0.0247 | 0.0463 | 0.5338 | 0.708 | 0.0262 | 0.4653 | 0.750 |
| 10 | 0.0260 | 0.0466 | 0.5592 | 0.583 | 0.0280 | 0.4902 | 0.562 |
| 20 | 0.0146 | 0.0517 | 0.2831 | 0.542 | 0.0123 | 0.1822 | 0.521 |
| 40 | 0.0220 | 0.0547 | 0.4014 | 0.604 | 0.0214 | 0.3235 | 0.583 |
| 60 | 0.0219 | 0.0590 | 0.3710 | 0.646 | 0.0226 | 0.3093 | 0.604 |

quantile mean forward 20d returns: Q1: 0.00746  Q2: 0.00923  Q3: 0.01205  Q4: 0.01440  Q5: 0.01274
Q5-Q1 long-short (gross, monthly): mean 0.00529, ann 0.0608, Sharpe 0.603, MDD -0.1604
top-quintile turnover: 0.494

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0059 | 0.114 | 0.500 |
| 2019 | 12 | 0.0409 | 0.642 | 0.583 |
| 2020 | 12 | -0.0052 | -0.068 | 0.500 |
| 2021 | 12 | 0.0075 | 0.114 | 0.500 |

regime split: up-market IC 0.0316 (n=28) / down-market IC -0.0148 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0239 | 0.0646 | 0.3696 | 0.750 | 0.0333 | 0.4456 | 0.708 |
| 5 | 0.0185 | 0.0448 | 0.4140 | 0.688 | 0.0266 | 0.4707 | 0.729 |
| 10 | 0.0204 | 0.0468 | 0.4358 | 0.562 | 0.0286 | 0.4992 | 0.542 |
| 20 | 0.0082 | 0.0507 | 0.1619 | 0.562 | 0.0122 | 0.1830 | 0.521 |
| 40 | 0.0172 | 0.0538 | 0.3199 | 0.604 | 0.0220 | 0.3307 | 0.583 |
| 60 | 0.0198 | 0.0597 | 0.3321 | 0.604 | 0.0231 | 0.3196 | 0.625 |

quantile mean forward 20d returns: Q1: 0.00742  Q2: 0.00911  Q3: 0.01201  Q4: 0.01464  Q5: 0.01269
Q5-Q1 long-short (gross, monthly): mean 0.00527, ann 0.0611, Sharpe 0.609, MDD -0.1676
top-quintile turnover: 0.498

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0044 | 0.085 | 0.500 |
| 2019 | 12 | 0.0440 | 0.725 | 0.583 |
| 2020 | 12 | -0.0057 | -0.075 | 0.500 |
| 2021 | 12 | 0.0062 | 0.096 | 0.500 |

regime split: up-market IC 0.0308 (n=28) / down-market IC -0.0138 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.455
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0207 | 0.0757 | 0.2733 | 0.667 | 0.0269 | 0.3041 | 0.625 |
| 5 | 0.0123 | 0.0788 | 0.1555 | 0.500 | 0.0193 | 0.2149 | 0.583 |
| 10 | 0.0189 | 0.0713 | 0.2647 | 0.625 | 0.0234 | 0.2707 | 0.500 |
| 20 | 0.0250 | 0.0798 | 0.3135 | 0.583 | 0.0295 | 0.3149 | 0.625 |
| 40 | 0.0091 | 0.0701 | 0.1296 | 0.500 | 0.0185 | 0.2161 | 0.542 |
| 60 | 0.0123 | 0.0645 | 0.1906 | 0.542 | 0.0201 | 0.2496 | 0.583 |

quantile mean forward 20d returns: Q1: 0.00035  Q2: 0.00287  Q3: -0.00193  Q4: 0.00405  Q5: 0.00420
Q5-Q1 long-short (gross, monthly): mean 0.00384, ann 0.0548, Sharpe 0.408, MDD -0.1115
top-quintile turnover: 0.561

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0328 | 0.419 | 0.583 |
| 2023 | 12 | 0.0262 | 0.246 | 0.667 |

regime split: up-market IC 0.0500 (n=13) / down-market IC 0.0052 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0193 | 0.0764 | 0.2531 | 0.583 | 0.0234 | 0.2599 | 0.625 |
| 5 | 0.0158 | 0.0767 | 0.2057 | 0.500 | 0.0234 | 0.2585 | 0.583 |
| 10 | 0.0203 | 0.0702 | 0.2895 | 0.583 | 0.0247 | 0.2927 | 0.583 |
| 20 | 0.0255 | 0.0834 | 0.3053 | 0.583 | 0.0258 | 0.2699 | 0.625 |
| 40 | 0.0124 | 0.0650 | 0.1902 | 0.500 | 0.0134 | 0.1521 | 0.542 |
| 60 | 0.0120 | 0.0605 | 0.1986 | 0.583 | 0.0155 | 0.1927 | 0.625 |

quantile mean forward 20d returns: Q1: 0.00035  Q2: 0.00260  Q3: -0.00028  Q4: 0.00400  Q5: 0.00286
Q5-Q1 long-short (gross, monthly): mean 0.00251, ann 0.0379, Sharpe 0.279, MDD -0.1205
top-quintile turnover: 0.578

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0301 | 0.378 | 0.583 |
| 2023 | 12 | 0.0214 | 0.197 | 0.667 |

regime split: up-market IC 0.0430 (n=13) / down-market IC 0.0054 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.457
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0244 | 0.0522 | 0.4676 | 0.667 | 0.0333 | 0.4883 | 0.708 |
| 5 | 0.0239 | 0.0566 | 0.4219 | 0.625 | 0.0317 | 0.4207 | 0.625 |
| 10 | 0.0209 | 0.0553 | 0.3782 | 0.625 | 0.0298 | 0.4940 | 0.667 |
| 20 | 0.0193 | 0.0326 | 0.5921 | 0.750 | 0.0213 | 0.4823 | 0.708 |
| 40 | 0.0077 | 0.0298 | 0.2594 | 0.583 | 0.0079 | 0.1592 | 0.583 |
| 60 | -0.0031 | 0.0341 | -0.0904 | 0.542 | -0.0077 | -0.1555 | 0.500 |

quantile mean forward 20d returns: Q1: 0.02876  Q2: 0.03288  Q3: 0.03240  Q4: 0.02916  Q5: 0.03966
Q5-Q1 long-short (gross, monthly): mean 0.01090, ann 0.1128, Sharpe 0.953, MDD -0.0628
top-quintile turnover: 0.485

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0179 | 0.447 | 0.583 |
| 2025 | 12 | 0.0247 | 0.518 | 0.833 |

regime split: up-market IC 0.0259 (n=15) / down-market IC 0.0136 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0241 | 0.0627 | 0.3847 | 0.667 | 0.0273 | 0.3624 | 0.667 |
| 5 | 0.0274 | 0.0558 | 0.4913 | 0.708 | 0.0253 | 0.3331 | 0.583 |
| 10 | 0.0275 | 0.0474 | 0.5805 | 0.792 | 0.0254 | 0.4295 | 0.625 |
| 20 | 0.0226 | 0.0315 | 0.7157 | 0.833 | 0.0215 | 0.4467 | 0.667 |
| 40 | 0.0106 | 0.0353 | 0.3016 | 0.625 | 0.0068 | 0.1362 | 0.625 |
| 60 | -0.0013 | 0.0401 | -0.0325 | 0.583 | -0.0069 | -0.1335 | 0.500 |

quantile mean forward 20d returns: Q1: 0.02908  Q2: 0.02974  Q3: 0.03560  Q4: 0.02895  Q5: 0.03950
Q5-Q1 long-short (gross, monthly): mean 0.01042, ann 0.1058, Sharpe 0.845, MDD -0.0705
top-quintile turnover: 0.495

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0179 | 0.378 | 0.500 |
| 2025 | 12 | 0.0252 | 0.516 | 0.833 |

regime split: up-market IC 0.0294 (n=15) / down-market IC 0.0084 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`news_count_5d`: 1.000  `news_importance_5d`: 0.960  `news_novelty_5d`: 0.938  `news_attention_5d`: 0.925  `announcement_attention_5d`: 0.925

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.