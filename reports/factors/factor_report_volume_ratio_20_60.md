# factor_report_volume_ratio_20_60.md

## definition

- factor: `volume_ratio_20_60`  ·  category: volume  ·  version 1.0
- formula: `MA(volume,20)/MA(volume,60)`
- source: market  ·  PIT: True
- required fields: volume
- description: 20-day vs 60-day average volume (activity acceleration)
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.969
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0079 | 0.0877 | 0.0903 | 0.542 | -0.0149 | -0.1529 | 0.438 |
| 5 | -0.0030 | 0.0934 | -0.0320 | 0.500 | -0.0291 | -0.2667 | 0.417 |
| 10 | -0.0105 | 0.0814 | -0.1294 | 0.396 | -0.0350 | -0.3580 | 0.271 |
| 20 | -0.0240 | 0.0842 | -0.2851 | 0.333 | -0.0466 | -0.4805 | 0.250 |
| 40 | -0.0260 | 0.0792 | -0.3281 | 0.375 | -0.0482 | -0.5005 | 0.271 |
| 60 | -0.0243 | 0.0770 | -0.3158 | 0.375 | -0.0464 | -0.5034 | 0.271 |

quantile mean forward 20d returns: Q1: 0.01441  Q2: 0.01287  Q3: 0.01122  Q4: 0.01083  Q5: 0.00639
Q5-Q1 long-short (gross, monthly): mean -0.00802, ann -0.0908, Sharpe -0.832, MDD -0.3283
top-quintile turnover: 0.765

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0443 | -0.813 | 0.167 |
| 2019 | 12 | -0.0521 | -1.182 | 0.083 |
| 2020 | 12 | 0.0044 | 0.040 | 0.417 |
| 2021 | 12 | -0.0942 | -0.749 | 0.333 |

regime split: up-market IC -0.0521 (n=28) / down-market IC -0.0389 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0092 | 0.0909 | 0.1010 | 0.542 | -0.0149 | -0.1529 | 0.438 |
| 5 | -0.0067 | 0.0966 | -0.0689 | 0.438 | -0.0291 | -0.2668 | 0.417 |
| 10 | -0.0148 | 0.0870 | -0.1701 | 0.396 | -0.0350 | -0.3579 | 0.271 |
| 20 | -0.0292 | 0.0849 | -0.3438 | 0.333 | -0.0466 | -0.4804 | 0.250 |
| 40 | -0.0312 | 0.0745 | -0.4180 | 0.333 | -0.0482 | -0.5005 | 0.271 |
| 60 | -0.0284 | 0.0736 | -0.3858 | 0.271 | -0.0464 | -0.5033 | 0.271 |

quantile mean forward 20d returns: Q1: 0.01442  Q2: 0.01286  Q3: 0.01122  Q4: 0.01082  Q5: 0.00640
Q5-Q1 long-short (gross, monthly): mean -0.00802, ann -0.0907, Sharpe -0.832, MDD -0.3285
top-quintile turnover: 0.765

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | -0.0443 | -0.812 | 0.167 |
| 2019 | 12 | -0.0521 | -1.182 | 0.083 |
| 2020 | 12 | 0.0044 | 0.040 | 0.417 |
| 2021 | 12 | -0.0942 | -0.749 | 0.333 |

regime split: up-market IC -0.0521 (n=28) / down-market IC -0.0389 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.989
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0007 | 0.0892 | -0.0078 | 0.458 | -0.0213 | -0.2089 | 0.417 |
| 5 | -0.0007 | 0.1034 | -0.0068 | 0.583 | -0.0231 | -0.1927 | 0.458 |
| 10 | -0.0149 | 0.0949 | -0.1567 | 0.458 | -0.0353 | -0.3114 | 0.375 |
| 20 | -0.0069 | 0.1049 | -0.0662 | 0.500 | -0.0319 | -0.2770 | 0.417 |
| 40 | -0.0145 | 0.0939 | -0.1542 | 0.458 | -0.0371 | -0.3402 | 0.375 |
| 60 | -0.0261 | 0.0849 | -0.3070 | 0.417 | -0.0489 | -0.4701 | 0.375 |

quantile mean forward 20d returns: Q1: 0.00263  Q2: 0.00303  Q3: 0.00627  Q4: 0.00191  Q5: 0.00070
Q5-Q1 long-short (gross, monthly): mean -0.00193, ann -0.0433, Sharpe -0.355, MDD -0.2139
top-quintile turnover: 0.806

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0615 | -0.488 | 0.333 |
| 2023 | 12 | -0.0022 | -0.023 | 0.500 |

regime split: up-market IC -0.0685 (n=13) / down-market IC 0.0115 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0009 | 0.0981 | -0.0093 | 0.458 | -0.0213 | -0.2089 | 0.417 |
| 5 | -0.0014 | 0.1078 | -0.0133 | 0.542 | -0.0231 | -0.1927 | 0.458 |
| 10 | -0.0197 | 0.0963 | -0.2051 | 0.458 | -0.0353 | -0.3113 | 0.375 |
| 20 | -0.0112 | 0.1067 | -0.1046 | 0.417 | -0.0319 | -0.2770 | 0.417 |
| 40 | -0.0209 | 0.0944 | -0.2212 | 0.375 | -0.0371 | -0.3402 | 0.375 |
| 60 | -0.0316 | 0.0848 | -0.3719 | 0.375 | -0.0489 | -0.4701 | 0.375 |

quantile mean forward 20d returns: Q1: 0.00263  Q2: 0.00302  Q3: 0.00628  Q4: 0.00190  Q5: 0.00071
Q5-Q1 long-short (gross, monthly): mean -0.00192, ann -0.0432, Sharpe -0.354, MDD -0.2139
top-quintile turnover: 0.806

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0615 | -0.488 | 0.333 |
| 2023 | 12 | -0.0022 | -0.023 | 0.500 |

regime split: up-market IC -0.0685 (n=13) / down-market IC 0.0115 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.988
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0104 | 0.1045 | -0.0998 | 0.417 | -0.0279 | -0.2226 | 0.417 |
| 5 | -0.0038 | 0.1114 | -0.0337 | 0.458 | -0.0328 | -0.2309 | 0.375 |
| 10 | -0.0196 | 0.0845 | -0.2314 | 0.417 | -0.0509 | -0.4916 | 0.333 |
| 20 | -0.0237 | 0.0691 | -0.3431 | 0.250 | -0.0526 | -0.6002 | 0.292 |
| 40 | -0.0203 | 0.0632 | -0.3211 | 0.375 | -0.0451 | -0.5614 | 0.250 |
| 60 | -0.0178 | 0.0562 | -0.3161 | 0.458 | -0.0446 | -0.6070 | 0.250 |

quantile mean forward 20d returns: Q1: 0.03695  Q2: 0.03373  Q3: 0.04117  Q4: 0.03216  Q5: 0.02671
Q5-Q1 long-short (gross, monthly): mean -0.01023, ann -0.1015, Sharpe -1.251, MDD -0.1928
top-quintile turnover: 0.836

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0496 | -0.608 | 0.250 |
| 2025 | 12 | -0.0557 | -0.596 | 0.333 |

regime split: up-market IC -0.0732 (n=15) / down-market IC -0.0184 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0088 | 0.1059 | -0.0833 | 0.417 | -0.0279 | -0.2231 | 0.417 |
| 5 | -0.0068 | 0.1119 | -0.0610 | 0.458 | -0.0328 | -0.2311 | 0.375 |
| 10 | -0.0225 | 0.0880 | -0.2552 | 0.333 | -0.0509 | -0.4919 | 0.333 |
| 20 | -0.0300 | 0.0705 | -0.4259 | 0.250 | -0.0526 | -0.6002 | 0.292 |
| 40 | -0.0278 | 0.0619 | -0.4485 | 0.250 | -0.0451 | -0.5613 | 0.250 |
| 60 | -0.0274 | 0.0533 | -0.5148 | 0.333 | -0.0446 | -0.6069 | 0.250 |

quantile mean forward 20d returns: Q1: 0.03695  Q2: 0.03373  Q3: 0.04121  Q4: 0.03213  Q5: 0.02671
Q5-Q1 long-short (gross, monthly): mean -0.01023, ann -0.1015, Sharpe -1.250, MDD -0.1927
top-quintile turnover: 0.836

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0496 | -0.609 | 0.250 |
| 2025 | 12 | -0.0556 | -0.596 | 0.333 |

regime split: up-market IC -0.0732 (n=15) / down-market IC -0.0183 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`price_vs_ma60`: 0.428  `volatility_20`: 0.406  `momentum_20`: 0.379  `reversal_20`: -0.379  `price_vs_ma120`: 0.264

## redundancy cluster

cluster members: `volume_ratio_20_60`

## interpretation & limitations

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.