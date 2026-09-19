# factor_report_volatility_20.md

## definition

- factor: `volatility_20`  ·  category: volatility  ·  version 1.0
- formula: `std(ret_daily, 20)`
- source: market  ·  PIT: True
- required fields: close, factor
- description: 20-day daily-return volatility
- declared (economic) direction: **negative**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.999
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0443 | 0.1493 | 0.2968 | 0.688 | 0.0205 | 0.1148 | 0.646 |
| 5 | 0.0168 | 0.1325 | 0.1268 | 0.604 | -0.0175 | -0.1057 | 0.438 |
| 10 | 0.0126 | 0.1200 | 0.1049 | 0.479 | -0.0286 | -0.1830 | 0.438 |
| 20 | -0.0235 | 0.1275 | -0.1846 | 0.396 | -0.0744 | -0.4824 | 0.271 |
| 40 | -0.0351 | 0.1140 | -0.3077 | 0.396 | -0.0905 | -0.6622 | 0.271 |
| 60 | -0.0394 | 0.1031 | -0.3818 | 0.396 | -0.0969 | -0.7872 | 0.229 |

quantile mean forward 20d returns: Q1: 0.00907  Q2: 0.01446  Q3: 0.01389  Q4: 0.01366  Q5: 0.00464
Q5-Q1 long-short (gross, monthly): mean -0.00442, ann -0.0735, Sharpe -0.414, MDD -0.3429
top-quintile turnover: 0.619

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0663 | -0.686 | 0.250 |
| 2019 | 12 | -0.0302 | -0.173 | 0.333 |
| 2020 | 12 | -0.0710 | -0.423 | 0.333 |
| 2021 | 12 | -0.1298 | -0.879 | 0.167 |

regime split: up-market IC -0.0338 (n=28) / down-market IC -0.1311 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0441 | 0.1503 | 0.2933 | 0.667 | 0.0205 | 0.1148 | 0.646 |
| 5 | 0.0111 | 0.1379 | 0.0803 | 0.542 | -0.0175 | -0.1057 | 0.438 |
| 10 | 0.0062 | 0.1246 | 0.0497 | 0.479 | -0.0286 | -0.1830 | 0.438 |
| 20 | -0.0337 | 0.1278 | -0.2642 | 0.333 | -0.0743 | -0.4824 | 0.271 |
| 40 | -0.0473 | 0.1074 | -0.4408 | 0.354 | -0.0905 | -0.6622 | 0.271 |
| 60 | -0.0518 | 0.0952 | -0.5440 | 0.354 | -0.0969 | -0.7870 | 0.229 |

quantile mean forward 20d returns: Q1: 0.00907  Q2: 0.01446  Q3: 0.01386  Q4: 0.01367  Q5: 0.00465
Q5-Q1 long-short (gross, monthly): mean -0.00442, ann -0.0735, Sharpe -0.413, MDD -0.3428
top-quintile turnover: 0.619

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0663 | -0.686 | 0.250 |
| 2019 | 12 | -0.0302 | -0.173 | 0.333 |
| 2020 | 12 | -0.0710 | -0.423 | 0.333 |
| 2021 | 12 | -0.1298 | -0.880 | 0.167 |

regime split: up-market IC -0.0338 (n=28) / down-market IC -0.1311 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0073 | 0.1180 | -0.0616 | 0.500 | -0.0503 | -0.3829 | 0.500 |
| 5 | 0.0071 | 0.1291 | 0.0547 | 0.500 | -0.0400 | -0.2486 | 0.458 |
| 10 | -0.0348 | 0.1058 | -0.3285 | 0.375 | -0.0885 | -0.6812 | 0.208 |
| 20 | -0.0466 | 0.1197 | -0.3895 | 0.417 | -0.1046 | -0.7675 | 0.250 |
| 40 | -0.0678 | 0.1143 | -0.5932 | 0.333 | -0.1248 | -0.9040 | 0.208 |
| 60 | -0.0895 | 0.0856 | -1.0458 | 0.208 | -0.1553 | -1.5517 | 0.083 |

quantile mean forward 20d returns: Q1: 0.00739  Q2: 0.00535  Q3: 0.00703  Q4: 0.00108  Q5: -0.00631
Q5-Q1 long-short (gross, monthly): mean -0.01370, ann -0.1632, Sharpe -1.192, MDD -0.3058
top-quintile turnover: 0.664

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0690 | -0.660 | 0.250 |
| 2023 | 12 | -0.1403 | -0.911 | 0.250 |

regime split: up-market IC -0.0683 (n=13) / down-market IC -0.1476 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0045 | 0.1344 | -0.0337 | 0.500 | -0.0503 | -0.3830 | 0.500 |
| 5 | 0.0069 | 0.1285 | 0.0534 | 0.500 | -0.0400 | -0.2486 | 0.458 |
| 10 | -0.0420 | 0.1074 | -0.3914 | 0.333 | -0.0884 | -0.6810 | 0.208 |
| 20 | -0.0518 | 0.1195 | -0.4335 | 0.375 | -0.1046 | -0.7674 | 0.250 |
| 40 | -0.0738 | 0.1126 | -0.6556 | 0.333 | -0.1248 | -0.9039 | 0.208 |
| 60 | -0.0973 | 0.0832 | -1.1689 | 0.125 | -0.1553 | -1.5516 | 0.083 |

quantile mean forward 20d returns: Q1: 0.00739  Q2: 0.00533  Q3: 0.00705  Q4: 0.00108  Q5: -0.00631
Q5-Q1 long-short (gross, monthly): mean -0.01370, ann -0.1632, Sharpe -1.192, MDD -0.3058
top-quintile turnover: 0.664

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0690 | -0.660 | 0.250 |
| 2023 | 12 | -0.1403 | -0.911 | 0.250 |

regime split: up-market IC -0.0683 (n=13) / down-market IC -0.1476 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.999
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0417 | 0.1815 | 0.2296 | 0.542 | 0.0134 | 0.0595 | 0.458 |
| 5 | -0.0377 | 0.1710 | -0.2204 | 0.458 | -0.0897 | -0.4188 | 0.333 |
| 10 | -0.0154 | 0.1653 | -0.0932 | 0.542 | -0.0593 | -0.2821 | 0.417 |
| 20 | -0.0150 | 0.1389 | -0.1081 | 0.500 | -0.0723 | -0.3927 | 0.375 |
| 40 | -0.0171 | 0.1202 | -0.1427 | 0.500 | -0.0713 | -0.4404 | 0.333 |
| 60 | -0.0006 | 0.1037 | -0.0057 | 0.583 | -0.0548 | -0.3987 | 0.333 |

quantile mean forward 20d returns: Q1: 0.02807  Q2: 0.03578  Q3: 0.04268  Q4: 0.03649  Q5: 0.02772
Q5-Q1 long-short (gross, monthly): mean -0.00035, ann -0.0167, Sharpe -0.093, MDD -0.1627
top-quintile turnover: 0.682

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0551 | -0.281 | 0.333 |
| 2025 | 12 | -0.0894 | -0.527 | 0.417 |

regime split: up-market IC -0.0093 (n=15) / down-market IC -0.1772 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0371 | 0.1806 | 0.2052 | 0.500 | 0.0134 | 0.0595 | 0.458 |
| 5 | -0.0382 | 0.1600 | -0.2388 | 0.417 | -0.0898 | -0.4188 | 0.333 |
| 10 | -0.0200 | 0.1564 | -0.1276 | 0.458 | -0.0593 | -0.2822 | 0.417 |
| 20 | -0.0285 | 0.1271 | -0.2245 | 0.417 | -0.0723 | -0.3928 | 0.375 |
| 40 | -0.0311 | 0.1095 | -0.2843 | 0.417 | -0.0713 | -0.4404 | 0.333 |
| 60 | -0.0181 | 0.0960 | -0.1889 | 0.417 | -0.0548 | -0.3986 | 0.333 |

quantile mean forward 20d returns: Q1: 0.02807  Q2: 0.03578  Q3: 0.04271  Q4: 0.03646  Q5: 0.02772
Q5-Q1 long-short (gross, monthly): mean -0.00035, ann -0.0167, Sharpe -0.093, MDD -0.1627
top-quintile turnover: 0.682

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0551 | -0.281 | 0.333 |
| 2025 | 12 | -0.0895 | -0.527 | 0.417 |

regime split: up-market IC -0.0093 (n=15) / down-market IC -0.1772 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`max_return_20`: 0.895  `downside_volatility_60`: 0.709  `limit_up_count_20`: 0.598  `earnings_yield`: -0.480  `amount_20`: 0.478

## redundancy cluster

cluster members: `downside_volatility_60`, `max_return_20`, `parkinson_vol_20`, `volatility_20`, `volatility_60`

## interpretation & limitations

- declared direction `negative` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.