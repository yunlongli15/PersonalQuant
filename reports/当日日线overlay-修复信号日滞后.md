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

## 六之二、2026-10-13：用户跑 refresh_all 报错，暴露了两个 bug

用户的失败记录（`data/quant/jobs.db`，18:12:59）：

```
market_update FAILED  (103s)
RuntimeError: 快照下载连续 3 次失败（最后一次：
  URLError: <urlopen error [WinError 10060] ...>）
```

重试与断点续传**都触发了**（日志里"5s 后从断点重试 1/2""2/2"），
但 GitHub 那 100 秒就是连不上。31 分钟后我重跑，同一份 568 MB 包一次过。

### Bug A（严重）：快照下载失败会打断整条链

`market_update` 抛错 → `run_all` 抛错 → **后面 10 个作业一个都没跑**。
于是走**另一家主机**的 `overlay_refresh` 根本没机会执行 ——
而它本来完全可以把 10-13 的日线补齐。用户当晚一份建议都拿不到。

这跟"当日数据取不到就别发信号"不矛盾：那一条由
`signals.assert_signal_date_is_backed` **独立**把关。

修法：给"没拿到文件"一个独立退出码（3）和独立异常类型
（`SnapshotUnavailable` → `DegradableJobError`）。这类失败**没有改动
任何数据**，所以记 FAILED、**继续跑**，整条链退出码仍是 1。
反过来，**拿到文件之后**才失败的（解压/导入坏档）照旧中断整条链 ——
那时本地状态可能已经半截，继续跑就是在污染信号。

### Bug B（更危险，且是静默的）：锚点取错

原实现锚在 **canonical 的最新日期**上。用户那种情形下
canonical 停在 10-09、overlay 已经有 10-12，而桥要算的是
`close(10-13)/prev(10-12)` —— 一天的收益，却被乘到了
**10-09 的复权价**上。**10-09 → 10-12 那两天的收益凭空消失**，
写出一根假 bar。

**而且复权连续性校验抓不到它**：`factor` 的定义就是"让复权序列连续的
那个值"，所以 (`close×factor`) 与锚点的比值**恒等于** `1+r`，天然通过。

修法：锚点取「**模型手里**最新的一根 bar」（canonical ∪ overlay），
并要求它**恰好等于 T 的前一个交易日**；中间缺了交易日就拒绝，并给出
可执行的下一步。顺带修了 `--force` 重建时锚点横截面取在错误日期的问题。

### 验证

- 重建 10-13（`--force`）：与原来的 10-13 **价格逐位相同**，
  factor/volume 差异在 float32 噪声内（1e-7）。
- 上游快照追上 10-12 后的对账：
  `close 中位相对差 3e-08，factor 中位比 1.0，volume 中位比 1.0`。

**最后一行是这套桥接最硬的一次验证**：它是把我自己拼的 bar 与
厂商权威数据逐字段比对，价格对到 7 位有效数字，而且**成交量口径也
对上了** —— 那个 `C(sym) = median(factor)/scale_volume` 的推导，
连同"factor 与 volume 耦合"的判断，是被独立数据源确认过的，不是自说自话。

---

## 六之三、冻结实验的数据源切换记录（§七）

`daily_exit_paper_clean_v1` 的观测从 **2026-10-13** 起由
`canonical+overlay` 产出。这一笔**补记在这里**，因为当时引擎还没有
"首次记录来源"的事件类型（第一笔没有可比较的前值），账本里不会有一条
独立的 `DATA_SOURCE_CHANGED`。

`experiments/daily_exit_paper_clean_v1/state.json` 与 10-13 那笔
`RUN_SUMMARY` 里都写着：

```json
"data_source": {
  "as_of": "2026-10-13",
  "bar_source": "canonical+overlay",
  "overlay_sessions": ["2026-10-13"],
  "overlay_bars_sha256": "74806c90d2cff2c86360bf5fe5e4fe66895856b8b6ddc1d245239cdb2164db98",
  "strategy": "production_clean_v1"
}
```

**实验规则一条都没改**：出场规则、仓位、成本、股票池、time_stop 全部照旧。
变的只是 T 日 bar 从哪来 —— 以前是"上游快照里没有 T，所以 T 日没有数据"，
现在是"由当日 overlay 补上"。模型、特征集、信号口径不变。

已补上 `DATA_SOURCE_FIRST_RECORDED` 事件类型：对**在"记录来源"之前就
已经在跑**的实验，第一笔记下来时写一条事件，明确说明"此前的观测没有
来源记录"，而不是沉默地开始记录。它**不会**谎称"来源变了"—— 之前是
什么没人知道。对 10-13 之后的任何一次真实切换，`DATA_SOURCE_CHANGED`
都会照常落账本。

---

## 六之四、2026-10-14：接第二个行情源，逼出一个我自己的单位 bug

用户要求给当日行情加备用源（腾讯一家挂了当晚就没有排名）。接新浪时，
两个源在 621 只标的上成交量差 **100 倍** —— 顺着查下去，发现是**我自己
的腾讯解析器**错了。

### 定位

两条独立线索指向同一个结论：

1. **按板块统计** `新浪量 / 腾讯(手×100)`：所有板块都是 1.00，
   **只有 688/689 是 0.01**。
2. **用成交额反推股数**（成交额 ÷ 收盘价）。两个源对 688001.SH 的成交额
   **完全一致**（6.494e8 元，比值 1.000000）：

   | 688001.SH（close 55.30） | 值 |
   |---|---|
   | 成交额 ÷ 收盘价 ≈ 真实股数 | 1.17e7 |
   | 新浪 | 12,123,933 ✓ |
   | 腾讯字段 6 | 12,123,933 —— **本来就是股** |
   | 我的代码 `f6 × 100` | 1.21e9 ✗ 差两个数量级 |

**腾讯的成交量字段：科创板报股，其余板块报手。** 我从 10-12 起一直统一
乘 100，于是 617 只科创板标的的 volume 大了 100 倍。

### 影响（已量化）

- 受影响的交易日：**10-12 与 10-13**（overlay 层建出来的那两天）。
- 10-13 信号重算对比：预测相关 0.9949，排序 spearman 0.9778，
  **Top-20 只换了 1 只** —— 科创板 `688717.SH` 进入，主板 `600210.SH` 退到 21。
- **对交易计划影响为零**：688717.SH 是科创板，需要 50 万日均资产，
  本账户 6.6 万 → `can_buy=False`，在计划里会被门槛过滤掉；
  而 `600210.SH` 退到第 21 名仍然在候选池里（`plan.py:293` 用的是
  **全量排序表**，不是 top-N 切片），照常入选。
- 因此 `daily_exit_paper_clean_v1` 在 10-13 的观测**不需要改**，
  也没有改 —— 冻结实验的账本一字未动。

**没有覆盖已落盘的 10-13 信号**：实验的账本是照着它做的，改掉信号
只会让账本与 parquet 对不上，而实际决策没变。已重建 overlay（10-13
的 `daily_bars` 现在是正确的），10-14 起用修好的解析器。

### 两个源的等价性（修完之后实测）

同一场 session（10-13）分别用腾讯、新浪各建一遍，逐位比：

| 字段 | 结果 |
|---|---|
| open / high / low / close | 99.9% 完全相同，最大相对差 **9.4e-07**（远小于一个最小报价单位）|
| factor | 比值 1.00000000 |
| volume / amount / vwap | 比值中位 1.00000000，p01–p99 在 5e-5 内 |
| 覆盖 | 两边都 5,566 只，只在一方出现的 **0** |

**唯一剩下的 100 倍离群是 4 个指数伪标的**（000300/000852/000905/000906.SH）。
指数没有"股数"，没有"正确的单位"可归一，而它们本来就被
`config index_exclude` 挡在因子股票池之外，永远进不了模型。

### 新浪接入后新增的两道防护

1. **跨 session 残留**：新浪会一直供应**退市股最后一次成交**的快照。
   实测 000004.SZ 国华退 的戳是 `20260713`，四个价格全非零、成交量正常
   —— 它能原样通过"是不是停牌"的检查（停牌股是 OHLC 全 0），然后以
   七月的价格被写成当天的 bar。现在按"行情自称的 session"过滤，
   实测丢掉 3 只（000004.SZ / 000638.SZ / 002231.SZ）。
2. **量化单位为真实单位**：出口统一成 **股 / 元**，把 `手`、`万元` 的
   换算收在解析器里。以前那个约定（`volume_lots` / `amount_wan`）正是
   上面这个 bug 的温床 —— 单位藏在字段名里，谁忘了乘就错 100 倍。
   旧快照的读取做了兼容（`recover_C_from_snapshots` 两种字段都认）。

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
