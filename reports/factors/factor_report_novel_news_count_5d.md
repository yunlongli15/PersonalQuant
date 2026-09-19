# factor_report_novel_news_count_5d.md

## definition

- factor: `novel_news_count_5d`  ·  category: news  ·  version 1.0
- formula: `count(novelty >= 0.8 events in 5d)`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: novel announcement count, 5d
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.401
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0068 | 0.0415 | 0.1651 | 0.521 | 0.0085 | 0.1696 | 0.438 |
| 5 | 0.0023 | 0.0392 | 0.0583 | 0.521 | 0.0044 | 0.0895 | 0.500 |
| 10 | 0.0049 | 0.0409 | 0.1209 | 0.521 | 0.0072 | 0.1417 | 0.500 |
| 20 | 0.0114 | 0.0476 | 0.2391 | 0.500 | 0.0147 | 0.2619 | 0.521 |
| 40 | 0.0037 | 0.0399 | 0.0932 | 0.542 | 0.0071 | 0.1506 | 0.521 |
| 60 | 0.0054 | 0.0423 | 0.1287 | 0.583 | 0.0079 | 0.1501 | 0.500 |

quantile mean forward 20d returns: Q1: 0.00857  Q2: 0.01140  Q3: 0.01483  Q4: 0.00989  Q5: 0.01120
Q5-Q1 long-short (gross, monthly): mean 0.00263, ann 0.0295, Sharpe 0.373, MDD -0.0864
top-quintile turnover: 0.573

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0098 | -0.254 | 0.417 |
| 2019 | 12 | 0.0277 | 0.490 | 0.667 |
| 2020 | 12 | 0.0264 | 0.402 | 0.583 |
| 2021 | 12 | 0.0144 | 0.281 | 0.417 |

regime split: up-market IC 0.0216 (n=28) / down-market IC 0.0049 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0074 | 0.0411 | 0.1794 | 0.542 | 0.0085 | 0.1699 | 0.438 |
| 5 | 0.0030 | 0.0392 | 0.0776 | 0.521 | 0.0044 | 0.0897 | 0.500 |
| 10 | 0.0057 | 0.0415 | 0.1369 | 0.521 | 0.0072 | 0.1417 | 0.500 |
| 20 | 0.0117 | 0.0482 | 0.2437 | 0.500 | 0.0147 | 0.2619 | 0.521 |
| 40 | 0.0041 | 0.0400 | 0.1032 | 0.542 | 0.0071 | 0.1507 | 0.521 |
| 60 | 0.0055 | 0.0426 | 0.1304 | 0.583 | 0.0079 | 0.1501 | 0.500 |

quantile mean forward 20d returns: Q1: 0.00857  Q2: 0.01140  Q3: 0.01483  Q4: 0.00989  Q5: 0.01120
Q5-Q1 long-short (gross, monthly): mean 0.00263, ann 0.0295, Sharpe 0.373, MDD -0.0864
top-quintile turnover: 0.573

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0098 | -0.254 | 0.417 |
| 2019 | 12 | 0.0277 | 0.490 | 0.667 |
| 2020 | 12 | 0.0264 | 0.403 | 0.583 |
| 2021 | 12 | 0.0144 | 0.281 | 0.417 |

regime split: up-market IC 0.0216 (n=28) / down-market IC 0.0049 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.455
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0026 | 0.0404 | 0.0640 | 0.542 | 0.0024 | 0.0506 | 0.417 |
| 5 | 0.0052 | 0.0388 | 0.1330 | 0.435 | 0.0072 | 0.1302 | 0.435 |
| 10 | 0.0049 | 0.0460 | 0.1072 | 0.435 | 0.0070 | 0.1140 | 0.478 |
| 20 | -0.0013 | 0.0378 | -0.0346 | 0.458 | -0.0013 | -0.0268 | 0.375 |
| 40 | -0.0079 | 0.0412 | -0.1924 | 0.375 | -0.0101 | -0.2096 | 0.375 |
| 60 | 0.0019 | 0.0347 | 0.0551 | 0.391 | -0.0004 | -0.0082 | 0.391 |

quantile mean forward 20d returns: Q1: 0.00330  Q2: 0.00370  Q3: 0.00084  Q4: 0.00291  Q5: -0.00121
Q5-Q1 long-short (gross, monthly): mean -0.00451, ann -0.0414, Sharpe -0.376, MDD -0.1654
top-quintile turnover: 0.554

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0128 | 0.303 | 0.500 |
| 2023 | 12 | -0.0143 | -0.268 | 0.250 |

regime split: up-market IC -0.0065 (n=13) / down-market IC 0.0043 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0029 | 0.0414 | 0.0706 | 0.522 | 0.0024 | 0.0506 | 0.435 |
| 5 | 0.0055 | 0.0388 | 0.1407 | 0.435 | 0.0072 | 0.1302 | 0.435 |
| 10 | 0.0053 | 0.0461 | 0.1160 | 0.435 | 0.0070 | 0.1140 | 0.478 |
| 20 | -0.0012 | 0.0388 | -0.0309 | 0.478 | -0.0013 | -0.0268 | 0.391 |
| 40 | -0.0082 | 0.0421 | -0.1947 | 0.391 | -0.0101 | -0.2096 | 0.391 |
| 60 | 0.0023 | 0.0344 | 0.0679 | 0.391 | -0.0004 | -0.0082 | 0.391 |

quantile mean forward 20d returns: Q1: 0.00066  Q2: 0.00021  Q3: -0.00247  Q4: 0.00128  Q5: -0.00535
Q5-Q1 long-short (gross, monthly): mean -0.00601, ann -0.0579, Sharpe -0.528, MDD -0.1654
top-quintile turnover: 0.565

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 11 | 0.0128 | 0.303 | 0.545 |
| 2023 | 12 | -0.0143 | -0.268 | 0.250 |

regime split: up-market IC -0.0065 (n=12) / down-market IC 0.0043 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.457
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0092 | 0.0593 | 0.1560 | 0.500 | 0.0102 | 0.1505 | 0.542 |
| 5 | 0.0172 | 0.0479 | 0.3585 | 0.652 | 0.0225 | 0.4232 | 0.652 |
| 10 | 0.0192 | 0.0502 | 0.3830 | 0.565 | 0.0242 | 0.4561 | 0.783 |
| 20 | 0.0092 | 0.0344 | 0.2676 | 0.542 | 0.0115 | 0.3319 | 0.583 |
| 40 | 0.0000 | 0.0239 | 0.0005 | 0.542 | 0.0013 | 0.0521 | 0.500 |
| 60 | 0.0007 | 0.0263 | 0.0253 | 0.417 | -0.0003 | -0.0083 | 0.458 |

quantile mean forward 20d returns: Q1: 0.02847  Q2: 0.03551  Q3: 0.03261  Q4: 0.03114  Q5: 0.03513
Q5-Q1 long-short (gross, monthly): mean 0.00666, ann 0.0703, Sharpe 0.716, MDD -0.0747
top-quintile turnover: 0.568

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0069 | 0.269 | 0.583 |
| 2025 | 12 | 0.0166 | 0.395 | 0.583 |

regime split: up-market IC 0.0129 (n=15) / down-market IC 0.0094 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0097 | 0.0606 | 0.1595 | 0.522 | 0.0102 | 0.1505 | 0.565 |
| 5 | 0.0172 | 0.0479 | 0.3593 | 0.652 | 0.0226 | 0.4232 | 0.652 |
| 10 | 0.0193 | 0.0502 | 0.3839 | 0.609 | 0.0243 | 0.4562 | 0.783 |
| 20 | 0.0096 | 0.0351 | 0.2744 | 0.522 | 0.0115 | 0.3320 | 0.609 |
| 40 | 0.0001 | 0.0243 | 0.0059 | 0.522 | 0.0013 | 0.0521 | 0.522 |
| 60 | 0.0008 | 0.0268 | 0.0285 | 0.435 | -0.0003 | -0.0084 | 0.478 |

quantile mean forward 20d returns: Q1: 0.02857  Q2: 0.03649  Q3: 0.03316  Q4: 0.03173  Q5: 0.03558
Q5-Q1 long-short (gross, monthly): mean 0.00701, ann 0.0742, Sharpe 0.741, MDD -0.0734
top-quintile turnover: 0.574

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0069 | 0.269 | 0.583 |
| 2025 | 11 | 0.0166 | 0.395 | 0.636 |

regime split: up-market IC 0.0129 (n=14) / down-market IC 0.0095 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`announcement_attention_5d`: 0.633  `news_attention_5d`: 0.633  `announcement_count_5d`: 0.591  `news_count_5d`: 0.591  `news_importance_5d`: 0.590

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.