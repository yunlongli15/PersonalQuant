# STEP 4 市场数据质量审计与修复（volume/amount 缩放）

生成：2026-09-08（审计脚本 scripts/audit_market_data.py，
自动结果 data/derived/audit/market_continuity.json；
测试 tests/data/test_market_data_continuity.py）

## 1. 背景问题

STEP 3 已发现 canonical daily_bars 的 volume/amount 存在**每股不同的源侧缩放**
（Yahoo 调整伪影），跨股票不可比（strategy_v1 的流动性过滤因此只能做粗过滤）。
STEP 4 的因子研究（amount_20/60、turnover 等流动性因子）要求跨股票可比，
因此先做统一审计 + 修复。

## 2. 审计结果（2015-01-01 ~ 2026-09-04，11,617,007 行）

### 2.1 复权因子连续性 —— 修复 v1 已生效

- 虚假因子跳变（factor/prev>2 且价格变动<15%）：**0 起**（STEP 3 的
  repair_factors.py 修复 22,906 行后保持为 0）。
- 真实公司行为的因子变动（送转等）：1,020 起 ±100%（正常，保留）。

### 2.2 逐日跳变普查（|比值-1| > 100%/200%/500%）

| 字段 | >100% | >200% | >500% |
| --- | --- | --- | --- |
| close | 7 | 4 | 0 |
| volume | 672,863 | 199,208 | 36,755 |
| amount | 708,229 | 216,503 | 40,177 |
| vwap | 8 | 5 | 0 |
| factor | 1,020 | 120 | 0 |

volume/amount 的大幅单日跳变主要是真实交易动态（消息日/换手率剧变），
与因子变动几乎不同期（3× 持续跳变中仅 0.5% 伴随因子变化），
**不能**用"跳变"作为缩放伪影的判据。

### 2.3 核心结论：k = amount/(close×volume) 的每股结构

- **组内稳定性极高**：每股 k 的组内 CV 中位数 0.11，100% 股票 CV<1 ——
  volume 与 amount 共享同一个每股常数缩放，且该常数在时间上稳定。
- **跨股不可比**：每股 k 中位数分布 0.0006（p01）~ 0.14（p99），
  跨度约 230×；log10 直方图近似单峰连续分布（峰值约 0.01），
  **不是**干净的单位档位（如手/股/万股）。
- 实例核对（2026-09-04）：贵州茅台 canonical volume 186,736 vs 真实约
  3,300 万股（×0.0057）；amount 6.0e6 vs 真实约 5.5e8 元（×0.011）。
  平安/招行/宁德/万科等比例各不相同。

即：**volume 与 amount 各自（共同）携带每股常数 s∈约[0.005, 0.3]，
price/factor 不受影响**（STEP 2 已与腾讯价格交叉验证一致）。

## 3. 修复管线（raw → detection → repair → validation）

`scripts/calibrate_market_scale.py`（可断点续跑，raw 响应缓存于
data/raw/akshare/kline_cal/<code>.json）：

1. **detection**：离线审计（上文）确立"每股常数缩放"结构；
2. **ground truth**：逐股拉取腾讯 K 线（单连接、1-3s 礼貌延迟；
   东财 push2his 当下被 WAF 封禁 → 自动降级，成交量来自腾讯，
   成交额由 成交量×close 推算并记录——东财可用时以真实成交额校准并
   交叉验证推算误差）；
3. **repair**：重叠窗口内 gt/canonical 比值的中位数 = 每股乘数
   scale_volume（volume×scale=股数）。**canonical 原始列不修改**
   （strategy_v1 位级不变）；产出 data/parquet/market/market_scale.parquet
   （symbol / scale_volume / scale_amount / ratio_median / ratio_cv /
   n_overlap / window / source / method / reason / repair_version=1.0），
   并在 source_registry 注册 market_scale_repair_v1；
4. **validation**：比值稳定性检查（ratio_cv<0.3 为常数模型成立；
   实测绝大多数 <0.03）；当东财可达时以真实成交额验证
   "成交量×close"推算误差（中位数约 1-2%）。

因子引擎消费：`amount_cny = amount×scale_amount`（东财校准股）或
`volume_shares×close`（推算）；`volume_shares = volume×scale_volume`；
无校准的股票 scale=1 并记录。因子研究股票池的流动性过滤改用
amount_cny ≥ 500 万元/日（config/factor_research.yaml）。

## 4. 已知限制（如实记录）

- 校准窗口为最近 640 个交易日；历史区间沿用同一乘数（组内 CV 极小，
  常数模型成立），个别历史缩放阶跃事件未单独分段（审计记录了
  265,585 起 3× 滚动均值变化，绝大多数为真实流动性机制变化）。
- 东财被 WAF 封禁期间：turnover（换手率）全市场序列不可得 →
  turnover_20/60 因子只覆盖财务股票池（用年报披露股本推算），
  全市场换手率留待东财恢复或引入其它源（数据源决策见 docs/data_sources.md）。
- strategy_v1 保持冻结：其流动性过滤仍用源单位 amount（已知限制，
  已记录于 config/strategy_v1.yaml 的 caveat）。
- 2026-09-04 校准进度：全市场逐股校准约 3 小时（单连接礼貌限速）。
