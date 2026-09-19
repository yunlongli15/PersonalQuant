# factor_report_limit_up_count_20.md

## definition

- factor: `limit_up_count_20`  ·  category: microstructure  ·  version 1.0
- formula: `count(ret >= 9.5%, 20d)`
- source: market  ·  PIT: True
- required fields: close, factor
- description: 20 日内涨停次数（资金关注度 / 情绪极值，A 股特有）
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0335 | 0.1019 | 0.3288 | 0.646 | 0.0058 | 0.0571 | 0.583 |
| 5 | -0.0035 | 0.0942 | -0.0369 | 0.500 | -0.0316 | -0.3142 | 0.312 |
| 10 | -0.0079 | 0.0790 | -0.1007 | 0.521 | -0.0374 | -0.4334 | 0.312 |
| 20 | -0.0435 | 0.0767 | -0.5665 | 0.229 | -0.0737 | -0.9062 | 0.188 |
| 40 | -0.0496 | 0.0575 | -0.8624 | 0.208 | -0.0846 | -1.3226 | 0.083 |
| 60 | -0.0479 | 0.0524 | -0.9137 | 0.125 | -0.0839 | -1.4358 | 0.042 |

quantile mean forward 20d returns: Q1: 0.01160  Q2: 0.01556  Q3: 0.01617  Q4: 0.00841  Q5: 0.00398
Q5-Q1 long-short (gross, monthly): mean -0.00762, ann -0.0925, Sharpe -0.870, MDD -0.3558
top-quintile turnover: 0.522

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0737 | -1.765 | 0.000 |
| 2019 | 12 | -0.0679 | -0.665 | 0.333 |
| 2020 | 12 | -0.0676 | -0.707 | 0.250 |
| 2021 | 12 | -0.0855 | -1.218 | 0.167 |

regime split: up-market IC -0.0581 (n=28) / down-market IC -0.0955 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0360 | 0.1095 | 0.3291 | 0.688 | 0.0058 | 0.0570 | 0.583 |
| 5 | -0.0053 | 0.1028 | -0.0519 | 0.479 | -0.0316 | -0.3141 | 0.333 |
| 10 | -0.0115 | 0.0849 | -0.1351 | 0.479 | -0.0374 | -0.4329 | 0.312 |
| 20 | -0.0485 | 0.0809 | -0.5996 | 0.229 | -0.0736 | -0.9059 | 0.188 |
| 40 | -0.0540 | 0.0585 | -0.9234 | 0.188 | -0.0845 | -1.3219 | 0.083 |
| 60 | -0.0532 | 0.0542 | -0.9813 | 0.104 | -0.0838 | -1.4350 | 0.042 |

quantile mean forward 20d returns: Q1: 0.01160  Q2: 0.01556  Q3: 0.01617  Q4: 0.00841  Q5: 0.00398
Q5-Q1 long-short (gross, monthly): mean -0.00762, ann -0.0925, Sharpe -0.870, MDD -0.3558
top-quintile turnover: 0.522

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0736 | -1.765 | 0.000 |
| 2019 | 12 | -0.0679 | -0.665 | 0.333 |
| 2020 | 12 | -0.0675 | -0.706 | 0.250 |
| 2021 | 12 | -0.0855 | -1.219 | 0.167 |

regime split: up-market IC -0.0580 (n=28) / down-market IC -0.0955 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0056 | 0.0880 | 0.0637 | 0.500 | -0.0187 | -0.2383 | 0.417 |
| 5 | 0.0010 | 0.0876 | 0.0116 | 0.583 | -0.0308 | -0.3626 | 0.458 |
| 10 | -0.0324 | 0.0737 | -0.4392 | 0.333 | -0.0607 | -0.8136 | 0.208 |
| 20 | -0.0342 | 0.0769 | -0.4451 | 0.333 | -0.0691 | -0.9282 | 0.125 |
| 40 | -0.0494 | 0.0750 | -0.6577 | 0.250 | -0.0809 | -1.0091 | 0.125 |
| 60 | -0.0644 | 0.0590 | -1.0905 | 0.125 | -0.0958 | -1.5368 | 0.042 |

quantile mean forward 20d returns: Q1: 0.00561  Q2: 0.00281  Q3: 0.00387  Q4: 0.00203  Q5: 0.00021
Q5-Q1 long-short (gross, monthly): mean -0.00540, ann -0.0714, Sharpe -0.478, MDD -0.2085
top-quintile turnover: 0.583

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0602 | -0.763 | 0.250 |
| 2023 | 12 | -0.0780 | -1.138 | 0.000 |

regime split: up-market IC -0.0738 (n=13) / down-market IC -0.0635 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0040 | 0.0966 | 0.0413 | 0.458 | -0.0187 | -0.2386 | 0.417 |
| 5 | -0.0008 | 0.0958 | -0.0084 | 0.583 | -0.0307 | -0.3624 | 0.458 |
| 10 | -0.0404 | 0.0772 | -0.5231 | 0.292 | -0.0606 | -0.8123 | 0.208 |
| 20 | -0.0399 | 0.0811 | -0.4919 | 0.375 | -0.0690 | -0.9271 | 0.125 |
| 40 | -0.0553 | 0.0795 | -0.6963 | 0.208 | -0.0808 | -1.0081 | 0.125 |
| 60 | -0.0705 | 0.0636 | -1.1088 | 0.125 | -0.0957 | -1.5351 | 0.042 |

quantile mean forward 20d returns: Q1: 0.00561  Q2: 0.00281  Q3: 0.00387  Q4: 0.00203  Q5: 0.00021
Q5-Q1 long-short (gross, monthly): mean -0.00540, ann -0.0714, Sharpe -0.478, MDD -0.2085
top-quintile turnover: 0.583

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0601 | -0.762 | 0.250 |
| 2023 | 12 | -0.0779 | -1.137 | 0.000 |

regime split: up-market IC -0.0737 (n=13) / down-market IC -0.0635 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0301 | 0.1434 | 0.2100 | 0.500 | 0.0089 | 0.0545 | 0.458 |
| 5 | -0.0176 | 0.0836 | -0.2107 | 0.500 | -0.0522 | -0.6102 | 0.250 |
| 10 | -0.0129 | 0.0961 | -0.1343 | 0.458 | -0.0418 | -0.3817 | 0.250 |
| 20 | -0.0378 | 0.0819 | -0.4617 | 0.333 | -0.0773 | -0.8305 | 0.250 |
| 40 | -0.0375 | 0.0737 | -0.5090 | 0.292 | -0.0776 | -0.8822 | 0.208 |
| 60 | -0.0402 | 0.0652 | -0.6163 | 0.333 | -0.0835 | -1.0174 | 0.167 |

quantile mean forward 20d returns: Q1: 0.03101  Q2: 0.04038  Q3: 0.03295  Q4: 0.03452  Q5: 0.03187
Q5-Q1 long-short (gross, monthly): mean 0.00086, ann -0.0051, Sharpe -0.027, MDD -0.1630
top-quintile turnover: 0.712

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0673 | -0.638 | 0.333 |
| 2025 | 12 | -0.0872 | -1.127 | 0.167 |

regime split: up-market IC -0.0673 (n=15) / down-market IC -0.0938 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0196 | 0.1358 | 0.1442 | 0.458 | 0.0089 | 0.0545 | 0.458 |
| 5 | -0.0214 | 0.0885 | -0.2420 | 0.458 | -0.0522 | -0.6103 | 0.250 |
| 10 | -0.0166 | 0.0972 | -0.1703 | 0.417 | -0.0418 | -0.3816 | 0.250 |
| 20 | -0.0446 | 0.0844 | -0.5287 | 0.333 | -0.0772 | -0.8306 | 0.250 |
| 40 | -0.0456 | 0.0745 | -0.6123 | 0.292 | -0.0775 | -0.8819 | 0.208 |
| 60 | -0.0487 | 0.0680 | -0.7158 | 0.250 | -0.0834 | -1.0173 | 0.167 |

quantile mean forward 20d returns: Q1: 0.03101  Q2: 0.04038  Q3: 0.03295  Q4: 0.03454  Q5: 0.03185
Q5-Q1 long-short (gross, monthly): mean 0.00084, ann -0.0054, Sharpe -0.028, MDD -0.1630
top-quintile turnover: 0.711

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0673 | -0.638 | 0.333 |
| 2025 | 12 | -0.0872 | -1.128 | 0.167 |

regime split: up-market IC -0.0673 (n=15) / down-market IC -0.0938 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`max_return_20`: 0.624  `momentum_20`: 0.323  `downside_volatility_60`: 0.313  `amount_20`: 0.276  `momentum_60`: 0.258

## redundancy cluster

cluster members: `limit_up_count_20`

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.