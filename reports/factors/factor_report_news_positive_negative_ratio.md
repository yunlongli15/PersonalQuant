# factor_report_news_positive_negative_ratio.md

## definition

- factor: `news_positive_negative_ratio`  ·  category: news  ·  version 1.0
- formula: `(1+pos_20d)/(1+neg_20d)`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: positive/negative event ratio, 20d
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.401
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0120 | 0.0483 | -0.2483 | 0.417 | -0.0184 | -0.2494 | 0.396 |
| 5 | -0.0068 | 0.0421 | -0.1607 | 0.458 | -0.0104 | -0.1746 | 0.417 |
| 10 | -0.0130 | 0.0456 | -0.2852 | 0.417 | -0.0180 | -0.2862 | 0.375 |
| 20 | 0.0002 | 0.0531 | 0.0041 | 0.417 | -0.0037 | -0.0517 | 0.438 |
| 40 | -0.0018 | 0.0563 | -0.0324 | 0.438 | -0.0041 | -0.0566 | 0.417 |
| 60 | -0.0015 | 0.0552 | -0.0280 | 0.438 | -0.0013 | -0.0193 | 0.458 |

quantile mean forward 20d returns: Q1: 0.00944  Q2: 0.01173  Q3: 0.01565  Q4: 0.00852  Q5: 0.01054
Q5-Q1 long-short (gross, monthly): mean 0.00110, ann 0.0061, Sharpe 0.069, MDD -0.1184
top-quintile turnover: 0.193

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0165 | -0.226 | 0.333 |
| 2019 | 12 | -0.0107 | -0.139 | 0.333 |
| 2020 | 12 | 0.0124 | 0.166 | 0.500 |
| 2021 | 12 | 0.0001 | 0.003 | 0.583 |

regime split: up-market IC -0.0101 (n=28) / down-market IC 0.0053 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0099 | 0.0486 | -0.2040 | 0.417 | -0.0152 | -0.1975 | 0.417 |
| 5 | -0.0073 | 0.0415 | -0.1748 | 0.479 | -0.0097 | -0.1624 | 0.417 |
| 10 | -0.0120 | 0.0456 | -0.2629 | 0.458 | -0.0178 | -0.2745 | 0.396 |
| 20 | 0.0007 | 0.0546 | 0.0123 | 0.438 | -0.0037 | -0.0521 | 0.438 |
| 40 | -0.0011 | 0.0579 | -0.0188 | 0.479 | -0.0022 | -0.0306 | 0.438 |
| 60 | 0.0000 | 0.0559 | 0.0008 | 0.438 | 0.0018 | 0.0261 | 0.479 |

quantile mean forward 20d returns: Q1: 0.00945  Q2: 0.01180  Q3: 0.01553  Q4: 0.00878  Q5: 0.01033
Q5-Q1 long-short (gross, monthly): mean 0.00088, ann 0.0035, Sharpe 0.040, MDD -0.1184
top-quintile turnover: 0.205

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0159 | -0.219 | 0.333 |
| 2019 | 12 | -0.0108 | -0.140 | 0.333 |
| 2020 | 12 | 0.0124 | 0.165 | 0.500 |
| 2021 | 12 | -0.0005 | -0.009 | 0.583 |

regime split: up-market IC -0.0099 (n=28) / down-market IC 0.0050 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.455
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0052 | 0.0640 | 0.0805 | 0.500 | 0.0036 | 0.0432 | 0.542 |
| 5 | -0.0134 | 0.0573 | -0.2340 | 0.375 | -0.0182 | -0.2200 | 0.417 |
| 10 | -0.0159 | 0.0522 | -0.3047 | 0.333 | -0.0228 | -0.3083 | 0.292 |
| 20 | -0.0095 | 0.0421 | -0.2270 | 0.333 | -0.0241 | -0.3926 | 0.208 |
| 40 | 0.0056 | 0.0494 | 0.1127 | 0.625 | -0.0049 | -0.0708 | 0.458 |
| 60 | 0.0063 | 0.0628 | 0.1004 | 0.542 | 0.0011 | 0.0136 | 0.417 |

quantile mean forward 20d returns: Q1: 0.00236  Q2: 0.00338  Q3: 0.00471  Q4: 0.00521  Q5: -0.00613
Q5-Q1 long-short (gross, monthly): mean -0.00849, ann -0.0851, Sharpe -0.746, MDD -0.1714
top-quintile turnover: 0.240

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0317 | -0.614 | 0.250 |
| 2023 | 12 | -0.0164 | -0.238 | 0.167 |

regime split: up-market IC -0.0217 (n=13) / down-market IC -0.0268 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0008 | 0.0638 | 0.0124 | 0.500 | 0.0023 | 0.0269 | 0.542 |
| 5 | -0.0172 | 0.0553 | -0.3114 | 0.292 | -0.0186 | -0.2241 | 0.417 |
| 10 | -0.0179 | 0.0507 | -0.3538 | 0.333 | -0.0236 | -0.3154 | 0.292 |
| 20 | -0.0139 | 0.0410 | -0.3396 | 0.292 | -0.0228 | -0.3635 | 0.208 |
| 40 | 0.0025 | 0.0488 | 0.0504 | 0.500 | -0.0048 | -0.0681 | 0.458 |
| 60 | 0.0041 | 0.0616 | 0.0670 | 0.542 | 0.0013 | 0.0158 | 0.417 |

quantile mean forward 20d returns: Q1: 0.00234  Q2: 0.00336  Q3: 0.00472  Q4: 0.00518  Q5: -0.00605
Q5-Q1 long-short (gross, monthly): mean -0.00839, ann -0.0840, Sharpe -0.737, MDD -0.1714
top-quintile turnover: 0.239

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0291 | -0.528 | 0.250 |
| 2023 | 12 | -0.0165 | -0.239 | 0.167 |

regime split: up-market IC -0.0217 (n=13) / down-market IC -0.0241 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.457
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0141 | 0.0639 | 0.2200 | 0.708 | 0.0149 | 0.1805 | 0.625 |
| 5 | 0.0137 | 0.0677 | 0.2018 | 0.542 | 0.0094 | 0.1129 | 0.500 |
| 10 | 0.0060 | 0.0577 | 0.1035 | 0.542 | 0.0041 | 0.0560 | 0.417 |
| 20 | 0.0078 | 0.0419 | 0.1867 | 0.625 | 0.0086 | 0.1620 | 0.583 |
| 40 | 0.0028 | 0.0343 | 0.0829 | 0.458 | 0.0028 | 0.0644 | 0.500 |
| 60 | -0.0102 | 0.0327 | -0.3121 | 0.333 | -0.0133 | -0.2908 | 0.375 |

quantile mean forward 20d returns: Q1: 0.02953  Q2: 0.03410  Q3: 0.03283  Q4: 0.02664  Q5: 0.03976
Q5-Q1 long-short (gross, monthly): mean 0.01023, ann 0.1059, Sharpe 1.019, MDD -0.0812
top-quintile turnover: 0.231

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0240 | 0.623 | 0.750 |
| 2025 | 12 | -0.0067 | -0.109 | 0.417 |

regime split: up-market IC 0.0014 (n=15) / down-market IC 0.0206 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0115 | 0.0646 | 0.1781 | 0.625 | 0.0097 | 0.1167 | 0.625 |
| 5 | 0.0141 | 0.0668 | 0.2106 | 0.542 | 0.0116 | 0.1381 | 0.542 |
| 10 | 0.0068 | 0.0574 | 0.1182 | 0.583 | 0.0080 | 0.1053 | 0.458 |
| 20 | 0.0126 | 0.0469 | 0.2693 | 0.667 | 0.0187 | 0.2829 | 0.625 |
| 40 | 0.0055 | 0.0363 | 0.1521 | 0.500 | 0.0092 | 0.1820 | 0.542 |
| 60 | -0.0074 | 0.0359 | -0.2060 | 0.375 | -0.0060 | -0.1048 | 0.417 |

quantile mean forward 20d returns: Q1: 0.02935  Q2: 0.03350  Q3: 0.03054  Q4: 0.02625  Q5: 0.04322
Q5-Q1 long-short (gross, monthly): mean 0.01387, ann 0.1501, Sharpe 1.068, MDD -0.0812
top-quintile turnover: 0.221

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0428 | 0.709 | 0.833 |
| 2025 | 12 | -0.0055 | -0.088 | 0.417 |

regime split: up-market IC 0.0175 (n=15) / down-market IC 0.0206 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`news_sentiment_20d`: 1.000  `buyback_event_count_20d`: 0.434  `negative_news_count_5d`: -0.271  `event_sentiment_shock`: -0.105  `announcement_count_20d`: 0.051

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.