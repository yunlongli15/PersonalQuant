# factor_report_news_count_1d.md

## definition

- factor: `news_count_1d`  ·  category: news  ·  version 1.0
- formula: `count(events with availability in (d-1d, d])`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: announcement count, 1-day window
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.401
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0090 | 0.0399 | 0.2251 | 0.562 | 0.0064 | 0.1250 | 0.500 |
| 5 | 0.0072 | 0.0422 | 0.1710 | 0.521 | 0.0066 | 0.1349 | 0.521 |
| 10 | 0.0082 | 0.0364 | 0.2252 | 0.500 | 0.0096 | 0.2125 | 0.542 |
| 20 | 0.0102 | 0.0408 | 0.2490 | 0.562 | 0.0101 | 0.1848 | 0.542 |
| 40 | 0.0085 | 0.0393 | 0.2173 | 0.479 | 0.0063 | 0.1373 | 0.500 |
| 60 | 0.0030 | 0.0296 | 0.1019 | 0.542 | -0.0002 | -0.0044 | 0.562 |

quantile mean forward 20d returns: Q1: 0.00918  Q2: 0.01205  Q3: 0.01326  Q4: 0.01007  Q5: 0.01132
Q5-Q1 long-short (gross, monthly): mean 0.00214, ann 0.0230, Sharpe 0.271, MDD -0.1250
top-quintile turnover: 0.370

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0183 | 0.483 | 0.667 |
| 2019 | 12 | 0.0277 | 0.465 | 0.500 |
| 2020 | 12 | 0.0038 | 0.068 | 0.583 |
| 2021 | 12 | -0.0092 | -0.163 | 0.417 |

regime split: up-market IC 0.0146 (n=28) / down-market IC 0.0039 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0058 | 0.0353 | 0.1639 | 0.542 | 0.0061 | 0.1189 | 0.479 |
| 5 | 0.0064 | 0.0345 | 0.1849 | 0.500 | 0.0066 | 0.1341 | 0.521 |
| 10 | 0.0072 | 0.0335 | 0.2141 | 0.500 | 0.0096 | 0.2093 | 0.542 |
| 20 | 0.0091 | 0.0406 | 0.2250 | 0.542 | 0.0100 | 0.1809 | 0.542 |
| 40 | 0.0073 | 0.0361 | 0.2029 | 0.458 | 0.0065 | 0.1422 | 0.521 |
| 60 | 0.0030 | 0.0308 | 0.0965 | 0.500 | -0.0001 | -0.0015 | 0.562 |

quantile mean forward 20d returns: Q1: 0.00918  Q2: 0.01205  Q3: 0.01326  Q4: 0.01008  Q5: 0.01131
Q5-Q1 long-short (gross, monthly): mean 0.00213, ann 0.0230, Sharpe 0.271, MDD -0.1250
top-quintile turnover: 0.370

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0183 | 0.483 | 0.667 |
| 2019 | 12 | 0.0273 | 0.458 | 0.500 |
| 2020 | 12 | 0.0038 | 0.069 | 0.583 |
| 2021 | 12 | -0.0096 | -0.168 | 0.417 |

regime split: up-market IC 0.0144 (n=28) / down-market IC 0.0037 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.455
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0204 | 0.0575 | 0.3545 | 0.542 | 0.0249 | 0.3682 | 0.583 |
| 5 | 0.0218 | 0.0595 | 0.3668 | 0.625 | 0.0295 | 0.3956 | 0.625 |
| 10 | 0.0202 | 0.0506 | 0.4003 | 0.583 | 0.0276 | 0.4403 | 0.542 |
| 20 | 0.0063 | 0.0504 | 0.1259 | 0.500 | 0.0046 | 0.0757 | 0.458 |
| 40 | 0.0017 | 0.0540 | 0.0309 | 0.542 | 0.0013 | 0.0199 | 0.458 |
| 60 | 0.0182 | 0.0698 | 0.2606 | 0.542 | 0.0175 | 0.2201 | 0.542 |

quantile mean forward 20d returns: Q1: 0.00305  Q2: 0.00371  Q3: 0.00032  Q4: 0.00397  Q5: -0.00150
Q5-Q1 long-short (gross, monthly): mean -0.00455, ann -0.0464, Sharpe -0.404, MDD -0.1612
top-quintile turnover: 0.411

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0098 | 0.144 | 0.500 |
| 2023 | 12 | -0.0006 | -0.012 | 0.417 |

regime split: up-market IC -0.0134 (n=13) / down-market IC 0.0258 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0211 | 0.0568 | 0.3704 | 0.542 | 0.0250 | 0.3685 | 0.583 |
| 5 | 0.0224 | 0.0582 | 0.3847 | 0.625 | 0.0296 | 0.3962 | 0.625 |
| 10 | 0.0216 | 0.0493 | 0.4379 | 0.583 | 0.0277 | 0.4409 | 0.542 |
| 20 | 0.0076 | 0.0497 | 0.1532 | 0.500 | 0.0046 | 0.0766 | 0.458 |
| 40 | 0.0037 | 0.0527 | 0.0692 | 0.542 | 0.0014 | 0.0203 | 0.458 |
| 60 | 0.0204 | 0.0684 | 0.2981 | 0.583 | 0.0175 | 0.2204 | 0.542 |

quantile mean forward 20d returns: Q1: 0.00305  Q2: 0.00371  Q3: 0.00032  Q4: 0.00397  Q5: -0.00150
Q5-Q1 long-short (gross, monthly): mean -0.00455, ann -0.0464, Sharpe -0.404, MDD -0.1612
top-quintile turnover: 0.411

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0099 | 0.145 | 0.500 |
| 2023 | 12 | -0.0006 | -0.012 | 0.417 |

regime split: up-market IC -0.0133 (n=13) / down-market IC 0.0258 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.457
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0099 | 0.0454 | 0.2175 | 0.542 | 0.0105 | 0.1857 | 0.500 |
| 5 | 0.0170 | 0.0476 | 0.3573 | 0.542 | 0.0166 | 0.2909 | 0.417 |
| 10 | 0.0190 | 0.0521 | 0.3654 | 0.542 | 0.0202 | 0.3262 | 0.542 |
| 20 | 0.0058 | 0.0380 | 0.1525 | 0.458 | 0.0087 | 0.1922 | 0.417 |
| 40 | -0.0074 | 0.0280 | -0.2657 | 0.375 | -0.0103 | -0.2836 | 0.375 |
| 60 | -0.0072 | 0.0274 | -0.2614 | 0.292 | -0.0108 | -0.3291 | 0.292 |

quantile mean forward 20d returns: Q1: 0.02885  Q2: 0.03605  Q3: 0.03366  Q4: 0.02646  Q5: 0.03785
Q5-Q1 long-short (gross, monthly): mean 0.00900, ann 0.0877, Sharpe 0.792, MDD -0.0726
top-quintile turnover: 0.472

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0086 | 0.171 | 0.417 |
| 2025 | 12 | 0.0088 | 0.222 | 0.417 |

regime split: up-market IC -0.0007 (n=15) / down-market IC 0.0244 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0118 | 0.0489 | 0.2418 | 0.458 | 0.0095 | 0.1649 | 0.458 |
| 5 | 0.0168 | 0.0482 | 0.3486 | 0.542 | 0.0150 | 0.2589 | 0.417 |
| 10 | 0.0178 | 0.0534 | 0.3327 | 0.542 | 0.0191 | 0.3036 | 0.542 |
| 20 | 0.0064 | 0.0378 | 0.1695 | 0.417 | 0.0086 | 0.1893 | 0.417 |
| 40 | -0.0064 | 0.0289 | -0.2220 | 0.417 | -0.0111 | -0.3001 | 0.375 |
| 60 | -0.0072 | 0.0275 | -0.2606 | 0.292 | -0.0108 | -0.3288 | 0.292 |

quantile mean forward 20d returns: Q1: 0.02885  Q2: 0.03605  Q3: 0.03366  Q4: 0.02642  Q5: 0.03789
Q5-Q1 long-short (gross, monthly): mean 0.00904, ann 0.0882, Sharpe 0.797, MDD -0.0717
top-quintile turnover: 0.472

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0083 | 0.165 | 0.417 |
| 2025 | 12 | 0.0089 | 0.223 | 0.417 |

regime split: up-market IC -0.0010 (n=15) / down-market IC 0.0245 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`news_attention_1d`: 0.994  `announcement_count_5d`: 0.560  `news_count_5d`: 0.560  `news_importance_5d`: 0.553  `news_novelty_5d`: 0.546

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.