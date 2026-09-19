# factor_report_llm_confidence_20d.md

## definition

- factor: `llm_confidence_20d`  ·  category: news  ·  version 1.0
- formula: `mean LLM confidence of events in 20d (NaN when no LLM tier)`
- source: news_llm  ·  PIT: True
- required fields: news_events, news_coverage
- description: 20-day mean LLM confidence (LLM tier only)
- declared (economic) direction: **neutral**

## research (48 monthly dates 2018-01-31 .. 2021-12-31)

- coverage: 0.000
- empirical direction: neutral

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | — | — | — | — | — | — | — |
| 5 | — | — | — | — | — | — | — |
| 10 | — | — | — | — | — | — | — |
| 20 | — | — | — | — | — | — | — |
| 40 | — | — | — | — | — | — | — |
| 60 | — | — | — | — | — | — | — |



### normalization: winsorized_zscore (missing: sector_median)

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

- coverage: 0.000
- empirical direction: neutral

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | — | — | — | — | — | — | — |
| 5 | — | — | — | — | — | — | — |
| 10 | — | — | — | — | — | — | — |
| 20 | — | — | — | — | — | — | — |
| 40 | — | — | — | — | — | — | — |
| 60 | — | — | — | — | — | — | — |



### normalization: winsorized_zscore (missing: sector_median)

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

- coverage: 0.000
- empirical direction: neutral

### normalization: rank (missing: sector_median)

| horizon | IC mean | IC std | ICIR | IC>0 | RankIC mean | RankICIR | RankIC>0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | — | — | — | — | — | — | — |
| 5 | — | — | — | — | — | — | — |
| 10 | — | — | — | — | — | — | — |
| 20 | — | — | — | — | — | — | — |
| 40 | — | — | — | — | — | — | — |
| 60 | — | — | — | — | — | — | — |



### normalization: winsorized_zscore (missing: sector_median)

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

- declared direction `neutral` is the economic intuition; the empirical sign is reported per period above and is never used to flip the factor.
- coverage limits follow the underlying data (see the financial coverage report for financial factors).
- long-short is gross of transaction costs.