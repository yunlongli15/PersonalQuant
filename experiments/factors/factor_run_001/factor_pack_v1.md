# factor_pack_v1

run: factor_run_001 · 2026-09-09T07:41:30

## selected (research+valid only)

- `amount_20` (liquidity, research rank-ICIR -0.448)
- `momentum_60` (momentum, research rank-ICIR -0.465)
- `price_vs_ma20` (price_position, research rank-ICIR -0.358)
- `reversal_20` (reversal, research rank-ICIR 0.517)
- `volatility_20` (volatility, research rank-ICIR -0.482)
- `volume_ratio_20_60` (volume, research rank-ICIR -0.480)
- `volume_ratio_5_20` (volume, research rank-ICIR -0.367)

## discarded

- `debt_to_asset`: |research rank-ICIR| 0.151 < 0.3
- `earnings_yield`: |research rank-ICIR| 0.089 < 0.3
- `gross_margin`: research IC +0.0726 vs valid IC -0.0100: sign flips
- `momentum_120`: |research rank-ICIR| 0.217 < 0.3
- `net_margin`: research IC +0.0509 vs valid IC -0.0123: sign flips
- `net_profit_growth`: |research rank-ICIR| 0.061 < 0.3
- `ocf_to_assets`: |research rank-ICIR| 0.228 < 0.3
- `ocf_to_net_profit`: |research rank-ICIR| 0.211 < 0.3
- `operating_cash_flow`: |research rank-ICIR| 0.078 < 0.3
- `pb`: coverage 0.04 < 0.2
- `pe`: |research rank-ICIR| 0.156 < 0.3
- `ps`: coverage 0.02 < 0.2
- `revenue_growth`: |research rank-ICIR| 0.190 < 0.3
- `reversal_5`: |research rank-ICIR| 0.195 < 0.3
- `roa`: |research rank-ICIR| 0.273 < 0.3
- `roe`: research IC +0.0853 vs valid IC -0.0525: sign flips
- `turnover_20`: coverage 0.02 < 0.2
- `turnover_60`: coverage 0.02 < 0.2
- `downside_volatility_60`: |corr| >= 0.8 with volatility_20 (cluster: downside_volatility_60, volatility_20, volatility_60)
- `volatility_60`: |corr| >= 0.8 with volatility_20 (cluster: downside_volatility_60, volatility_20, volatility_60)
- `price_vs_ma120`: |corr| >= 0.8 with momentum_60 (cluster: momentum_60, price_vs_ma120, price_vs_ma60)
- `price_vs_ma60`: |corr| >= 0.8 with momentum_60 (cluster: momentum_60, price_vs_ma120, price_vs_ma60)
- `amount_60`: |corr| >= 0.8 with amount_20 (cluster: amount_20, amount_60)
- `momentum_20`: |corr| >= 0.8 with reversal_20 (cluster: momentum_20, reversal_20)