# daily_exit_paper_v1 —— 执行链专项审计

> **状态：PHASE 2（审计完成）｜PHASE 3-12（设计/实现/测试/试跑）未开始**
> 本文件是活文档：第 4-10 节在实现完成后补齐。
> 审计日期：2026-10-01 ｜ 审计方式：代码级（全部结论附 `文件:行号`），关键结论用真实数据实证。
> 设计文档：`reports/daily_exit_paper_v1_design.md`（PHASE 3）

---

## 0. 实验事实声明（必读）

**用户此前确实按照系统给出的选股建议进行过人工模拟交易，但这些交易没有经过
PersonalQuant 的 paper_live / ledger 系统持久化。**

```text
历史人工模拟交易
      ≠
当前 paper_live 数据库中的交易记录
```

由此确立三条纪律：

1. **不得反推**。不根据聊天记录、主观描述、账户余额或任何间接证据去重建
   过去的成交并写回数据库。系统里没有的成交，就是没有记录，不是"待补录"。
2. **不得误读**。本报告第 3.1 节的 `paper_live = 0 fills` **不等于**
   "用户以前从未进行过模拟交易"。准确表述是：
   > 当前 PersonalQuant paper_live 执行引擎没有成功结算成交；此前用户自行进行的
   > 人工模拟交易没有进入该系统的交易账本。两者是两个不同的数据集合。
3. **不得伪造**。`daily_exit_paper_v1` 从**零状态**开始建立账本，绝不预置任何
   "历史持仓"或"初始成交"来让曲线好看。

---

## 1. Executive Summary

**结论：现有系统的"信号层"是可信的，"执行层"是坏的。**

现有 paper-live（forward holdout 引擎）**从未真正交易过**，且它记录的每一条前瞻观测都存在口径问题。
这不是"策略表现不好"，而是**执行层从未跑通**——它记录的是预测，不是一个交易过的组合。

| 项目 | 结论 |
|---|---|
| strategy_v2 的**历史回测** | ✅ 未受影响（回测用完整区间生成调仓日） |
| strategy_v2 的**信号层**（S3 / 因子 / PIT） | ✅ 审计未发现前视泄漏（详见第 7 节） |
| **paper-live 执行层** | ❌ 3 个 CRITICAL bug，从未成交 |
| **forward holdout 记录** | ⚠️ 3 条观测全部口径失真（详见 3.1 / 3.4） |
| 成本核算 | ❌ 展示口径单边、记账口径双边，同一张表自相矛盾 |
| 目标价 / 止损 / 时间止损 | ❌ **完全是展示字段**，不进任何状态机；相关代码是死代码 |

**对 daily_exit_paper_v1 的直接含义**：新实验**不能**建立在现有 paper-live 执行层之上。
现有执行层缺少你需要的东西（限价成交、持仓状态机、target/stop 退出、非调仓日退出路径），
而它已有的那部分（挂单结算、调仓判定）是坏的。执行层要新写。

---

## 2. Current Execution Architecture

### 2.1 真实调用图（代码级，非 README）

```
scripts/quant/refresh_all.py
    └─ pipeline/refresh.py : run_all()
         ├─ market_update ─────► scripts/quant/update_market_snapshot.py
         │                          └─ personal_quant/ingest/qlib_baseline.py（重建 canonical）
         ├─ factor_rebase_repair ► scripts/quant/repair_factor_rebase.py
         ├─ news_update ────────► scripts/news/update_news.py（→ canonical news_documents）
         ├─ news_events_refresh ► scripts/news/build_events.py（→ 派生 news_events/news_coverage）
         ├─ valuation_update ───► personal_quant/ingest/market_online.py
         ├─ factor_refresh ─────► scripts/factor_prepare.py（→ derived/factors/*）
         ├─ signal_refresh ─────► pipeline/signals.py:refresh_signals
         │                          └─ compute_signals()
         │                               ├─ build_universe()            personal_quant/strategy/universe.py
         │                               ├─ compute_features(cache=False) personal_quant/strategy/features.py
         │                               ├─ load_factor_data(start, d)   factors/base.py
         │                               └─ AlphaModel.predict()         personal_quant/strategy/model.py（冻结模型）
         │                          └─ save_signals() ──► data/quant/signals_<d>.parquet
         ├─ live_price_refresh ─► scripts/quant/refresh_live_prices.py ──► data/quant/live_prices.json
         ├─ forecast_refresh ───► pipeline/forecast.py ──► data/quant/forecasts/
         └─ portfolio_refresh ──► scripts/quant/write_recommendation_note.py
                                    └─ trade_plan/plan.py:build_trade_plan()
                                         └─ save_plan() ──► data/quant/trade_plans/trade_plan_<d>.json
                                         └─ pipeline/signals.py:save_portfolio_state()

scripts/run_daily.py ──► pipeline/daily.py:run_daily()
    └─ task_paper_prediction ──► paper_live/engine.py:run_day()   ← 本次审计的核心
                                   ├─ _settle_pending()      （结算上一日挂单）
                                   ├─ LiveDataProvider       （paper_live/data.py）
                                   ├─ build_orders()         （paper_live/execution.py）
                                   ├─ execute_orders()       （paper_live/execution.py）
                                   │    └─ execute_order()   （personal_quant/strategy/execution.py）
                                   │         └─ TransactionCostModel（personal_quant/strategy/costs.py）
                                   └─ ForwardStore           （paper_live/store.py）→ forward_holdout/
```

### 2.2 执行时序链（T → T+1）

| 节点 | 由谁负责 | 实际行为 |
|---|---|---|
| **T 日收盘** | — | 数据截止 |
| **T 日收盘后：信号** | `pipeline/signals.py:compute_signals` | 用冻结模型打分全市场 |
| **T 日收盘后：下单计划** | `paper_live/execution.py:build_orders` | 按 T 日收盘价算目标股数 |
| **T+1 开盘：成交判定** | `personal_quant/strategy/execution.py:execute_order` | **市价成交**：只要不停牌、不涨停，**无条件按 T+1 开盘价全额成交** |
| **成交价** | 同上 `:98` | `open_price`（T+1 原始开盘价） |
| **费用** | `costs.py:_cost` | 买卖双边，滑点计入费用而非价格 |
| **持仓** | `paper_live/engine.py:PaperPortfolio` | **纯字典，无状态机**；平仓 = 删 key |
| **退出（target/stop/时间止损）** | **不存在** | 无任何代码读取这些字段 |
| **非调仓日** | `paper_live/engine.py:230-232, 239` | **不产生任何订单**（既不买也不卖） |
| **现金释放** | `paper_live/execution.py:179-181` | 先卖后买，卖出所得当次即可用于买入 |
| **下一轮** | `engine.py:164` 读 `state/paper_portfolio.json` | 现金/持仓跨日延续 |

---

## 3. Problems Found

### 3.1 🔴 CRITICAL-1：挂单永远不结算，paper-live 从未成交

**实证**：

```
forward_holdout/observations/
  2026-09-18  is_rebalance=True  n_orders=20  n_fills=0
  2026-09-24  is_rebalance=True  n_orders=20  n_fills=0
  2026-09-29  is_rebalance=True  n_orders=20  n_fills=0
forward_holdout/state/paper_portfolio.json → {"cash": 500000.0, "holdings": {}}
forward_holdout/trades/ → 空
```

**3 个调仓日、60 笔订单、0 笔成交，账户始终满额现金、空仓。**

**机制（两条路径，殊途同归）**：

1. **写入路径** [paper_live/engine.py:246-251](paper_live/engine.py#L246-L251)
   `exec_date = _next_trading_day(d, calendar)` —— 当晚流程刷新数据后 `d` 就是日历最后一天 → 返回 `None`
   → `_t1_has_data(..., None)` 命中 `if exec_date is None: return False`（[engine.py:380](paper_live/engine.py#L380)）
   → 写挂单，`execution_date: null`（[engine.py:264-269](paper_live/engine.py#L264-L269)）

2. **结算路径** [paper_live/engine.py:416](paper_live/engine.py#L416)
   `pd.Timestamp(pend["execution_date"])` 把 JSON 的 `null` 变成 **`NaT`（不是 `None`）** → 上面那个 `is None` 判断**不生效**
   → `provider.prices(syms, NaT)` 抛 DuckDB 类型转换异常 → 被 [engine.py:384-386](paper_live/engine.py#L384-L386) 的 `except Exception: return False` **吞掉**

3. **订单被静默丢弃**：下一次运行**无条件覆盖** `pending_orders.json`（[engine.py:263-269](paper_live/engine.py#L263-L269)），
   上一次的 20 笔订单**不留痕迹地消失**（`forward_holdout/state/state_log.jsonl` 可见 09-18 → 09-24 → 09-29 连续覆盖）

**为什么必然发生**：这套逻辑假设你"在 T+1 收盘后、T+2 之前"运行，
但你的每晚流程是 `refresh_all → run_daily` —— 刷新完数据后信号日**就是**数据最后一天，T+1 必然不存在。

**影响**：forward holdout 是 V1 唯一的样本外证据来源，而它**从未持有过任何头寸**。

---

### 3.2 🔴 CRITICAL-2：每一天都被判成调仓日

**代码** [paper_live/engine.py:97-106](paper_live/engine.py#L97-L106)：

```python
lo = (d - pd.Timedelta(days=70)).strftime("%Y-%m-%d")
dates = rebalance_dates(lo, d.strftime("%Y-%m-%d"), rb["frequency"], rb["rule"])
return bool(dates) and pd.Timestamp(dates[-1]) == d
```

`rebalance_dates` 取区间内**每个月最后一个交易日**，而这个区间的**右边界就是 `d` 自己** ——
`d` 永远是它所在月份组的最后一个元素，`dates[-1] == d` **恒成立**。

**实证**：三次观测的信号日是 09-18、09-24、09-29 —— 同一个月里出现三个"月末"。

**范围界定（重要）**：只有 `paper_live/engine.py:104` 用了这个截断窗口。
历史回测用完整区间（[personal_quant/strategy/backtest.py:87](personal_quant/strategy/backtest.py#L87)）：
```python
rbs = rebalance_dates(start, end, cfg["rebalance"]["frequency"], cfg["rebalance"]["rule"])
```
→ **strategy_v2 的历史回测结果不受影响**。

---

### 3.3 🔴 CRITICAL-3：特征缓存会静默返回**错误日期**的横截面

**代码** [personal_quant/strategy/features.py:216-224](personal_quant/strategy/features.py#L216-L224)：

```python
for d in dates:
    f = FEATURE_CACHE / f"{d.strftime('%Y-%m')}.parquet"     # ← 只按月份命名
    if cache and f.exists():
        sub = pd.read_parquet(f)                             # ← 直接赋给请求的日期，不校验
        ...
        out[d] = sub
```

- worker 写盘时把 `datetime` 列 **drop 掉**（[features.py:76](personal_quant/strategy/features.py#L76)）→ **文件本身无法自证日期**
- 同月多个日期 → 后写覆盖先写（[features.py:84](personal_quant/strategy/features.py#L84)）
- 实盘触发点：[paper_live/data.py:108](paper_live/data.py#L108) `compute_features(symbols, [d], cache=True)`

**实证（本次独立复现）**：`data/derived/features/2026-09.parquet` 的内容唯一匹配 **2026-09-29**
（用 Alpha158 的 `KMID=(close-open)/open` 逐票反解比对 `daily_bars`，最大偏差 `6.8e-08`；行数 2982 = 实盘股票池）。

**对已有 3 条前瞻观测的影响（逐条重建时间线）**：

| 观测 | created_at (CST) | 当时文件内容 | 请求日期 | 判定 |
|---|---|---|---|---|
| 2026-09-18 | 09-19 22:11 | **09-17** | 09-18 | ⚠️ 用了**旧一天**的特征 |
| 2026-09-24 | 09-27 19:51 | **09-22** | 09-24 | ⚠️ 用了**旧两天**的特征 |
| 2026-09-29 | 09-29 22:45 | **09-29** | 09-29 | ✅ 同日 |

文件内容由"最近一次信号刷新"决定（signals 路径 `cache=False` 每次重写）：
09-17 22:11 → 09-22 00:30(09-18) → 09-22 22:19(09-22) → 09-27 20:05(09-24) → 09-29 22:29(09-29)。

**结论：三条观测都没有吃到"未来"数据（用的是更旧的特征，保守方向），但用的是错误日期的特征。**
这是**写入顺序的运气，不是设计保证** —— 反向顺序（先请求早的日期、文件里已是晚的日期）就会**真实泄漏未来信息**。
而且 [paper_live/audit.py:99-104](paper_live/audit.py#L99-L104) 的特征审计**只看 shape**（"159 列 × 2982 行"），
[pipeline/freshness.py:180-190](pipeline/freshness.py#L180-L190) 只看文件 mtime，
**整条链路没有任何一层能发现这件事**。

**补充排查（PHASE 3 追加，只读）—— 三个放大器：**

1. **`cache=False` 并不安全，它照样写共享缓存。**
   [features.py:252-256](personal_quant/strategy/features.py#L252-L256) 重算后**仍然落盘到同一个文件**并读回。
   所以 `pipeline/signals.py:99`（`cache=False`）自己拿到的是对的，
   但它**改写了月文件**，从而污染了所有 `cache=True` 的读者 —— 这正是 09-18/09-24 两次观测吃错日期的**机制**。
   ⇒ 只加"读时校验"修不干净，**写入路径也必须改**。

2. **同一次调用传同月多个日期 → 全部拿到最后一天。**
   [features.py:75-84](personal_quant/strategy/features.py#L75-L84) 对每个日期各写一次同名文件，
   [:253-256](personal_quant/strategy/features.py#L253-L256) 再对每个 `d` 读回同一份。
   当前调用方恰好都传单日期或月末日期，**尚未触发**，但这是同一根因的第二个出口。

3. **同类事故已经真实发生过一次。**
   [tests/strategy/test_no_future_leakage.py:17-24](tests/strategy/test_no_future_leakage.py#L17-L24) 的注释记载：
   该测试曾把 `2024-01.parquet`（4943 行）覆盖成 2 行。现场仍在：
   `data/derived/features/2024-01.parquet.corrupt-20260920`（102,109 B）。

**当前状态下的重放 = 真实泄漏（新增结论）**：
`2026-09.parquet` 现在装的是 **09-29**。今天若回放 `run_day(2026-09-18)`，
会拿到 09-29 的横截面 —— **这是真实的未来数据泄漏**。
即：这个缺陷**"当天正着跑"时是保守的，"事后回放"时是泄漏的**。
`experiments/paper_live/engine_validation/` 走的正是回放路径。
⇒ **修复完成前，禁止任何形式的特征回放/补跑。**

完整调用点清单（14 个直接入口 + 2 个手工读路径 + 3 个检测盲区）见
[design.md §2.3](daily_exit_paper_v1_design.md)。

---

### 3.4 🟠 HIGH-4：target / stop / time_stop **不进入任何状态机**

- 计算：[trade_plan/plan.py:131-133](trade_plan/plan.py#L131-L133) `target_and_stop()`
- 存储：写在 plan row（[plan.py:439-444](trade_plan/plan.py#L439-L444)）
- 消费方：**只有展示** —— GUI [webapp/pages.py:716](webapp/pages.py#L716)、
  [app/pages/recommendations.py:62](app/pages/recommendations.py#L62)、
  建议 note [write_recommendation_note.py:122](scripts/quant/write_recommendation_note.py#L122)
- `paper_live/` 目录下 grep `target_price|stop_loss|time_stop` → **0 命中**

**两条死代码**：
- `sell_reasons()`（[plan.py:620](trade_plan/plan.py#L620)）—— 全仓库**无任何调用方**
- `holding["stop_price"]`（[plan.py:638](trade_plan/plan.py#L638)）—— **从未被任何代码写入**

**结论：系统里不存在止盈/止损/时间止损的退出逻辑。持仓只能靠下一次（每个月都在发生的）调仓被动替换。**

---

### 3.5 🟠 HIGH-5：不存在限价成交模型

[personal_quant/strategy/execution.py:92-98](personal_quant/strategy/execution.py#L92-L98)：
成交价 = **T+1 开盘价，无条件成交**，只排除三种情况（停牌无 bar / 涨停买不进 / 跌停卖不出）。

`recommended_entry_price` 与 `entry_low–entry_high` 区间**从不参与成交判定**。
`PlannedOrder`（[paper_live/execution.py:37-55](paper_live/execution.py#L37-L55)）**没有 limit price 字段**。

**你要的"价格没到我的限价就不成交"语义，需要新实现。**

---

### 3.6 🟠 HIGH-6：非调仓日没有任何退出路径

卖单只在 `if is_reb and len(target_weights):` 分支里由 `build_orders()` 产生（[engine.py:239](paper_live/engine.py#L239)）。
非调仓日 `target_weights = {}`（[engine.py:230-232](paper_live/engine.py#L230-L232)），既不买也不卖，持仓原样跨日。

---

### 3.7 🟠 HIGH-7：成本核算口径不一致（你 §12 担心的事确实存在）

**同一份交易计划里，展示的费用是单边、展示的净收益是双边**：

```python
# trade_plan/plan.py:493-495  —— 展示给用户的「预估交易费用」
fees_est = sum(_position_fees(strategy_cfg, v, v)[0]      # ← 只取买边
               for v in df["buy_value"] if v > 0)

# trade_plan/plan.py:400-406  —— 同一行的「预期净收益」
buy_fee, sell_fee = _position_fees(strategy_cfg, value, exit_value)
fee_rate = (buy_fee + sell_fee) / value                   # ← 双边
```

`estimated_fees` 的累加口径还有三个问题：
| 问题 | 说明 |
|---|---|
| 按**目标持仓**算，不是按**交易差额** | 全仓买入时相同；ADD/HOLD/REDUCE 模式下就错了 |
| 把 **HOLD 行也算进去** | HOLD 行 `buy_value > 0` 但根本不交易 |
| 把 **REDUCE 行当买入收费** | REDUCE 是卖出，应计印花税，却按买入佣金算 |

连带 `remaining_cash = capital - invested - fees_est`（[plan.py:520](trade_plan/plan.py#L520)）**高估剩余现金**。
`write_recommendation_note.py:126` 还把这个单边数字标注为"佣金+印花税+过户费+滑点" —— 而印花税只有卖出才收（[costs.py:36](personal_quant/strategy/costs.py#L36)）。

**paper_live 结算日的费用"扣了现金但不记账"**：结算在 [engine.py:171-178](paper_live/engine.py#L171-L178) 完成（`cash -= fee`），
紧接着 [engine.py:238](paper_live/engine.py#L238) 把 `fills` 重置为 `None`，
到 [engine.py:288-289](paper_live/engine.py#L288-L289) `fees = fills.fees if fills is not None else 0.0` → **当日 metrics/月报显示成本为 0**。

**其他**：
- 费率被独立复制 **6 份**（4 份 YAML + qlib workflow + 测试硬编码）；改一份不传播
- `paper_live/execution.py:209` 把最低佣金**硬编码成 5.0**，绕过 `cost_model.min_commission`
- 同一个"费用"在系统里有**三种口径**：unit rate（不含最低佣金，用于 sizing/优化器/计划 JSON）、
  真实模型（用户看到的）、以及财富库的**人工录入 fee**（与模型计算无关，且 `commission/stamp_duty/other_fee` 三列是死列）
- `trades` 表里的逐笔 fee 是**估算值**（T 日收盘价算的），不是实际扣费（[execution.py:242](paper_live/execution.py#L242)）

---

### 3.8 🟡 MEDIUM：其他已确认事实

| 事实 | 位置 |
|---|---|
| 持仓**无状态机**，纯字典全量重建；平仓 = 删 key | [engine.py:41-45](paper_live/engine.py#L41-L45)、[execution.py:240-241](paper_live/execution.py#L240-L241) |
| 挂单期间**不预留现金**（`pf.cash` 不变） | [engine.py:261-269](paper_live/engine.py#L261-L269) |
| 幂等短路发生在**结算之前** → 重复跑同一天连挂单都不结算 | [engine.py:146](paper_live/engine.py#L146) 早于 `:168` |
| `config/paper_live.yaml` 的 `on_limit` / `on_no_bar` / `cash_buffer` / `min_trade_value` **无代码读取**（死配置） | 全仓库 grep |
| `label_isolation` 审计项是**硬编码 `VALID`**，不做实际检查 | [audit.py:165-166](paper_live/audit.py#L165-L166) |
| `audit.replay_mode` 定义了但**没被 engine 调用** | [audit.py:188-196](paper_live/audit.py#L188-L196) |
| 涨跌停阈值对所有板块统一用 9.5%（未区分 5%/20%） | `config/paper_live.yaml:64` |
| 不足 1 手的残仓被标 `HOLD` 而非清仓 → 会永久留在账户 | [execution.py:119-121](paper_live/execution.py#L119-L121) |

---

## 4-6. Changes Made / State Machine / Cost Accounting

**设计完成于 PHASE 3**，见 [design.md](daily_exit_paper_v1_design.md)：

| 节 | 内容 | 对应本报告 |
|---|---|---|
| §2.1 | C1 修复设计（挂单三态、读-改-写、账本为真相） | 3.1 |
| §2.2 | C2 修复设计（纯函数月末判定，已实证 2026-08 全月 0 误差） | 3.2 |
| §2.3 | C3 修复设计（按日期存储 + 读时断言 + 写路径整改） | 3.3 |
| §3 | 执行状态机 `PENDING_ENTRY → OPEN → PENDING_EXIT → CLOSED` | 3.4 / 3.6 |
| §4.2 | 出场成交价的 OHLC 可判定规则（含跳空） | 3.5 |
| §7 | 成本核算（唯一来源，单双边一致，配断言测试） | 3.7 |
| §8.3 | 同日 target+stop 冲突 → `stop_first`（保守） | 新增 |

**本阶段未修改任何代码。** 实施在 PHASE 4 起。

---

## 7. No-lookahead Verification

**信号层（strategy_v2）审计结论：未发现前视泄漏。**

| 检查项 | 结论 | 证据 |
|---|---|---|
| Alpha158 特征窗口 | ✅ 全部后视 | [features.py:67-68](personal_quant/strategy/features.py#L67-L68) 加载 `[quarter_start-170d, d]`，只取 d 那一行 |
| label 是否混入特征 | ✅ 四道过滤 | [features.py:38-40](personal_quant/strategy/features.py#L38-L40)、`:78-83`、`:220-223`、训练脚本显式 drop |
| 因子 rolling 窗口 | ✅ 无负向 shift | 全仓 grep `shift(-` 在 factors/ pipeline/ trade_plan/ paper_live/ 下 0 命中 |
| 财务 PIT | ✅ 保守方向 | [fundamental.py:63](factors/fundamental.py#L63) `availability_date < d`（公告日当天不可用） |
| 新闻 PIT | ✅ 用 availability 而非 publication | [news_factors.py:36-46](factors/news_factors.py#L36-L46) |
| 信号取数上界 | ✅ = 信号日 | [factors/base.py:181-188](factors/base.py#L181-L188) `trade_date <= end`，`end = signal_date` |
| 成交价 | ✅ T+1 开盘 | [execution.py:98](personal_quant/strategy/execution.py#L98)，**未用 T+1 的 high/low 做 T 日决策** |
| forecast 校准 embargo | ✅ 双重 | [forecast.py:162-167](pipeline/forecast.py#L162-L167) `date < as_of` 且 `window_end < as_of` |
| 绩效未走完窗口 | ✅ 置 NA | [metrics.py:52-64](paper_live/metrics.py#L52-L64) `incomplete_window_mask` |

**前视问题的唯一真实位置是执行层的特征缓存（3.3）** —— 那是工程缺陷，不是因子公式问题。

---

## 8-10. Test Results / Dry Run / Experiment Rules

**未开始**（PHASE 6 起）。测试清单（17 组 / 33 条）见
[design.md §13.4](daily_exit_paper_v1_design.md)。

### 已有 3 条观测的处置（PHASE 3 确定，见 design.md §15）

**不删除、不覆盖、不重新生成、不追认成交。**

```text
forward_holdout/observations/2026-09-{18,24,29}.json   ← 原文件字节不变
forward_holdout/audit/<date>.execution_validity.json   ← 新增 sidecar
```

```yaml
execution_validity: invalid
usable_as: evidence_of_bug          # 不可作为业绩样本
reasons:
  - C1_paper_live_no_fill
  - C2_rebalance_date_bug
  - C3_feature_cache_date_mismatch
lookahead: not_observed             # 明确：未发现未来数据泄漏
```

表述纪律（用户明确要求）：

```text
✅ 写：wrong-date feature cache, but no verified future-data leakage
❌ 不写：lookahead contaminated
```

三条观测的拆分是 **pre_fix**；修复后的干净观测进入
`experiments/daily_exit_paper_v1/`，与 pre_fix **物理分离**，
因此"修复前 / 修复后"永远可区分。

**`forward_holdout/state/pending_orders.json` 不结算、只归档**：
它的 `signal_date` 已过期、`exec_date` 为 null，
按今天的价格"补成交"就是伪造历史。

---

## 附：你提出的 14 个问题的逐条答案

| # | 问题 | 答案 |
|---|---|---|
| 1 | 真实执行链 | 见 2.1 调用图 |
| 2 | Paper Live 实际成交逻辑 | T+1 开盘**市价**成交；但见 3.1 —— **实际从未成交** |
| 3 | target/stop 如何计算 | [plan.py:122-135](trade_plan/plan.py#L122-L135)：target = 计划价×(1+预期收益×profile系数)；stop = 计划价×(1−stop_sigma×vol×√(h/20))，下限 −30% |
| 4 | 是否进入持仓状态机 | **否**。无状态机，且 paper_live 完全不读这些字段 |
| 5 | 非调仓日是否卖 | **否**。只有调仓日 `build_orders` 产生卖单 |
| 6 | limit-entry 是否模拟"触及才成交" | **否**。无 limit price 字段，市价成交 |
| 7 | T+1 是否严格 | ✅ 信号层严格（T+1 开盘成交）；但见 3.1/3.2 —— paper 层因两个 bug 从未走到成交 |
| 8 | cash / available / reserved 是否一致 | 只有单一 `cash` 标量，无 reserved/available 概念；挂单不预留资金 |
| 9 | 卖出后现金能否参与下一轮 | ✅ 机制上可以（先卖后买，[execution.py:179-181](paper_live/execution.py#L179-L181)）；但见 3.1 —— 从未发生 |
| 10 | 重复运行会不会重复下单/扣款 | ✅ 幂等（观测文件短路 + store 内容比对 + 时间序断言）；但幂等会**跳过挂单结算** |
| 11 | 费用口径是否统一 | ❌ 见 3.7 |
| 12 | 是否存在前视 | ❌ 执行层特征缓存（3.3）；信号层未发现 |
| 13 | 未来数据是否进入 signal/target/stop | signal/target/stop 的计算本身没有；但**输入特征**可能取错日期（3.3） |
| 14 | 哪些可安全复用 | 见下方 |

### 可安全复用的部分（建议）

| 组件 | 位置 | 复用方式 |
|---|---|---|
| S3 信号（冻结模型打分） | `pipeline/signals.py:compute_signals` | **原样复用**（`cache=False` 路径是安全的） |
| T+1 执行模型 | `personal_quant/strategy/execution.py` | 复用其"T+1 开盘 + 涨跌停/停牌 NO_TRADE"，**另加限价层** |
| 成本模型 | `personal_quant/strategy/costs.py` | **唯一费用来源**，新实验直接引用，不再复制费率 |
| 订单/成交数据结构 | `paper_live/execution.py:PlannedOrder` | 参考其形状，**新增 limit/状态字段** |
| 三层留痕设计 | `wealth/decisions.py` | **设计可借鉴**（recommendation / decision / execution 分离 + 滑点 + inside_band），但**不能写进 wealth 库**（那是真实财富） |
| 存储层 | `paper_live/store.py` | 复用（append-only + 内容比对 + 时间序断言，写得不错） |

### 必须新写的部分

- 持仓状态机（CASH / PENDING_ENTRY / OPEN / PENDING_EXIT / CLOSED）
- 限价成交模型 + `execution_granularity` 声明
- target / stop / time_stop 的**成交时快照**与退出触发
- 非调仓日的退出路径
- 独立实验账本（与 forward_holdout、wealth 库都隔离）
- 成本核算（只认一个费用来源）
