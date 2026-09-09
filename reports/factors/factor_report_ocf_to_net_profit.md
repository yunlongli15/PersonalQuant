# factor_report_ocf_to_net_profit.md

## definition

- factor: `ocf_to_net_profit`  ·  category: cash_flow  ·  version 1.0
- formula: `operating_cash_flow/net_profit`
- source: financial  ·  PIT: True
- required fields: operating_cash_flow, net_profit
- description: earnings quality (cash coverage of profit), latest PIT annual report; undefined when |net_profit| is tiny
- declared (economic) direction: **positive**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.023
- empirical direction: negative  ⚠️ disagrees with declared direction

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0257 | 0.1384 | -0.1858 | 0.348 | -0.0263 | -0.1811 | 0.457 |
| 5 | -0.0286 | 0.1462 | -0.1958 | 0.391 | -0.0258 | -0.1832 | 0.370 |
| 10 | -0.0202 | 0.1382 | -0.1458 | 0.457 | -0.0257 | -0.1910 | 0.391 |
| 20 | -0.0254 | 0.1497 | -0.1699 | 0.435 | -0.0295 | -0.2111 | 0.348 |
| 40 | -0.0207 | 0.1530 | -0.1356 | 0.478 | -0.0174 | -0.1164 | 0.478 |
| 60 | -0.0337 | 0.1507 | -0.2233 | 0.478 | -0.0219 | -0.1354 | 0.457 |

quantile mean forward 20d returns: Q1: 0.01285  Q2: 0.01551  Q3: 0.01487  Q4: 0.01432  Q5: 0.00694
Q5-Q1 long-short (gross, monthly): mean -0.00591, ann -0.0822, Sharpe -0.581, MDD -0.3576
top-quintile turnover: 0.109

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 10 | -0.0104 | -0.081 | 0.400 |
| 2019 | 12 | -0.0936 | -1.153 | 0.167 |
| 2020 | 12 | -0.0173 | -0.116 | 0.333 |
| 2021 | 12 | 0.0064 | 0.039 | 0.500 |

regime split: up-market IC -0.0153 (n=27) / down-market IC -0.0497 (n=19)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0301 | 0.0949 | -0.3169 | 0.391 | -0.0263 | -0.1808 | 0.457 |
| 5 | -0.0338 | 0.1161 | -0.2909 | 0.370 | -0.0259 | -0.1834 | 0.370 |
| 10 | -0.0220 | 0.0957 | -0.2302 | 0.435 | -0.0257 | -0.1912 | 0.391 |
| 20 | -0.0253 | 0.0913 | -0.2773 | 0.435 | -0.0296 | -0.2113 | 0.348 |
| 40 | -0.0229 | 0.1033 | -0.2219 | 0.348 | -0.0174 | -0.1165 | 0.478 |
| 60 | -0.0260 | 0.1118 | -0.2330 | 0.348 | -0.0219 | -0.1355 | 0.457 |

quantile mean forward 20d returns: Q1: 0.01285  Q2: 0.01551  Q3: 0.01487  Q4: 0.01432  Q5: 0.00694
Q5-Q1 long-short (gross, monthly): mean -0.00591, ann -0.0822, Sharpe -0.581, MDD -0.3576
top-quintile turnover: 0.109

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 10 | -0.0104 | -0.081 | 0.400 |
| 2019 | 12 | -0.0936 | -1.153 | 0.167 |
| 2020 | 12 | -0.0175 | -0.117 | 0.333 |
| 2021 | 12 | 0.0064 | 0.039 | 0.500 |

regime split: up-market IC -0.0154 (n=27) / down-market IC -0.0497 (n=19)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.021
- empirical direction: positive

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0704 | 0.1216 | 0.5793 | 0.708 | 0.0631 | 0.4881 | 0.750 |
| 5 | 0.0815 | 0.1444 | 0.5648 | 0.583 | 0.0889 | 0.5825 | 0.708 |
| 10 | 0.0689 | 0.1315 | 0.5240 | 0.708 | 0.0773 | 0.5839 | 0.750 |
| 20 | 0.0818 | 0.1231 | 0.6645 | 0.792 | 0.0908 | 0.7135 | 0.792 |
| 40 | 0.0940 | 0.1113 | 0.8447 | 0.750 | 0.1081 | 0.8531 | 0.792 |
| 60 | 0.1099 | 0.0826 | 1.3313 | 0.917 | 0.1236 | 1.1927 | 0.875 |

quantile mean forward 20d returns: Q1: -0.00029  Q2: -0.00466  Q3: 0.00212  Q4: 0.01702  Q5: 0.01139
Q5-Q1 long-short (gross, monthly): mean 0.01169, ann 0.1172, Sharpe 1.388, MDD -0.0619
top-quintile turnover: 0.064

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0755 | 0.668 | 0.750 |
| 2023 | 12 | 0.1061 | 0.767 | 0.833 |

regime split: up-market IC 0.0442 (n=13) / down-market IC 0.1459 (n=11)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0034 | 0.0704 | -0.0478 | 0.458 | 0.0631 | 0.4881 | 0.750 |
| 5 | 0.0133 | 0.0943 | 0.1411 | 0.458 | 0.0889 | 0.5825 | 0.708 |
| 10 | 0.0247 | 0.0782 | 0.3157 | 0.542 | 0.0773 | 0.5839 | 0.750 |
| 20 | 0.0398 | 0.0891 | 0.4470 | 0.625 | 0.0908 | 0.7135 | 0.792 |
| 40 | 0.0497 | 0.0846 | 0.5874 | 0.667 | 0.1081 | 0.8531 | 0.792 |
| 60 | 0.0595 | 0.0877 | 0.6784 | 0.792 | 0.1236 | 1.1927 | 0.875 |

quantile mean forward 20d returns: Q1: -0.00029  Q2: -0.00466  Q3: 0.00212  Q4: 0.01702  Q5: 0.01139
Q5-Q1 long-short (gross, monthly): mean 0.01169, ann 0.1172, Sharpe 1.388, MDD -0.0619
top-quintile turnover: 0.064

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | 0.0755 | 0.668 | 0.750 |
| 2023 | 12 | 0.1061 | 0.767 | 0.833 |

regime split: up-market IC 0.0442 (n=13) / down-market IC 0.1459 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.020
- empirical direction: positive

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0322 | 0.1156 | -0.2781 | 0.458 | -0.0280 | -0.2389 | 0.417 |
| 5 | -0.0021 | 0.1119 | -0.0186 | 0.500 | -0.0014 | -0.0126 | 0.458 |
| 10 | 0.0175 | 0.1025 | 0.1712 | 0.542 | 0.0066 | 0.0641 | 0.583 |
| 20 | 0.0211 | 0.0838 | 0.2522 | 0.667 | 0.0129 | 0.1294 | 0.542 |
| 40 | 0.0134 | 0.0835 | 0.1600 | 0.625 | 0.0137 | 0.1471 | 0.458 |
| 60 | 0.0120 | 0.0904 | 0.1330 | 0.542 | 0.0195 | 0.1904 | 0.583 |

quantile mean forward 20d returns: Q1: 0.02721  Q2: 0.02550  Q3: 0.03006  Q4: 0.03080  Q5: 0.02960
Q5-Q1 long-short (gross, monthly): mean 0.00239, ann 0.0432, Sharpe 0.650, MDD -0.0779
top-quintile turnover: 0.095

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0156 | 0.171 | 0.583 |
| 2025 | 12 | 0.0101 | 0.095 | 0.500 |

regime split: up-market IC -0.0165 (n=15) / down-market IC 0.0618 (n=9)


### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0262 | 0.0855 | -0.3062 | 0.375 | -0.0280 | -0.2389 | 0.417 |
| 5 | 0.0126 | 0.0714 | 0.1763 | 0.625 | -0.0014 | -0.0126 | 0.458 |
| 10 | -0.0039 | 0.0733 | -0.0534 | 0.417 | 0.0066 | 0.0641 | 0.583 |
| 20 | -0.0111 | 0.0648 | -0.1719 | 0.333 | 0.0129 | 0.1294 | 0.542 |
| 40 | -0.0152 | 0.0627 | -0.2423 | 0.375 | 0.0137 | 0.1471 | 0.458 |
| 60 | -0.0130 | 0.0502 | -0.2586 | 0.333 | 0.0195 | 0.1904 | 0.583 |

quantile mean forward 20d returns: Q1: 0.02721  Q2: 0.02550  Q3: 0.03006  Q4: 0.03080  Q5: 0.02960
Q5-Q1 long-short (gross, monthly): mean 0.00239, ann 0.0432, Sharpe 0.650, MDD -0.0779
top-quintile turnover: 0.095

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | 0.0156 | 0.171 | 0.583 |
| 2025 | 12 | 0.0101 | 0.095 | 0.500 |

regime split: up-market IC -0.0165 (n=15) / down-market IC 0.0618 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`operating_cash_flow`: 0.597  `roe`: -0.432  `ocf_to_assets`: 0.390  `roa`: -0.360  `net_margin`: -0.312

## interpretation & limitations

- declared direction `positive` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.