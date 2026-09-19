# factor_report_shareholder_change_count_20d.md

## definition

- factor: `shareholder_change_count_20d`  ·  category: news  ·  version 1.0
- formula: `count(shareholder_change events in 20d)`
- source: news  ·  PIT: True
- required fields: news_events, news_coverage
- description: shareholder-change event count, 20d
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.401
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0105 | 0.0389 | 0.2699 | 0.542 | 0.0148 | 0.2929 | 0.542 |
| 5 | -0.0004 | 0.0314 | -0.0122 | 0.521 | -0.0008 | -0.0189 | 0.562 |
| 10 | -0.0003 | 0.0384 | -0.0079 | 0.438 | -0.0027 | -0.0558 | 0.458 |
| 20 | -0.0029 | 0.0385 | -0.0761 | 0.458 | -0.0034 | -0.0717 | 0.542 |
| 40 | 0.0007 | 0.0421 | 0.0167 | 0.500 | -0.0004 | -0.0080 | 0.479 |
| 60 | 0.0007 | 0.0369 | 0.0188 | 0.521 | -0.0013 | -0.0251 | 0.479 |

quantile mean forward 20d returns: Q1: 0.00930  Q2: 0.01214  Q3: 0.01576  Q4: 0.00907  Q5: 0.00961
Q5-Q1 long-short (gross, monthly): mean 0.00031, ann 0.0014, Sharpe 0.013, MDD -0.1762
top-quintile turnover: 0.151

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0002 | 0.006 | 0.750 |
| 2019 | 12 | 0.0141 | 0.283 | 0.417 |
| 2020 | 12 | -0.0214 | -0.379 | 0.333 |
| 2021 | 12 | -0.0066 | -0.161 | 0.667 |

regime split: up-market IC -0.0155 (n=28) / down-market IC 0.0134 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0105 | 0.0389 | 0.2709 | 0.542 | 0.0149 | 0.2934 | 0.542 |
| 5 | -0.0003 | 0.0314 | -0.0098 | 0.521 | -0.0009 | -0.0199 | 0.562 |
| 10 | -0.0002 | 0.0384 | -0.0064 | 0.438 | -0.0027 | -0.0564 | 0.458 |
| 20 | -0.0030 | 0.0385 | -0.0773 | 0.458 | -0.0034 | -0.0715 | 0.542 |
| 40 | 0.0006 | 0.0421 | 0.0150 | 0.500 | -0.0005 | -0.0091 | 0.479 |
| 60 | 0.0006 | 0.0370 | 0.0162 | 0.521 | -0.0013 | -0.0255 | 0.479 |

quantile mean forward 20d returns: Q1: 0.00930  Q2: 0.01214  Q3: 0.01576  Q4: 0.00907  Q5: 0.00961
Q5-Q1 long-short (gross, monthly): mean 0.00031, ann 0.0014, Sharpe 0.013, MDD -0.1762
top-quintile turnover: 0.151

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0003 | 0.009 | 0.750 |
| 2019 | 12 | 0.0141 | 0.283 | 0.417 |
| 2020 | 12 | -0.0214 | -0.379 | 0.333 |
| 2021 | 12 | -0.0066 | -0.163 | 0.667 |

regime split: up-market IC -0.0155 (n=28) / down-market IC 0.0135 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.455
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0037 | 0.0706 | 0.0531 | 0.417 | -0.0006 | -0.0087 | 0.458 |
| 5 | -0.0016 | 0.0385 | -0.0409 | 0.417 | -0.0022 | -0.0510 | 0.417 |
| 10 | 0.0044 | 0.0489 | 0.0891 | 0.500 | 0.0060 | 0.1103 | 0.500 |
| 20 | 0.0064 | 0.0663 | 0.0968 | 0.417 | 0.0088 | 0.1350 | 0.625 |
| 40 | 0.0078 | 0.0386 | 0.2030 | 0.500 | 0.0060 | 0.1676 | 0.542 |
| 60 | 0.0094 | 0.0432 | 0.2168 | 0.500 | 0.0074 | 0.1943 | 0.542 |

quantile mean forward 20d returns: Q1: 0.00302  Q2: 0.00304  Q3: -0.00016  Q4: 0.00377  Q5: -0.00014
Q5-Q1 long-short (gross, monthly): mean -0.00316, ann -0.0268, Sharpe -0.218, MDD -0.1543
top-quintile turnover: 0.071

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0001 | -0.006 | 0.500 |
| 2023 | 12 | 0.0178 | 0.201 | 0.750 |

regime split: up-market IC -0.0112 (n=13) / down-market IC 0.0325 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0037 | 0.0706 | 0.0531 | 0.417 | -0.0006 | -0.0087 | 0.458 |
| 5 | -0.0016 | 0.0385 | -0.0410 | 0.417 | -0.0022 | -0.0510 | 0.417 |
| 10 | 0.0044 | 0.0489 | 0.0891 | 0.500 | 0.0060 | 0.1103 | 0.500 |
| 20 | 0.0064 | 0.0663 | 0.0968 | 0.417 | 0.0088 | 0.1351 | 0.625 |
| 40 | 0.0078 | 0.0386 | 0.2032 | 0.500 | 0.0060 | 0.1676 | 0.542 |
| 60 | 0.0094 | 0.0432 | 0.2170 | 0.500 | 0.0074 | 0.1944 | 0.542 |

quantile mean forward 20d returns: Q1: 0.00302  Q2: 0.00304  Q3: -0.00016  Q4: 0.00377  Q5: -0.00014
Q5-Q1 long-short (gross, monthly): mean -0.00316, ann -0.0268, Sharpe -0.218, MDD -0.1543
top-quintile turnover: 0.071

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0001 | -0.006 | 0.500 |
| 2023 | 12 | 0.0178 | 0.201 | 0.750 |

regime split: up-market IC -0.0112 (n=13) / down-market IC 0.0325 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.457
- empirical direction: positive

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0040 | 0.0296 | -0.1336 | 0.375 | -0.0082 | -0.2147 | 0.375 |
| 5 | -0.0013 | 0.0198 | -0.0667 | 0.542 | -0.0005 | -0.0174 | 0.583 |
| 10 | 0.0037 | 0.0183 | 0.1998 | 0.750 | 0.0036 | 0.1383 | 0.708 |
| 20 | 0.0029 | 0.0229 | 0.1250 | 0.458 | 0.0002 | 0.0073 | 0.458 |
| 40 | 0.0027 | 0.0171 | 0.1558 | 0.417 | -0.0023 | -0.1272 | 0.417 |
| 60 | 0.0026 | 0.0209 | 0.1225 | 0.417 | -0.0044 | -0.1682 | 0.417 |

quantile mean forward 20d returns: Q1: 0.02864  Q2: 0.03657  Q3: 0.03554  Q4: 0.02610  Q5: 0.03602
Q5-Q1 long-short (gross, monthly): mean 0.00738, ann 0.0804, Sharpe 0.787, MDD -0.0708
top-quintile turnover: 0.068

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0030 | -0.158 | 0.417 |
| 2025 | 12 | 0.0035 | 0.095 | 0.500 |

regime split: up-market IC 0.0006 (n=15) / down-market IC -0.0004 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0039 | 0.0296 | -0.1336 | 0.375 | -0.0082 | -0.2145 | 0.375 |
| 5 | -0.0013 | 0.0198 | -0.0667 | 0.542 | -0.0005 | -0.0167 | 0.583 |
| 10 | 0.0037 | 0.0183 | 0.1998 | 0.750 | 0.0037 | 0.1387 | 0.708 |
| 20 | 0.0029 | 0.0229 | 0.1249 | 0.458 | 0.0002 | 0.0068 | 0.458 |
| 40 | 0.0027 | 0.0171 | 0.1557 | 0.417 | -0.0023 | -0.1279 | 0.417 |
| 60 | 0.0026 | 0.0209 | 0.1226 | 0.417 | -0.0043 | -0.1660 | 0.417 |

quantile mean forward 20d returns: Q1: 0.02864  Q2: 0.03657  Q3: 0.03554  Q4: 0.02610  Q5: 0.03602
Q5-Q1 long-short (gross, monthly): mean 0.00738, ann 0.0804, Sharpe 0.787, MDD -0.0708
top-quintile turnover: 0.068

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0030 | -0.159 | 0.417 |
| 2025 | 12 | 0.0034 | 0.095 | 0.500 |

regime split: up-market IC 0.0006 (n=15) / down-market IC -0.0004 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`negative_news_count_5d`: 0.429  `announcement_count_20d`: 0.304  `news_count_20d`: 0.304  `announcement_count_5d`: 0.271  `news_count_5d`: 0.271

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.