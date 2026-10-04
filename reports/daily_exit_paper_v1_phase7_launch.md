# PHASE 7 LAUNCH REPORT

> 日期：2026-10-04 ｜ 版本：**v1.1.0**
> 上游：PHASE 1–6 全部 PASS
> **本阶段没有开始正式 forward trading。**

---

## 1. Code Freeze

**冻结对象：`daily_exit_paper_v1` 的全部交易规则。**

```text
strategy_v2 / S3 / horizon(20) / Top-K(20) / risk_profile(balanced) /
入场规则(limit=entry_high) / target 规则 / stop 规则 / time stop(40) /
成本模型 / 仓位规模 / T+1 规则 / 状态机 / 记账
```

从本版起，除非发现**真实 bug**，以上任何一项都不得修改。
改规则 = 新建 `daily_exit_paper_v1.1`（新目录、新账本），绝不改完继续叫 v1。

**代码冻结的落地方式**（不是靠自觉，是靠机制）：

| 机制 | 位置 |
|---|---|
| 配置哈希冻结 | `config/daily_exit_paper_v1.yaml` 的 `config_sha256` 在首次运行时写入 `experiment.json`，之后每次校验，漂移即 `ConfigDrift` |
| 冻结值自检 | `config.validate()` 拒绝任何被改过的 `top_k` / `horizon` / `time_stop` / `signal_exit` / `invest_target` |
| 本金锁定 | `--capital` 首次写入即锁定，改值直接拒绝 |
| 规则不变量测试 | `tests/daily_exit_paper/test_config_and_costs.py`（11 条） |
| incident 记录 | `experiments/daily_exit_paper_v1/incidents.md`（实验创建时自动生成，含四条纪律） |

**启动时的 git 状态会被写进实验元数据**（`git_commit` / `git_dirty` /
`working_tree`）—— 只看 commit 是不够的，工作区脏着的话 commit 并不代表
实际跑的代码。

## 2. Database State

| 项 | 值 |
|---|---|
| `trading_calendar` max（is_open） | **2026-09-30** |
| `daily_bars` max | **2026-09-30**（5,566 条 bar） |
| 已观测交易日总数 | **6,482 天**（2000-01-04 … 2026-09-30） |
| 按日期特征缓存 max | **2026-09-30**（`feature_2026-09-30.parquet`，2978 × 158） |
| 信号快照 | `signals_2026-09-30.parquet`（2978 只） |
| 预测快照 | `forecast_2026-09-30.parquet`（200 只 × 3 horizons） |
| 旧月度特征缓存 | 132 个，原样保留、新 loader 不读 |

**三者一致 → PASS。**

### §八 专项：2026-09-30 是否已正确入库

```text
trading_calendar 里有 2026-09-30 且 is_open : True
daily_bars 里 2026-09-30 的 bar 数          : 5,566
feature_2026-09-30.parquet                  : 存在，且 feature_date == 2026-09-30（命中）
signals_2026-09-30.parquet                  : 存在
forecast_2026-09-30.parquet                 : 存在
```

**PASS。** 未触发 §八 的 STOP。

### 本轮刷新记录（如实）

上游在 2026-10-03 发布了新快照（release `2026-10-04`），数据止于 **2026-09-30**。
本地当时还停在 09-29，因此按 §七 执行了 `refresh_all.py`。

**过程中发生了一次中断**：第一次后台执行在 `signal_refresh` 算出特征的中途
被后台任务的默认 30 分钟时限杀掉（我启动时没有指定更长的 `timeout`，是我的疏忽）。
此时 1–6 号作业已全部 SUCCESS、**行情与日历已经推进到 09-30**，只有信号/预测/
计划没算完。随后用 `--only signal_refresh,live_price_refresh,forecast_refresh,
portfolio_refresh` 补跑完成，退出码 0。

刷新后的数据状态：

```text
| domain     | latest     | status |
| Market Data| 2026-09-30 |   ✓    |
| Valuation  | 2026-09-30 |   ✓    |
| News       | 2026-09-29 |   ✓    |   （官方索引滞后约 5 天，属正常）
| Factors    | 2026-10-04 |   ✓    |
| Forecast   | 2026-09-30 |   ✓    |
| Portfolio  | 2026-09-30 |   ✓    |
```

**这次中断不影响实验**：实验目录当时不存在，没有任何实验状态被写坏。

## 3. Market Calendar

| 项 | 值 |
|---|---|
| 已观测交易日 | 6,482 天 |
| 最新已观测交易日 | **2026-09-30** |
| 它的下一交易日（**已观测**意义上） | **无 → `NEXT_SESSION_STATUS = NOT_YET`** |
| 实际下一交易日（交易所日历） | **2026-10-08**（国庆休市 10-01 ~ 10-07） |

**这正好演示了两个概念必须分开**：引擎只知道**已经拿到行情**的交易日，
所以 09-30 的"下一交易日"是 `NOT_YET` —— **这不是失败，不是 NO_FILL，
而是"还没发生"**。同理，10-08 收盘后运行时，日历里会有 10-08，
那时 `next_session(10-08)` 仍然是 `NOT_YET`，挂单保持 PENDING，
等 10-09 的数据到位后再判定成交。

日历边界另有验证（PHASE 6）：日历里**不含周末**；长假后首个交易日识别正确
（2026-05-06 劳动节后、2026-06-22 端午后、2026-09-28 中秋后）；
`next_session(周六) → 下周一`。

## 4. Feature Freshness

| requested | 文件 | 文件内 `feature_date` | 结果 |
|---|---|---|---|
| 2026-09-30 | `feature_2026-09-30.parquet` | 2026-09-30 | **HIT** ✅ |
| 2026-09-29 | `feature_2026-09-29.parquet` | 2026-09-29 | **HIT** ✅ |
| 2026-09-28 | 不存在 | — | 未缓存（会重算） |

- `max(feature_date_used) <= requested_date` ✅
- 旧月度文件（132 个）仍在盘上，**新 loader 读不到它们** ✅
- 仓库级断言测试持续保证不存在旁路自拼路径 ✅

## 5. Clean Experiment State

```text
experiments/daily_exit_paper_v1/   —— 不存在
```

**PASS。** 没有 `experiment.json`、没有 state、没有 ledger、没有推荐快照、
没有 decisions / executions / daily。

本阶段做过的两次 `--dry-run`（一次在 09-29 数据上、一次在 09-30 数据上）
**磁盘零变化**，已实测确认目录仍未创建。

## 6. Initial Capital

```text
INITIAL CAPITAL: NOT LOCKED
```

**你没有给出初始本金。** 系统不会替你选，也**不会**沿用任何历史测试数字
（66,000 只是 PHASE 5/6 里 `--dry-run` 用的临时值，从未写入任何 `experiment.json`）。

```text
WAITING_FOR_USER_INITIAL_CAPITAL
```

## 7. First Signal Date

```text
FIRST SIGNAL DATE: NOT SET
```

你在 §六 提出的推荐起跑方式是「**2026-10-08 收盘以后**运行 nightly，
用 ≤10-08 的数据产生正式 recommendation，T+1 = 2026-10-09 执行第一批 entry」。
这个起跑方式在技术上完全可行，但：

1. **10-08 的行情现在还不存在**（今天是 10-04，国庆休市中），
   所以无法在今天完成正式启动；
2. §三十三 要求 start date 必须由你**明确给出**。

```text
START DATE: 待你在 2026-10-08 当晚确认
（届时 menu：python scripts/quant/run_daily_exit_paper.py --capital <本金>）
```

**绝不使用 2026-09-29 或 09-30 的旧信号作为正式实验第一笔交易**（§五）。

## 8. First Expected Execution Date

按 §六 的推荐起跑方式：

```text
first_signal_date    = 2026-10-08（待定）
first execution date = 2026-10-09（T+1 开盘）
```

`experiment.json` 里的 `first_signal_date` 会记**信号日**（10-08），
不是"程序安装日"—— 这两件事完全不同。

## 9. First Recommendation

**正式推荐：无。**（实验未启动。）

作为**只读观察**，在 2026-09-30 数据上的 dry-run 输出如下（**不会落盘**）：

```text
signal_date            2026-09-30
recommended_count      20
eligible_count         1,898（过指数伪标的 + 板块门槛后）
excluded_restricted    50（代码上限；创业板 28 / 科创板 22）
budget_below_one_lot   12
per_slot_budget        3,135.00
available_cash         66,000.00 → 预留 53,397.17 → 可用 12,602.83
```

样本行（`*` 表示目标/止损按**计划价**预估，成交后会按实际成交价重新锚定并锁定）：

```text
605179.SH 一鸣食品   100 股  限价 23.910  目标* 23.894  止损* 20.315  预留 2,397.22
002674.SZ 兴业科技   100 股  限价 20.120  目标* 20.066  止损* 17.614  预留 2,018.03
603079.SH 圣达生物   200 股  限价 13.810  目标* 13.622  止损* 12.437  预留 2,768.41
```

> `budget_below_one_lot = 12` 即 PHASE 5/6 反复记录的现象：6.6 万本金下
> 20 个等权空位有 12 个连 1 手都买不起。**这是继承冻结 `top_k=20` 的必然结果，
> 只观察、不调整** —— 要更集中必须新开版本（那等于改仓位规模）。

## 10. First Pending Orders

**无。** 实验未启动，`pending_entries` 为空。

机制上已经锁死（3 条测试）：第一次运行时**只处理启动日这一天**，
产生的挂单全部指向**下一交易日**，`resolved_exec_date` 为 `None`，
状态 `PENDING` —— **绝不在启动当晚提前成交，也绝不补任何历史日期**。

## 11. Accounting State

**不适用（实验未启动）。**

机制已就绪并经过验证：

```text
账本        append-only 的 experiments/daily_exit_paper_v1/ledger.jsonl
恒等式      cash ≥ 0 / reserved ≥ 0 / available ≥ 0 / 持仓 ≥ 0
            portfolio_value == cash + 持仓市值
            cash == 账本重算值
落盘顺序    先写 state、再写账本（崩溃时账本落后 → 下次大声报错，
            不会重放同一段交易日导致重复记账）
对账失败    raise，**绝不自动改账**
```

真实数据影子验证（PHASE 6）里：09-24 → 09-28（跨中秋假期）20 笔成交、
现金 `63,314.56 == 账本重算 63,314.56` 精确相等，费用 227.24。

## 12. Strategy Configuration Hash

```text
daily_exit_paper config_sha256 : b1d42beee295f39a387f6c90352ca245962307f99cb4ea70ff3c71c62a608950
```

（不含 `freeze` 块自指的哈希；首次正式运行时写入 `experiment.json` 并从此校验。）

被继承的冻结参数（有测试断言与来源一致）：

```text
signal_horizon_days = 20   ← config/strategy_v2.yaml alpha.label_horizon_days
top_k               = 20   ← config/strategy_v2.yaml portfolio.top_k
risk_profile        = balanced  ← trade_plan/plan.py 既有默认档
time_stop.days      = 40   ← plan.py 的 horizon×2 定义
transaction_costs          ← 与 config/paper_live.yaml 逐字相同
```

## 13. Git Commit

```text
VERSION        1.1.0
本次发布      v1.1.0 — 执行链专项审计 + 独立前瞻实验
```

提交后工作区 **clean**；正式启动时 `experiment.json` 会记录
`git_commit` + `git_dirty: false` + `working_tree: "clean"`。

本版新增/改动（全部在 `daily_exit_paper/` 及其测试、文档、报告内）：

```text
新增  daily_exit_paper/                2,717 行（10 个模块）
新增  scripts/quant/run_daily_exit_paper.py
新增  config/daily_exit_paper_v1.yaml
新增  tests/daily_exit_paper/          1,807 行 / 8 个文件 / 104 条
新增  tests/forward/test_pending_lifecycle.py   （C1，9 条）
新增  tests/forward/test_rebalance_dates.py     （C2，14 条）
新增  tests/strategy/test_feature_cache_contract.py（C3，13 条）
新增  7 份报告（audit / design / phase4 / phase5 / phase6 / phase7 + v1.1.0 说明）
修改  paper_live/engine.py               （C1 + C2）
修改  personal_quant/strategy/features.py（C3 缓存契约）
修改  pipeline/daily.py                  （C2 接线）
修改  scripts/paper_live/run_daily.py    （C2 接线）
修改  3 个研究脚本                        （C3 调用路径）
修改  docs/USER_GUIDE.md / README.md / docs/V1_RELEASE.md
```

**未修改任何受保护模块**：`strategy_v2` / `S3` / `top_k` / `horizon` /
`target` / `stop` / `risk profile` / 成本模型 / `forward_holdout` / `wealth`。

测试：**1160 passed / 0 failed**（v1.0.5 时为 1020；本版新增 140 条）。

## 14. Launch Status

```text
OFFICIAL PAPER TRADING: NOT STARTED
```

```text
WAITING_FOR_USER_INITIAL_CAPITAL
START DATE: 待确认（推荐 2026-10-08 当晚）
```

### 启动检查（§三十二）

```text
CODE FREEZE             : PASS   （提交后工作区 clean；规则冻结机制已落地）
DATABASE FRESHNESS      : PASS   （行情 2026-09-30，与信号同日）
CALENDAR                : PASS   （09-30 是已观测交易日；下一交易日 NOT_YET）
FEATURE FRESHNESS       : PASS   （09-30 / 09-29 命中且自证日期；旧文件读不到）
CLEAN EXPERIMENT STATE  : PASS   （实验目录不存在）
INITIAL CAPITAL         : NOT LOCKED            ← 等你给
START DATE              : 待确认（§六 提议 2026-10-08）
NO HISTORICAL CATCH-UP  : PASS   （fresh start 只处理启动日，3 条测试锁死）
```

### 只有两个值缺你确认

```text
INITIAL CAPITAL = ?
START DATE      = ?
```

给出之后的启动动作（**两步，先看后写**）：

```bash
source .venv/Scripts/activate

# STEP A —— 空跑，磁盘零变化，看清三个时间与全部推荐
python scripts/quant/run_daily_exit_paper.py --capital <你的本金> --dry-run

# STEP B —— 正式起跑（**这一步才创建 experiment.json / 锁定本金 / 写账本**）
python scripts/quant/run_daily_exit_paper.py --capital <你的本金>
```

STEP B 会打印 **OFFICIAL START 横幅**（实验 ID / 策略 / 起始信号日 /
下一执行日 / 初始本金 / 数据库日期 / `CLEAN START`），
并把这一刻永久钉进 `experiment.json` 与 `ledger.jsonl`。

### 启动之后

```text
每天：refresh_all.py → run_daily.py → write_recommendation_note.py → run_daily_exit_paper.py
产出：reports/daily_exit_paper_v1/daily_<日期>.md + experiments/daily_exit_paper_v1/ledger.jsonl
规矩：规则固定、市场真实变化、观察结果。不因最近几笔盈亏调参。
      改规则 = 新建 v1.1；错误必须保留；影响历史状态的 bug → 停止实验先审计。
```

> **PHASE 7 之后，PersonalQuant 不再"每天被我们改得更好"，
> 而是作为一个固定的实验对象接受市场检验。**
