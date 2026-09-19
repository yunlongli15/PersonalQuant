# factor_report_ps.md

## definition

- factor: `ps`  ·  category: valuation  ·  version 1.0
- formula: `close*shares/revenue_latest_annual; shares=net_assets/bps`
- source: financial  ·  PIT: True
- required fields: close, revenue, net_assets, bps
- description: price-to-sales on the latest PIT annual report
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

`amihud_20`: —  `amount_20`: —  `amount_60`: —  `amount_share_20`: —  `announcement_attention_5d`: —

## interpretation & limitations

- declared direction `negative` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.