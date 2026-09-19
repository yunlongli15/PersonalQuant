# factor_report_regulatory_event_count_20d.md

## definition

- factor: `regulatory_event_count_20d`  ·  category: news  ·  version 1.0
- formula: `count(regulatory/penalty/investigation events in 20d)`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: regulatory-risk event count, 20d
- declared (economic) direction: **negative**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.401
- empirical direction: positive  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0107 | 0.0495 | 0.2163 | 0.543 | 0.0100 | 0.1820 | 0.587 |
| 5 | 0.0027 | 0.0239 | 0.1148 | 0.457 | 0.0032 | 0.1027 | 0.500 |
| 10 | 0.0085 | 0.0368 | 0.2318 | 0.543 | 0.0114 | 0.2781 | 0.630 |
| 20 | 0.0010 | 0.0349 | 0.0275 | 0.413 | 0.0005 | 0.0115 | 0.500 |
| 40 | 0.0092 | 0.0359 | 0.2553 | 0.522 | 0.0072 | 0.1828 | 0.543 |
| 60 | 0.0067 | 0.0275 | 0.2444 | 0.587 | 0.0053 | 0.1612 | 0.565 |

quantile mean forward 20d returns: Q1: 0.00936  Q2: 0.01192  Q3: 0.01590  Q4: 0.00837  Q5: 0.01034
Q5-Q1 long-short (gross, monthly): mean 0.00098, ann 0.0105, Sharpe 0.107, MDD -0.1368
top-quintile turnover: 0.084

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0132 | 0.275 | 0.500 |
| 2019 | 10 | 0.0066 | 0.208 | 0.600 |
| 2020 | 12 | -0.0022 | -0.064 | 0.417 |
| 2021 | 12 | -0.0137 | -0.329 | 0.500 |

regime split: up-market IC 0.0033 (n=27) / down-market IC -0.0038 (n=19)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0109 | 0.0500 | 0.2189 | 0.533 | 0.0100 | 0.1817 | 0.600 |
| 5 | 0.0028 | 0.0241 | 0.1161 | 0.444 | 0.0032 | 0.1016 | 0.511 |
| 10 | 0.0087 | 0.0372 | 0.2345 | 0.578 | 0.0113 | 0.2767 | 0.644 |
| 20 | 0.0010 | 0.0353 | 0.0279 | 0.422 | 0.0004 | 0.0110 | 0.511 |
| 40 | 0.0094 | 0.0362 | 0.2585 | 0.533 | 0.0072 | 0.1825 | 0.556 |
| 60 | 0.0069 | 0.0278 | 0.2475 | 0.600 | 0.0053 | 0.1606 | 0.578 |

quantile mean forward 20d returns: Q1: 0.00406  Q2: 0.00576  Q3: 0.00841  Q4: 0.00378  Q5: 0.00566
Q5-Q1 long-short (gross, monthly): mean 0.00160, ann 0.0024, Sharpe 0.025, MDD -0.1368
top-quintile turnover: 0.086

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 11 | 0.0132 | 0.275 | 0.545 |
| 2019 | 10 | 0.0066 | 0.208 | 0.600 |
| 2020 | 12 | -0.0022 | -0.064 | 0.417 |
| 2021 | 12 | -0.0138 | -0.331 | 0.500 |

regime split: up-market IC 0.0033 (n=27) / down-market IC -0.0039 (n=18)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.455
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0024 | 0.0380 | 0.0634 | 0.458 | 0.0014 | 0.0340 | 0.500 |
| 5 | 0.0084 | 0.0608 | 0.1381 | 0.458 | 0.0105 | 0.1525 | 0.500 |
| 10 | 0.0101 | 0.0570 | 0.1765 | 0.542 | 0.0086 | 0.1349 | 0.458 |
| 20 | -0.0031 | 0.0364 | -0.0849 | 0.500 | -0.0045 | -0.1103 | 0.500 |
| 40 | -0.0136 | 0.0436 | -0.3124 | 0.500 | -0.0143 | -0.2760 | 0.458 |
| 60 | -0.0092 | 0.0377 | -0.2435 | 0.375 | -0.0140 | -0.3092 | 0.417 |

quantile mean forward 20d returns: Q1: 0.00346  Q2: 0.00369  Q3: -0.00010  Q4: 0.00475  Q5: -0.00227
Q5-Q1 long-short (gross, monthly): mean -0.00573, ann -0.0559, Sharpe -0.481, MDD -0.1462
top-quintile turnover: 0.141

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0076 | -0.188 | 0.500 |
| 2023 | 12 | -0.0017 | -0.042 | 0.500 |

regime split: up-market IC -0.0131 (n=13) / down-market IC 0.0048 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0025 | 0.0389 | 0.0647 | 0.478 | 0.0014 | 0.0340 | 0.522 |
| 5 | 0.0088 | 0.0621 | 0.1411 | 0.478 | 0.0105 | 0.1525 | 0.522 |
| 10 | 0.0105 | 0.0582 | 0.1804 | 0.522 | 0.0086 | 0.1349 | 0.478 |
| 20 | -0.0032 | 0.0371 | -0.0868 | 0.478 | -0.0045 | -0.1103 | 0.522 |
| 40 | -0.0142 | 0.0445 | -0.3198 | 0.522 | -0.0143 | -0.2760 | 0.478 |
| 60 | -0.0096 | 0.0384 | -0.2491 | 0.391 | -0.0140 | -0.3092 | 0.435 |

quantile mean forward 20d returns: Q1: 0.00143  Q2: 0.00175  Q3: -0.00232  Q4: 0.00199  Q5: -0.00298
Q5-Q1 long-short (gross, monthly): mean -0.00441, ann -0.0298, Sharpe -0.256, MDD -0.1462
top-quintile turnover: 0.133

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 11 | -0.0076 | -0.188 | 0.545 |
| 2023 | 12 | -0.0017 | -0.042 | 0.500 |

regime split: up-market IC -0.0131 (n=12) / down-market IC 0.0048 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.457
- empirical direction: positive  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0137 | 0.0503 | 0.2721 | 0.500 | 0.0134 | 0.2462 | 0.500 |
| 5 | 0.0172 | 0.0517 | 0.3333 | 0.545 | 0.0173 | 0.3242 | 0.545 |
| 10 | 0.0158 | 0.0480 | 0.3287 | 0.545 | 0.0144 | 0.2943 | 0.591 |
| 20 | 0.0154 | 0.0382 | 0.4044 | 0.500 | 0.0118 | 0.3051 | 0.500 |
| 40 | 0.0064 | 0.0195 | 0.3309 | 0.625 | 0.0028 | 0.1523 | 0.458 |
| 60 | 0.0088 | 0.0210 | 0.4212 | 0.565 | 0.0066 | 0.2993 | 0.478 |

quantile mean forward 20d returns: Q1: 0.02851  Q2: 0.03598  Q3: 0.03457  Q4: 0.02615  Q5: 0.03766
Q5-Q1 long-short (gross, monthly): mean 0.00915, ann 0.1010, Sharpe 0.898, MDD -0.0768
top-quintile turnover: 0.059

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 11 | -0.0015 | -0.060 | 0.455 |
| 2025 | 11 | 0.0250 | 0.555 | 0.545 |

regime split: up-market IC 0.0201 (n=13) / down-market IC -0.0037 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0150 | 0.0525 | 0.2864 | 0.500 | 0.0134 | 0.2462 | 0.550 |
| 5 | 0.0190 | 0.0539 | 0.3516 | 0.550 | 0.0173 | 0.3242 | 0.600 |
| 10 | 0.0173 | 0.0500 | 0.3466 | 0.500 | 0.0144 | 0.2943 | 0.650 |
| 20 | 0.0170 | 0.0397 | 0.4276 | 0.550 | 0.0118 | 0.3051 | 0.550 |
| 40 | 0.0077 | 0.0211 | 0.3666 | 0.600 | 0.0028 | 0.1523 | 0.550 |
| 60 | 0.0102 | 0.0222 | 0.4579 | 0.600 | 0.0066 | 0.2993 | 0.550 |

quantile mean forward 20d returns: Q1: 0.02071  Q2: 0.02495  Q3: 0.02243  Q4: 0.01794  Q5: 0.03039
Q5-Q1 long-short (gross, monthly): mean 0.00967, ann 0.1080, Sharpe 1.111, MDD -0.0758
top-quintile turnover: 0.088

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 10 | -0.0015 | -0.060 | 0.500 |
| 2025 | 10 | 0.0250 | 0.555 | 0.600 |

regime split: up-market IC 0.0201 (n=13) / down-market IC -0.0037 (n=7)

---

## correlation with other factors (avg cross-sectional spearman, research)

`major_event_count_20d`: 0.354  `negative_news_count_5d`: 0.293  `announcement_count_20d`: 0.178  `news_count_20d`: 0.178  `announcement_count_5d`: 0.151

## interpretation & limitations

- declared direction `negative` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.