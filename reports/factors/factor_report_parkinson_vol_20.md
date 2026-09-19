# factor_report_parkinson_vol_20.md

## definition

- factor: `parkinson_vol_20`  ·  category: volatility  ·  version 1.0
- formula: `sqrt(mean(ln(high/low)^2,20d)/(4 ln2))`
- source: market  ·  PIT: True
- required fields: high, low
- description: Parkinson 高低价波动率（比收盘价波动率更有效的日内波动估计）
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0359 | 0.1561 | 0.2302 | 0.688 | 0.0100 | 0.0540 | 0.604 |
| 5 | 0.0118 | 0.1410 | 0.0840 | 0.542 | -0.0258 | -0.1466 | 0.417 |
| 10 | 0.0097 | 0.1258 | 0.0774 | 0.458 | -0.0354 | -0.2170 | 0.417 |
| 20 | -0.0250 | 0.1332 | -0.1875 | 0.417 | -0.0799 | -0.4959 | 0.271 |
| 40 | -0.0349 | 0.1206 | -0.2893 | 0.396 | -0.0947 | -0.6594 | 0.292 |
| 60 | -0.0394 | 0.1104 | -0.3571 | 0.375 | -0.1012 | -0.7680 | 0.333 |

quantile mean forward 20d returns: Q1: 0.00964  Q2: 0.01410  Q3: 0.01437  Q4: 0.01270  Q5: 0.00491
Q5-Q1 long-short (gross, monthly): mean -0.00472, ann -0.0785, Sharpe -0.431, MDD -0.3301
top-quintile turnover: 0.559

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0803 | -0.789 | 0.167 |
| 2019 | 12 | -0.0330 | -0.186 | 0.333 |
| 2020 | 12 | -0.0706 | -0.401 | 0.417 |
| 2021 | 12 | -0.1355 | -0.850 | 0.167 |

regime split: up-market IC -0.0374 (n=28) / down-market IC -0.1393 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0357 | 0.1609 | 0.2216 | 0.667 | 0.0099 | 0.0540 | 0.604 |
| 5 | 0.0075 | 0.1472 | 0.0509 | 0.500 | -0.0258 | -0.1466 | 0.417 |
| 10 | 0.0054 | 0.1308 | 0.0416 | 0.458 | -0.0354 | -0.2171 | 0.417 |
| 20 | -0.0335 | 0.1342 | -0.2501 | 0.396 | -0.0799 | -0.4958 | 0.271 |
| 40 | -0.0459 | 0.1169 | -0.3922 | 0.375 | -0.0947 | -0.6594 | 0.292 |
| 60 | -0.0510 | 0.1052 | -0.4844 | 0.375 | -0.1012 | -0.7680 | 0.333 |

quantile mean forward 20d returns: Q1: 0.00964  Q2: 0.01411  Q3: 0.01437  Q4: 0.01270  Q5: 0.00490
Q5-Q1 long-short (gross, monthly): mean -0.00473, ann -0.0785, Sharpe -0.432, MDD -0.3303
top-quintile turnover: 0.559

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0803 | -0.790 | 0.167 |
| 2019 | 12 | -0.0330 | -0.186 | 0.333 |
| 2020 | 12 | -0.0706 | -0.401 | 0.417 |
| 2021 | 12 | -0.1355 | -0.850 | 0.167 |

regime split: up-market IC -0.0374 (n=28) / down-market IC -0.1393 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0106 | 0.1208 | -0.0875 | 0.500 | -0.0570 | -0.4215 | 0.417 |
| 5 | 0.0044 | 0.1417 | 0.0312 | 0.542 | -0.0454 | -0.2578 | 0.500 |
| 10 | -0.0390 | 0.1208 | -0.3231 | 0.333 | -0.0945 | -0.6398 | 0.208 |
| 20 | -0.0553 | 0.1328 | -0.4166 | 0.375 | -0.1161 | -0.7606 | 0.292 |
| 40 | -0.0762 | 0.1272 | -0.5992 | 0.333 | -0.1386 | -0.9289 | 0.167 |
| 60 | -0.0975 | 0.0965 | -1.0104 | 0.208 | -0.1703 | -1.5059 | 0.083 |

quantile mean forward 20d returns: Q1: 0.00751  Q2: 0.00704  Q3: 0.00743  Q4: 0.00016  Q5: -0.00760
Q5-Q1 long-short (gross, monthly): mean -0.01511, ann -0.1729, Sharpe -1.145, MDD -0.3165
top-quintile turnover: 0.584

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0761 | -0.646 | 0.333 |
| 2023 | 12 | -0.1561 | -0.908 | 0.250 |

regime split: up-market IC -0.0719 (n=13) / down-market IC -0.1684 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0088 | 0.1384 | -0.0636 | 0.500 | -0.0570 | -0.4216 | 0.417 |
| 5 | 0.0046 | 0.1423 | 0.0322 | 0.500 | -0.0454 | -0.2578 | 0.500 |
| 10 | -0.0470 | 0.1222 | -0.3842 | 0.292 | -0.0945 | -0.6397 | 0.208 |
| 20 | -0.0606 | 0.1336 | -0.4536 | 0.375 | -0.1161 | -0.7604 | 0.292 |
| 40 | -0.0829 | 0.1265 | -0.6556 | 0.375 | -0.1386 | -0.9288 | 0.167 |
| 60 | -0.1056 | 0.0940 | -1.1241 | 0.125 | -0.1702 | -1.5057 | 0.083 |

quantile mean forward 20d returns: Q1: 0.00751  Q2: 0.00705  Q3: 0.00742  Q4: 0.00016  Q5: -0.00760
Q5-Q1 long-short (gross, monthly): mean -0.01511, ann -0.1729, Sharpe -1.145, MDD -0.3165
top-quintile turnover: 0.584

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0761 | -0.646 | 0.333 |
| 2023 | 12 | -0.1561 | -0.908 | 0.250 |

regime split: up-market IC -0.0719 (n=13) / down-market IC -0.1683 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0384 | 0.1616 | 0.2374 | 0.500 | 0.0097 | 0.0475 | 0.458 |
| 5 | -0.0433 | 0.1735 | -0.2495 | 0.458 | -0.0981 | -0.4530 | 0.333 |
| 10 | -0.0136 | 0.1666 | -0.0818 | 0.500 | -0.0609 | -0.2929 | 0.375 |
| 20 | -0.0093 | 0.1436 | -0.0647 | 0.500 | -0.0703 | -0.3684 | 0.375 |
| 40 | -0.0139 | 0.1245 | -0.1116 | 0.458 | -0.0722 | -0.4231 | 0.333 |
| 60 | 0.0018 | 0.1038 | 0.0171 | 0.583 | -0.0556 | -0.3961 | 0.417 |

quantile mean forward 20d returns: Q1: 0.02658  Q2: 0.03521  Q3: 0.04327  Q4: 0.03764  Q5: 0.02803
Q5-Q1 long-short (gross, monthly): mean 0.00145, ann -0.0030, Sharpe -0.015, MDD -0.1699
top-quintile turnover: 0.635

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0526 | -0.253 | 0.333 |
| 2025 | 12 | -0.0879 | -0.517 | 0.417 |

regime split: up-market IC -0.0037 (n=15) / down-market IC -0.1812 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0315 | 0.1612 | 0.1955 | 0.500 | 0.0097 | 0.0474 | 0.458 |
| 5 | -0.0455 | 0.1684 | -0.2702 | 0.458 | -0.0981 | -0.4530 | 0.333 |
| 10 | -0.0184 | 0.1616 | -0.1140 | 0.500 | -0.0609 | -0.2929 | 0.375 |
| 20 | -0.0210 | 0.1366 | -0.1535 | 0.458 | -0.0703 | -0.3684 | 0.375 |
| 40 | -0.0261 | 0.1174 | -0.2227 | 0.375 | -0.0722 | -0.4231 | 0.333 |
| 60 | -0.0144 | 0.0987 | -0.1457 | 0.583 | -0.0556 | -0.3961 | 0.417 |

quantile mean forward 20d returns: Q1: 0.02658  Q2: 0.03521  Q3: 0.04328  Q4: 0.03763  Q5: 0.02803
Q5-Q1 long-short (gross, monthly): mean 0.00145, ann -0.0030, Sharpe -0.015, MDD -0.1699
top-quintile turnover: 0.635

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0526 | -0.253 | 0.333 |
| 2025 | 12 | -0.0879 | -0.517 | 0.417 |

regime split: up-market IC -0.0037 (n=15) / down-market IC -0.1812 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`max_return_20`: 0.833  `downside_volatility_60`: 0.689  `earnings_yield`: -0.532  `limit_up_count_20`: 0.515  `amount_20`: 0.463

## redundancy cluster

cluster members: `downside_volatility_60`, `max_return_20`, `parkinson_vol_20`, `volatility_20`, `volatility_60`

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.