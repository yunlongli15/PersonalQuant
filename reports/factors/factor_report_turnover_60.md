# factor_report_turnover_60.md

## definition

- factor: `turnover_60`  ·  category: liquidity  ·  version 1.0
- formula: `MA(volume_shares,60)/shares_latest_annual`
- source: financial+market  ·  PIT: True
- required fields: volume, market_scale, net_assets, bps
- description: 60-day average share turnover; shares from the latest PIT annual report (financial-universe coverage only)
- declared (economic) direction: **negative**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.002
- empirical direction: neutral  ⚠️ disagrees with declared direction

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | — | — | — | — | — | — | — |
| 5 | — | — | — | — | — | — | — |
| 10 | — | — | — | — | — | — | — |
| 20 | — | — | — | — | — | — | — |
| 40 | — | — | — | — | — | — | — |
| 60 | — | — | — | — | — | — | — |



### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | — | — | — | — | — | — | — |
| 5 | — | — | — | — | — | — | — |
| 10 | — | — | — | — | — | — | — |
| 20 | — | — | — | — | — | — | — |
| 40 | — | — | — | — | — | — | — |
| 60 | — | — | — | — | — | — | — |


---

## valid (24 monthly dates 2022-01-28 .. 2023-12-29)

- coverage: 0.002
- empirical direction: neutral  ⚠️ disagrees with declared direction

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | — | — | — | — | — | — | — |
| 5 | — | — | — | — | — | — | — |
| 10 | — | — | — | — | — | — | — |
| 20 | — | — | — | — | — | — | — |
| 40 | — | — | — | — | — | — | — |
| 60 | — | — | — | — | — | — | — |



### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | — | — | — | — | — | — | — |
| 5 | — | — | — | — | — | — | — |
| 10 | — | — | — | — | — | — | — |
| 20 | — | — | — | — | — | — | — |
| 40 | — | — | — | — | — | — | — |
| 60 | — | — | — | — | — | — | — |


---

## test (24 monthly dates 2024-01-31 .. 2025-12-31)

- coverage: 0.002
- empirical direction: neutral  ⚠️ disagrees with declared direction

### normalization: rank (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | — | — | — | — | — | — | — |
| 5 | — | — | — | — | — | — | — |
| 10 | — | — | — | — | — | — | — |
| 20 | — | — | — | — | — | — | — |
| 40 | — | — | — | — | — | — | — |
| 60 | — | — | — | — | — | — | — |



### normalization: winsorized_zscore (missing: drop)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | — | — | — | — | — | — | — |
| 5 | — | — | — | — | — | — | — |
| 10 | — | — | — | — | — | — | — |
| 20 | — | — | — | — | — | — | — |
| 40 | — | — | — | — | — | — | — |
| 60 | — | — | — | — | — | — | — |


---

## correlation with other factors (avg cross-sectional spearman, research)

`amount_20`: —  `amount_60`: —  `debt_to_asset`: —  `downside_volatility_60`: —  `earnings_yield`: —

## interpretation & limitations

- declared direction `negative` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.