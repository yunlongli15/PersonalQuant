# strategy_v1 — first low-frequency alpha strategy

- 月度调仓（每月最后一个交易日收盘生成信号），T+1 开盘执行
- 全 A 股动态股票池（上市 180 日 + 停牌 + 粗流动性过滤；ST 过滤仅 paper live）
- 特征：Qlib 官方 Alpha158（经 canonical 数据 custom provider，单一事实来源）
- 标签：未来 20 个交易日调整后收益（严格 future-only）
- 模型：LightGBM（参数固定于 config/strategy_v1.yaml，禁止暗中调参）
- 组合：Top 20 等权 + 5% 现金缓冲；A 股 100 股手数；保守成本模型
- 训练 2015–2021 / 验证 2022–2023 / 测试 2024–2025 / 2026 paper live
- Walk-forward：季度重训 + 月调仓（training_frequency 可配置）

代码位于 personal_quant/strategy/（引擎与模型为所有 strategy 共用），
本目录保留策略级入口与版本记录；实验输出在 experiments/strategy_v1/run_XXX/。
