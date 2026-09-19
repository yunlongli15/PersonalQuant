# factor_report_announcement_attention_5d.md

## definition

- factor: `announcement_attention_5d`  ·  category: news  ·  version 1.0
- formula: `count(5d) / mean_count(60d) — 同 news_attention_5d（v1 公告=全部文档）`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: announcement attention, 5d vs 60d baseline
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.201
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0056 | 0.0578 | 0.0966 | 0.542 | 0.0110 | 0.1552 | 0.521 |
| 5 | 0.0093 | 0.0413 | 0.2262 | 0.562 | 0.0111 | 0.2145 | 0.583 |
| 10 | 0.0151 | 0.0431 | 0.3500 | 0.625 | 0.0172 | 0.3110 | 0.562 |
| 20 | 0.0176 | 0.0501 | 0.3521 | 0.604 | 0.0200 | 0.3205 | 0.604 |
| 40 | 0.0180 | 0.0522 | 0.3456 | 0.583 | 0.0202 | 0.3124 | 0.562 |
| 60 | 0.0164 | 0.0571 | 0.2863 | 0.542 | 0.0191 | 0.2655 | 0.542 |

quantile mean forward 20d returns: Q1: 0.00762  Q2: 0.00911  Q3: 0.01281  Q4: 0.01282  Q5: 0.01353
Q5-Q1 long-short (gross, monthly): mean 0.00591, ann 0.0701, Sharpe 0.750, MDD -0.0878
top-quintile turnover: 0.742

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0083 | 0.167 | 0.417 |
| 2019 | 12 | 0.0286 | 0.443 | 0.583 |
| 2020 | 12 | 0.0165 | 0.205 | 0.583 |
| 2021 | 12 | 0.0266 | 0.566 | 0.833 |

regime split: up-market IC 0.0335 (n=28) / down-market IC 0.0010 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0025 | 0.0607 | 0.0414 | 0.458 | 0.0111 | 0.1542 | 0.542 |
| 5 | 0.0031 | 0.0423 | 0.0725 | 0.542 | 0.0103 | 0.1984 | 0.562 |
| 10 | 0.0090 | 0.0412 | 0.2178 | 0.521 | 0.0173 | 0.3091 | 0.562 |
| 20 | 0.0134 | 0.0455 | 0.2933 | 0.604 | 0.0198 | 0.3155 | 0.604 |
| 40 | 0.0092 | 0.0502 | 0.1822 | 0.583 | 0.0201 | 0.3039 | 0.562 |
| 60 | 0.0088 | 0.0562 | 0.1571 | 0.542 | 0.0195 | 0.2710 | 0.562 |

quantile mean forward 20d returns: Q1: 0.00787  Q2: 0.00833  Q3: 0.01272  Q4: 0.01309  Q5: 0.01387
Q5-Q1 long-short (gross, monthly): mean 0.00600, ann 0.0711, Sharpe 0.762, MDD -0.0895
top-quintile turnover: 0.745

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0072 | 0.144 | 0.417 |
| 2019 | 12 | 0.0268 | 0.409 | 0.583 |
| 2020 | 12 | 0.0158 | 0.195 | 0.583 |
| 2021 | 12 | 0.0294 | 0.651 | 0.833 |

regime split: up-market IC 0.0340 (n=28) / down-market IC -0.0000 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.188
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0014 | 0.0578 | -0.0243 | 0.458 | -0.0019 | -0.0286 | 0.500 |
| 5 | -0.0079 | 0.0516 | -0.1529 | 0.417 | -0.0093 | -0.1429 | 0.417 |
| 10 | -0.0050 | 0.0477 | -0.1056 | 0.417 | -0.0077 | -0.1196 | 0.417 |
| 20 | 0.0094 | 0.0567 | 0.1667 | 0.542 | 0.0128 | 0.1755 | 0.583 |
| 40 | 0.0120 | 0.0571 | 0.2101 | 0.458 | 0.0194 | 0.2790 | 0.583 |
| 60 | 0.0164 | 0.0553 | 0.2973 | 0.542 | 0.0154 | 0.2159 | 0.500 |

quantile mean forward 20d returns: Q1: -0.00192  Q2: 0.00472  Q3: 0.00133  Q4: 0.00752  Q5: -0.00211
Q5-Q1 long-short (gross, monthly): mean -0.00019, ann 0.0101, Sharpe 0.090, MDD -0.0893
top-quintile turnover: 0.752

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0322 | 0.495 | 0.667 |
| 2023 | 12 | -0.0066 | -0.087 | 0.500 |

regime split: up-market IC 0.0302 (n=13) / down-market IC -0.0077 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0066 | 0.0536 | -0.1229 | 0.417 | 0.0008 | 0.0109 | 0.458 |
| 5 | -0.0070 | 0.0530 | -0.1322 | 0.375 | -0.0025 | -0.0388 | 0.417 |
| 10 | -0.0034 | 0.0523 | -0.0656 | 0.375 | -0.0019 | -0.0302 | 0.500 |
| 20 | 0.0006 | 0.0552 | 0.0111 | 0.542 | 0.0122 | 0.1724 | 0.625 |
| 40 | 0.0061 | 0.0500 | 0.1224 | 0.458 | 0.0176 | 0.2450 | 0.583 |
| 60 | 0.0118 | 0.0497 | 0.2373 | 0.500 | 0.0238 | 0.3219 | 0.625 |

quantile mean forward 20d returns: Q1: -0.00166  Q2: 0.00398  Q3: 0.00276  Q4: 0.00708  Q5: -0.00261
Q5-Q1 long-short (gross, monthly): mean -0.00095, ann 0.0010, Sharpe 0.009, MDD -0.0893
top-quintile turnover: 0.748

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0370 | 0.632 | 0.750 |
| 2023 | 12 | -0.0126 | -0.172 | 0.500 |

regime split: up-market IC 0.0299 (n=13) / down-market IC -0.0088 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.203
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0119 | 0.0591 | 0.2007 | 0.417 | 0.0128 | 0.1928 | 0.542 |
| 5 | 0.0218 | 0.0535 | 0.4083 | 0.667 | 0.0265 | 0.4160 | 0.708 |
| 10 | 0.0270 | 0.0561 | 0.4818 | 0.667 | 0.0303 | 0.4972 | 0.708 |
| 20 | 0.0100 | 0.0430 | 0.2327 | 0.708 | 0.0148 | 0.2875 | 0.667 |
| 40 | -0.0028 | 0.0407 | -0.0699 | 0.583 | 0.0035 | 0.0723 | 0.667 |
| 60 | -0.0117 | 0.0344 | -0.3411 | 0.417 | -0.0120 | -0.2874 | 0.417 |

quantile mean forward 20d returns: Q1: 0.03097  Q2: 0.03182  Q3: 0.03320  Q4: 0.02791  Q5: 0.03897
Q5-Q1 long-short (gross, monthly): mean 0.00800, ann 0.0777, Sharpe 0.827, MDD -0.0896
top-quintile turnover: 0.798

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0076 | 0.125 | 0.667 |
| 2025 | 12 | 0.0220 | 0.569 | 0.667 |

regime split: up-market IC 0.0128 (n=15) / down-market IC 0.0181 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0155 | 0.0666 | 0.2331 | 0.417 | 0.0115 | 0.1623 | 0.458 |
| 5 | 0.0288 | 0.0577 | 0.4988 | 0.708 | 0.0250 | 0.3513 | 0.625 |
| 10 | 0.0317 | 0.0613 | 0.5171 | 0.750 | 0.0310 | 0.4657 | 0.625 |
| 20 | 0.0144 | 0.0439 | 0.3288 | 0.708 | 0.0171 | 0.3681 | 0.625 |
| 40 | 0.0020 | 0.0451 | 0.0437 | 0.583 | 0.0004 | 0.0089 | 0.667 |
| 60 | -0.0072 | 0.0347 | -0.2072 | 0.458 | -0.0116 | -0.2799 | 0.417 |

quantile mean forward 20d returns: Q1: 0.02825  Q2: 0.03274  Q3: 0.03384  Q4: 0.02967  Q5: 0.03836
Q5-Q1 long-short (gross, monthly): mean 0.01010, ann 0.1054, Sharpe 1.174, MDD -0.0615
top-quintile turnover: 0.775

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0109 | 0.203 | 0.583 |
| 2025 | 12 | 0.0233 | 0.628 | 0.667 |

regime split: up-market IC 0.0192 (n=15) / down-market IC 0.0136 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`news_attention_5d`: 1.000  `announcement_count_5d`: 0.925  `news_count_5d`: 0.925  `news_importance_5d`: 0.920  `news_novelty_5d`: 0.901

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.