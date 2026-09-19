# factor_report_volume_price_corr_20.md

## definition

- factor: `volume_price_corr_20`  ·  category: volume  ·  version 1.0
- formula: `corr(volume, ret, 20d)`
- source: market  ·  PIT: True
- required fields: volume, close, factor
- description: 量价相关性（放量上涨 vs 放量下跌的方向性）
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0147 | 0.0592 | 0.2480 | 0.604 | -0.0059 | -0.0829 | 0.458 |
| 5 | 0.0018 | 0.0625 | 0.0293 | 0.521 | -0.0172 | -0.2168 | 0.479 |
| 10 | -0.0031 | 0.0534 | -0.0575 | 0.417 | -0.0185 | -0.2856 | 0.271 |
| 20 | -0.0176 | 0.0523 | -0.3368 | 0.396 | -0.0320 | -0.5131 | 0.292 |
| 40 | -0.0243 | 0.0593 | -0.4093 | 0.375 | -0.0400 | -0.5534 | 0.271 |
| 60 | -0.0197 | 0.0607 | -0.3239 | 0.333 | -0.0351 | -0.4831 | 0.312 |

quantile mean forward 20d returns: Q1: 0.01328  Q2: 0.01264  Q3: 0.01271  Q4: 0.00887  Q5: 0.00820
Q5-Q1 long-short (gross, monthly): mean -0.00508, ann -0.0524, Sharpe -0.816, MDD -0.2099
top-quintile turnover: 0.788

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0567 | -0.769 | 0.167 |
| 2019 | 12 | -0.0296 | -0.534 | 0.333 |
| 2020 | 12 | -0.0143 | -0.313 | 0.250 |
| 2021 | 12 | -0.0273 | -0.433 | 0.417 |

regime split: up-market IC -0.0391 (n=28) / down-market IC -0.0221 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0159 | 0.0607 | 0.2623 | 0.625 | -0.0059 | -0.0830 | 0.458 |
| 5 | 0.0034 | 0.0610 | 0.0553 | 0.562 | -0.0172 | -0.2170 | 0.479 |
| 10 | -0.0016 | 0.0544 | -0.0289 | 0.479 | -0.0186 | -0.2859 | 0.271 |
| 20 | -0.0170 | 0.0529 | -0.3209 | 0.396 | -0.0320 | -0.5133 | 0.292 |
| 40 | -0.0235 | 0.0589 | -0.3993 | 0.375 | -0.0400 | -0.5535 | 0.271 |
| 60 | -0.0190 | 0.0598 | -0.3180 | 0.354 | -0.0351 | -0.4832 | 0.312 |

quantile mean forward 20d returns: Q1: 0.01329  Q2: 0.01264  Q3: 0.01268  Q4: 0.00890  Q5: 0.00820
Q5-Q1 long-short (gross, monthly): mean -0.00509, ann -0.0525, Sharpe -0.817, MDD -0.2102
top-quintile turnover: 0.788

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0567 | -0.769 | 0.167 |
| 2019 | 12 | -0.0296 | -0.534 | 0.333 |
| 2020 | 12 | -0.0143 | -0.313 | 0.250 |
| 2021 | 12 | -0.0274 | -0.433 | 0.417 |

regime split: up-market IC -0.0391 (n=28) / down-market IC -0.0221 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0111 | 0.0616 | -0.1801 | 0.375 | -0.0382 | -0.5349 | 0.292 |
| 5 | -0.0132 | 0.0596 | -0.2216 | 0.417 | -0.0330 | -0.4567 | 0.292 |
| 10 | -0.0181 | 0.0572 | -0.3164 | 0.417 | -0.0386 | -0.5447 | 0.375 |
| 20 | -0.0285 | 0.0603 | -0.4724 | 0.417 | -0.0468 | -0.6197 | 0.292 |
| 40 | -0.0264 | 0.0686 | -0.3843 | 0.333 | -0.0475 | -0.5875 | 0.292 |
| 60 | -0.0269 | 0.0550 | -0.4882 | 0.417 | -0.0493 | -0.7045 | 0.333 |

quantile mean forward 20d returns: Q1: 0.00438  Q2: 0.00572  Q3: 0.00768  Q4: 0.00192  Q5: -0.00515
Q5-Q1 long-short (gross, monthly): mean -0.00953, ann -0.1102, Sharpe -1.596, MDD -0.2083
top-quintile turnover: 0.837

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0688 | -0.821 | 0.250 |
| 2023 | 12 | -0.0247 | -0.425 | 0.333 |

regime split: up-market IC -0.0544 (n=13) / down-market IC -0.0377 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0100 | 0.0592 | -0.1693 | 0.375 | -0.0382 | -0.5348 | 0.292 |
| 5 | -0.0099 | 0.0592 | -0.1665 | 0.458 | -0.0330 | -0.4568 | 0.292 |
| 10 | -0.0158 | 0.0571 | -0.2770 | 0.417 | -0.0386 | -0.5448 | 0.375 |
| 20 | -0.0258 | 0.0603 | -0.4287 | 0.417 | -0.0468 | -0.6197 | 0.292 |
| 40 | -0.0245 | 0.0694 | -0.3526 | 0.417 | -0.0475 | -0.5876 | 0.292 |
| 60 | -0.0243 | 0.0544 | -0.4472 | 0.417 | -0.0493 | -0.7046 | 0.333 |

quantile mean forward 20d returns: Q1: 0.00438  Q2: 0.00572  Q3: 0.00768  Q4: 0.00192  Q5: -0.00515
Q5-Q1 long-short (gross, monthly): mean -0.00953, ann -0.1102, Sharpe -1.596, MDD -0.2083
top-quintile turnover: 0.837

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0688 | -0.821 | 0.250 |
| 2023 | 12 | -0.0247 | -0.424 | 0.333 |

regime split: up-market IC -0.0544 (n=13) / down-market IC -0.0377 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0190 | 0.0601 | 0.3157 | 0.625 | -0.0018 | -0.0239 | 0.417 |
| 5 | 0.0080 | 0.0724 | 0.1104 | 0.583 | -0.0106 | -0.1133 | 0.458 |
| 10 | 0.0110 | 0.0655 | 0.1686 | 0.625 | -0.0094 | -0.1120 | 0.583 |
| 20 | 0.0108 | 0.0627 | 0.1719 | 0.625 | -0.0086 | -0.1157 | 0.542 |
| 40 | 0.0077 | 0.0580 | 0.1322 | 0.583 | -0.0146 | -0.1893 | 0.542 |
| 60 | -0.0080 | 0.0591 | -0.1351 | 0.458 | -0.0320 | -0.4053 | 0.417 |

quantile mean forward 20d returns: Q1: 0.03055  Q2: 0.03051  Q3: 0.04070  Q4: 0.03367  Q5: 0.03530
Q5-Q1 long-short (gross, monthly): mean 0.00475, ann 0.0316, Sharpe 0.382, MDD -0.0715
top-quintile turnover: 0.839

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0101 | -0.118 | 0.583 |
| 2025 | 12 | -0.0070 | -0.116 | 0.500 |

regime split: up-market IC -0.0025 (n=15) / down-market IC -0.0186 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0200 | 0.0597 | 0.3343 | 0.625 | -0.0018 | -0.0240 | 0.417 |
| 5 | 0.0072 | 0.0717 | 0.1003 | 0.542 | -0.0106 | -0.1134 | 0.458 |
| 10 | 0.0116 | 0.0639 | 0.1814 | 0.667 | -0.0094 | -0.1120 | 0.583 |
| 20 | 0.0106 | 0.0614 | 0.1731 | 0.625 | -0.0086 | -0.1157 | 0.542 |
| 40 | 0.0085 | 0.0570 | 0.1484 | 0.583 | -0.0146 | -0.1894 | 0.542 |
| 60 | -0.0062 | 0.0594 | -0.1043 | 0.458 | -0.0320 | -0.4054 | 0.417 |

quantile mean forward 20d returns: Q1: 0.03055  Q2: 0.03050  Q3: 0.04070  Q4: 0.03367  Q5: 0.03530
Q5-Q1 long-short (gross, monthly): mean 0.00475, ann 0.0316, Sharpe 0.382, MDD -0.0715
top-quintile turnover: 0.839

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0101 | -0.118 | 0.583 |
| 2025 | 12 | -0.0070 | -0.116 | 0.500 |

regime split: up-market IC -0.0025 (n=15) / down-market IC -0.0186 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`momentum_20`: 0.458  `max_return_20`: 0.349  `momentum_60`: 0.198  `limit_down_count_20`: -0.153  `high_52w_proximity`: 0.145

## redundancy cluster

cluster members: `volume_price_corr_20`

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.