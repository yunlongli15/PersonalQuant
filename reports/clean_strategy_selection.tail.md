---

## 10. Selected production strategy

# **Candidate A — `production_clean_v1`**

**Alpha158 only，不使用任何新闻因子。**

选择依据（§十 / §十一）：

| 判据 | A | B | 结论 |
|---|---|---|---|
| 年化收益 | **31.9%** | 26.2% | A 更高 |
| 夏普 | **1.039** | 0.858 | A 更高 |
| 最大回撤 | **−20.3%** | −28.3% | A 显著更浅 |
| Calmar | **1.575** | 0.923 | A 更高 |
| 月度胜率 | **60.9%** | 52.2% | A 更高 |
| 逐年稳定 | 2024/2025 均正 | 均正 | 相当 |
| 换手 | 983% | 1009% | A 略低 |
| 费用 | 50,675 | 51,392 | A 略低 |

**A 在每一项上都不劣于 B，在收益、夏普、回撤、Calmar 上明显更好。**
§十 写明"不要为了保留 factor_pack 而强行选择 B" —— 这里不存在那个诱惑，
数据指向很干脆：`factor_pack_v1` 的 7 个量价因子在这段样本上没有增量。

### ⚠️ 必须点名的一件事：S3_v1 的**数字仍然更好**

| | 年化 | 夏普 | 最大回撤 |
|---|---|---|---|
| **S3_v1（污染基线）** | **35.2%** | **1.080** | −22.8% |
| production_clean_v1 | 31.9% | 1.039 | −20.3% |

修好执行引擎后重跑，S3_v1 依然比选定模型高约 **3.3 个百分点年化**。
消融同样显示：无新闻 26.2% → 有新闻 35.2%，**新闻特征贡献约 9pp**。

**我们仍然不选它，理由不是业绩，是数据来源**：那批特征是在一份
上交所只有定期报告的语料上选出来的，它们测的东西和它们声称测的东西
不是一回事（见 §1）。**这是一次有代价的保守选择** —— 明确记录在此，
不藏在脚注里。

---

## 11. Recommendation validation

真实数据库实跑（§十九 / §二十），非仅靠测试：

```
python scripts/quant/refresh_all.py     -> EXIT 0，10/10 作业 OK
python scripts/run_daily.py             -> EXIT 0，2 warning（数据陈旧，非失败）
python scripts/quant/write_recommendation_note.py -> EXIT 0
```

`signal_refresh` 回执：`{'as_of': '2026-09-30', 'n_symbols': 2978,
'strategy': 'production_clean_v1'}`

建议书 `reports/paper_live/recommendation_2026-09-30.md` 头部：

```
> Strategy: production_clean_v1
> Features: Alpha158
> News factors: DISABLED
> Horizon: 20 trading days
> Model: experiments/clean/clean_A/model.txt
```

内容检查：**8 只**买入清单、建议买入价、可接受区间、**目标价**、**止损**、
**预期净收益** 全部在场。

### PIT 实跑检查（§二十）

| 检查 | 结果 |
|---|---|
| `feature_2026-09-30.parquet` 内 `feature_date` 全等于信号日 | **PASS** |
| `max(feature_date) <= signal_date` | **PASS** |
| 信号快照日期唯一且等于信号日 | **PASS** |
| `forecast as_of` == 信号日 | **PASS** |
| `portfolio as_of` == 信号日 | **PASS** |
| `forecast_*.parquet` 的 `signal_date` 全等于信号日 | **PASS** |
| 前瞻覆盖 1/5/20 三个 horizon 且无缺失 | **PASS** |
| 建议书含策略版本 / News DISABLED / Horizon | **PASS** |

### 预测层已切到干净模型（§十六）

`pipeline/forecast.py` 原先**写死**读 S3 的预测来建条件分布。
生产策略换成 `production_clean_v1` 后如果不改，就会把 clean 模型的
分数排名映射到**污染模型**的收益分布上 —— 校准与打分函数对不上。

已改为按生产策略取数，并**只在生产策略就是 S3 时**才并入 2018-2021
走查研究段（那段是 S3 的分数，混进别的模型等于两种分布搅在一起）。

现在：`base_model = production_clean_v1 (Alpha158)`，
校准观测 693,064 条，全部来自 clean_A 自己的样本外预测
（2022-01-28 ~ 2025-12-31）。

### ⚠️ v1 语料正在被"半修复"，这让它更不适合作为基础

跑完整刷新链之后发现 `data/derived/news/news_events.parquet`（**v1**）变了：
186,003 → 190,130 行。逐年核对：

| 年份 | HEAD 提交里 | 当前 |
|---|---|---|
| 2022 / 2023 / 2024 / 2025 | 21,343 / 19,116 / 19,332 / 21,659 | **完全相同** |
| 2026 | 31,327 | **35,452（+4,125）** |

**历史一条没动，增长全在 2026。** 原因是修复后的 SSE provider 正在给
**每日增量**供数，新公告照常写进 v1 的 canonical 表 `news_documents`。

后果：v1 现在是一份**混合语料** —— 2026 年之前是坏采集的产物，
2026 年之后是修好之后的。这让它比"纯粹坏掉"更难解释，
**更加不能作为下一阶段的基础**（§1 的理由因此更充分，不是更弱）。

本阶段没有回滚这次增量（它会每天继续发生），也没有改任何历史行；
`production_clean_v1` 完全不读新闻，因此不受影响。

### ⚠️ 两处需要你知道的状态

1. **数据陈旧**：行情/估值/新闻快照最新都是 2026-09-30，而今天是
   2026-10-06。`market_update` 自己报告"上游没有更新的内容 —— 跳过下载"。
   所以全部业务日期锚在 09-30。这是**数据源滞后，不是流水线故障**。

2. **"生产"现在有两个含义，它们不相等：**
   - `PRODUCTION_STRATEGY = production_clean_v1` —— 生成**每日建议书**的模型；
   - `config/paper_live.yaml`（**冻结件，哈希受 `drift.py` 每日校验**）
     —— 前瞻观察实验跑的仍然是 `experiments/news/strategy/model.txt`（S3_v1）。

   二者被设计成互相隔离（paper_live 走自己的 provider，不读
   `PRODUCTION_STRATEGY`），所以**改建议书不会污染已在跑的前瞻记录**。
   但这意味着从现在起，建议书与前瞻实验观察的**不是同一个策略**。
   要不要为 clean 模型另起一个前瞻观察，是**新决策**，不属于本阶段
   （§二十一 明确不要启动 daily_exit_paper_v1）。现有的 2026-09-18 起
   的前瞻观测**一个字节都没有改动**。

---

## 12. Scheduler validation

`scheduler.py` 原先用本地日期去比 SQLite `datetime('now')`（UTC）存的时间戳，
CST 00:00–08:00 之间相差一天，日常任务会被判成"今天没跑过"而重复执行 ——
只在深夜复现，白天测永远是绿的（2026-10-06 00:02 实测触发）。

修法（§十七 / §十八，**只动时间处理，不碰调仓/信号/策略语义**）：

- 时间语义**统一到市场时区 Asia/Shanghai**，写死，不跟随机器时区；
- 写入侧改用带显式偏移的 UTC 时间戳（`utc_now_iso()`），不再依赖
  SQLite 的无标记 `datetime('now')`；旧的裸时间戳按 UTC 解释；
- 读取侧 `utc_to_market_day()` 做换算，朴素时间按市场时区解释。

覆盖测试：UTC / Asia/Shanghai / 午夜边界 / 日界与周边界 / 月界跨年 /
机器时区无关性 / 新旧格式兼容。见
`tests/pipeline/test_scheduler_timezone.py`（25 项）。

> `tests/pipeline/test_scheduler.py::test_weekly_due_across_iso_weeks`
> 里有**一行**被改：它原先写 `finished_at[:10]`，即把 UTC 字符串前 10 位
> 当日期用 —— 那正是被修掉的那个混淆。测试一直是绿的只因为运行时
> 10-05 与 10-06 恰好同属 ISO 第 41 周；换成周一凌晨就会失败。
> 这不是"改测试让它通过"，是那一行的前提本身错了，改用
> `scheduler.utc_to_market_day()` 取市场日。

---

## 13. Final verdict

**选定 `production_clean_v1`（Candidate A，Alpha158 only，新闻因子停用）。**

本阶段同时修掉两个此前隐藏的真 bug：

1. **停牌股的 NULL 价格被当成有效成交价。** `daily_bars` 里停牌日有行但
   OHLC 全为 NULL（全库 577,218 行 / 3.2%），而 `execute_order` 的守卫写的是
   `if open_price is None` —— `float(NaN)` 不会触发它。于是一次停牌股成交
   把 `cash` 变成 NaN，**此后每一天的 NAV 都是 NaN**，回测却一声不吭跑完。
   已修（`_price()` 把 NaN 归一成 None；`_px()` 真正向前填充）。
   受影响面已核验：**只有 clean_A 的旧产物有 NaN**，其余所有 run 的 NAV
   都是干净的 —— 因此这个修复不可能改动任何既有冻结结果。

2. **预测层写死读 S3 的分数**（见 §11），已在切换生产策略时一并修掉。

---

# PHASE 7 CLEAN PRODUCTION STRATEGY REPORT

### Clean Candidates

| | 特征 | 自定义特征数 | 新闻 |
|---|---|---|---|
| Candidate A | Alpha158 | 0 | DISABLED |
| Candidate B | Alpha158 + factor_pack_v1 | 7 | DISABLED |

### Backtest Results（2024-01-02 ~ 2025-12-31，485 日）

| | 年化 | 累计 | 夏普 | 最大回撤 | Calmar | 胜率 |
|---|---|---|---|---|---|---|
| **A（选定）** | **31.9%** | **73.8%** | **1.039** | **−20.3%** | **1.575** | **60.9%** |
| B | 26.2% | 59.0% | 0.858 | −28.3% | 0.923 | 52.2% |
| S3_v1（污染，参考） | 35.2% | 82.5% | 1.080 | −22.8% | 1.540 | 60.9% |
| S3_v2（失败，参考） | 9.7% | 20.2% | 0.410 | −27.1% | 0.357 | 56.5% |

### Stability

逐年：2024 +22.5% / 2025 +44.4%，**两年都赚，不依赖单一年份**。
逐年 rank IC：2022 0.042 / 2023 0.031 / 2024 0.051 / 2025 0.046 —— 四年全正。

> 更早的 2018-2021 不在表内：那是训练集，在上面算 P&L 没有意义。

### Risk

最大回撤 −20.3%（比 B 浅 8pp），回撤主要来自 2024 年。
Top-K 名义换手月均见 §9；零成交月 1 个（2024-09-30，涨停开盘买不进）。

### Cost

费用合计 **50,675 元**（期末权益 1,737,000），约占 **2.9%**；
其中买入费/卖出费见 §8。换手合计 983%。

### Small Account

Top-K 固定 20。不可买入比例均值 **7.4%**，资金利用率均值 **85.3%**，
平均现金比例 14.7%。最差月份一单未成（涨停开盘），已单独说明。

### Selected Model

`production_clean_v1` — **Alpha158 only**，No custom features，**News DISABLED**。

### Feature Set

Alpha158（158 列），horizon 20 交易日，月度调仓（每月最后交易日），
T+1 开盘执行，涨跌停/停牌 NO_TRADE，成本复用 `strategy_v1` 的
`TransactionCostModel`。

### Production Configuration

`experiments/clean/production_clean_v1.json` —— 模型哈希、特征清单、
配置哈希、训练数据快照 id、git commit、冻结测试段指标。

```
model    : experiments/clean/clean_A/model.txt
sha256   : 44a3368db727095b…
dataset  : 15ac69153030254c
ann 31.92%  sharpe 1.039  mdd -20.27%
```

### Recommendation Test

**PASS** —— 三脚本实跑 EXIT 0；建议书头部标注
`Strategy: production_clean_v1 / Features: Alpha158 / News factors: DISABLED`；
PIT 实跑 8 项全 PASS。

### Scheduler Test

**PASS** —— 时区语义统一到 Asia/Shanghai，25 项覆盖测试通过。

### Full Test Suite

**PASS** —— `1324 passed, 1 skipped, 0 failed`（251 秒），
运行时刻 **2026-10-06 01:13 CST** —— 正是原先调度器时区 bug 必复现的
00:00–08:00 窗口。修复前同一时刻是 `2 failed`。

新增测试：调度器时区 25 项、停牌 NaN 价格 10 项、生产策略接线 4 项。

---

```
Selected Strategy: production_clean_v1
Model:             experiments/clean/clean_A/model.txt
Features:          Alpha158 only（0 个自定义特征）
News:              DISABLED
Horizon:           20 trading days

Annual Return:     31.9%
Sharpe:            1.039
Max Drawdown:      -20.3%
Calmar:            1.575

Recommendation:    PASS
Full Test:         PASS

Final:             READY FOR PAPER TRADING
```
