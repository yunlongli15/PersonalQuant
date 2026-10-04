# daily_exit_paper_v1 —— 架构设计（PHASE 3）

> **状态：设计稿。本轮只设计。**
> 未实现任何代码、未运行任何迁移、未改动任何历史数据。
> 审计结果见 `reports/daily_exit_paper_v1_audit.md`（PHASE 1/2）。

---

## 0. 实验事实声明（必读，写入 audit 与 experiment metadata）

**用户此前确实按照系统给出的选股建议进行过人工模拟交易，但这些交易没有经过
PersonalQuant 的 paper_live / ledger 系统持久化。**

```text
历史人工模拟交易
      ≠
当前 paper_live 数据库中的交易记录
```

由此确立三条纪律：

1. **不得反推**。不根据聊天记录、主观描述、账户余额或任何间接证据去重建过去的
   成交并写回数据库。系统里没有的成交，就是没有记录，不是"待补录"。
2. **不得误读**。`paper_live = 0 fills` **不等于**"用户以前从未进行过模拟交易"。
   准确表述是：
   > 当前 PersonalQuant paper_live 执行引擎没有成功结算成交；此前用户自行进行的
   > 人工模拟交易没有进入该系统的交易账本。两者是两个不同的数据集合。
3. **不得伪造**。`daily_exit_paper_v1` 从**零状态**开始建立账本，绝不预置任何
   "历史持仓"或"初始成交"来让曲线好看。


---

## 1. Existing Strategy Boundary（现有策略边界）

### 1.1 冻结对象

| 对象 | 位置 | 本实验的态度 |
|---|---|---|
| alpha 信号 S3 | `experiments/news/strategy/model.txt` + 两个 factor pack | **只读调用**，一个字节不改 |
| 组合配置 strategy_v2 | `config/strategy_v2.yaml` | **只读**。`label_horizon_days: 20`、`top_k: 20` 原样继承 |
| 回测/执行基础设施 | `personal_quant/strategy/{backtest,execution,costs,rebalance}.py` | 成本模型与执行规则**复用**；`backtest.py` 不改 |
| 现有 paper_live 观察 | `forward_holdout/**` | **不读不写**（见 §11） |
| 财富库 | `data/wealth/wealth.db`、`wealth/**` | **绝不触碰**（数据隔离铁律） |

### 1.2 本实验不做的事（一句话版）

`daily_exit_paper_v1` **不训练、不选因子、不调参、不优化**。它是一个**执行层实验**：
把已经冻结的 S3 信号，用一套**有明确出场规则、有账本、可对账**的方式跑成前瞻记录。

### 1.3 与现有 monthly paper_live 的根本差别

| | 现有 monthly paper_live | daily_exit_paper_v1 |
|---|---|---|
| 决策频率 | 每月调仓一次 | 每日监控（**入场一次，出场按规则**） |
| 持仓期 | 固定到下个月末 | target / stop / time_stop 决定 |
| 出场 | 只有"下次调仓" | 三层出场规则 + 状态机 |
| 入场 | T+1 开盘市价成交 | T+1 **限价**入场（可 NO_FILL） |
| 状态 | 无持仓状态机 | `PENDING_ENTRY → OPEN → PENDING_EXIT → CLOSED` |
| 资金 | 500,000（回测口径） | 用户指定并**锁定**（`--capital`，见 §12） |


---

## 2. Shared Infrastructure Fixes（C1 / C2 / C3）

这三个都是**共享基础设施缺陷**，不是新实验的私有问题。它们必须先在基础设施层修好，
新实验才谈得上"干净"。

### 2.1 C1 —— 挂单永远不结算（🔴 CRITICAL）

#### 真实根因（三层，缺一不可）

**第一层：T 日晚上，"下一个交易日"在当前数据模型里不存在。**

`paper_live/engine.py:246` `exec_date = _next_trading_day(d, calendar)`，
而 `calendar` 来自 `provider.trading_calendar()` → `factors.base.load_calendar()`
→ **只包含已经发生过的交易日**，最后一天 == 信号日 `d`。
`calendar[calendar > d]` 为空 → `exec_date = None`。

实测（2026-10-01）：`trading_calendar` 表 6481 行，范围 2000-01-04 ~ **2026-09-29**，
`trade_date > '2026-09-29'` 的行数为 **0**。**系统里不存在未来交易日历。**

**第二层：`None` 被静默转成 `NaT`，绕过守卫，异常被吞。**

```text
write_state("pending_orders", {..., "execution_date": None})       # engine.py:264-269
      ↓  下次运行
_settle_pending(...)  →  pd.Timestamp(pend["execution_date"])      # engine.py:416
      ↓  pd.Timestamp(None) = NaT   ← 不是 None
_t1_has_data(provider, orders, NaT)  的 `if exec_date is None` 守卫**拦不住 NaT**
      ↓
provider.prices(syms, NaT)  →  SQL `trade_date = 'NaT'`  →  DuckDB 转换异常
      ↓
except Exception: return False                                      # engine.py:385-386
      ↓  静默吞掉 → _settle_pending 返回 None → 状态原地不动
```

**第三层：每次运行无条件覆盖 `pending_orders.json`。**

`engine.py:263-269` 在 `t1_ready == False` 时**直接写一个全新的 payload**，
读都没读旧的。实证：`forward_holdout/state/pending_orders.json` 里现在**只有
2026-09-29 这一批** —— 09-18、09-24 两批已经消失，且没有任何日志。

#### 修复设计

**F1 — 挂单不再记录"此刻算不出来的 exec_date"。**

挂单是**意图**，不是**成交**。文件结构改为：

```json
{
  "experiment": "daily_exit_paper_v1.0",
  "signal_date": "2026-09-29",
  "exec_rule": "NEXT_SESSION_OPEN",
  "status": "PENDING",
  "orders": [ { "order_id": "...", "symbol": "...", "side": "BUY",
                "shares": 400, "limit_price": 53.10,
                "reserved_cash": 21256.06, "state": "PENDING" } ],
  "attempts": [
    { "at": "2026-09-29T14:45:54Z", "outcome": "NOT_YET",
      "detail": "观察到的交易日历止于 2026-09-29，T+1 尚未出现" }
  ],
  "created_at": "...", "updated_at": "..."
}
```

`execution_date` **不写进文件**，由结算时解析（那时日历里一定有了）。
`exec_rule` 记录的是**规则**（"下一个交易日开盘"），不是**日期**。

**F2 — 结算走同一条已经写对、但从未被走到的路径。**

`personal_quant/strategy/execution.py:60` 的 `t1_open_and_prev_close()`
**内部自己调 `next_trading_day(signal_date)`**，本来就是对的。
`_settle_pending` 只需把 **`signal_date`** 传进去，成交价自动落在正确的 T+1 开盘。
不需要新写任何 T+1 逻辑。

**F3 — 异常不再被吞。`_t1_has_data` 改为三态，原因必须落盘。**

```python
class T1Status(str, Enum):
    READY   = "READY"     # T+1 行情已存在          → 结算
    NOT_YET = "NOT_YET"   # T+1 尚未被观测到        → 保持 PENDING（正常）
    ERROR   = "ERROR"     # 查询本身出错            → **raise**，不返回 False
```

**NOT_YET 与 ERROR 的判定必须显式，不能靠 try/except 猜**（这是本次修复的核心）：

```text
nxt = min{ c ∈ 已观测日历 : c > signal_date }
  ├─ 不存在          → NOT_YET      （T+1 还没被观测到；日历里没有就是还没到）
  └─ 存在 = nxt
       ├─ nxt 有该股 bar  → READY   （可结算）
       └─ nxt 无该股 bar  → 终态 NO_FILL(reason="no_bar")
            理由：nxt 出现在日历中 ⇒ 该日市场有成交、数据已入库；
            某只股票当天没有 bar ⇒ 它当天就是没交易（停牌），
            真实挂单一样不会成交。这是**可判定**的，不是"等待"。
```

真正的数据访问失败（DB 不可用、schema 变化）→ **ERROR → raise**。
`except Exception: return False` 在本模块**全面禁止**。

**F4 — 挂单文件改为「读-改-写 + 幂等」，绝不整体覆盖。**

```text
读现有 pending
  → 逐单 reconcile（已 SETTLED 的移入 ledger，仍 PENDING 的保留）
  → 追加本次新产生的 order（按 order_id 去重）
  → 写回
```

- `order_id = f"{experiment}:{signal_date}:{symbol}:{side}"` —— **稳定、可复现**。
  同一 `(rule_version, signal_date, symbol, side)` 不得重复创建。
- 每次尝试（无论成功失败）**追加**一条 `attempts[]`。失败也要留痕。
- **PENDING 不会因为程序再次运行而丢失。**

**F5 — 账本是真相，`paper_portfolio.json` 是缓存。**

`store.py` 自己的 docstring 已经写明"状态是指针，不是记录"。据此：
结算记录**先**写账本，再更新 portfolio 指针；崩溃后可用
`rebuild_portfolio_from_ledger()` 自愈。启动时校验
`state.cash == ledger 重算值`，不一致 → **报错，不自动改数**。

#### 影响面

- `paper_live/engine.py`：`run_day` 第 0.5 / 5 步、`_t1_has_data`、`_settle_pending`、`_next_trading_day`
- `paper_live/data.py`：`prices()` 的日期取值路径（不再接受 NaT）
- `pipeline/daily.py:543-544`：`run_day` 调用点
- `scripts/paper_live/run_daily.py:36`

---

### 2.2 C2 —— 每一天都被判成调仓日（🔴 CRITICAL）

#### 真实根因（比"窗口写错"更深一层）

`paper_live/engine.py:97-106`：

```python
lo = (d - pd.Timedelta(days=70)).strftime("%Y-%m-%d")
dates = rebalance_dates(lo, d.strftime("%Y-%m-%d"), rb["frequency"], rb["rule"])
return bool(dates) and pd.Timestamp(dates[-1]) == d
```

`rebalance_dates` 的实现（`strategy/rebalance.py:44-50`）是
`trading_days(start, end)` → 按周期分组 → **`g.iloc[-1]`**。
当 `end == d` 时，最后一个 group 是"被窗口截断的当月"，它的最后一个元素
**恒等于 `d` 自己**（只要 `d` 是交易日）。所以：

> **`is_rebalance_date` 对任何交易日恒返回 True，对非交易日返回 False。**

实证（2026-08，一个**已经完整结束**的月份，可与回测参照物逐日比对）：

| | 与回测参照物不一致的交易日 |
|---|---|
| 现行实现 | **20 / 21 天全部误判**（只有 08-31 这天碰巧对） |
| 下述修法 | **0 / 21** |

**但更深的根因是：系统里根本没有"未来交易日历"**（§2.1 实测）。
`trading_calendar` 表止于最后一个**已发生**的交易日。
因此"d 是不是本月最后一个交易日"这个问题，**在 d 当天无法回答** ——
回答它需要知道 d 之后同月还有没有交易日，而那个知识不在数据里。

#### 修复设计（已实证）

```python
def is_rebalance_date(date, cfg, calendar) -> bool:
    """d 是否是**本月的最后一个交易日**。

    只用【已观测到的】交易日历，不引入任何未来数据，也不查 DB。

    语义与 backtest 的 rebalance_dates(完整区间) 在日历完整时**逐位一致**；
    日历尚未覆盖到 d 之后时**保守返回 False**（"本月是否结束"尚不可知），
    而不是猜。
    """
    d = pd.Timestamp(date)
    if d not in calendar:
        return False                       # 非交易日
    nxt = calendar[calendar > d]
    if len(nxt) == 0:
        return False                       # 尚未观测到下一个月 → 不可判定
    return (nxt[0].year, nxt[0].month) != (d.year, d.month)
```

**实测验证**（真实日历 + 回测参照物）：

| 日期 | 现行实现 | 修法 | 回测参照物 |
|---|---|---|---|
| 2026-08-28 | True ❌ | False | False |
| 2026-08-31 | True | **True** | True |
| 2026-09-18 | True ❌ | **False** | False |
| 2026-09-24 | True ❌ | **False** | False |
| 2026-09-29 | True ❌ | **False** | （见下） |

- 2026-08 全月 21 个交易日：修法与参照物 **0 处不一致**。
- 2026-09-29：参照物（在"数据止于 09-29"的假设下）说 True，修法说 **False**。
  两者**都对**，只是在回答不同的问题 ——
  修法回答的是"**此刻可确认吗**"，参照物回答的是"**事后回看是不是**"。
  真实的九月最后交易日是 **09-30**（周三，非节假日），库里没有这一天，
  所以 09-29 本来就不该调仓。修法给出的 False 才是正确答案。

> **⚠️ 一处必须记录的排除**
> 排查过程中曾提出另一种修法："传完整月份窗口 `[月初, 月末]` 做成员判断"。
> **实测该修法对 2026-09-29 返回 True**（因为 `trading_days` 查 DB 时
> 09-30 根本不存在，截断问题原样保留），与指定测试冲突。**不采纳。**

#### 操作性后果（必须写清楚）

调仓日只能在**下个月的第一个交易日**被确认。因此引擎需要区分
**运行日**与**信号日**，并新增：

```python
def rebalance_signal_date(run_date, cfg, calendar) -> Optional[pd.Timestamp]:
    """在 run_date 运行时，应当补做的调仓的信号日；没有则 None。

    若 run_date 是本月的第一个交易日 → 返回上一个交易日
    （= 上个月的最后一个交易日，此时已可确认）。
    """
```

- `run_day(run_date, signal_date=None)`：默认 `signal_date = run_date`。
- `pipeline/daily.py:703-710` 的 `_is_rebalance` → 改调 `rebalance_signal_date`。
- 执行仍走 `execute_order(symbol, signal_date, ...)` ——
  它内部的 `next_trading_day(signal_date)` **正好就是今天**，天然正确，无需改动。
- 观测文件按 **run_date** 命名（"哪天发生了什么"）；
  `metrics` 里**同时**记 `signal_date` 与 `execution_date`。
- **不引入未来数据**：信号只用到 ≤ signal_date 的行情/特征；成交价是今天已经发生的开/收盘价。

#### 不修改什么

- `personal_quant/strategy/backtest.py:87-88`（完整区间用法）**一字不动**
- `personal_quant/strategy/rebalance.py::rebalance_dates` **一字不动**
- `factors/base.py::cached_rebalance_dates`、`portfolio/rebalance.py` **一字不动**

#### 备选方案（B）及其否决理由

把规则从 `rule: last_trading_day` 改成 `rule: first_trading_day`
（在 d 当天即可纯函数判定，无需等待）。**更简单，但改变了策略语义** ——
必须新开 v1.1，不能在 v1.0 里悄悄改。**不采纳。**

#### 顺带确认（不在本次范围）

`pipeline/scheduler.py:46-47` 的 `monthly_rebalance` 任务声明了 `day=1`，
但 `is_due()`（:73-77）**只比较月份是否变化**，`day` 字段从未被读取。
这是**另一个子系统**的同名概念缺陷，本次**只记录、不修改**。

---

### 2.3 C3 —— 特征缓存会静默返回错误日期的横截面（🔴 CRITICAL）

#### 现状

`data/derived/features/YYYY-MM.parquet` 是**按月命名的单日横截面**：

- 写入时把 `datetime` 列 drop 掉（`features.py:75-76`）→ 文件里**没有任何日期字段**
- 文件名只有 `%Y-%m`（`features.py:84`）→ **不含日**
- 读取时**不校验**请求日期（`features.py:217-224`）→ `out[d] = sub` 把整份文件原样当作 `d` 的横截面
- 同一个月的**多个日期会互相覆盖**：后写的赢

即：**文件按"月"命名，内容却是"某一天"，且这一天是谁无从查证。**

实证（审计阶段已独立复现）：`2026-09.parquet` 的内容经 KMID 逐票反解，
唯一匹配 **2026-09-29**（2982 行，最大偏差 6.8e-08）。
抽样复核 2015-01 / 2020-06 / 2024-02 / 2025-12，内容分别是各月**最后一个交易日**
（2015-01-30 / 2020-06-30 / 2024-02-29 / 2025-12-31，偏差 ~5e-8）。

> **这只能算是"多年来的惯例，不是设计保证"** —— 132 个月度文件里，
> 只有 5 个被逐一验证过内容日期。任何一次"同月不同日"的写入都会
> **静默改变**后续所有 `cache=True` 读者的输入，且没有任何告警。

#### ⚠️ 两条必须一并处理的伴生缺陷

**(a) `cache=False` 并不安全 —— 它照样写共享缓存。**

`features.py:252-256`：重算之后**仍然落盘到共享的月文件**，并在读回时
从同一路径取。因此：

```text
cache=False 的调用方（如 pipeline/signals.py:99）
    自己拿到的是对的  ✅
    但它把月文件改写成"自己那一天"  ❌
    于是所有 cache=True 的读者（paper_live 等）拿到的是它的数据
```

**这正是 2026-09-18 / 09-24 两次观测吃到错误日期特征的机制。**

⇒ 修复必须**同时改写入路径**，只加"读时断言"是不够的。

**(b) 同一次调用传入同月多个日期 → 全部拿到最后一天。**

`features.py:75-84` 对每个日期各写一次同名文件（后者覆盖前者），
`features.py:253-256` 再对每个 `d` 都读回同一个文件。
**当前调用方恰好都传单日期或月末日期，所以尚未触发**，但这是同一根因的第二个出口。
按日期存储后，此缺陷**由构造消除**。

**(c) 有过一次真实事故，且已被记录。**

`tests/strategy/test_no_future_leakage.py:17-24` 的注释记载：
该测试曾把 `2024-01.parquet`（4943 行）覆盖成 2 行。现场证据仍在：
`data/derived/features/2024-01.parquet.corrupt-20260920`（102,109 B）。
**同一种失效模式已经真实发生过一次。**

**(d) 两个"检测不到本缺陷"的审计点（说明为什么它一直没被发现）。**

| 位置 | 为什么检测不到 |
|---|---|
| `scripts/audit_point_in_time.py:100-105` | 只 `glob` 数文件个数，不读内容 |
| `pipeline/freshness.py:180-190` `features_latest()` | 只看 mtime |
| `paper_live/audit.py:99-104` 的"特征审计" | 只看 shape |

⇒ 本设计必须新增**能发现它的检查**（§13.4 的 T-26 ~ T-30），否则修完仍然没有守卫。

**(e) 🔴 当前状态下，重放任何非当月的日期 = 真实的前视泄漏。**

必须把两件事分清：

| | 内容 | 性质 |
|---|---|---|
| **当时发生了什么** | 09-18 观测写入时，文件里是 09-17 的数据 | 用了**更旧**的特征（保守方向），**无泄漏** |
| **今天重放会怎样** | `2026-09.parquet` 现在装的是 **09-29**。今天跑 `run_day(2026-09-18)` 会拿到 09-29 的横截面 | **真实的未来数据泄漏** |

也就是说：**这个缺陷在"当天正着跑"时是保守的，在"事后回放/补跑"时是泄漏的。**
历史验证（`scripts/paper_live/validate_engine.py`、`experiments/paper_live/engine_validation/`）
走的正是回放路径 —— 只要它的日期落在**同一个有文件的月份**里，就会吃到错误日期。

⇒ **PHASE 4 修复完成前，禁止任何形式的特征回放/补跑。**
⇒ 这条约束要写进 `run_daily_exit_paper.py` 的启动守卫：
检测到所请求日期的缓存契约不成立时**拒绝运行**，而不是警告后继续。

#### 修复设计：统一的可验证缓存契约

**契约（Contract）**

```text
FeatureRequest(date=T)
      ↓
Cache lookup（路径里带日期，见下）
      ↓
Parse metadata → stored_feature_date
      ↓
stored_feature_date == T  ?
      ├─ 是 → 返回
      └─ 否 → **FAIL LOUDLY**（raise FeatureCacheDateMismatch）
               不得回退、不得静默重算后仍声称命中
```

**存储形式：两层保险**

1. **路径带日期**：`data/derived/features/feature_<YYYY-MM-DD>.parquet`
   —— 文件名即契约，同月不同日不再可能撞车。
2. **文件内写 `feature_date` 列**（单值）+ parquet metadata
   —— 即使文件被复制、改名、手工搬运，仍然自描述。

**写入路径也必须改（否则修不干净）**

```text
requested dates = [d1, d2, ...]
      ↓
每个日期**各自**写 feature_<d>.parquet      ← 不再有"同名覆盖"
      ↓
写前断言：待写内容的 feature_date 列 == 文件名里的日期
```

这一条同时消灭了伴生缺陷 (a) 与 (b)：
`cache=False` 的重算结果**只写它自己那一天的文件**，
不可能再污染别人的输入。

**读取时断言**（唯一的放行条件）：

```python
stored = pd.read_parquet(p, columns=["feature_date"])["feature_date"].iloc[0]
if pd.Timestamp(stored) != pd.Timestamp(requested):
    raise FeatureCacheDateMismatch(
        f"请求 {requested} 的特征，文件 {p.name} 内记录的是 {stored} —— "
        f"拒绝使用（宁可重算，不可错用）")
```

**回退行为**：日期不匹配 = **视为未命中**，重算该日期并写**它自己的**新文件。
**绝不**返回错误日期的数据，**绝不**覆盖别的日期的文件。

**边界情形**（必须处理，否则会造出空文件污染）：

请求日**不是交易日**（无行情）时，重算会得到空结果。此时
**不写文件**，并在返回里显式标记 `no_data`。
（历史上前述 2024-01 事故正是"非交易日重算 → 写出 2 行 → 覆盖了整月"。）

**列集合的确定性**：`features.py:257-258` 的 `ALPHA158_COLS` 取自**第一次
读到的文件**，不同月份文件的列集合若有差异会影响后续。按日期存储后，
每次读取都要**显式校验列集合 == 该次计算的列集合**，不一致 → raise。

#### 迁移与兼容

| 项 | 处理 |
|---|---|
| 旧文件 `data/derived/features/YYYY-MM.parquet` | **保留不删**（是缺陷证据，也是历史记录）；新代码**永不读取** |
| 新文件 | 首次请求某日期时重算并落盘，一次性成本 |
| 生产每日运行 | 每天只请求 1 个日期（信号日），与旧逻辑的"每月重算一次"成本相当 |
| 特征计算逻辑 | **一字不改**（只改缓存契约，不改 Alpha158 与因子定义） |

#### 影响面（完整清单，来自只读排查）

修复契约只有一处实现（`features.py`），但**必须先列清全部入口**，
否则"改了核心、漏了旁路"会让新契约变成一纸空文。

**(A) 经 `compute_features` / `build_training_data`**

| # | 位置 | 日期来源 | cache | 风险 |
|---|---|---|---|---|
| A1 | `paper_live/data.py:108` `feature_matrix` | CLI `--date` / 最近交易日 | **True** | 🔴 **会受影响**（同月任意日都命中同一文件） |
| A2 | `pipeline/signals.py:99` `compute_signals` | 最近交易日 | False | 🟠 **自身输出正确，但会写覆盖月文件** —— 正是污染 A1 的源头 |
| A3 | `scripts/generate_recommendation.py:69` | `--date` 必填 | False | 🟠 同 A2 |
| A4 | `scripts/portfolio/generate_v2_recommendation.py:60` | `--date`（默认 2026-09-04） | False | 🟠 同 A2 |
| A5 | `scripts/news/generate_news_recommendation.py:53` | `--date` 必填 | False | 🟠 同 A2 |
| A6 | `scripts/_smoke_strategy.py:39` | 2015 月末 | False | 🟠 同 A2 |
| A7 | `scripts/backtest_strategy.py:127` + `features.py:320`（`build_training_data` 默认 `cache=True`） | 回测月末 | True | 🟡 当前不受影响（月末），**非设计保证** |
| A8 | `scripts/backtest_ablation.py:199` | 回测月末 | True | 🟡 同上 |
| A9 | `scripts/portfolio/build_alpha_predictions.py:103` | 研究年末月 | True | 🟡 同上 |
| A10 | `scripts/portfolio/run_micro_ablation.py:111` | time_split 月末 | True | 🟡 同上 |
| A11 | `scripts/news/run_news_strategy.py:75` | time_split 月末 | True | 🟡 同上 |
| A12 | `scripts/news/run_news_ablation.py:133` | time_split 月末 | True | 🟡 同上 |
| A13 | `scripts/research_portfolio.py:105` `build_predictor` | valid/test 月末 | True | 🟡 同上 |
| A14 | `scripts/sanity_check_strategy.py:60` | 写死 2019–2024 月末 | True | 🟡 同上 |

> 🟡 的含义：**当前没事，但没有任何东西保证它没事**。
> 任何一个研究脚本哪天改了日期，它会静默吃错，且无人知晓。

**(B) 直接读月文件（绕过 `compute_features`，与核心读路径同病）**

| 位置 | 说明 |
|---|---|
| `scripts/research_independent_info.py:139` `_load_alpha158` | 自拼 `%Y-%m` 路径、只判存在、无校验 |
| `scripts/run_incremental_factor_selection.py:88` `load_alpha158` | 同上 |

**(C) 只看文件名/mtime，检测不到本缺陷**

`scripts/audit_point_in_time.py:100-105`、`pipeline/freshness.py:180-190`

**(D) 不受影响（已确认）**

- `scripts/quant/write_recommendation_note.py` —— 不碰特征，只读已落盘的信号快照
- `factors/` 包 —— 读的是 `data/derived/factors/*`，`use_cache` 是进程内 memo
- `tests/strategy/test_no_future_leakage.py` / `test_quarter_worker_retry.py` —— 已 monkeypatch 隔离

**(E) 悬空配置**

`config/strategy_v1.yaml:42` 的 `cache_dir: data/derived/features` ——
全仓库**没有任何 Python 读取这个键**。修复时**保留原样**（不改配置），
只在文档中注明它已失效。

#### 实施纪律

- 新契约的实现**只有一处**（`features.py`），所有入口自然继承。
- 但 A13/A14 这类"当前恰好没事"的入口**必须逐个核对**，
  不能因为"现在是对的"就跳过。
- 配一条**仓库级断言测试**（T-27）：grep 全部源码，
  任何 `data/derived/features` 的手工路径拼接都必须消失或改走新接口。

#### 与 `labels` 的对比

`data/derived/labels/` **按日命名**，且 CLAUDE.md 明确写着"勿改回月键"。
特征缓存当初选月键、又 drop 掉日期，是一个**已知教训的重复**。
本次修复就是把特征缓存对齐到 labels 的做法。


---

## 3. Execution State Machine（执行状态机）

### 3.1 持仓状态

```text
                    ┌──────────────┐
                    │ PENDING_ENTRY│   T 日收盘后建单；exec_date 未知
                    └──────┬───────┘
        T+1 开盘限价成交     │      T+1 未触及限价 / 停牌 / 涨跌停
        ┌──────────────────┴──────────────────┐
        ▼                                     ▼
   ┌─────────┐                          ┌──────────┐
   │  OPEN   │  持仓中，每日检查出场      │ NO_FILL  │  终态：本次入场作废
   └────┬────┘                          └──────────┘
        │  触发 target / stop / time_stop
        ▼
   ┌──────────────┐
   │ PENDING_EXIT │  出场信号已触发，等待成交
   └──────┬───────┘
          │  成交
          ▼
     ┌─────────┐
     │ CLOSED  │  终态：已平仓，资金回到 cash
     └─────────┘

   任何状态 ──用户显式取消──▶ CANCELLED（终态）
```

### 3.2 状态定义（逐条，无歧义）

| 状态 | 含义 | 进入条件 | 可否离开 |
|---|---|---|---|
| `PENDING_ENTRY` | 入场单已创建，**尚未成交** | T 日收盘后生成买单 | 是 |
| `OPEN` | 已持仓 | T+1 限价成交 | 是 |
| `PENDING_EXIT` | 出场已触发，尚未成交 | target/stop/time_stop 任一触发 | 是 |
| `CLOSED` | 已平仓 | 出场成交 | **否（终态）** |
| `NO_FILL` | 入场未能成交 | T+1 未触及限价 / 停牌 / 涨跌停 | **否（终态）** |
| `CANCELLED` | 用户显式取消 | 手工操作 | **否（终态）** |

**关键约束**

- `NO_FILL` **是终态，不重试**。真实世界里"今天没买到"就是没买到，
  明天再买就变成"用明天的信号做今天的决定"。下一次入场要到下一个
  signal cycle 重新走完整流程。
- `PENDING_ENTRY` **不得因为"T+1 行情还没到"被判为 NO_FILL 或 FAILED**。
  数据没到 ≠ 没成交（见 §2.1 F3 的三态判定）。
- `OPEN` 状态下**禁止卖出**，直到 `entry_exec_date` 之后的第一个交易日
  （A 股 T+1 制度，见 §4.3）。


---

## 4. Event Timeline（事件时间线）

### 4.1 正常路径

```text
T 日（信号日）收盘后运行
  ├─ 计算 ≤T 的特征 → S3 打分 → Top-K 候选
  ├─ 生成 target/stop/time_stop（一次性，见 §6）
  ├─ 生成入场单：limit = entry_high(T)，shares 按 limit + 预估费用反算
  ├─ reserved_cash += 每单预估资金占用
  ├─ 状态 → PENDING_ENTRY，写 ledger（只写，不结算）
  └─ 记录 attempts: NOT_YET（T+1 尚未观测到）

T+1 日（任意时刻运行）
  ├─ 结算 PENDING_ENTRY：
  │    open ≤ limit          → FILLED @ open      （价格改善）
  │    open > limit, low ≤ limit → FILLED @ limit （盘中触及）
  │    open > limit, low > limit → NO_FILL（终态）
  │    无 bar（停牌）        → NO_FILL（终态）
  │    开盘涨停              → NO_FILL（终态）
  ├─ 成交者：状态 → OPEN；锁 target/stop/time_stop；扣 cash、释放 reserved
  └─ T+1 **不做任何出场判断**（T+1 制度）

T+2 起，每个交易日运行
  ├─ 先结算所有 PENDING_EXIT
  ├─ 再对每个 OPEN 持仓按**当日 OHLC** 判出场（见 §4.2 / §8）
  ├─ 触发者 → PENDING_EXIT，次日（或当日，见 §8.3）成交
  └─ 未触发者 → 更新 mark price / holding_days（**只更新这两个字段**）

出场成交
  ├─ cash += proceeds − sell_fee      （卖出资金**当日可用**）
  ├─ 状态 → CLOSED
  └─ 释放的现金进入下一轮入场的可用资金
```

### 4.2 出场判定的可判定性

日线 OHLC 下，resting order（挂着的止盈/止损单）的成交价**是可判定的**：

```text
止损单（sell stop @ S）：
    open ≤ S           → 跳空穿过，成交价 = open   （更差，如实记录）
    open > S, low ≤ S  → 盘中触及，成交价 = S
    low > S            → 未触发

止盈单（sell limit @ Tg）：
    open ≥ Tg          → 跳空穿过，成交价 = open   （更好，如实记录）
    open < Tg, high ≥ Tg → 盘中触及，成交价 = Tg
    high < Tg          → 未触发
```

**这不是"假装知道盘中先后顺序"** —— 它只用了 OHLC 里确实存在的信息，
且对"跳空"情形一律采用**实际开盘价**而非挂单价，方向上是保守的。

### 4.3 同日禁卖（A 股 T+1 制度）

T+1 开盘买入的股票，**当天不能卖出**。这不是建模选择，是交易所规则。
因此：`entry_exec_date` 之后的第一个交易日才可以进入出场判定。

### 4.4 同日 target 与 stop 同时成立（§13 专项）

当 `high ≥ target` **且** `low ≤ stop` 同一天成立时，日线**无法知道先后**。
本实验采用**保守解**，详见 §8.3。


---

## 5. Order Lifecycle（订单生命周期）

| 状态 | 含义 | 是否终态 |
|---|---|---|
| `CREATED` | 订单已生成，尚未进入挂单文件 | 否 |
| `PENDING` | 已挂出，等待成交判定 | 否 |
| `FILLED` | 已成交（全量） | **是** |
| `PARTIAL` | **不支持** | — |
| `EXPIRED` | 超过有效期仍未成交 | **是** |
| `CANCELLED` | 用户取消 | **是** |

### 5.1 `PARTIAL = unsupported`（明确声明，不伪造）

本实验**不建模部分成交**。理由：日线数据不足以判断一笔委托在盘中成交了多少手；
凭开盘价与成交量去猜"成交了 60%"是**编造**。

代码层面显式声明：

```python
PARTIAL_FILL_SUPPORTED = False   # 明确：本执行模型不支持部分成交
```

所有成交都是**全量成交或全量不成交**。若将来接入分钟数据，再新开版本。

### 5.2 `EXPIRED` 的适用范围

**入场单不过夜。** `PENDING_ENTRY` 在 T+1 的判定结果只有三种：
`FILLED` / `NO_FILL`（终态）/ 尚未观测到 T+1（保持 `PENDING`）。
**不存在"挂 3 天等更好的价"** —— 那需要真实券商支持的挂单有效期，
本实验不建模。

`PENDING_EXIT` 同理：触发后到成交为止；若成交日**停牌**导致无法卖出，
则保持 `PENDING_EXIT` 并每日重试，同时记为 `EXPIRED`-risk 状态
（停牌无法卖出是真实的，不是系统的失败）。


---

## 6. Target / Stop Snapshot（目标价 / 止损快照）

### 6.1 锁定时点

**在 `PENDING_ENTRY → OPEN` 的那一刻锁定**（即入场成交时），
而不是信号日生成时。理由：

- 信号日算出的 target/stop 是基于**计划价 plan_price**；
- 实际成交价可能落在 `[entry_low, entry_high]` 内任意位置；
- 用**实际成交价**重算，target/stop 才与真实持仓成本一致。

但为避免"成交后再算"引入口径争议，**两项都记录**：

```json
{ "symbol": "600519.SH",
  "entry_signal_date": "2026-09-29",
  "entry_exec_date": "2026-09-30",
  "entry_price": 12.34,
  "entry_shares": 1800,
  "entry_fee": 4.63,
  "plan_price": 12.30,
  "at_signal": { "target_price": 13.10, "stop_loss": 11.42,
                 "time_stop_days": 40, "expected_return": 0.0651,
                 "vol": 0.0214, "risk_profile": "balanced" },
  "at_entry":  { "target_price": 13.14, "stop_loss": 11.45,
                 "time_stop_days": 40 },
  "locked_at": "2026-09-30",          // ← 锁定后**永不改变**
  "rule_version": "daily_exit_paper_v1.0" }
```

**`at_entry` 是唯一生效的口径**，`at_signal` 仅作留痕（回答"成交价差了多少"）。

### 6.2 锁定后不得修改（铁律 + 代码级守卫）

每日重算信号时**绝不允许**改动已有持仓的 target/stop/time_stop。
原因：那等于每天用最新价格"重新优化"出场线，是把未来信息泄回决策。

**代码级守卫**：持仓更新函数只允许写白名单字段：

```python
_MUTABLE_POSITION_FIELDS = frozenset({
    "last_price", "market_value", "holding_days", "unrealized_pnl",
    "mark_date",
})
# target_price / stop_loss / time_stop_days / entry_* 一旦写入即冻结
```

写入白名单外的字段 → **raise**。配测试 T-20 断言。

### 6.3 公式来源（复用，不新写）

```text
entry_band   ← trade_plan/plan.py:103-119   (half = min(entry_band×vol, 3%))
target/stop  ← trade_plan/plan.py:122-135
                 target = plan_price × (1 + expected_return × target_scale)
                 stop   = plan_price × (1 − stop_sigma × vol × √(horizon/20))
                 stop   = max(stop, plan_price × 0.70)
                 time_stop_days = horizon × 2
```

**风险档 = `balanced`**（`trade_plan/plan.py:221` 的既有默认值），**不是新选的**。


---

## 7. Cost Model（成本模型）

### 7.1 唯一来源

```python
from personal_quant.strategy.costs import TransactionCostModel
model = TransactionCostModel.from_config({"transaction_costs": s["transaction_costs"]})
```

参数取自 `config/daily_exit_paper_v1.yaml` 的 `transaction_costs` 块，
**数值与 `config/paper_live.yaml:69-74` 逐字相同**（佣金 0.025%、最低 5 元、
印花税 0.05% 仅卖出、过户费 0.001%、滑点 0.05%）。

**禁止第二套费率表。** 任何地方出现 `0.00025` 这样的字面量都是 bug。

### 7.2 逐笔口径（与账本**必须**一致）

```text
entry_fee = buy_cost(entry_value)              = 佣金 + 过户费 + 滑点
exit_fee  = sell_cost(exit_value)              = 佣金 + 印花税 + 过户费 + 滑点
gross_pnl = (exit_value − entry_value)         方向：卖出为正
net_pnl   = exit_value − exit_fee − entry_value − entry_fee
```

`buy_cost` / `sell_cost` **自带滑点**（`costs.py:38`），因此
**成交价不再另行加滑点**，避免重复计费。

### 7.3 预估口径与账本口径必须一致

审计 HIGH-7 发现现有 `trade_plan/plan.py` 存在**单边 vs 双边**的口径分裂
（`:493-495` 的 `estimated_fees` 单边，`:400-406` 的 `expected_net_return` 双边），
且按"目标持仓"而非"交易差额"累加。

**本实验不继承该缺陷**：

- 本实验自己计算 `estimated_fee`，**只对实际要成交的差额**、**双向对称**；
- 断言 `abs(estimated_fee − ledger_fee) / ledger_fee < 1e-6`
  （同一 value 输入必须得到同一 fee）；
- 副产物：这条断言会**顺带证明**成本模型没有被复制成第二套。

> `trade_plan/plan.py` 的 HIGH-7 **属于另一个子系统**，本次**只记录、不修改**。


---

## 8. Cash Accounting（现金核算）

### 8.1 五个量，定义互不重叠

| 量 | 定义 |
|---|---|
| `cash` | 账本余额（含已成交与已实现费用的净额） |
| `reserved_cash` | Σ 未成交买单的**预估资金占用**（含预估费用） |
| `available_cash` | `cash − reserved_cash` |
| `position_value` | Σ `shares × mark_price` |
| `portfolio_value` | `cash + position_value` |

> **注意**：`portfolio_value` 用 **cash** 而非 available_cash ——
> 预留只是"计划占用"，钱还在账上。

### 8.2 状态转移（逐条）

| 事件 | cash | reserved_cash | 说明 |
|---|---|---|---|
| 建入场单 | — | `+= shares×limit + buy_cost(...)` | 按**限价**预留（最坏情况） |
| 买单成交 | `−= filled×fill_px + buy_fee` | `−= 该单预留额` | 实际 ≤ 预留（成交价 ≤ limit） |
| 买单 NO_FILL | — | `−= 该单预留额` | 释放 |
| 卖单成交 | `+= filled×fill_px − sell_fee` | — | **资金当日可用**（A 股 T+0 资金） |
| 用户手动注资 | `+= amount` | — | 记录为**外部流**，与盈亏分开 |

### 8.3 同日 target+stop 冲突的解决策略（🔒 保守）

**策略：`stop_first`（止损优先）。**

```yaml
resolution:
  same_day_target_and_stop: stop_first   # conservative
```

**配置 + 代码 + 报告 + 测试四处同时写入**：

1. **配置**：`config/daily_exit_paper_v1.yaml` 的 `resolution` 块（上面）
2. **代码**：`daily_exit_paper/engine.py` 显式分支，注释引用本节
3. **报告**：每次出场记录 `resolution_applied: "stop_first"` +
   `both_hit_same_day: true`，可统计有多少笔受此影响
4. **测试**：T-12 构造 `high ≥ target` 且 `low ≤ stop` 的一天，断言按 stop 成交

**为什么是 stop_first**：日线不知道先后。若假设 target 先到，
就是**系统性地高估收益**；若假设 stop 先到，是**低估**。
在一份"用来验证策略是否有效"的实验里，低估是安全的，高估是自欺。
**未来若接入分钟数据，再设计更精确的执行模型并新开版本。**

### 8.4 恒等式（全部写成测试）

```text
I1  cash ≥ 0                              （现金守卫，绝不允许透支）
I2  reserved_cash ≤ cash
I3  portfolio_value == cash + Σ shares × mark_price
I4  Σ(ledger 全部现金流) == cash − capital_initial
I5  Σ(每笔卖出 proceeds − fee) == 已实现盈亏 + Σ(已平仓买入成本)
```

**I4 是总对账公式**，PHASE 9/10 的 20 日 dry run 与现金对账以它为准。


---

## 9. Idempotency（幂等）

| 重复动作 | 行为 |
|---|---|
| 同一天运行两次 | 读 `runs/<date>.json`，已 `COMPLETED` → **直接返回，零写入**（沿用现有 `run_day` 幂等分支，`engine.py:146-160`） |
| 同一挂单重复结算 | 按 `order_id` 判重；已 `SETTLED` 的不再结算 |
| 同一 `(signal_date, symbol, side)` 重复建单 | `order_id` 相同 → **去重，不追加** |
| 重跑历史日期 | **拒绝**（`store.assert_time_order` 已实现，`store.py:227-233`） |

**状态文件写入纪律**：`pending_orders` / `portfolio` 一律
**读-改-写**，写前 diff，相同则跳过（沿用 `write_state` 的 state_log 机制）。

**崩溃恢复**：ledger 是真相，`portfolio.json` 是缓存。
启动时 `assert_portfolio_consistent()` 校验 I3/I4，不一致 → **raise**，
打印差异，**不自动修补**（自动修补会让"账错了"变成"账悄悄被改了"）。


---

## 10. Manual Override（人工干预）

### 10.1 三层独立保存（**不进 wealth DB**）

```text
experiments/daily_exit_paper_v1/
  recommendations/<date>.json   ① 系统建议（引擎写，写后只读）
  decisions/<date>.json         ② 用户决定（人工/CLI 写；缺省 = ADOPT_ALL）
  executions/<date>.json        ③ 实际执行（人工回填；缺省 = 按系统价成交）
  ledger.jsonl                  ④ append-only 账本（由 ①②③ 推导）
```

**范式借鉴 `wealth/decisions.py`**（`save_recommendation` /
`record_decision` / `record_execution` 三层留痕 + 滑点 + inside_band），
**但绝不 import wealth 模块、绝不写 `data/wealth/wealth.db`**
（CLAUDE.md：财富库与研究库严格分离）。

### 10.2 规则

- 引擎**永远只写 ①**。
- ②③ 缺省即"完全采纳系统建议"，**不产生额外文件** ——
  只有人为干预时才落盘，因此"被干预过"本身就是可检索的信号。
- 干预与系统建议的差异单独统计（`override_stats`：
  成交价滑点、股数偏差、跳过次数、额外卖出次数）。
- **绝不据干预结果自动调参**（top_k / target_scale / stop_sigma / horizon /
  入场折价 / 风险档 / 仓位规模）。改了任何一项 = **新建 v1.1**，
  老版本记录原样保留。

### 10.3 与"系统建议"的边界

`SIGNAL != ALLOCATION` 在人工层的延伸：
**"引擎建议什么"（①）与"人做了什么"（②③）永远可分离**，
因此可以回答"如果完全照系统执行会怎样"——这正是本实验存在的意义。


---

## 11. Experiment Isolation（实验隔离）

### 11.1 四个互不污染的数据集

```text
strategy_v2 / S3            config/*.yaml + experiments/news/strategy/model.txt
                            冻结只读 —— 本实验一个字节不改

历史回测结果                experiments/{factors,portfolio}/**、stats 产物
                            本实验不读不写

clean forward holdout       forward_holdout/**  （现有 monthly paper_live）
                            本实验**不读不写**（只读的只有 C 修复所需的日历）

daily_exit_paper_v1         experiments/daily_exit_paper_v1/   ← 唯一可写目录
```

### 11.2 代码级隔离

- `daily_exit_paper/` **不得 import `paper_live` 的任何模块**
  （两套执行语义必须彻底分开，避免"改一处影响两处"）。
  可共享的只有**纯函数与成本模型**：
  `personal_quant.strategy.costs`、`personal_quant.strategy.execution`。
- `daily_exit_paper/` **不得 import `duckdb` 之外的财富模块**，
  不得引用 `wealth/**`、不得触碰 `data/wealth/**`。
- 配 **AST 断言测试 T-31**（照 `webapp/pages.py` 已有的 AST 测试做法）：
  `daily_exit_paper` 源码中不出现 `forward_holdout`，也不出现 `wealth`。

### 11.3 为什么必须隔离

现有 `forward_holdout` 的 `config/paper_live.yaml` 冻结了 **500,000**
的回测口径本金；新实验用**用户指定的可投资金**（§12.4）。
两者混在一起，任何一个指标都会失去意义。
更进一步：**forward holdout 一旦被污染就洗不干净**（`store.py` 铁律 1）。


---

## 12. daily_exit_paper_v1 参数（冻结，v1.0）

### 12.1 全部参数（不得在实验期内改动）

```yaml
# config/daily_exit_paper_v1.yaml  （新增文件，PHASE 4 创建）
experiment: daily_exit_paper_v1.0
frozen_at: "<首次运行日>"

base_signal: strategy_v2          # S3 + equal_weight，冻结，继承不改
horizon_days: 20                  # = strategy_v2.label_horizon_days（继承）
top_k: 20                         # = strategy_v2.portfolio.top_k（继承）
risk_profile: balanced            # = trade_plan/plan.py:221 既有默认（继承）

entry:
  rule: next_session_open_limit   # T 收盘信号 → T+1 开盘限价
  limit_price: entry_high         # 限价 = 区间上沿（"最多愿意付到这里"）
  band_max_width: 0.03            # = plan.py entry_band 的既有上限（继承）
  lot_size: 100
  min_trade_value: 0.0

exit:
  target: on
  stop: on
  time_stop: on                   # time_stop_days = horizon_days × 2 = 40（继承）
  signal_exit: off                # 默认关闭：排名跌出 Top-K 不触发卖出
  no_same_day_exit: true          # A 股 T+1 制度（规则，非参数）

resolution:
  same_day_target_and_stop: stop_first   # 保守，见 §8.3

transaction_costs:                # 与 config/paper_live.yaml:69-74 逐字相同
  commission_rate: 0.00025
  min_commission: 5.0
  stamp_duty: 0.0005
  transfer_fee: 0.00001
  slippage: 0.0005
```

### 12.2 所有数值都是**继承**，不是新选

| 参数 | 来源 | 本实验是否新选 |
|---|---|---|
| `horizon_days = 20` | `config/strategy_v2.yaml:23` | ❌ 继承 |
| `top_k = 20` | `config/strategy_v2.yaml:29` | ❌ 继承 |
| `risk_profile = balanced` | `trade_plan/plan.py:39-48, 221` | ❌ 继承 |
| `band_max_width = 0.03` | `trade_plan/plan.py:104` | ❌ 继承 |
| `time_stop_days = 40` | `trade_plan/plan.py:133` | ❌ 继承 |
| `transaction_costs` | `config/paper_live.yaml:69-74` | ❌ 继承 |

**唯一新增的判断是"出场规则是否生效"，而这正是实验的自变量。**

### 12.3 版本纪律

- 任何**规则**变化（新增/删除出场条件、改 resolution、改限价定义）
  → **新建 `daily_exit_paper_v1.1` / `v2`**，新目录、新 config、新 ledger。
- **绝不允许覆盖 v1.0 的任何记录。**
- `config/daily_exit_paper_v1.yaml` 的 `freeze.sha256` 每次运行校验；
  不一致 → `DRIFT_DETECTED`，该日**不作为干净观测**。
  （复用 `paper_live/config.py` 的 `_strip_freeze_block` + `freeze_hashes`
  设计，但**独立实现**，不 import。）

### 12.4 本金：`--capital` 首次确定后**锁定**

本金来自 CLI 一次性指定（默认值 `config/account_profile.yaml` 的 `capital`，
当前 66,000），首次 `--execute` 时写入实验状态：

```json
{ "capital_initial": 66000.0, "locked_at": "2026-10-XX",
  "source": "--capital 66000" }
```

此后 `--capital` 与锁定值不同 → **拒绝运行并提示新建版本**。
理由：本金直接决定 `suggest_top_k`、手数与仓位规模；
允许中途改本金 = 允许中途改仓位规模 = 违反"不得调参"。

### 12.5 在 `strategy_v2` 之上，本实验**不新增任何买入规则**

入场只看 S3 的 Top-K 排序（与 monthly paper_live 完全一致），
唯一的差别是**入场方式**（限价 vs 市价）与**出场方式**（三层规则 vs 下次调仓）。
**没有新增筛选条件、没有新增因子、没有新增行业约束。**


---

## 13. Implementation Plan（文件级变更计划）

### 13.1 将修改（共享基础设施）

| 文件 | 改什么 | 对应 |
|---|---|---|
| `paper_live/engine.py` | `is_rebalance_date` 重写；新增 `rebalance_signal_date`；`run_day` 分离 run_date/signal_date；`_t1_has_data` 三态化；`_settle_pending` 不再吞异常 + 延迟解析 exec_date；pending 读-改-写 + order_id 去重 | C1, C2 |
| `paper_live/data.py` | `feature_matrix` 走带日期校验的缓存接口；`prices()` 拒绝 NaT 入参 | C1, C3 |
| `personal_quant/strategy/features.py` | 缓存契约：改按日期存储 + 写 `feature_date` + 读时断言 + `FeatureCacheDateMismatch` | C3 |
| `pipeline/daily.py` | `_is_rebalance` → `rebalance_signal_date`；`run_day` 调用点传 signal_date | C1, C2 |

### 13.2 将新增

| 文件 | 作用 |
|---|---|
| `config/daily_exit_paper_v1.yaml` | 冻结参数（§12.1） |
| `daily_exit_paper/__init__.py` | 包 |
| `daily_exit_paper/config.py` | 配置读取 + freeze 校验（独立实现） |
| `daily_exit_paper/state.py` | 持仓状态机 + 白名单写入守卫（§6.2） |
| `daily_exit_paper/execution.py` | 限价入场 / 三层出场的 OHLC 判定（§4.2 / §8.3） |
| `daily_exit_paper/ledger.py` | append-only 账本 + 恒等式 I1–I5 + `rebuild_portfolio_from_ledger()` |
| `daily_exit_paper/engine.py` | 单日编排 |
| `daily_exit_paper/report.py` | 实验报告 |
| `scripts/quant/run_daily_exit_paper.py` | CLI：`--capital / --date / --dry-run / --execute` |
| `tests/daily_exit_paper/` | 16+ 场景（§13.4） |
| `reports/daily_exit_paper_v1_design.md` | 本文档 |
| `experiments/daily_exit_paper_v1/` | **运行时生成**（不在 PHASE 3 创建） |

### 13.3 不允许修改

```text
config/strategy_v2.yaml                    冻结
config/strategy_v1.yaml                    冻结
config/paper_live.yaml                     冻结（哈希被 forward holdout 引用）
personal_quant/strategy/rebalance.py       回测语义正确，不动
personal_quant/strategy/backtest.py        同上
personal_quant/strategy/costs.py           成本模型唯一来源，只读引用
factors/base.py::cached_rebalance_dates    研究侧，语义正确，不动
portfolio/rebalance.py                     组合侧，语义正确，不动
trade_plan/plan.py                         本实验只**读取**其公式函数，不改
forward_holdout/**                         一个字节不动
experiments/**/*（既有产物）               一个字节不动
wealth/**  data/wealth/**                  绝不可触碰
pipeline/scheduler.py                      day=1 缺陷只记录、不修（§2.2）
```

### 13.4 将新增测试（17 组 / 33 条，超过 15 要求）

| # | 测试名 | 断言 |
|---|---|---|
| **C1 挂单** | | |
| T-01 | `test_entry_pending_when_t1_not_observed` | T 晚建单 → `PENDING`，**不判失败** |
| T-02 | `test_pending_survives_rerun` | 同日重跑，pending 单**不丢、不重复** |
| T-03 | `test_pending_survives_multiple_days` | 连续 N 日无 T+1 → pending 持续保留，attempts 累积 |
| T-04 | `test_entry_fills_when_t1_arrives` | T+1 数据到 → FILLED @ 正确开盘价 |
| T-05 | `test_error_raised_not_swallowed` | 数据访问异常 → **raise**，不返回 False |
| T-06 | `test_order_not_settled_twice` | 同一 order_id 结算两次 → 第二次为 no-op |
| T-07 | `test_pending_orders_reconciled_not_overwritten` | 旧批仍 pending 时新批加入 → 两批都在 |
| **C2 调仓日** | | |
| T-08 | `test_rebalance_midmonth_false` | 月中任意交易日 → False |
| T-09 | `test_rebalance_true_at_confirmed_month_end` | 已结束月份的最后一个交易日 → True（用 2026-08 全月逐日比对回测参照物，0 处不一致） |
| T-10 | `test_rebalance_weekend_boundary` | 月末落周末 → 识别为该月最后一个交易日 |
| T-11 | `test_rebalance_unconfirmed_is_false` | 日历止于 d → **False**（含 09-18 / 09-24 / 09-29 三个指定日期） |
| **出场** | | |
| T-12 | `test_target_hit_fills_at_target` | `high ≥ target` → 以 target 成交；`open ≥ target` → 以 open |
| T-13 | `test_stop_hit_fills_at_stop` | `low ≤ stop` → 以 stop 成交；`open ≤ stop` → 以 open |
| T-14 | `test_same_day_target_and_stop_resolves_to_stop` | 同日双触发 → **按 stop**（conservative） |
| T-15 | `test_no_same_day_exit` | 入场当日**不得**卖出 |
| T-16 | `test_time_stop_at_horizon_times_two` | 持有满 40 个交易日 → 退出 |
| T-17 | `test_signal_exit_disabled_by_default` | 排名跌出 Top-K → **不卖** |
| **幂等 / 状态** | | |
| T-18 | `test_rerun_same_day_idempotent` | 同日重跑 → **零写入** |
| T-19 | `test_target_stop_locked_at_entry` | 入场后重算信号 → target/stop **一字不变** |
| T-20 | `test_position_field_whitelist_enforced` | 写白名单外字段 → **raise** |
| **成本 / 现金** | | |
| T-21 | `test_sell_fee_includes_stamp_duty` | 买不含印花税、卖含；最低佣金 5 元生效 |
| T-22 | `test_estimated_fee_matches_ledger_fee` | 同一 value 的预估费 ≡ 账本费（< 1e-6） |
| T-23 | `test_available_cash_excludes_reserved` | I2 恒等式 |
| T-24 | `test_cash_recycling_same_day` | 当日卖出资金可在当日买入 |
| T-25 | `test_ledger_identity_i4` | Σ现金流 == cash − capital_initial |
| **缓存契约（读写两侧都要测）** | | |
| T-26 | `test_feature_cache_date_mismatch_raises` | 文件内日期 ≠ 请求日期 → **raise**，绝不返回错日期 |
| T-27 | `test_feature_cache_write_is_per_date` | 一次调用请求**同月两个日期** → 生成两个文件，各自内容正确，**互不覆盖**（消灭伴生缺陷 b） |
| T-28 | `test_cache_false_does_not_pollute_others` | A 用 `cache=False` 算 d1，B 用 `cache=True` 请求同月 d2 → B 拿到 **d2 自己的**数据（消灭伴生缺陷 a） |
| T-29 | `test_non_trading_day_writes_no_file` | 请求非交易日 → **不落盘**、返回 `no_data`，不产生空文件 |
| T-30 | `test_no_manual_feature_cache_paths` | 仓库级 grep：除 `features.py` 外无手工拼接 `data/derived/features` 路径 |
| **隔离** | | |
| T-31 | `test_experiment_isolation_ast` | `daily_exit_paper` 源码不含 `forward_holdout` / `wealth` |
| **回归** | | |
| T-32 | `test_strategy_v2_regression` | 修复后 S3 信号与回测锚点**逐位不变**（P0 等权 drift = 0.0000） |
| T-33 | `test_forward_holdout_untouched` | 三个观测文件 + `paper_portfolio.json` + `pending_orders.json` 哈希不变 |

### 13.5 既有测试套件

PHASE 7 必须先跑**全部旧测试**并全绿，再跑新增测试。已知会受影响的：

- `tests/market_data/`（含 `test_no_spurious_factor_jumps`）
- `tests/forward/`（两个文件显式传 `force_rebalance`，语义不变，但需确认）
- `tests/strategy/`、`tests/factors/`
- 若 `test_strategy_v2_regression` 有任何一位不同 → **停下来诊断，不得放行**


---

## 14. Migration / Data Compatibility Plan（迁移与兼容）

| 对象 | 处置 | 理由 |
|---|---|---|
| `forward_holdout/observations/2026-09-{18,24,29}.json` | **原样保留**，新增 sidecar（§15） | 是 bug 的证据，不是可修正的错误 |
| `forward_holdout/state/pending_orders.json` | **原样保留**，另存归档副本 + 标注 `LEGACY_ABANDONED` | 它的 signal 已失效、exec_date 为 null；**不追认成交** |
| `forward_holdout/state/paper_portfolio.json` | **不动**（保持 cash=500000, holdings={}） | 从未成交是事实 |
| `data/derived/features/*.parquet`（132 个月文件） | **保留不删**，新代码不再读取 | 一次性重算即可；删除会毁掉证据 |
| `data/derived/features/2024-01.parquet.corrupt-20260920` | **保留不删** | 是 2024-01 事故的现场，且已被 `.gitignore` 之外的规则覆盖不到；它是"同类失效已发生过"的证明 |
| `config/strategy_v1.yaml:42` 的 `cache_dir`（悬空键） | **保留原样** | 无任何读取者；改配置会动到 strategy_v1 的哈希 |
| `trading_calendar` / `data/derived/factors/calendar.parquet` | **不动** | 本来就没有未来日历，这是设计约束不是缺陷 |
| 数据库 schema | **无迁移** | 本实验不新增表、不改表 |
| 财富库 | **无操作** | 隔离铁律 |
| 新实验目录 | **运行时创建**，从零状态开始 | §0 纪律 3 |

**一次性成本**：特征缓存改为按日期后，每个**首次请求的日期**需要重算一次。
生产链路每天只请求 1 个日期，与现状（每月重算）量级相同。


---

## 15. Historical Observation Handling（已有 3 条观测的处置）

### 15.1 绝对不做的事

```text
✗ 删除      2026-09-18 / 2026-09-24 / 2026-09-29
✗ 覆盖      用新代码重跑后写回原文件
✗ 重新生成  把它们"修正"成看起来正常的记录
✗ 追认成交  把 pending 里的订单按今天的价格"补成交"
```

### 15.2 要做的事：新增 sidecar，不动原文件

```text
forward_holdout/observations/2026-09-18.json              ← 原文件，字节不变
forward_holdout/audit/2026-09-18.execution_validity.json  ← 新增
```

sidecar 内容：

```yaml
execution_validity: invalid
usable_as: evidence_of_bug          # 不可作为业绩样本
reasons:
  - C1_paper_live_no_fill
  - C2_rebalance_date_bug
  - C3_feature_cache_date_mismatch
feature_vintage:
  requested: "2026-09-18"
  delivered: "2026-09-17"           # 各日不同，逐日记录
  basis: "KMID 反解，最大偏差 6.8e-08"
lookahead: not_observed             # 明确：未发现未来数据泄漏
note: >
  C3 导致的是【错误日期的特征】，不是【未来数据】。经逐条重建时间线，
  三条观测实际使用的都是更旧的特征（保守方向），未发生泄漏。
split:
  pre_fix: true                     # 修复前
  post_fix: false
```

### 15.3 三条观测的确切性质

| 观测 | 实际使用的特征日 | 方向 | 结论 |
|---|---|---|---|
| 2026-09-18 | 2026-09-17 | 更旧 | 无泄漏，但日期错误 |
| 2026-09-24 | 2026-09-22 | 更旧 | 无泄漏，但日期错误 |
| 2026-09-29 | 2026-09-29 | 同日 | 无泄漏，日期正确 |

**C3 的表述纪律**（用户明确要求）：

```text
✅ 写：wrong-date feature cache, but no verified future-data leakage
❌ 不写：lookahead contaminated
```

### 15.4 分类与用途

- 归类为 **`historical invalid execution observations`**
- **不是** valid performance sample —— `n_fills = 0`，没有任何成交
- **不删除**，因为它们**证明 bug 存在**，是修复的合法性来源
- 修复后的观测进入 `experiments/daily_exit_paper_v1/`，
  与 pre-fix 观测在**物理上分离**，
  因此"修复前 / 修复后"永远可区分


---

## Explicit Non-Goals（明确不做的事）

```text
✗ 不重写 strategy_v2
✗ 不重新训练模型
✗ 不改变 S3（信号定义 / 因子集 / 模型文件）
✗ 不重新优化 target / stop（公式与风险档都继承既有值）
✗ 不改变 horizon_days / top_k 的定义
✗ 不把月度调仓改成每日调仓（那是另一个实验）
✗ 不做历史验证（historical validation 不在本实验范围）
✗ 不改变 benchmark（基准定义原样）
✗ 不回测未来结果后调参（前视调参 = 自欺）
✗ 不覆盖历史结果文件（append-only 铁律）
✗ 不把人工交易伪造进数据库（§0）
✗ 不把 daily_exit_paper_v1 混入 monthly paper_live（§11）
✗ 不新建第二套成本公式（复用 TransactionCostModel）
✗ 不新增未在 §12.1 列出的卖出规则
✗ 不在 forward 实验期间自动调参
      （top_k / target_scale / stop_sigma / horizon / 入场折价 /
        风险档 / 仓位规模 —— 全部锁定在 daily_exit_paper_v1.0）
✗ 不建模部分成交（PARTIAL = unsupported，明确声明而非伪造）
✗ 不接入券商 API / 不自动下单 / 不涉及真实资金
✗ 不修改 pipeline/scheduler.py 的 day=1 缺陷（只记录）
✗ 不修改 trade_plan/plan.py 的 HIGH-7 单双边口径问题（只记录）
✗ 不删除任何既有文件
```

---

## 附：本设计中的三处**独立验证**（非推理，已实测）

| # | 结论 | 验证方式 |
|---|---|---|
| 1 | 系统无未来日历 | `trading_calendar` 表 6481 行，max = 2026-09-29，`> 2026-09-29` 行数 = **0** |
| 2 | C2 修法正确 | 2026-08 全月 21 个交易日逐日比对回测参照物：修法 **0 处**不一致，现行实现 **20 处**不一致 |
| 3 | 另一种修法不成立 | "整月窗口做成员判断"对 2026-09-29 返回 **True**，与指定测试冲突 → 已排除 |
