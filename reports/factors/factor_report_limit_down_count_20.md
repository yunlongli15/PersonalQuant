# factor_report_limit_down_count_20.md

## definition

- factor: `limit_down_count_20`  ·  category: microstructure  ·  version 1.0
- formula: `count(ret <= -9.5%, 20d)`
- source: market  ·  PIT: True
- required fields: close, factor
- description: 20 日内跌停次数（风险事件频率，A 股特有）
- declared (economic) direction: **negative**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0008 | 0.0753 | -0.0104 | 0.479 | -0.0051 | -0.0627 | 0.396 |
| 5 | -0.0023 | 0.0823 | -0.0283 | 0.500 | -0.0095 | -0.1045 | 0.458 |
| 10 | 0.0023 | 0.0799 | 0.0293 | 0.417 | -0.0068 | -0.0762 | 0.396 |
| 20 | -0.0063 | 0.0714 | -0.0883 | 0.438 | -0.0188 | -0.2410 | 0.250 |
| 40 | -0.0227 | 0.0508 | -0.4479 | 0.250 | -0.0389 | -0.6961 | 0.208 |
| 60 | -0.0325 | 0.0450 | -0.7223 | 0.271 | -0.0508 | -0.9782 | 0.167 |

quantile mean forward 20d returns: Q1: 0.00871  Q2: 0.01262  Q3: 0.01374  Q4: 0.01045  Q5: 0.01020
Q5-Q1 long-short (gross, monthly): mean 0.00149, ann 0.0122, Sharpe 0.113, MDD -0.1819
top-quintile turnover: 0.361

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0124 | 0.154 | 0.417 |
| 2019 | 12 | -0.0149 | -0.173 | 0.250 |
| 2020 | 12 | -0.0292 | -0.345 | 0.167 |
| 2021 | 12 | -0.0436 | -1.076 | 0.167 |

regime split: up-market IC 0.0030 (n=28) / down-market IC -0.0494 (n=20)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0010 | 0.0755 | -0.0129 | 0.479 | -0.0051 | -0.0621 | 0.396 |
| 5 | -0.0022 | 0.0830 | -0.0270 | 0.479 | -0.0095 | -0.1041 | 0.458 |
| 10 | 0.0021 | 0.0806 | 0.0267 | 0.438 | -0.0067 | -0.0757 | 0.396 |
| 20 | -0.0077 | 0.0717 | -0.1068 | 0.458 | -0.0188 | -0.2401 | 0.250 |
| 40 | -0.0238 | 0.0510 | -0.4675 | 0.250 | -0.0388 | -0.6949 | 0.208 |
| 60 | -0.0335 | 0.0455 | -0.7352 | 0.250 | -0.0508 | -0.9770 | 0.188 |

quantile mean forward 20d returns: Q1: 0.00871  Q2: 0.01262  Q3: 0.01374  Q4: 0.01045  Q5: 0.01020
Q5-Q1 long-short (gross, monthly): mean 0.00149, ann 0.0122, Sharpe 0.113, MDD -0.1819
top-quintile turnover: 0.361

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2018 | 12 | 0.0123 | 0.153 | 0.417 |
| 2019 | 12 | -0.0148 | -0.172 | 0.250 |
| 2020 | 12 | -0.0290 | -0.342 | 0.167 |
| 2021 | 12 | -0.0435 | -1.075 | 0.167 |

regime split: up-market IC 0.0031 (n=28) / down-market IC -0.0494 (n=20)

---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0175 | 0.0658 | -0.2658 | 0.417 | -0.0214 | -0.3324 | 0.417 |
| 5 | 0.0020 | 0.0659 | 0.0309 | 0.500 | -0.0075 | -0.1096 | 0.500 |
| 10 | -0.0203 | 0.0564 | -0.3599 | 0.375 | -0.0292 | -0.4777 | 0.250 |
| 20 | -0.0097 | 0.0600 | -0.1622 | 0.375 | -0.0240 | -0.3911 | 0.292 |
| 40 | -0.0191 | 0.0556 | -0.3443 | 0.333 | -0.0318 | -0.5188 | 0.250 |
| 60 | -0.0353 | 0.0410 | -0.8609 | 0.208 | -0.0500 | -0.9961 | 0.125 |

quantile mean forward 20d returns: Q1: 0.00304  Q2: 0.00193  Q3: 0.00227  Q4: 0.00499  Q5: 0.00231
Q5-Q1 long-short (gross, monthly): mean -0.00073, ann -0.0107, Sharpe -0.069, MDD -0.1224
top-quintile turnover: 0.304

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0092 | -0.138 | 0.417 |
| 2023 | 12 | -0.0388 | -0.755 | 0.167 |

regime split: up-market IC -0.0251 (n=13) / down-market IC -0.0227 (n=11)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0171 | 0.0661 | -0.2592 | 0.417 | -0.0214 | -0.3332 | 0.417 |
| 5 | 0.0019 | 0.0655 | 0.0291 | 0.500 | -0.0075 | -0.1092 | 0.500 |
| 10 | -0.0208 | 0.0556 | -0.3746 | 0.375 | -0.0291 | -0.4778 | 0.250 |
| 20 | -0.0103 | 0.0592 | -0.1737 | 0.375 | -0.0239 | -0.3895 | 0.292 |
| 40 | -0.0198 | 0.0547 | -0.3630 | 0.333 | -0.0317 | -0.5183 | 0.250 |
| 60 | -0.0363 | 0.0390 | -0.9293 | 0.208 | -0.0500 | -0.9967 | 0.125 |

quantile mean forward 20d returns: Q1: 0.00304  Q2: 0.00193  Q3: 0.00227  Q4: 0.00499  Q5: 0.00231
Q5-Q1 long-short (gross, monthly): mean -0.00073, ann -0.0107, Sharpe -0.069, MDD -0.1224
top-quintile turnover: 0.304

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2022 | 12 | -0.0090 | -0.135 | 0.417 |
| 2023 | 12 | -0.0388 | -0.756 | 0.167 |

regime split: up-market IC -0.0249 (n=13) / down-market IC -0.0227 (n=11)

---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 1.000
- empirical direction: negative

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0004 | 0.1004 | -0.0039 | 0.333 | 0.0001 | 0.0006 | 0.333 |
| 5 | -0.0023 | 0.0762 | -0.0308 | 0.458 | -0.0138 | -0.1544 | 0.417 |
| 10 | 0.0007 | 0.0769 | 0.0089 | 0.375 | -0.0062 | -0.0652 | 0.333 |
| 20 | -0.0121 | 0.0728 | -0.1664 | 0.458 | -0.0288 | -0.3367 | 0.292 |
| 40 | -0.0265 | 0.0538 | -0.4921 | 0.292 | -0.0430 | -0.6222 | 0.208 |
| 60 | -0.0251 | 0.0533 | -0.4718 | 0.250 | -0.0451 | -0.6636 | 0.167 |

quantile mean forward 20d returns: Q1: 0.02792  Q2: 0.03701  Q3: 0.03137  Q4: 0.02855  Q5: 0.04587
Q5-Q1 long-short (gross, monthly): mean 0.01794, ann 0.2186, Sharpe 1.130, MDD -0.1072
top-quintile turnover: 0.449

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0010 | -0.010 | 0.417 |
| 2025 | 12 | -0.0565 | -0.965 | 0.167 |

regime split: up-market IC -0.0085 (n=15) / down-market IC -0.0625 (n=9)


### normalization: winsorized_zscore (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -0.0010 | 0.0996 | -0.0099 | 0.333 | 0.0001 | 0.0008 | 0.333 |
| 5 | -0.0018 | 0.0764 | -0.0240 | 0.458 | -0.0138 | -0.1549 | 0.417 |
| 10 | 0.0015 | 0.0792 | 0.0183 | 0.375 | -0.0062 | -0.0657 | 0.333 |
| 20 | -0.0123 | 0.0753 | -0.1628 | 0.458 | -0.0288 | -0.3371 | 0.292 |
| 40 | -0.0270 | 0.0536 | -0.5042 | 0.292 | -0.0430 | -0.6225 | 0.208 |
| 60 | -0.0261 | 0.0532 | -0.4912 | 0.208 | -0.0450 | -0.6632 | 0.167 |

quantile mean forward 20d returns: Q1: 0.02792  Q2: 0.03701  Q3: 0.03137  Q4: 0.02855  Q5: 0.04587
Q5-Q1 long-short (gross, monthly): mean 0.01794, ann 0.2186, Sharpe 1.130, MDD -0.1072
top-quintile turnover: 0.449

| year | n | rank IC mean | ICIR | IC>0 |
| --- | --- | --- | --- | --- |
| 2024 | 12 | -0.0010 | -0.010 | 0.417 |
| 2025 | 12 | -0.0566 | -0.966 | 0.167 |

regime split: up-market IC -0.0085 (n=15) / down-market IC -0.0625 (n=9)

---

## correlation with other factors (avg cross-sectional spearman, research)

`downside_volatility_60`: 0.363  `limit_up_count_20`: 0.247  `max_return_20`: 0.242  `amount_20`: 0.192  `earnings_yield`: -0.148

## interpretation & limitations

- declared direction `negative` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.