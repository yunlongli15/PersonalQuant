# factor_report_event_sentiment_shock.md

## definition

- factor: `event_sentiment_shock`  ·  category: news  ·  version 1.0
- formula: `sentiment_5d - sentiment_60d`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: 5d vs 60d sentiment deviation
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.401
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0022 | 0.0619 | -0.0348 | 0.438 | -0.0040 | -0.0524 | 0.438 |
| 5 | -0.0061 | 0.0464 | -0.1306 | 0.438 | -0.0084 | -0.1378 | 0.438 |
| 10 | -0.0035 | 0.0517 | -0.0684 | 0.479 | -0.0046 | -0.0657 | 0.500 |
| 20 | -0.0119 | 0.0536 | -0.2218 | 0.542 | -0.0126 | -0.1803 | 0.479 |
| 40 | -0.0117 | 0.0554 | -0.2118 | 0.375 | -0.0135 | -0.1870 | 0.354 |
| 60 | -0.0173 | 0.0482 | -0.3585 | 0.354 | -0.0142 | -0.2044 | 0.500 |

quantile mean forward 20d returns: Q1: 0.01166  Q2: 0.01145  Q3: 0.01372  Q4: 0.00844  Q5: 0.01061
Q5-Q1 long-short (gross, monthly): mean -0.00106, ann -0.0108, Sharpe -0.109, MDD -0.1682
top-quintile turnover: 0.307

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0049 | -0.062 | 0.500 |
| 2019 | 12 | -0.0288 | -0.424 | 0.417 |
| 2020 | 12 | -0.0373 | -0.547 | 0.333 |
| 2021 | 12 | 0.0206 | 0.457 | 0.667 |

regime split: up-market IC -0.0102 (n=28) / down-market IC -0.0160 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0025 | 0.0612 | 0.0410 | 0.500 | 0.0029 | 0.0377 | 0.479 |
| 5 | -0.0048 | 0.0463 | -0.1039 | 0.375 | -0.0087 | -0.1330 | 0.458 |
| 10 | -0.0019 | 0.0487 | -0.0384 | 0.521 | -0.0023 | -0.0328 | 0.542 |
| 20 | -0.0086 | 0.0495 | -0.1738 | 0.458 | -0.0140 | -0.2018 | 0.500 |
| 40 | -0.0118 | 0.0545 | -0.2168 | 0.333 | -0.0181 | -0.2540 | 0.333 |
| 60 | -0.0149 | 0.0495 | -0.3004 | 0.396 | -0.0217 | -0.3019 | 0.458 |

quantile mean forward 20d returns: Q1: 0.01185  Q2: 0.01153  Q3: 0.01360  Q4: 0.00815  Q5: 0.01076
Q5-Q1 long-short (gross, monthly): mean -0.00109, ann -0.0113, Sharpe -0.113, MDD -0.1723
top-quintile turnover: 0.305

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0104 | -0.133 | 0.417 |
| 2019 | 12 | -0.0290 | -0.426 | 0.417 |
| 2020 | 12 | -0.0221 | -0.299 | 0.583 |
| 2021 | 12 | 0.0055 | 0.114 | 0.583 |

regime split: up-market IC -0.0129 (n=28) / down-market IC -0.0155 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.455
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0116 | 0.0879 | -0.1321 | 0.458 | -0.0055 | -0.0499 | 0.417 |
| 5 | 0.0041 | 0.0591 | 0.0688 | 0.542 | 0.0002 | 0.0019 | 0.458 |
| 10 | -0.0151 | 0.0631 | -0.2394 | 0.458 | -0.0241 | -0.2618 | 0.500 |
| 20 | -0.0168 | 0.0663 | -0.2532 | 0.417 | -0.0232 | -0.2630 | 0.333 |
| 40 | -0.0015 | 0.0764 | -0.0197 | 0.500 | -0.0058 | -0.0578 | 0.542 |
| 60 | -0.0085 | 0.0757 | -0.1128 | 0.625 | -0.0152 | -0.1683 | 0.500 |

quantile mean forward 20d returns: Q1: 0.00547  Q2: 0.00199  Q3: 0.00088  Q4: 0.00201  Q5: -0.00081
Q5-Q1 long-short (gross, monthly): mean -0.00629, ann -0.0649, Sharpe -0.693, MDD -0.1571
top-quintile turnover: 0.418

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0017 | -0.021 | 0.500 |
| 2023 | 12 | -0.0446 | -0.511 | 0.167 |

regime split: up-market IC -0.0361 (n=13) / down-market IC -0.0080 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0095 | 0.0744 | -0.1277 | 0.458 | -0.0073 | -0.0660 | 0.417 |
| 5 | 0.0047 | 0.0554 | 0.0851 | 0.500 | -0.0038 | -0.0425 | 0.417 |
| 10 | -0.0127 | 0.0541 | -0.2351 | 0.458 | -0.0266 | -0.2871 | 0.500 |
| 20 | -0.0064 | 0.0539 | -0.1193 | 0.500 | -0.0239 | -0.2714 | 0.292 |
| 40 | 0.0028 | 0.0625 | 0.0445 | 0.500 | -0.0058 | -0.0573 | 0.500 |
| 60 | -0.0089 | 0.0640 | -0.1394 | 0.458 | -0.0175 | -0.1936 | 0.458 |

quantile mean forward 20d returns: Q1: 0.00531  Q2: 0.00225  Q3: 0.00080  Q4: 0.00204  Q5: -0.00086
Q5-Q1 long-short (gross, monthly): mean -0.00617, ann -0.0634, Sharpe -0.694, MDD -0.1561
top-quintile turnover: 0.417

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0043 | -0.051 | 0.417 |
| 2023 | 12 | -0.0434 | -0.501 | 0.167 |

regime split: up-market IC -0.0395 (n=13) / down-market IC -0.0054 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.457
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0094 | 0.0505 | -0.1862 | 0.417 | -0.0106 | -0.1289 | 0.417 |
| 5 | 0.0093 | 0.0681 | 0.1360 | 0.625 | 0.0223 | 0.2220 | 0.667 |
| 10 | -0.0019 | 0.0492 | -0.0386 | 0.500 | 0.0076 | 0.0914 | 0.542 |
| 20 | -0.0173 | 0.0494 | -0.3498 | 0.375 | -0.0116 | -0.1786 | 0.417 |
| 40 | -0.0056 | 0.0422 | -0.1322 | 0.500 | 0.0055 | 0.0841 | 0.500 |
| 60 | 0.0016 | 0.0433 | 0.0363 | 0.625 | 0.0120 | 0.1988 | 0.708 |

quantile mean forward 20d returns: Q1: 0.03179  Q2: 0.03641  Q3: 0.03276  Q4: 0.02599  Q5: 0.03592
Q5-Q1 long-short (gross, monthly): mean 0.00413, ann 0.0456, Sharpe 0.549, MDD -0.0672
top-quintile turnover: 0.302

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0025 | -0.038 | 0.500 |
| 2025 | 12 | -0.0207 | -0.330 | 0.333 |

regime split: up-market IC -0.0249 (n=15) / down-market IC 0.0104 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0032 | 0.0588 | -0.0549 | 0.500 | -0.0105 | -0.1267 | 0.417 |
| 5 | 0.0186 | 0.0663 | 0.2814 | 0.708 | 0.0214 | 0.2071 | 0.667 |
| 10 | 0.0067 | 0.0554 | 0.1213 | 0.583 | 0.0066 | 0.0781 | 0.542 |
| 20 | -0.0179 | 0.0505 | -0.3551 | 0.375 | -0.0125 | -0.1896 | 0.375 |
| 40 | -0.0078 | 0.0411 | -0.1893 | 0.500 | 0.0048 | 0.0741 | 0.500 |
| 60 | 0.0017 | 0.0489 | 0.0342 | 0.625 | 0.0119 | 0.1972 | 0.708 |

quantile mean forward 20d returns: Q1: 0.03189  Q2: 0.03642  Q3: 0.03269  Q4: 0.02594  Q5: 0.03594
Q5-Q1 long-short (gross, monthly): mean 0.00405, ann 0.0447, Sharpe 0.541, MDD -0.0672
top-quintile turnover: 0.304

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0025 | -0.038 | 0.500 |
| 2025 | 12 | -0.0225 | -0.350 | 0.250 |

regime split: up-market IC -0.0261 (n=15) / down-market IC 0.0101 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`negative_news_count_5d`: -0.292  `buyback_event_count_20d`: -0.118  `announcement_count_20d`: -0.068  `news_count_20d`: -0.068  `announcement_count_5d`: -0.041

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.