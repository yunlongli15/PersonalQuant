# factor_report_news_novelty_5d.md

## definition

- factor: `news_novelty_5d`  ·  category: news  ·  version 1.0
- formula: `mean novelty of events in 5d`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: 5-day mean event novelty
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.401
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0222 | 0.0539 | 0.4114 | 0.729 | 0.0248 | 0.3682 | 0.708 |
| 5 | 0.0157 | 0.0460 | 0.3407 | 0.625 | 0.0147 | 0.2669 | 0.604 |
| 10 | 0.0202 | 0.0447 | 0.4526 | 0.625 | 0.0207 | 0.3706 | 0.583 |
| 20 | 0.0165 | 0.0474 | 0.3480 | 0.604 | 0.0185 | 0.3054 | 0.604 |
| 40 | 0.0213 | 0.0488 | 0.4376 | 0.646 | 0.0220 | 0.3749 | 0.646 |
| 60 | 0.0209 | 0.0559 | 0.3732 | 0.625 | 0.0187 | 0.2826 | 0.583 |

quantile mean forward 20d returns: Q1: 0.00849  Q2: 0.00818  Q3: 0.01058  Q4: 0.01392  Q5: 0.01471
Q5-Q1 long-short (gross, monthly): mean 0.00622, ann 0.0701, Sharpe 0.794, MDD -0.1030
top-quintile turnover: 0.691

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0217 | 0.606 | 0.667 |
| 2019 | 12 | 0.0432 | 0.783 | 0.667 |
| 2020 | 12 | 0.0064 | 0.080 | 0.583 |
| 2021 | 12 | 0.0026 | 0.049 | 0.500 |

regime split: up-market IC 0.0314 (n=28) / down-market IC 0.0003 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0227 | 0.0544 | 0.4180 | 0.750 | 0.0241 | 0.3625 | 0.708 |
| 5 | 0.0139 | 0.0450 | 0.3087 | 0.625 | 0.0148 | 0.2660 | 0.583 |
| 10 | 0.0186 | 0.0435 | 0.4286 | 0.604 | 0.0215 | 0.3795 | 0.604 |
| 20 | 0.0143 | 0.0453 | 0.3166 | 0.667 | 0.0188 | 0.3058 | 0.625 |
| 40 | 0.0170 | 0.0464 | 0.3661 | 0.625 | 0.0222 | 0.3690 | 0.604 |
| 60 | 0.0187 | 0.0553 | 0.3385 | 0.667 | 0.0196 | 0.2832 | 0.583 |

quantile mean forward 20d returns: Q1: 0.00841  Q2: 0.00825  Q3: 0.01035  Q4: 0.01426  Q5: 0.01461
Q5-Q1 long-short (gross, monthly): mean 0.00620, ann 0.0698, Sharpe 0.772, MDD -0.1011
top-quintile turnover: 0.722

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0212 | 0.588 | 0.667 |
| 2019 | 12 | 0.0445 | 0.782 | 0.750 |
| 2020 | 12 | 0.0068 | 0.084 | 0.583 |
| 2021 | 12 | 0.0028 | 0.051 | 0.500 |

regime split: up-market IC 0.0319 (n=28) / down-market IC 0.0004 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.455
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0214 | 0.0586 | 0.3661 | 0.583 | 0.0281 | 0.3853 | 0.625 |
| 5 | 0.0132 | 0.0653 | 0.2017 | 0.500 | 0.0217 | 0.2813 | 0.542 |
| 10 | 0.0215 | 0.0588 | 0.3665 | 0.625 | 0.0282 | 0.3888 | 0.583 |
| 20 | 0.0274 | 0.0714 | 0.3836 | 0.625 | 0.0318 | 0.3700 | 0.625 |
| 40 | 0.0230 | 0.0574 | 0.4003 | 0.625 | 0.0279 | 0.3744 | 0.625 |
| 60 | 0.0284 | 0.0623 | 0.4564 | 0.708 | 0.0330 | 0.4006 | 0.625 |

quantile mean forward 20d returns: Q1: 0.00098  Q2: 0.00116  Q3: 0.00060  Q4: 0.00298  Q5: 0.00382
Q5-Q1 long-short (gross, monthly): mean 0.00283, ann 0.0408, Sharpe 0.298, MDD -0.1452
top-quintile turnover: 0.680

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0485 | 0.801 | 0.667 |
| 2023 | 12 | 0.0152 | 0.148 | 0.583 |

regime split: up-market IC 0.0457 (n=13) / down-market IC 0.0154 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0258 | 0.0606 | 0.4257 | 0.625 | 0.0283 | 0.3937 | 0.625 |
| 5 | 0.0197 | 0.0642 | 0.3072 | 0.583 | 0.0216 | 0.2775 | 0.542 |
| 10 | 0.0258 | 0.0586 | 0.4402 | 0.667 | 0.0285 | 0.4005 | 0.583 |
| 20 | 0.0317 | 0.0763 | 0.4155 | 0.625 | 0.0338 | 0.3889 | 0.625 |
| 40 | 0.0268 | 0.0601 | 0.4459 | 0.625 | 0.0290 | 0.3901 | 0.625 |
| 60 | 0.0309 | 0.0669 | 0.4609 | 0.708 | 0.0341 | 0.4131 | 0.625 |

quantile mean forward 20d returns: Q1: 0.00096  Q2: 0.00119  Q3: 0.00057  Q4: 0.00267  Q5: 0.00414
Q5-Q1 long-short (gross, monthly): mean 0.00318, ann 0.0447, Sharpe 0.321, MDD -0.1477
top-quintile turnover: 0.689

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0495 | 0.796 | 0.667 |
| 2023 | 12 | 0.0181 | 0.175 | 0.583 |

regime split: up-market IC 0.0491 (n=13) / down-market IC 0.0157 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.457
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0201 | 0.0485 | 0.4141 | 0.583 | 0.0279 | 0.4817 | 0.708 |
| 5 | 0.0171 | 0.0555 | 0.3075 | 0.625 | 0.0281 | 0.4025 | 0.667 |
| 10 | 0.0213 | 0.0419 | 0.5069 | 0.667 | 0.0323 | 0.6821 | 0.792 |
| 20 | 0.0149 | 0.0308 | 0.4832 | 0.708 | 0.0215 | 0.4977 | 0.750 |
| 40 | 0.0027 | 0.0294 | 0.0906 | 0.458 | 0.0043 | 0.0911 | 0.583 |
| 60 | -0.0053 | 0.0315 | -0.1676 | 0.500 | -0.0106 | -0.2286 | 0.417 |

quantile mean forward 20d returns: Q1: 0.02752  Q2: 0.03220  Q3: 0.03301  Q4: 0.03461  Q5: 0.03553
Q5-Q1 long-short (gross, monthly): mean 0.00802, ann 0.0779, Sharpe 0.825, MDD -0.0717
top-quintile turnover: 0.675

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0245 | 0.628 | 0.667 |
| 2025 | 12 | 0.0185 | 0.395 | 0.833 |

regime split: up-market IC 0.0221 (n=15) / down-market IC 0.0203 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0235 | 0.0488 | 0.4814 | 0.667 | 0.0278 | 0.4817 | 0.708 |
| 5 | 0.0174 | 0.0552 | 0.3144 | 0.583 | 0.0277 | 0.3965 | 0.667 |
| 10 | 0.0234 | 0.0411 | 0.5690 | 0.708 | 0.0321 | 0.6789 | 0.792 |
| 20 | 0.0178 | 0.0315 | 0.5632 | 0.750 | 0.0214 | 0.4967 | 0.750 |
| 40 | 0.0047 | 0.0320 | 0.1459 | 0.500 | 0.0041 | 0.0865 | 0.583 |
| 60 | -0.0036 | 0.0316 | -0.1152 | 0.542 | -0.0108 | -0.2347 | 0.417 |

quantile mean forward 20d returns: Q1: 0.02752  Q2: 0.03220  Q3: 0.03296  Q4: 0.03457  Q5: 0.03563
Q5-Q1 long-short (gross, monthly): mean 0.00811, ann 0.0791, Sharpe 0.837, MDD -0.0717
top-quintile turnover: 0.673

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0246 | 0.625 | 0.667 |
| 2025 | 12 | 0.0183 | 0.394 | 0.833 |

regime split: up-market IC 0.0223 (n=15) / down-market IC 0.0200 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`news_importance_5d`: 0.958  `announcement_count_5d`: 0.938  `news_count_5d`: 0.938  `announcement_attention_5d`: 0.901  `news_attention_5d`: 0.901

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.