# 当日日线 overlay —— 修复"信号日永远慢一天"

日期：2026-10-12
起因：用户两次反馈（2026-09-22、2026-10-12）——"今天 12 号是交易日啊，
今天的 market 数据应该有了才对，不然我怎么预测明天买什么"。

---

## 一、根因与原始调用链

### 现象

T 日（2026-10-12）收盘后跑 `refresh_all.py`，交易计划里的**价格是 T 日的，
排序却是 T-1 日的**。报告自己写着：

> 排序基于 2026-10-09，价格基于 2026-10-12；上游快照尚未发布 2026-10-12
> 的完整数据，因此排序比价格旧一个交易日。

对 20 个交易日预测周期的策略，这是约 5% 的时滞。

### 原始调用链（逐行核对，不是按文件名猜的）

```
refresh_all.py
 └─ pipeline/refresh.py :: run_all(REFRESH_JOBS)
     ├─ market_update ─→ scripts/quant/update_market_snapshot.py
     │     下载 chenditc/investment_data 最新 release → 换 qlib_data/
     │     → personal_quant/ingest/qlib_baseline.py :: ingest_daily_bars()
     │     → data/parquet/daily/bars_<year>.parquet
     │
     ├─ factor_refresh ─→ scripts/factor_prepare.py
     │     db.trading_calendar → data/derived/factors/calendar.parquet
     │
     ├─ signal_refresh ─→ pipeline/signals.py :: refresh_signals()
     │     signal_date 默认 = pipeline/freshness.py :: last_trading_day()
     │       └─ trading_calendar() 读 derived/factors/calendar.parquet
     │     └─ compute_signals(signal_date)
     │          ├─ build_universe(d)         ← DuckDB 的 daily_bars 视图
     │          └─ compute_features(...)     ← personal_quant/strategy/features.py
     │               └─ 每季度子进程 worker
     │                    └─ init_qlib_with_canonical()
     │                         └─ CanonicalFeatureProvider._load_raw()
     │                              ← pyarrow 直读 data/parquet/daily/*.parquet
     │                              ← 价格按 raw × factor 供给 Alpha158
     │
     ├─ live_price_refresh ─→ scripts/quant/refresh_live_prices.py
     │     逐只抓候选股当日收盘价 → data/quant/live_prices.json
     │     （只覆盖"价格"，不碰"排序"）
     └─ portfolio_refresh ─→ trade_plan 生成计划
```

### 真正的卡点

三个独立的日期闸门，**全都锁在 T-1**：

1. **数据**：上游 release 含 T 的包要到次日约 00:40 CST 才发布。
   2026-10-12 20:37 实测：release tag 是 `2026-10-11`，
   但 manifest 的 `target_trade_date` = `2026-10-09`。
   逐字节验证过 pack 里确实没有 T：`close.day.bin` = 25,940 字节
   = 6,485 个 float32，与日历的 6,485 天严丝合缝。

2. **日历**：`qlib_data/calendars/day.txt` 与 `db.trading_calendar` 都止于 T-1，
   所以 `last_trading_day()` 返回 T-1。

3. **特征**：Alpha158 的 handler 把时间区间换算成**日历下标**，
   日历里没有 T 就根本不会产出 T 那一行 —— 就算数据到位也一样。

`live_price_refresh` 之所以补不上，是因为它只抓 **60 只候选股的价格**，
而排序要的是**全市场横截面**（Alpha158 是横截面的，`build_universe`
的流动性门槛也要全市场 20 日均额）。逐只抓全市场按项目规定的单连接
速率实测 0.48 秒/只 → **45 分钟以上**，不可行。

---

## 二、修改文件与设计理由

### 新增

| 文件 | 作用 |
|---|---|
| `personal_quant/providers/batch_quote.py` | 全市场**批量**行情 provider（腾讯 `qt.gtimg.cn`），约 15 秒取完整市场 |
| `scripts/quant/update_daily_overlay.py` | 当日 bar 的桥接、校验、落盘、对账 |
| `tests/market_data/test_daily_overlay.py` | 22 条（桥接代数、拒绝条件、幂等、对账） |
| `tests/market_data/test_overlay_merged_view.py` | 视图/日历/信号闸门/无未来数据 |

### 修改

| 文件 | 改动 | 理由 |
|---|---|---|
| `personal_quant/db.py` | `daily_bars` 视图 = canonical ∪ overlay（overlay 优先） | 一处合并，**所有** `daily_bars` 读者（特征、标签、股票池）自动跟上 |
| `personal_quant/strategy/qlib_provider.py` | `_load_raw` 并入 overlay；新增 `CanonicalCalendarProvider` | 特征 provider 不走 DuckDB，得单独并；日历要加 T，否则 handler 不产 T 行 |
| `pipeline/freshness.py` | `market_latest` 含 overlay；`trading_calendar` 并入 overlay 日期 | 否则面板会一边显示"市场落后一天"、一边排名已经用上 T |
| `pipeline/refresh.py` | 新作业 `overlay_refresh`，排在 `factor_refresh` **之前** | `factor_refresh` 用 `trading_calendar` 重建 derived 日历，T 要一起带出去 |
| `pipeline/signals.py` | `assert_signal_date_is_backed()`；信号元数据记录数据来源 | §四 的**独立**第二道闸：即使 overlay 被跳过也不许拿旧排名冒充新信号 |
| `personal_quant/ingest/qlib_baseline.py` | `ingest_calendar()` 保留 overlay 的日期 | 它是 DELETE + INSERT，换快照会把 overlay 登记的日子抹掉 |
| `daily_exit_paper/engine.py` | 实验 state / 账本记录信号来源，来源变了记 `DATA_SOURCE_CHANGED` | §七：不得在同一实验名下**无痕**切换数据源 |
| `scripts/quant/update_daily_overlay.py` | `reconcile()` | §五：上游追上后先对账、再交还权威 |

### 为什么是 overlay 而不是改 canonical

§三 要求"优先实现经过校验的当日日线 overlay / merged feature view，
不要无必要地重写全部历史数据"。所以：

- **canonical 原文件一个字节都没动**（有测试断言 `bars_2026.parquet`
  的最大日期仍 < overlay 的日期）；
- 合并只发生在**视图层**；
- **回滚 = 删掉 `data/parquet/overlay/` 目录**，系统立刻回到原状。

---

## 三、新数据源实测（2026-10-12 20:37–21:00 CST，收盘后）

### 候选源可达性

| 源 | 批量能力 | 全市场耗时 | 结论 |
|---|---|---|---|
| **`qt.gtimg.cn`** | **900 只/请求** | **14.5 秒 / 12 次请求** | **采用** |
| `hq.sinajs.cn` | 800 只/请求 | 约 3 秒 | 交叉核对 |
| `push2.eastmoney.com` | 不定 | — | ❌ 20:39 起连 `pz=5` 都直接断连（20:36 还能用）|
| `push2his` / 腾讯 `fqkline` | 逐只 | >45 分钟 | ❌ 且约 200 次请求后限流 |

东财的表现与 `docs/数据来源与口径.md` 记录的"WAF 间歇封禁、直接断连"
完全一致，**不能作为依赖**。逐只抓取被 §二.1 明确排除。

### 字段口径（全部实测核对，不照文档假设）

- `close/open/high/low`：原始价（元），0.01 档。
  **2026-10-09 对 229 只抽样与 canonical 逐位比较：中位相对差 3.1e-8，
  最大 0.0。**
- `prev`：**除权除息日是交易所的除权除息参考价**，不是昨收。
  5,564 只里 15 只如此，全部命中当日公司行为，且股票简称带 `XD`/`DR`
  前缀。例：688110.SH canonical T-1 收盘 104.38、参考价 69.65，
  比值 1.4986 = 10 送 5。
  → 所以 `close/prev − 1` **本身就是复权后的真实收益**，不用另查公司行为表。
- `volume`：单位**手**；`amount`：单位**万元**。

### 覆盖率与失败处理

2026-10-12 实测：**5,564 / 5,564 = 100%**，12 次请求，0 失败。

拒绝条件（任一不过 → **当天一条都不发布**）：

| 条件 | 阈值 |
|---|---|
| 成交标的数 | ≥ 1,000 |
| 覆盖率 | ≥ 90% |
| symbol 重复 | 必须无 |
| `factor` | 必须 > 0 |
| OHLC 几何 | `low ≤ open,close ≤ high` |
| 复权序列连续性 | 漂移 ≤ 1e-6 |
| 行情自称的 session | 必须 == 目标日 |
| 收盘确认 | 行情最新时间戳 ≥ 15:00（否则是盘中的半截 bar）|
| 周末 | 直接拒绝 |

---

## 四、复权与跨源一致性验证

### 价格桥（canonical 存原始价 + factor，模型吃 `raw × factor`）

```
A(T-1) = close_canonical(T-1) × factor_canonical(T-1)
r      = close_live / prev_live − 1
A(T)   = A(T-1) × (1 + r)
factor(T) = A(T) / close_live          # open/high/low/close/vwap 原样透传
```

2026-10-12 结果：**复权收益分布中位 −1.68%、标准差 2.9%**，
超出 ±11% 的 23 只**全部**是 300/301 开头（创业板 20% 涨跌幅），
两只正好打在 ±20.00%。边界行为与真实涨跌幅制度一致。

### 成交量桥（本次最不显然的一处）

canonical 的 volume **不是股数**，而且**与复权因子耦合**：

```
canonical_volume(t) = C(sym) × 真实股数(t) / factor(t)
```

`C` 才是那只股票的常数。实测 600519.SH 183 个交易日：2026-06-26 除息时
`factor` 涨 2.3667%，volume 比率**恰好跌 1/1.023667** —— 六位有效数字吻合。

**因此不能直接用 `market_scale.scale_volume`**：它是窗口内 `factor/C` 的
中位数，跨了多个除权平台。离线实测按它还原的误差：

| 分位 | 误差 |
|---|---|
| 中位 | 1.1% |
| p90 | 20.3% |
| 最大 | 207% |
| > 5% 的标的 | **21%** |

正确做法是还原 `C`：

```
C(sym) = median_窗口(factor) / scale_volume(sym)
canonical_volume(T) = C(sym) × 真实股数(T) / factor(T)
```

**逐位验证**（以腾讯 K 线真实股数为 ground truth）：

| 标的 | 实测 C | 公式还原 C | 相对误差 |
|---|---|---|---|
| 600519.SH | 0.00999998 | 0.00999990 | 0.0008% |
| 000002.SZ | 0.01000000 | 0.01000000 | 0.0000% |
| 688110.SH | 0.00010000 | 0.00010000 | 0.0000% |

`amount` 同理：`canonical_amount ≈ U(sym) × canonical_volume ×
canonical_vwap`（实测每股常数，CV 约 0.008）。Alpha158 **不读 `$amount`**
（已对 `Alpha158DL.get_feature_config` 核验：只用
`$open/$high/$low/$close/$volume/$vwap`），但 `build_universe` 的流动性
门槛用的是它 20 日均值，所以照写；一天近似对 20 日均值的影响约 0.05%。

### 未覆盖标的

362 只（2026-10-12；其中 286 只是北交所）不在标定表里（该表标定窗口
止于 2026-09-04，这些是新上市标的）。处理：

- **价格照常精确**（只依赖 quote + T-1 的 factor）；
- **volume/amount 写 NaN**，并在 manifest 里列出。

宁缺毋假：写一个猜的缩放会污染 VMA/VSTD/VSUM；NaN 是模型本来就当作
"未知"的东西。**从第二个交易日起自动恢复**：前一天的原始快照
（`data/raw/batch_quote/`，每次运行都会落盘）能把这支股票的 `C` 精确补上
（`recover_C_from_snapshots()`）。

---

## 五、端到端验收

### 2026-10-12 收盘后实测

```
$ python scripts/quant/update_daily_overlay.py
canonical 最新: 2026-10-09
overlay  最新: —
T-1 = 2026-10-09，锚定 5564 个标的
批量行情: 5564 只 / 12 次请求；行情自称 session = 2026-10-12（最新戳 20261012161500）
桥接: 5564 根 bar，覆盖率 100.0%；除权除息 14，停牌 0，无锚点 0
已写入 data/parquet/overlay/daily_overlay.parquet

$ python scripts/quant/refresh_all.py --only signal_refresh
[features] 2026-10-01..2026-10-12: 2860 instruments in 287s (kernels=10, WROTE 1)
[1/1] signal_refresh -> SUCCESS (293s)
  {'as_of': '2026-10-12', 'n_symbols': 2860, 'latest_bar': '2026-10-12'}

$ python scripts/quant/refresh_all.py --only overlay_refresh,factor_refresh,forecast_refresh,portfolio_refresh
[1/4] overlay_refresh -> SUCCESS (20s)
[2/4] factor_refresh  -> SUCCESS (30s)   bars 2017-01-03..2026-10-12
[3/4] forecast_refresh -> SUCCESS (1s)   as_of 2026-10-12
[4/4] portfolio_refresh -> SUCCESS (5s)  信号日 2026-10-12；买入 7 只 / 40,132 元

| domain | latest | expected | status |
| Market Data | 2026-10-12 | 2026-10-12 | ✓ |
| Forecast    | 2026-10-12 | 2026-10-12 | ✓ |
| Portfolio   | 2026-10-12 | 2026-10-12 | ✓ |
```

### 各日期闸门（§四 要求"都应是同一个最近完整交易日 T"）

| 项 | 值 |
|---|---|
| 行情日 / 特征截止日 | **2026-10-12** |
| 信号日 `as_of` | **2026-10-12** |
| 预测日（forecast as_of） | **2026-10-12** |
| 组合 / 交易计划 as_of | **2026-10-12** |
| 计划里的 `price_source` | `canonical, same date as the signal` |
| 建议执行日 | **下一交易日（T+1）** |

**报告里的错位说明已经消失。** 修复前 `reports/paper_live/recommendation_2026-10-09.md`
写着"排序基于 2026-10-09，价格基于 2026-10-12"；现在的
`recommendation_2026-10-12.md` 只有一行"基准信号日 2026-10-12"。

### T+1 语义未变（`run_daily_exit_paper.py --dry-run`，只读）

```
PENDING ENTRIES
  603950.SH 长源东谷  200 股  限价 45.010  信号日 2026-10-12  执行日 下一交易日
PREFLIGHT CHECKS
  data_freshness  PASS  行情 2026-10-12；信号快照与行情同日
  calendar        PASS  2026-10-12 是已观测交易日；下一交易日尚未观测到（正常）
  feature_date    PASS  2026-10-12: HIT
  strategy_signal PASS  signal_date == market_data_last_date == 2026-10-12
```

dry-run **未写账本、未建订单、未改状态** —— 冻结实验的历史观测没有被改动。

### 信号确实变了（不是把 T-1 换个日期）

| 指标 | T=10-12 vs T-1=10-09 |
|---|---|
| 预测值相关系数 | 0.515 |
| 排序 Spearman 相关 | 0.607 |
| Top-50 重合 | 22 / 50 |
| 标的数 | 2,860（vs 2,965）|

标的数变化来自流动性门槛的 20 日窗口整体前移一天，其中 103/106
是跌破门槛被正常剔除（已逐只核对，**与 overlay 的 volume NaN 无关**）。

---

## 六、测试

**全量：`1378 passed, 1 skipped, 0 failed`（256 秒）。**

新增 33 条，全部在 `tests/market_data/`：

| 文件 | 条数 | 覆盖 |
|---|---|---|
| `test_daily_overlay.py` | 22 | 桥接代数（复权连续性、除权参考价、volume 耦合口径）、拒绝条件（OHLC 几何、覆盖率、重复 symbol、非正 factor、盘中/周末/跨 session）、幂等写、对账退场、C 的恢复 |
| `test_overlay_merged_view.py` | 11 | 视图两条路径、日历、信号闸门、无未来数据、历史不被污染、盯住"删 overlay 就能回滚" |

逐目录（全部通过）：daily 85 · daily_exit_paper 121 · factors 153 ·
forward 127 · gui 97 · market_data 55 · news 131 · news_factors 23 ·
pipeline 77 · portfolio 98 · portfolio_account 97 · strategy 71 ·
trade_plan 26 · wealth 74 · webapp 63 · production 16 · quant 6 ·
根目录 58。

**未通过 → 已修**：`tests/pipeline/test_data_freshness.py::test_market_stale_when_behind`。
它用 fixture 造了一棵 2026-09-10 截止的假数据树，而
`trading_calendar()` 当时会把**真实** overlay 的 2026-10-12 并进这棵假日历，
把"日历滞后"判据顶掉。**这是实现的缺陷，不是测试的问题**：改数据根的调用方
应该拿到一致的视图。现在 overlay 从 `PARQUET/overlay/` 读（跟着同一个数据根走），
并且显式传 `calendar_path` 时不再并入。断言一行未改。

### 性能（这里踩了一个坑，值得记下来）

`daily_bars` 是**每个读者都要经过**的视图，所以它的代价会被放大。
实测回测里最热的那条取价查询（`backtest.py::_px`，按 symbol 取最近一根 bar）：

| 视图形态 | `_px` 耗时 |
|---|---|
| 纯 canonical（改动前） | 0.039 s |
| **第一版**：overlay 用 `read_parquet()` 挂在视图里 + 反连接 | **0.342 s（8.8×）** |
| 第二版：overlay 物化成 `CREATE TABLE` + 反连接 | 0.342 s |
| **第三版（最终）**：无重叠时走朴素 `UNION ALL` | **0.033 s** |

反连接才是瓶颈，不是读文件：它要对每一行求值，而 DuckDB 没法把
`symbol IN (...)` 下推到 NOT EXISTS 里面。而**正常状态下这个连接一
行都匹配不上**（上游滞后，canonical 根本没有 overlay 那些交易日）。

所以现在在**建视图时**先查一次有没有 (symbol, trade_date) 重叠：

- **没有**（正常）→ `UNION ALL`，零额外成本，比改动前还快一点点；
- **有**（快照刚追上，overlay 还没退场）→ 用反连接保证 overlay 优先，
  并在下一次 `overlay_refresh` 的对账里退场。

两条路径都有测试钉住（`test_view_uses_the_cheap_union_when_nothing_collides`
/ `test_view_still_deduplicates_when_a_session_collides`）。

效果：`tests/strategy` 从"5 分钟跑不完 2 条"回到 **71 passed / 62 秒**。

---

## 七、未解决 / 已知限制

1. **362 只标的当日 volume/amount 为 NaN**（2026-10-12 的实况，绝大多数是
   北交所新股，标定表没覆盖）。价格精确、bar 保留，只有成交量派生的
   ~25 个特征在这**一天**为 NaN。第二个交易日起由前一天的原始快照自动补齐。
   要彻底消除，需要把 `scripts/calibrate_market_scale.py` 的标定范围扩到
   北交所（它需要逐只取腾讯 K 线，约 286 次请求）。

2. **`amount` 是近似量**。Alpha158 不读 `$amount`，但 `build_universe`
   的流动性门槛读它。每股常数 `U` 的实测 CV 约 0.008，一天的量对 20 日均值
   的影响约 0.05%。

3. **当日行情源只有腾讯一家**。东财 push2 当天实测全封。腾讯 `qt.gtimg.cn`
   如果也挂掉，当日 overlay 就没有来源 —— 这时系统**如实失败**，不会退回 T-1。
   换源或加备用源是后续可以做的事（新浪 `hq.sinajs.cn` 实测也支持批量，
   但字段更少、没有印证过复权口径）。

4. **`ingest_calendar()` 会重新并入 overlay 的交易日**，但
   `data/parquet/overlay/calendar_extra.parquet` 被手工删掉时，
   `db.trading_calendar` 里那条仍会留着（它已经是正式日历的一部分）。
   这是有意的：删 overlay 只回滚**当日 bar**，不追溯已登记的交易日。

---

## 八、回滚

```bash
# 完全回滚：删掉 overlay 层即可，canonical 原文件从未被改
rm -rf data/parquet/overlay
python -c "import sys;sys.path.insert(0,'.');import personal_quant.config;from personal_quant import db;db.refresh_daily_bars_view()"

# 只停用当日补齐，保留已有产物
python scripts/quant/refresh_all.py --only factor_refresh,signal_refresh,forecast_refresh,portfolio_refresh
```

`PIPELINE` 里去掉 `overlay_refresh` 也能停用；`signal_refresh` 的
`assert_signal_date_is_backed` 会如实报 `StaleSignalError`，**不会**
静默退回 T-1。
