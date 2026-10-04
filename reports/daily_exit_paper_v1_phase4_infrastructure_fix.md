# PHASE 4 INFRASTRUCTURE FIX REPORT

> 阶段：PHASE 4（共享基础设施修复：C1 / C2 / C3）
> 日期：2026-10-01 ｜ 上游依据：`reports/daily_exit_paper_v1_audit.md`（PHASE 1/2）、
> `reports/daily_exit_paper_v1_design.md`（PHASE 3）
> **本阶段没有实现 daily_exit_paper_v1，没有接入 run_daily.py，没有修改 strategy_v2，
> 没有修改任何历史数据，没有重跑任何历史 forward observation。**

---

## 1. C1 Fix

### 1.1 根因（三层叠加，已实测）

| 层 | 事实 |
|---|---|
| ① 没有未来日历 | `trading_calendar` 表 6481 行，范围 2000-01-04 ~ **2026-09-29**；`> 2026-09-29` 的行数为 **0**。T 日收盘后运行时日历的最后一天就是 T，`_next_trading_day` 必然返回 `None`。 |
| ② `None → NaT` 绕过守卫 | `pd.Timestamp(None)` 得到 **`NaT`** 而不是 `None`，`if exec_date is None` 拦不住；随后 DuckDB 对 `'NaT'` 报类型错误，被 `except Exception: return False` 吞掉。 |
| ③ 挂单文件被无条件覆盖 | 旧代码每次都写一个全新的 payload，读都不读旧的。实证：`pending_orders.json` 里只剩 2026-09-29 一批，09-18 / 09-24 两批无声消失。 |

### 1.2 修复内容（`paper_live/engine.py`）

**三态可用性判定，完全显式**

```python
class Availability(str, Enum):
    READY   = "READY"     # T+1 已在已观测日历里 -> 可以判成交
    NOT_YET = "NOT_YET"   # T+1 尚未出现 -> 保持 PENDING（正常，不是失败）
    ERROR   = "ERROR"     # 读取失败 -> 抛 PendingError，绝不吞

def t1_availability(provider, signal_date): ...
```

判定规则（不靠 try/except 猜）：

```
nxt = 已观测日历里 > signal_date 的第一个交易日
  ├─ 不存在          -> NOT_YET
  └─ 存在 = nxt      -> READY
       （此时单只股票没有 bar 是**可判定**的 NO_FILL(停牌)：
         nxt 出现在日历里 ⇒ 市场有成交、数据已入库 ⇒ 这只票当天就是没交易）
```

`except Exception: return False` 在挂单路径上**全面移除**。唯一的 `except` 是
"为了抛"（包成 `PendingError` 并带原始异常），不是"为了吞"。

**挂单文件改为读-改-写 + 幂等**

- 结构带 `format: "paper_live.pending/2"`；逐单带 `order_id / signal_date / exec_rule / status / resolved_exec_date`。
- `order_id = {strategy_version}:{signal_date}:{symbol}:{side}`，同键不重复创建。
- 写入前先读、再并、最后写；**PENDING 不会因为程序再次运行而丢失**。
- 每次尝试追加一条 `attempts[]`：`attempt_timestamp / observed_run_date / signal_date / resolved_exec_date / availability_state / result / error_if_any`。

**旧格式挂单：归档，不结算**

旧文件（无 `format` 标记、`execution_date=null`）**既不算也不覆盖**：
另存为 `pending_orders.legacy-<UTC戳>.json` 后再清空工作文件。
理由：拿今天的日历去"补成交"= 用一个早已过去的开盘价伪造历史成交。

**账本为真相（§1.6）**

```python
ledger_cash(store, capital_initial)          # 从 trades/ + metrics/ 重算现金
assert_portfolio_matches_ledger(store, pf)   # 对不上 -> raise LedgerMismatch
```

恒等式：`期末现金 = 初始本金 − Σ(filled_shares × fill_price) − Σ(当日交易费用)`
（`filled_shares` 买正卖负，本身就是带符号现金流）。
**对不上就 raise，绝不自动改账。**

配套修正：**INVALID 的运行不再推进 `paper_portfolio`** —— 否则现金变了却没有
对应的 `trades/`，账本一致性从根上不成立。

**顺带修正的既有缺陷**：结算产生的成交与费用以前完全没进 `metrics`
（`transaction_cost` 在结算后记为 0）。现在结算批次与即时成交批次一起计入
`traded_value` / `transaction_cost`，并一起写入同一天的 `trades/`。

### 1.3 语义保持

`signal_date` 与 `run_date` 分开（C2 的产物，见 §2），但在正常情况下两者相同，
既有行为不变。

---

## 2. C2 Fix

### 2.1 根因

`is_rebalance_date` 把窗口取成 `[d-70天, d]` 再比较 `dates[-1] == d`。
`rebalance_dates` 按周期分组取 `g.iloc[-1]`，而窗口右端点就是 `d` ——
**最后一个分组的最后一个元素恒等于 d**，于是只要 d 是交易日就返回 True。

实测（2026-08，一个已完整结束、可与回测参照物逐日比对的月份）：

| | 与回测参照物不一致的交易日 |
|---|---|
| 修复前 | **20 / 21 天全部误判** |
| 修复后 | **0 / 21** |

更深的根因：**系统里没有未来交易日历**，所以"d 是不是本月最后一个交易日"
在 d 当天无法回答。

### 2.2 修复内容

```python
def is_rebalance_date(date, cfg, calendar) -> bool:
    """d 是调仓日 ⟺ d 之后**已观测到**的第一个交易日落在下一个周期"""
    d = pd.Timestamp(date)
    cal = _as_calendar(calendar)
    if d not in cal:
        return False                      # 非交易日
    later = cal[cal > d]
    if len(later) == 0:
        return False                      # 本周期是否结束尚不可知 -> 保守
    return later[0].to_period(offset) != d.to_period(offset)
```

- 周期偏移取自 `strategy/rebalance.py::FREQ_MAP`（**单一来源**，不另起一套）。
- `rule` 同时支持 `last_trading_day` / `first_trading_day`；未知取值直接 raise。
- **`calendar` 形参现在真的被使用**（旧实现收了它却完全忽略、直接查 DB，
  与 `run_day` 里"日历必须来自 provider"的注释自相矛盾）。

### 2.3 信号日 ≠ 确认日（§4 的核心要求）

新增纯函数：

```python
def rebalance_signal_date(run_date, cfg, calendar) -> Optional[pd.Timestamp]:
    """run_date 是本周期第一个交易日 -> 返回**上一个交易日**（上期最后一天）。"""
```

行为对照：

| 运行日 | `rebalance_signal_date` |
|---|---|
| 2026-07-01（七月首个交易日，日历起点） | `None` |
| 2026-08-03 | **2026-07-31** |
| 2026-09-01 | **2026-08-31** |
| 2026-10-01 | **2026-09-30** |
| 月中任意日 | `None` |

**信号日仍然是"上个月最后一个交易日"，没有被挪到下个月第一天。**
执行落在**运行日开盘** —— `execute_order` 内部算的 `next_trading_day(signal_date)`
正好就是 run_date，天然正确，不需要新写任何 T+1 逻辑。

写入 `run_day(run_date, signal_date=...)`；`run_day` 拒绝 `signal_date > run_date`
（那就是用未来的横截面下单）。

### 2.4 接线

| 位置 | 改动 |
|---|---|
| `pipeline/daily.py` | `_is_rebalance` → `_rebalance_signal_date`；`run_day(..., signal_date=sig)`；**不再吞异常**（日历读不出来就是数据链路坏了，应当 FAILED） |
| `scripts/paper_live/run_daily.py` | 同样传入 `rebalance_signal_date`（否则修复后它将永远不会调仓） |
| `run_rebalance.py` / `validate_engine.py` | 恒传 `force_rebalance=True`，行为不变 |
| `pipeline/daily.py` 日报 | `ctx.store_data["is_rebalance"]` 改由 `result.is_rebalance` 提供 |

### 2.5 未修改

`personal_quant/strategy/rebalance.py`、`backtest.py`、`factors/base.py::cached_rebalance_dates`、
`portfolio/rebalance.py` **一字未动**。

### 2.6 有意的行为变化（必须写清楚）

调仓日只能在**下个周期第一个交易日**被确认。因此：

- **错过那一天 = 错过这次调仓**，不回溯补单（回溯 = 用一个已经过去很久的开盘价成交）。
- 修复后现有 monthly paper_live 不再"每天调仓"，而是**每月一次**。

---

## 3. C3 Fix

### 3.1 根因（三条并存，不止一条）

| # | 事实 |
|---|---|
| ① | worker 写盘时把 `datetime` 列 **drop 掉**（`features.py:76`），文件名只有 `%Y-%m` → **文件无法自证日期** |
| ② | 读取时**零校验**：`out[d] = sub` 把整份月度文件当作"请求的那一天" |
| ③ | **`cache=False` 并不安全** —— 重算后**照样写共享的月文件**并读回。所以 `pipeline/signals.py:99`（`cache=False`）自己是对的，却改写了月文件、污染所有 `cache=True` 读者。**这正是 2026-09-18 / 09-24 两次前瞻观测吃到错误日期特征的机制。** |

伴生缺陷：同一次调用传同月多日期 → 全部拿到最后一天（当前调用方恰好未触发）。

同类事故已经真实发生过一次：`tests/strategy/test_no_future_leakage.py:17-24` 记载
该测试曾把 `2024-01.parquet`（4943 行）覆盖成 2 行；现场仍在
`data/derived/features/2024-01.parquet.corrupt-20260920`。

### 3.2 修复内容（`personal_quant/strategy/features.py`）

**存储契约：路径带日期 + 文件内自述日期**

```
data/derived/features/feature_<YYYY-MM-DD>.parquet
   └─ 列 ('feature_date', '<YYYY-MM-DD>')
```

**读侧**：`read_feature_cache(date)` —— 唯一放行条件是
`文件名日期 == 文件内 feature_date == 请求日期`。
不一致 → 打印 `WARNING 缓存日期不匹配：请求 X，文件 Y 内记录的是 Z` 并返回 `None`
（调用方重算），**绝不返回错误日期的数据**。返回值已剥离元数据列，调用方拿到的
特征矩阵与加这列之前完全一致（158 列）。

**写侧**：worker 只写 `feature_<自己那一天>.parquet`，并

- **空切片不落盘**（`if len(sub) == 0: continue`）—— 不制造空文件污染后续读者；
- 写前把日期写进文件内部。

写侧这一条同时消灭了伴生缺陷 ③ 与"同月多日期互相覆盖"：
`cache=False` 的重算结果**只写它自己那一天**，不可能再改到别人。

**非交易日**：worker 不落盘 → `read_feature_cache` 返回 `None` →
`compute_features` 返回空 DataFrame，**不创建假的空缓存文件**。

**特征计算逻辑一字未改**：Alpha158 的 handler 参数、窗口、label 过滤全部原样。

### 3.3 调用路径整改

| 位置 | 处置 |
|---|---|
| `personal_quant/strategy/features.py` | 契约唯一实现处（读+写） |
| `pipeline/signals.py:99` | 经 `compute_features` 自动继承（`cache=False` 现在只写自己的日期） |
| `paper_live/data.py:108` | 经 `compute_features` 自动继承（`cache=True` 现在带日期校验） |
| `scripts/research_independent_info.py:139` | **改为走 `read_feature_cache`**，删除自拼的 `%Y-%m` 路径与 `FEATURE_CACHE` 常量 |
| `scripts/run_incremental_factor_selection.py:88` | 同上 |
| `scripts/audit_point_in_time.py:100` | 清点证据的文案改为与事实一致（新旧两种格式并存，分别计数） |

`scripts/backtest_strategy.py` 等 8 个研究脚本走 `compute_features`，自动继承。
仓库级断言测试（见 §6）保证不会再有旁路自拼路径。

### 3.4 旧文件处置（§10）

- **不删除、不覆盖、不批量迁移**。132 个月度文件原样保留，其中包括
  `2024-01.parquet.corrupt-20260920`。
- 新 loader **永不读取**旧格式（路径不同、且缺 `feature_date` 列）。
- 未设计 migration 脚本（本阶段不需要：按日期重建即可，成本与前持平 ——
  生产链路每天只请求 1 个日期）。

### 3.5 一处诚实的边界（写入 Known Remaining Issues）

缓存是**按日期**的整份横截面，**不按 symbol 筛选**：命中时返回文件里的全部行，
调用方自己 `reindex`。这是**旧实现就有的性质**（旧月度文件同样如此），
本次未改变，也未引入新风险；但它是一个值得日后收紧的尖锐边界。

---

## 4. Files Changed

| 文件 | 改动 |
|---|---|
| `paper_live/engine.py` | C1 全部 + C2 判定与信号日；`run_day` 分离 run_date / signal_date；账本对账 |
| `personal_quant/strategy/features.py` | C3 缓存契约（读 + 写 + 元数据剥离） |
| `pipeline/daily.py` | C2 接线；`signal_date` 传递；不再吞日历异常 |
| `scripts/paper_live/run_daily.py` | C2 接线（否则修复后永不调仓） |
| `scripts/research_independent_info.py` | C3 调用路径 + 删除自拼路径 |
| `scripts/run_incremental_factor_selection.py` | C3 调用路径 + 删除自拼路径 |
| `scripts/audit_point_in_time.py` | 缓存清点文案与事实一致 |

**新增文件**

| 文件 | 作用 |
|---|---|
| `tests/forward/test_pending_lifecycle.py` | C1 测试（9 条） |
| `tests/forward/test_rebalance_dates.py` | C2 测试（14 条） |
| `tests/strategy/test_feature_cache_contract.py` | C3 测试（13 条） |

**未改动的计划项**：`paper_live/data.py` 本在设计里列为"将修改"，实际**不需要** ——
C3 的保护落在 `features.py`，`data.py` 通过 `compute_features` 自动继承。
少改一个文件。

---

## 5. Files Protected

`git status` 逐一核对，以下路径**零改动**：

```
config/strategy_v1.yaml          config/strategy_v2.yaml       config/paper_live.yaml
personal_quant/strategy/rebalance.py
personal_quant/strategy/backtest.py
personal_quant/strategy/costs.py
factors/base.py                  portfolio/rebalance.py
trade_plan/plan.py
forward_holdout/**               experiments/**
wealth/**                        pipeline/scheduler.py
```

---

## 6. New Tests

**36 条新测试，全部通过 `pytest` 正常发现与运行**（`tests/` 下，非手工脚本）。

### C1 — `tests/forward/test_pending_lifecycle.py`（9 条）

| 测试 | 锁死的行为 |
|---|---|
| `test_signal_on_the_last_observed_session_stays_pending` | **核心用例**：`signal_date` = 数据库最后一个交易日 → `PENDING`，不是 NO_FILL / FAILED / CANCELLED |
| `test_pending_orders_carry_stable_unique_ids` | order_id 稳定且唯一 |
| `test_rerun_keeps_pending_and_creates_no_duplicates` | 重跑不丢单、不重复建单；两次尝试都留痕 |
| `test_pending_survives_across_repeated_runs` | 连续多次运行挂单一直在 |
| `test_pending_settles_once_the_next_session_appears` | 日历前进 → READY → 按 T+1 开盘价成交 |
| `test_ready_but_symbol_has_no_bar_is_a_settled_no_fill` | T+1 已存在但无 bar → 可判定的 NO_FILL（停牌），**不是**继续等待 |
| `test_data_error_raises_and_is_recorded` | 读日历失败 → **raise** + attempts 记 `ERROR/RAISED`，挂单不丢 |
| `test_legacy_pending_is_archived_not_settled` | 旧格式挂单只归档不结算，账户不变 |
| `test_cash_mismatch_raises_and_never_auto_corrects` | 账本对不上 → raise，**不自动改账**，状态文件原样不动 |

### C2 — `tests/forward/test_rebalance_dates.py`（14 条）

含用户指定的全部日期：`2026-08-28 → False`、`2026-08-31 → True`、
`2026-09-18 / 09-24 / 09-29 → False`；另含月中日期、周末、**月末落周末回退到最后一个交易日**、
**含长假月份以交易日历为准**、非交易日、未确认即保守，
以及两条**与 backtest 语义逐日比对**的测试（真实已观测日历 + 合成完整区间，均 0 处不一致）、
4 条 `rebalance_signal_date` 测试（含"信号日不得被挪进下个月"）、
2 条端到端测试（补做的调仓在**运行日开盘**成交；拒绝 `signal_date > run_date`）。

**没有对任何单独日期写特殊判断** —— 全部由同一个纯函数算出。

### C3 — `tests/strategy/test_feature_cache_contract.py`（13 条）

正确日期 → 命中；缺文件 / 错日期 → 未命中且**绝不返回**；
`cache=False` 不碰别的日期；同月多日期互不覆盖；非交易日不落盘；
worker 源码契约（按日期命名 / 空切片不落盘 / 写 feature_date / 旧 `%Y-%m` 已消失）；
**回放前视保护**（回放 T 时用到的特征日期必须 ≤ T）；
仓库级"无旁路自拼路径"断言。

---

## 7. Old Tests

```text
PHASE 4 之前（基线，改动前实测）：  1020 passed
PHASE 4 之后（完整套件）：          1056 passed
```

1056 − 1020 = **36**，正好是本次新增的测试数 ⇒ **没有任何既有测试被改、被删、被跳过**。

**没有为了通过而修改任何既有测试。** 全程只修改了**我自己新写的**测试里 5 处写错的预期：

| # | 我的测试写错了什么 | 处理 |
|---|---|---|
| 1 | "旧挂单不结算"用例没截断日历，导致**当次运行自己真的调仓了**，却断言账户不变 | 截断日历，把"旧单有没有被结算"与"本次有没有调仓"分开 |
| 2 | 把 2026-08-03 当作"非调仓日"，但它其实是八月首个交易日，返回 07-31 是**对的** | 改用真正的月中日期，并另加一条"每个首个交易日都要触发"的测试 |
| 3 | worker 模板断言 `"%Y-%m" not in t` —— 但新写法 `%Y-%m-%d` 也含这个子串 | 改成整段匹配 `strftime('%Y-%m')` |
| 4 | 仓库级扫描把**测试自己**扫成了违规项 | 排除自身文件 |
| 5 | 断言 `read_feature_cache(...).to_numpy() == 9.0`，但返回的帧里还带着 `feature_date` 元数据列 | **这一条暴露了真实的 API 隐患** —— 改成 `read_feature_cache` 内部就剥离元数据，调用方不必记得手动摘 |

第 5 条是唯一一次因测试而改**代码**：改的是让接口更安全（读取即返回纯特征矩阵），
不是为了让断言通过而放宽标准。**没有任何一处是因为"期望值与代码不符"就把期望值改成代码的样子。**

---

## 8. Strategy_v2 Regression

### 8.1 结论

**PASS。strategy_v2 / S3 / horizon=20 / Top-K=20 / monthly rebalance 定义 / 历史回测 /
benchmark 全部未受影响。**

### 8.2 证据

| 维度 | 证据 |
|---|---|
| 代码路径 | `git diff` 显示 `backtest.py`、`rebalance.py`、`costs.py`、`portfolio/`、模型文件、全部配置文件**逐字节未变** |
| 特征数值 | 见 §9（按日期重算 vs 旧缓存，2026-09-29 **max diff = 0.0**，470,456 格全等） |
| 冻结哈希 | `tests/production/test_production_freeze.py` 全绿；`config/strategy_v2.yaml` 未被改动 |
| 全量测试 | 1056 passed，含 `tests/strategy/`、`tests/portfolio/`、`tests/factors/`、`tests/production/` |
| 历史产物 | `experiments/**` 零改动（见 §5、§10） |

### 8.3 明确记录：**本阶段没有重跑 `--check-anchor`**

`python scripts/research_portfolio.py --method equal_weight --period test --check-anchor`
会在 `experiments/portfolio/` 下**新建一个 run 目录**，而 `experiments/**` 是本阶段的
保护对象（§16）。按 §24"不得自行突破保护边界"，**我没有执行它**，而是用上面
四条证据替代。建议把它作为 **PHASE 7 的正式门槛**执行。

---

## 9. Feature Cache Regression

### 9.1 方法

先反解出每个旧月文件**真实装的那一天**（用 Alpha158 的 `KMID=(close-open)/open`
与 `daily_bars` 逐日比对），再用**新代码**重算同一天，逐格比对。

| 旧文件 | 反解出的真实日期 | 最大 KMID 偏差 |
|---|---|---|
| `2024-01.parquet` | **不存在**（只剩损坏文件 `2024-01.parquet.corrupt-20260920`，2 行） | — |
| `2025-01.parquet` | **2025-01-27**（春节前最后交易日，确实是月末） | 1.04e-07 |
| `2026-08.parquet` | **不存在** | — |
| `2026-09.parquet` | **2026-09-29** | 1.10e-07 |

`2024-01` 与 `2026-08` **无法比对**（理由如实列出，不用别的日期冒充）：

- `2024-01`：只有损坏现场（2 行，symbol 恰为 `000001.SZ` / `600519.SH` ——
  测试用的两只），**明确标记为 corruption，不能当 baseline**。
- `2026-08`：文件根本不存在（2026-01..2026-08 整体缺失）。

### 9.2 结果

| 月份 | 比较格子数 | max&#124;diff&#124; | >1e-6 的格子 | NaN 模式不一致 | 判定 |
|---|---|---|---|---|---|
| **2026-09**（09-29） | 470,456 | **0.0** | **0** | 0 | ✅ **完全一致** |
| **2025-01**（01-27） | 785,512 | 7.57e-06 | 45（0.0057%） | 0 | ⚠️ 见 §9.3 |

日期隔离验证：同月另一天算出来的内容**不同**（旧实现下两者会是同一份文件）。

### 9.3 2025-01 那 45 个格子的定性（**不是 C3 造成的，也不是错误日期**）

按 §19 的要求逐层查证：

1. **旧文件的日期是对的**（2025-01-27，KMID 偏差 1.04e-07）——**不是 wrong-date cache**。
2. **只有 5 只股票涉及差异**：`000698.SZ / 002370.SZ / 002571.SZ / 300692.SZ / 600745.SH`。
3. **有差异的列全部是成交量相关特征**：`WVMA5/10/20/30/60`、`CORR5/10`、`CORD5/10/20`、
   `SUM*5`、`RSV5`、`RSQR5`、`KLOW2`、`KMID2`、`KUP2`、`KSFT2` —— 无一例外。
4. **这 5 只全部在成交量校准表 `data/parquet/market/market_scale.parquet` 里**
   （5557 行，reason = "Yahoo-source per-stock volume/amount scaling"）。
5. **差异幅度与校准系数无关**：`old/new ≈ 0.99999 ~ 1.000000`，而 `scale_volume` 是 12~33×。
   所以不是"套用/没套用校准"，而是**上游快照重述**。
6. **时间线吻合**：`2025-01.parquet` 的 mtime 是 **2026-09-08**，而
   `data/parquet/daily/bars_*.parquet` 全部是 **2026-09-29 22:25** 重新 ingest 的
   （换快照）。旧缓存是**旧数据**算的。
7. **旧有新无的 3 只**（`301557.SZ` / `301629.SZ` / `603124.SH`）上市日分别是
   2025-03-04 / 2025-03-24 / 2025-03-20，**全都落在 2025-Q1 窗口之外** ——
   被既有的 `have_bars` 过滤排除，与 C3 无关。

**定性：上游数据重述（volume/amount 相对变化 ≲1e-5）+ 窗口外新股，
不是缓存契约改动造成的。** 这正符合 §19 的要求 ——
**不能把错误/过期的旧文件当 baseline，也不能声称"新 cache 改变了策略"。**

### 9.4 回放前视保护（永久测试）

`test_replay_never_uses_a_feature_date_after_the_replay_date`：
构造"文件名 09-18、内容 09-29"的错配缓存，回放 09-18，
断言用到的每一个特征日期都 ≤ 09-18，且返回空表而不是 09-29 的横截面。

---

## 10. Historical Observation Protection

三条前瞻观测**未被删除、覆盖、重跑、修正或补成交**：

| 文件 | mtime（**全部早于本阶段**） | sha256（前 16 位） |
|---|---|---|
| `forward_holdout/observations/2026-09-18.json` | 2026-09-19 22:11 | `fe3bf0c00437c640` |
| `forward_holdout/observations/2026-09-24.json` | 2026-09-27 19:51 | `a85e9e8ad5d923f7` |
| `forward_holdout/observations/2026-09-29.json` | 2026-09-29 22:45 | `ed783d84c1384dd1` |
| `forward_holdout/state/paper_portfolio.json` | 2026-09-29 22:45 | `e9defd59ac47f1b8` |
| `forward_holdout/state/pending_orders.json` | 2026-09-29 22:45 | `06a99e47f2fe4e67` |

全部 mtime 停留在各自创建时刻（最新一个是 2026-09-29），**本阶段（2026-10-01）一次都没有碰过**。

`pending_orders.json` 仍然是**旧格式、内容原样**：代码里已经有了"检测到旧格式就归档
而不是结算"的分支，但**本阶段没有运行过任何 paper_live 日更**，所以它连归档都还没发生。

本阶段**没有**：
`✗ 运行 run_daily.py / refresh_all.py` ｜ `✗ 重跑历史 observation` ｜ `✗ 历史 feature replay`
｜ `✗ 补录旧交易` ｜ `✗ 用今天的数据重建过去`。

---

## 11. Git Diff Audit

```text
 M paper_live/engine.py                             C1 + C2
 M personal_quant/strategy/features.py              C3
 M pipeline/daily.py                                C2 接线
 M scripts/paper_live/run_daily.py                  C2 接线
 M scripts/research_independent_info.py             C3 调用路径
 M scripts/run_incremental_factor_selection.py      C3 调用路径
 M scripts/audit_point_in_time.py                   缓存清点文案

?? tests/forward/test_pending_lifecycle.py          C1 测试（9 条）
?? tests/forward/test_rebalance_dates.py            C2 测试（14 条）
?? tests/strategy/test_feature_cache_contract.py    C3 测试（13 条）
?? reports/daily_exit_paper_v1_audit.md             PHASE 2
?? reports/daily_exit_paper_v1_design.md            PHASE 3
?? reports/daily_exit_paper_v1_phase4_infrastructure_fix.md   本文件
```

（另有 `reports/daily/*` 的既有日报改动与 `data/` 下的派生缓存，
均为 PHASE 4 之前就存在的运行产物，不是本次改动。）

- **改动全部落在允许清单内**：`paper_live/`、`personal_quant/strategy/features.py`、
  `pipeline/daily.py`、`scripts/` 下的调用路径。
- **冻结清单零改动**（§5 逐条核对通过）。
- **没有扩大改动范围**：删掉了自己引入但从未使用的 `LEGACY_SUFFIX` 与
  `FeatureCacheDateMismatch`；`paper_live/data.py` 最终**不需要改**。
- 生成的 `data/derived/features/feature_*.parquet`（4 个）是**派生缓存**，
  不覆盖任何旧文件（新旧路径不同名）。

---

## 12. Known Remaining Issues

| # | 问题 | 处置 |
|---|---|---|
| R1 | **缓存按日期但不按 symbol**：命中时返回文件里全部行，调用方自己 `reindex`。若某天先用 A 股池算、后用 B 股池请求，会拿到 A 的行 | 旧实现同样如此，非本次引入。已在 §3.5 明确记录；收紧需另开变更 |
| R2 | **错过下月首个交易日 = 错过该月调仓** | C2 的有意行为（不回溯补单）。需要调度器保证当天跑到，或在 PHASE 5 引入状态化补做（带明确的时间语义） |
| R3 | `--check-anchor` 未在本阶段执行 | 见 §8.3。建议作为 PHASE 7 正式门槛 |
| R4 | `2024-01` / `2026-08` 的特征无法做数值回归 | 前者只剩损坏现场，后者文件不存在。原因如实列出，未用替代日期冒充 |
| R5 | 未验证 `pipeline/signals.py` 的端到端运行 | 会改写 `data/quant/signals_*.parquet` 等生产产物，超出本阶段范围；其代码路径经 `compute_features` 自动继承新契约，且被 `tests/trade_plan` / `tests/webapp` 间接覆盖 |
| R6 | `pipeline/scheduler.py:46-47` 的 `monthly_rebalance` 任务 `day=1` 从未被读取 | **只记录，不修改**（另一个子系统的缺陷） |
| R7 | `trade_plan/plan.py:493-495` 的 HIGH-7 单双边口径不一致 | **只记录，不修改** |
| R8 | `pending_orders.json` 仍是旧格式 | 下次真正运行 paper_live 时会自动归档并转为新格式；本阶段刻意不运行 |
| R9 | `LEGACY_SUFFIX` 等设计文档里的次要设计点未实现 | 属设计稿的细化项，未实现即为未实现，不声称已完成 |

**R5（daily_exit_paper_v1 何时接入 run_daily.py）= DEFERRED**（按 §23），
不是永久拒绝。

---

## 13. Verdict

```text
C1: PASS
C2: PASS
C3: PASS

Old tests:                          PASS   （1056 passed / 0 failed；基线 1020 + 新增 36）
New tests:                          PASS   （36 条，pytest 正常发现）
Strategy_v2 regression:             PASS   （代码路径零改动 + 特征数值一致 + 全量测试绿；
                                             --check-anchor 未执行，见 §8.3）
Feature replay safety:              PASS   （回流用到的特征日期恒 ≤ 回放日，永久测试）
Historical observation protection:  PASS   （三条观测 mtime/sha256 全部停在创建时刻）
Git isolation:                      PASS   （冻结清单零改动）

PHASE 4: PASS
```

### 需要用户裁决的一件事（不是失败项）

§8.3 的 `--check-anchor`：我没有执行，因为它会在受保护的 `experiments/` 下
新建 run 目录，且需要重算 2024–2025 共 8 个季度的特征（约 30 分钟）。
按 §24"不要自行突破保护边界"，我停下来报告而不是自行决定。

三个选项：

1. 批准在 PHASE 4 补跑（会新增 `experiments/portfolio/<run_id>/`）；
2. 推迟到 PHASE 7 作为正式门槛（当前建议）；
3. 保持只读验证，永久不重跑锚点。

**PHASE 4 到此为止，不进入 PHASE 5。**
