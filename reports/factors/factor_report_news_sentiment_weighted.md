# factor_report_news_sentiment_weighted.md

## definition

- factor: `news_sentiment_weighted`  ·  category: news  ·  version 1.0
- formula: `sum(sentiment*importance)/sum(importance) over 20d`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: importance-weighted 20d sentiment
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.401
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0084 | 0.0479 | -0.1762 | 0.417 | -0.0231 | -0.3043 | 0.375 |
| 5 | -0.0070 | 0.0456 | -0.1529 | 0.458 | -0.0123 | -0.2013 | 0.438 |
| 10 | -0.0128 | 0.0483 | -0.2657 | 0.417 | -0.0182 | -0.2931 | 0.354 |
| 20 | 0.0018 | 0.0530 | 0.0331 | 0.438 | -0.0078 | -0.1102 | 0.458 |
| 40 | 0.0005 | 0.0542 | 0.0092 | 0.479 | -0.0028 | -0.0395 | 0.417 |
| 60 | 0.0023 | 0.0551 | 0.0411 | 0.438 | -0.0012 | -0.0165 | 0.438 |

quantile mean forward 20d returns: Q1: 0.01027  Q2: 0.01132  Q3: 0.01575  Q4: 0.00854  Q5: 0.01001
Q5-Q1 long-short (gross, monthly): mean -0.00026, ann -0.0098, Sharpe -0.116, MDD -0.1242
top-quintile turnover: 0.195

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0160 | -0.218 | 0.333 |
| 2019 | 12 | -0.0125 | -0.185 | 0.417 |
| 2020 | 12 | -0.0071 | -0.087 | 0.417 |
| 2021 | 12 | 0.0045 | 0.081 | 0.667 |

regime split: up-market IC -0.0215 (n=28) / down-market IC 0.0115 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0169 | 0.0548 | -0.3092 | 0.375 | -0.0215 | -0.2970 | 0.354 |
| 5 | -0.0093 | 0.0465 | -0.1991 | 0.500 | -0.0148 | -0.2436 | 0.417 |
| 10 | -0.0168 | 0.0481 | -0.3500 | 0.417 | -0.0228 | -0.3686 | 0.333 |
| 20 | -0.0040 | 0.0551 | -0.0721 | 0.396 | -0.0077 | -0.1078 | 0.438 |
| 40 | -0.0051 | 0.0592 | -0.0868 | 0.354 | -0.0041 | -0.0571 | 0.417 |
| 60 | -0.0010 | 0.0564 | -0.0179 | 0.438 | 0.0006 | 0.0083 | 0.458 |

quantile mean forward 20d returns: Q1: 0.01017  Q2: 0.01128  Q3: 0.01585  Q4: 0.00852  Q5: 0.01006
Q5-Q1 long-short (gross, monthly): mean -0.00011, ann -0.0082, Sharpe -0.095, MDD -0.1242
top-quintile turnover: 0.195

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0159 | -0.218 | 0.333 |
| 2019 | 12 | -0.0104 | -0.151 | 0.417 |
| 2020 | 12 | -0.0073 | -0.088 | 0.417 |
| 2021 | 12 | 0.0030 | 0.055 | 0.583 |

regime split: up-market IC -0.0178 (n=28) / down-market IC 0.0066 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.455
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0027 | 0.0630 | 0.0431 | 0.500 | 0.0016 | 0.0196 | 0.583 |
| 5 | -0.0152 | 0.0504 | -0.3010 | 0.333 | -0.0236 | -0.3098 | 0.375 |
| 10 | -0.0124 | 0.0484 | -0.2569 | 0.458 | -0.0215 | -0.2888 | 0.292 |
| 20 | -0.0126 | 0.0375 | -0.3351 | 0.375 | -0.0284 | -0.4811 | 0.208 |
| 40 | 0.0023 | 0.0489 | 0.0462 | 0.583 | -0.0079 | -0.1138 | 0.458 |
| 60 | 0.0081 | 0.0639 | 0.1272 | 0.542 | 0.0042 | 0.0514 | 0.500 |

quantile mean forward 20d returns: Q1: 0.00303  Q2: 0.00276  Q3: 0.00466  Q4: 0.00525  Q5: -0.00616
Q5-Q1 long-short (gross, monthly): mean -0.00919, ann -0.0929, Sharpe -0.826, MDD -0.1846
top-quintile turnover: 0.243

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0331 | -0.633 | 0.250 |
| 2023 | 12 | -0.0237 | -0.366 | 0.167 |

regime split: up-market IC -0.0268 (n=13) / down-market IC -0.0302 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0019 | 0.0659 | -0.0283 | 0.458 | 0.0000 | 0.0002 | 0.583 |
| 5 | -0.0187 | 0.0530 | -0.3525 | 0.417 | -0.0241 | -0.3173 | 0.375 |
| 10 | -0.0182 | 0.0477 | -0.3826 | 0.417 | -0.0221 | -0.2978 | 0.292 |
| 20 | -0.0149 | 0.0344 | -0.4322 | 0.333 | -0.0285 | -0.4852 | 0.208 |
| 40 | -0.0044 | 0.0413 | -0.1056 | 0.458 | -0.0088 | -0.1305 | 0.458 |
| 60 | -0.0011 | 0.0551 | -0.0198 | 0.542 | 0.0033 | 0.0420 | 0.500 |

quantile mean forward 20d returns: Q1: 0.00301  Q2: 0.00275  Q3: 0.00523  Q4: 0.00478  Q5: -0.00624
Q5-Q1 long-short (gross, monthly): mean -0.00925, ann -0.0935, Sharpe -0.835, MDD -0.1846
top-quintile turnover: 0.231

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0334 | -0.642 | 0.250 |
| 2023 | 12 | -0.0237 | -0.367 | 0.167 |

regime split: up-market IC -0.0282 (n=13) / down-market IC -0.0289 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.457
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0141 | 0.0636 | 0.2217 | 0.708 | 0.0191 | 0.2292 | 0.667 |
| 5 | 0.0136 | 0.0671 | 0.2032 | 0.542 | 0.0064 | 0.0788 | 0.500 |
| 10 | 0.0059 | 0.0573 | 0.1037 | 0.542 | -0.0002 | -0.0028 | 0.417 |
| 20 | 0.0075 | 0.0413 | 0.1815 | 0.625 | -0.0025 | -0.0374 | 0.625 |
| 40 | 0.0023 | 0.0341 | 0.0665 | 0.417 | -0.0041 | -0.0800 | 0.500 |
| 60 | -0.0105 | 0.0327 | -0.3222 | 0.333 | -0.0218 | -0.4120 | 0.375 |

quantile mean forward 20d returns: Q1: 0.03298  Q2: 0.03181  Q3: 0.03177  Q4: 0.02658  Q5: 0.03973
Q5-Q1 long-short (gross, monthly): mean 0.00675, ann 0.0628, Sharpe 0.723, MDD -0.0809
top-quintile turnover: 0.240

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0066 | 0.085 | 0.750 |
| 2025 | 12 | -0.0116 | -0.213 | 0.500 |

regime split: up-market IC -0.0156 (n=15) / down-market IC 0.0193 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0130 | 0.0596 | 0.2185 | 0.708 | 0.0163 | 0.1970 | 0.667 |
| 5 | 0.0080 | 0.0639 | 0.1249 | 0.500 | 0.0033 | 0.0391 | 0.500 |
| 10 | 0.0006 | 0.0548 | 0.0110 | 0.500 | -0.0027 | -0.0361 | 0.417 |
| 20 | 0.0008 | 0.0439 | 0.0177 | 0.625 | -0.0046 | -0.0689 | 0.583 |
| 40 | -0.0017 | 0.0327 | -0.0530 | 0.458 | -0.0050 | -0.0991 | 0.500 |
| 60 | -0.0147 | 0.0330 | -0.4461 | 0.292 | -0.0222 | -0.4244 | 0.375 |

quantile mean forward 20d returns: Q1: 0.03298  Q2: 0.03181  Q3: 0.03205  Q4: 0.02680  Q5: 0.03924
Q5-Q1 long-short (gross, monthly): mean 0.00626, ann 0.0566, Sharpe 0.663, MDD -0.0809
top-quintile turnover: 0.236

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0025 | 0.032 | 0.667 |
| 2025 | 12 | -0.0117 | -0.214 | 0.500 |

regime split: up-market IC -0.0156 (n=15) / down-market IC 0.0138 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`buyback_event_count_20d`: 0.404  `negative_news_count_5d`: -0.312  `event_sentiment_shock`: -0.092  `announcement_attention_5d`: -0.036  `news_attention_5d`: -0.036

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.