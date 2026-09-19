# factor_pack_v1

run: micro_run_001 · 2026-09-19T14:50:32

## selected (research+valid only)

- `amount_20` (liquidity, research rank-ICIR -0.448)
- `limit_up_count_20` (microstructure, research rank-ICIR -0.906)
- `max_return_20` (microstructure, research rank-ICIR -0.610)
- `momentum_60` (momentum, research rank-ICIR -0.465)
- `price_vs_ma20` (price_position, research rank-ICIR -0.358)
- `reversal_20` (reversal, research rank-ICIR 0.517)
- `skewness_60` (microstructure, research rank-ICIR -0.502)
- `volume_price_corr_20` (volume, research rank-ICIR -0.513)
- `volume_ratio_20_60` (volume, research rank-ICIR -0.480)
- `volume_ratio_5_20` (volume, research rank-ICIR -0.367)
- `volume_trend_5_60` (volume, research rank-ICIR -0.543)

## discarded

- `amihud_20`: |research rank-ICIR| 0.283 < 0.3
- `amount_share_20`: |research rank-ICIR| 0.192 < 0.3
- `announcement_attention_5d`: coverage 0.20 < 0.6
- `announcement_count_20d`: coverage 0.40 < 0.6
- `announcement_count_5d`: coverage 0.40 < 0.6
- `buyback_event_count_20d`: coverage 0.40 < 0.6
- `debt_to_asset`: |research rank-ICIR| 0.151 < 0.3
- `earnings_event_count_60d`: coverage 0.40 < 0.6
- `earnings_yield`: |research rank-ICIR| 0.089 < 0.3
- `event_sentiment_shock`: coverage 0.40 < 0.6
- `event_shock`: coverage 0.01 < 0.6
- `gap_count_20`: |research rank-ICIR| 0.083 < 0.3
- `gross_margin`: research IC +0.0726 vs valid IC -0.0100: sign flips
- `high_52w_proximity`: |research rank-ICIR| 0.052 < 0.3
- `intraday_return_20`: |research rank-ICIR| 0.092 < 0.3
- `kurtosis_60`: |research rank-ICIR| 0.283 < 0.3
- `limit_down_count_20`: |research rank-ICIR| 0.241 < 0.3
- `llm_confidence_20d`: coverage 0.00 < 0.6
- `major_event_count_20d`: coverage 0.40 < 0.6
- `momentum_120`: |research rank-ICIR| 0.217 < 0.3
- `negative_news_count_5d`: coverage 0.40 < 0.6
- `net_margin`: research IC +0.0509 vs valid IC -0.0123: sign flips
- `net_profit_growth`: |research rank-ICIR| 0.061 < 0.3
- `news_attention_1d`: coverage 0.20 < 0.6
- `news_attention_20d`: coverage 0.20 < 0.6
- `news_attention_5d`: coverage 0.20 < 0.6
- `news_count_1d`: coverage 0.40 < 0.6
- `news_count_20d`: coverage 0.40 < 0.6
- `news_count_5d`: coverage 0.40 < 0.6
- `news_importance_5d`: coverage 0.40 < 0.6
- `news_novelty_5d`: coverage 0.40 < 0.6
- `news_positive_negative_ratio`: coverage 0.40 < 0.6
- `news_risk_20d`: coverage 0.40 < 0.6
- `news_sentiment_1d`: coverage 0.40 < 0.6
- `news_sentiment_20d`: coverage 0.40 < 0.6
- `news_sentiment_5d`: coverage 0.40 < 0.6
- `news_sentiment_weighted`: coverage 0.40 < 0.6
- `novel_news_count_5d`: coverage 0.40 < 0.6
- `ocf_to_assets`: |research rank-ICIR| 0.228 < 0.3
- `ocf_to_net_profit`: |research rank-ICIR| 0.211 < 0.3
- `operating_cash_flow`: |research rank-ICIR| 0.078 < 0.3
- `overnight_intraday_ratio_20`: |research rank-ICIR| 0.085 < 0.3
- `overnight_return_20`: |research rank-ICIR| 0.087 < 0.3
- `pb`: coverage 0.04 < 0.2
- `pe`: |research rank-ICIR| 0.156 < 0.3
- `positive_news_count_5d`: coverage 0.40 < 0.6
- `ps`: coverage 0.02 < 0.2
- `regulatory_event_count_20d`: coverage 0.40 < 0.6
- `revenue_growth`: |research rank-ICIR| 0.190 < 0.3
- `reversal_5`: |research rank-ICIR| 0.195 < 0.3
- `roa`: |research rank-ICIR| 0.273 < 0.3
- `roe`: research IC +0.0853 vs valid IC -0.0525: sign flips
- `shareholder_change_count_20d`: coverage 0.40 < 0.6
- `turnover_20`: coverage 0.02 < 0.2
- `turnover_60`: coverage 0.02 < 0.2
- `turnover_volatility_20`: coverage 0.00 < 0.6
- `downside_volatility_60`: |corr| >= 0.8 with max_return_20 (cluster: downside_volatility_60, max_return_20, parkinson_vol_20, volatility_20, volatility_60)
- `parkinson_vol_20`: |corr| >= 0.8 with max_return_20 (cluster: downside_volatility_60, max_return_20, parkinson_vol_20, volatility_20, volatility_60)
- `volatility_20`: |corr| >= 0.8 with max_return_20 (cluster: downside_volatility_60, max_return_20, parkinson_vol_20, volatility_20, volatility_60)
- `volatility_60`: |corr| >= 0.8 with max_return_20 (cluster: downside_volatility_60, max_return_20, parkinson_vol_20, volatility_20, volatility_60)
- `price_vs_ma120`: |corr| >= 0.8 with momentum_60 (cluster: momentum_60, price_vs_ma120, price_vs_ma60)
- `price_vs_ma60`: |corr| >= 0.8 with momentum_60 (cluster: momentum_60, price_vs_ma120, price_vs_ma60)
- `amount_60`: |corr| >= 0.8 with amount_20 (cluster: amount_20, amount_60)
- `momentum_20`: |corr| >= 0.8 with reversal_20 (cluster: momentum_20, reversal_20)