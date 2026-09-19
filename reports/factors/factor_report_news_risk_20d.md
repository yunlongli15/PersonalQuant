# factor_report_news_risk_20d.md

## definition

- factor: `news_risk_20d`  ·  category: news  ·  version 1.0
- formula: `mean risk of events in 20d (rule tier: risk = importance of negative-direction events)`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: 20-day mean event risk
- declared (economic) direction: **negative**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.401
- empirical direction: positive  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0241 | 0.0640 | 0.3763 | 0.688 | 0.0281 | 0.3812 | 0.646 |
| 5 | 0.0093 | 0.0419 | 0.2225 | 0.562 | 0.0124 | 0.2192 | 0.542 |
| 10 | 0.0157 | 0.0504 | 0.3117 | 0.604 | 0.0182 | 0.2899 | 0.625 |
| 20 | 0.0029 | 0.0552 | 0.0534 | 0.583 | 0.0014 | 0.0197 | 0.500 |
| 40 | 0.0085 | 0.0521 | 0.1636 | 0.521 | 0.0076 | 0.1170 | 0.521 |
| 60 | 0.0043 | 0.0475 | 0.0916 | 0.583 | 0.0032 | 0.0501 | 0.604 |

quantile mean forward 20d returns: Q1: 0.00924  Q2: 0.01205  Q3: 0.01420  Q4: 0.00836  Q5: 0.01203
Q5-Q1 long-short (gross, monthly): mean 0.00279, ann 0.0318, Sharpe 0.306, MDD -0.1865
top-quintile turnover: 0.151

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0057 | 0.082 | 0.667 |
| 2019 | 12 | 0.0310 | 0.461 | 0.500 |
| 2020 | 12 | -0.0171 | -0.211 | 0.417 |
| 2021 | 12 | -0.0141 | -0.274 | 0.417 |

regime split: up-market IC 0.0056 (n=28) / down-market IC -0.0045 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0255 | 0.0637 | 0.4007 | 0.688 | 0.0282 | 0.3820 | 0.646 |
| 5 | 0.0099 | 0.0439 | 0.2259 | 0.583 | 0.0125 | 0.2206 | 0.542 |
| 10 | 0.0170 | 0.0507 | 0.3348 | 0.604 | 0.0182 | 0.2898 | 0.625 |
| 20 | 0.0041 | 0.0552 | 0.0751 | 0.542 | 0.0014 | 0.0196 | 0.500 |
| 40 | 0.0102 | 0.0541 | 0.1887 | 0.521 | 0.0076 | 0.1169 | 0.521 |
| 60 | 0.0048 | 0.0503 | 0.0952 | 0.583 | 0.0033 | 0.0514 | 0.604 |

quantile mean forward 20d returns: Q1: 0.00924  Q2: 0.01205  Q3: 0.01420  Q4: 0.00836  Q5: 0.01203
Q5-Q1 long-short (gross, monthly): mean 0.00279, ann 0.0318, Sharpe 0.306, MDD -0.1865
top-quintile turnover: 0.151

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0057 | 0.081 | 0.667 |
| 2019 | 12 | 0.0310 | 0.461 | 0.500 |
| 2020 | 12 | -0.0172 | -0.212 | 0.417 |
| 2021 | 12 | -0.0139 | -0.272 | 0.417 |

regime split: up-market IC 0.0056 (n=28) / down-market IC -0.0045 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.455
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0024 | 0.0674 | 0.0358 | 0.458 | -0.0023 | -0.0333 | 0.458 |
| 5 | 0.0110 | 0.0569 | 0.1931 | 0.625 | 0.0140 | 0.1844 | 0.583 |
| 10 | 0.0062 | 0.0479 | 0.1285 | 0.458 | 0.0080 | 0.1271 | 0.417 |
| 20 | -0.0056 | 0.0362 | -0.1538 | 0.333 | -0.0082 | -0.1801 | 0.375 |
| 40 | -0.0076 | 0.0399 | -0.1898 | 0.500 | -0.0106 | -0.2402 | 0.500 |
| 60 | -0.0072 | 0.0449 | -0.1598 | 0.417 | -0.0158 | -0.3245 | 0.333 |

quantile mean forward 20d returns: Q1: 0.00353  Q2: 0.00354  Q3: 0.00139  Q4: 0.00347  Q5: -0.00240
Q5-Q1 long-short (gross, monthly): mean -0.00593, ann -0.0612, Sharpe -0.521, MDD -0.1616
top-quintile turnover: 0.118

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0063 | -0.168 | 0.417 |
| 2023 | 12 | -0.0102 | -0.193 | 0.333 |

regime split: up-market IC -0.0201 (n=13) / down-market IC 0.0057 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0025 | 0.0684 | 0.0365 | 0.458 | -0.0025 | -0.0362 | 0.458 |
| 5 | 0.0105 | 0.0570 | 0.1839 | 0.625 | 0.0137 | 0.1799 | 0.583 |
| 10 | 0.0060 | 0.0480 | 0.1245 | 0.458 | 0.0078 | 0.1235 | 0.458 |
| 20 | -0.0059 | 0.0361 | -0.1620 | 0.333 | -0.0083 | -0.1815 | 0.375 |
| 40 | -0.0079 | 0.0403 | -0.1965 | 0.500 | -0.0107 | -0.2428 | 0.500 |
| 60 | -0.0078 | 0.0455 | -0.1712 | 0.417 | -0.0159 | -0.3265 | 0.333 |

quantile mean forward 20d returns: Q1: 0.00353  Q2: 0.00354  Q3: 0.00139  Q4: 0.00347  Q5: -0.00240
Q5-Q1 long-short (gross, monthly): mean -0.00593, ann -0.0612, Sharpe -0.521, MDD -0.1616
top-quintile turnover: 0.118

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0064 | -0.171 | 0.417 |
| 2023 | 12 | -0.0102 | -0.194 | 0.333 |

regime split: up-market IC -0.0203 (n=13) / down-market IC 0.0058 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.457
- empirical direction: positive  ⚠️ disagrees with declared direction

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0100 | 0.0589 | 0.1697 | 0.417 | 0.0060 | 0.0858 | 0.458 |
| 5 | 0.0129 | 0.0495 | 0.2606 | 0.542 | 0.0150 | 0.2667 | 0.625 |
| 10 | 0.0189 | 0.0467 | 0.4057 | 0.667 | 0.0168 | 0.3205 | 0.667 |
| 20 | 0.0226 | 0.0646 | 0.3496 | 0.542 | 0.0146 | 0.2377 | 0.500 |
| 40 | 0.0189 | 0.0413 | 0.4580 | 0.542 | 0.0114 | 0.3117 | 0.583 |
| 60 | 0.0227 | 0.0461 | 0.4924 | 0.625 | 0.0163 | 0.3617 | 0.625 |

quantile mean forward 20d returns: Q1: 0.02865  Q2: 0.03582  Q3: 0.03216  Q4: 0.02565  Q5: 0.04060
Q5-Q1 long-short (gross, monthly): mean 0.01194, ann 0.1341, Sharpe 0.903, MDD -0.0786
top-quintile turnover: 0.120

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0125 | 0.177 | 0.500 |
| 2025 | 12 | 0.0168 | 0.329 | 0.500 |

regime split: up-market IC 0.0222 (n=15) / down-market IC 0.0020 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0097 | 0.0593 | 0.1632 | 0.417 | 0.0060 | 0.0857 | 0.458 |
| 5 | 0.0122 | 0.0492 | 0.2486 | 0.542 | 0.0150 | 0.2668 | 0.625 |
| 10 | 0.0181 | 0.0464 | 0.3896 | 0.667 | 0.0168 | 0.3205 | 0.667 |
| 20 | 0.0222 | 0.0650 | 0.3420 | 0.542 | 0.0146 | 0.2376 | 0.500 |
| 40 | 0.0188 | 0.0415 | 0.4516 | 0.542 | 0.0114 | 0.3116 | 0.583 |
| 60 | 0.0227 | 0.0464 | 0.4879 | 0.625 | 0.0163 | 0.3614 | 0.625 |

quantile mean forward 20d returns: Q1: 0.02865  Q2: 0.03582  Q3: 0.03216  Q4: 0.02565  Q5: 0.04060
Q5-Q1 long-short (gross, monthly): mean 0.01194, ann 0.1341, Sharpe 0.903, MDD -0.0786
top-quintile turnover: 0.120

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0125 | 0.177 | 0.500 |
| 2025 | 12 | 0.0168 | 0.329 | 0.500 |

regime split: up-market IC 0.0222 (n=15) / down-market IC 0.0020 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`negative_news_count_5d`: 0.619  `major_event_count_20d`: 0.409  `announcement_count_20d`: 0.376  `news_count_20d`: 0.376  `announcement_count_5d`: 0.338

## interpretation & limitations

- declared direction `negative` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.