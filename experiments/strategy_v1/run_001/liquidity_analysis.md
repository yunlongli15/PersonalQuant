# Liquidity analysis (source amount field)

Caveat: canonical volume/amount carry per-stock source scaling
(Yahoo artifacts; verified vs Tencent raw volume: ratios 0.008-0.20
vary across stocks). Thresholds below are in SOURCE units and are
used only as a coarse filter.

| month-end | n stocks | P25 | P50 | P75 | P90 | kept>=1e6 |
| --- | --- | --- | --- | --- | --- | --- |
| 2024-01-31 | 5355 | 0.04M | 0.07M | 0.15M | 0.30M | 73 |
| 2024-02-29 | 5361 | 0.05M | 0.08M | 0.16M | 0.32M | 98 |
| 2024-03-29 | 5366 | 0.05M | 0.09M | 0.18M | 0.38M | 127 |
| 2024-04-30 | 5371 | 0.04M | 0.09M | 0.18M | 0.38M | 134 |
| 2024-05-31 | 5371 | 0.04M | 0.08M | 0.17M | 0.36M | 108 |
| 2024-06-28 | 5374 | 0.04M | 0.07M | 0.15M | 0.33M | 105 |
| 2024-07-31 | 5375 | 0.03M | 0.06M | 0.13M | 0.27M | 90 |
| 2024-08-30 | 5362 | 0.02M | 0.05M | 0.12M | 0.25M | 70 |
| 2024-09-30 | 5358 | 0.03M | 0.06M | 0.13M | 0.28M | 87 |
| 2024-10-31 | 5362 | 0.06M | 0.11M | 0.25M | 0.56M | 244 |
| 2024-11-29 | 5375 | 0.09M | 0.17M | 0.37M | 0.78M | 378 |
| 2024-12-31 | 5388 | 0.09M | 0.16M | 0.33M | 0.70M | 321 |

Decision: min_amount = 100,000 (source units) -> keeps ~1,800-1,900
stocks per month (>=1e6 would keep only ~95; >=1e5 keeps 1,867).
The threshold only removes names with negligible recorded activity.
A precise liquidity filter needs a clean turnover source (STEP 4).
