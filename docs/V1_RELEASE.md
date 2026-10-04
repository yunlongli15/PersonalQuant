# PersonalQuant 发布说明

**最新：V1.1.0（2026-10-04）** ｜ `cat VERSION` → `1.1.0` ｜
本版重点见 [§18](#18-v110--执行链专项审计--独立前瞻实验2026-10-04)
（执行链三个 CRITICAL bug 修复 + `daily_exit_paper_v1` 独立前瞻实验 + 代码冻结）。

**首版：V1.0.0（2026-09-19）** ｜ 以下为 V1.0.0 的原始说明。

> 一个**完全本地运行**的个人投资研究、组合管理与决策辅助终端。
> 不连接券商、不自动下单、不涉及真实资金操作。

---

## 1. 系统能力

```
本地 A 股数据层 → PIT 财务 → 新闻/公告 → 因子研究 → Alpha 模型
    → 组合优化 → 交易计划 → Paper Live → Forward Holdout
    → 个人账户 → 收益/风险 → 本地 GUI → 每日自动化与报告
```

| 能力 | 状态 |
|---|---|
| 本地 A 股日线 / 证券主表 / 日历 / 行业 / 公司行为 | ✅ |
| PIT 财务数据（按需年报提取，公告日可用性） | ✅ |
| 新闻/公告事件（官方交易所优先，严格 PIT） | ✅ |
| 因子研究平台（75 因子，IC/衰减/分位/相关性） | ✅ |
| Alpha 模型（Alpha158 + LightGBM，冻结） | ✅ |
| 组合优化（7 种分配方法，PIT 协方差） | ✅ |
| 交易计划（入场区间/目标/止损/手数/费用/板块权限） | ✅ |
| Paper Live（T+1 执行、append-only、按日幂等） | ✅ |
| Forward Holdout（2026-09-18 起，只记录） | ✅ |
| 个人账户（账本 / TWR / XIRR / 对账 / 备份） | ✅ |
| 本地 GUI（Streamlit 12 页 + FastAPI 15 页） | ✅ |
| 每日自动化与报告 | ✅ |

## 2. 数据源

- **行情**：chenditc/investment_data（qlib 官方 README 推荐的社区源）
- **财务**：SSE/CNINFO 年报 PDF，按需提取（**从不批量下载**）
- **公告**：SSE 按日全量、SZSE 按股（top-60）、CNINFO
- **估值**：腾讯行情（东财被 WAF 封禁时的替代）

全部离线可用；`PQ_MODE=offline` 禁网。

## 3. 模型与策略

- **alpha**：S3 = Alpha158 + `factor_pack_v1` + `factor_pack_news_v1`
- **模型**：LightGBM（固定参数，2015-2021 训练，**冻结**）
- **分配**：equal_weight，Top-20，5% 现金缓冲
- **执行**：T 日收盘信号 → T+1 开盘成交，100 股手数，涨跌停/停牌 NO_TRADE

## 4. Paper Live 与 Forward Holdout

- **起点 2026-09-18**，`record_only`：只记录 / 观察 / 评估
- 起点之前的结果写入 `experiments/paper_live/pre_forward/`，
  **绝不污染** `forward_holdout/`
- 观测 append-only，已写下的记录永不覆盖

## 5. GUI

```bash
python scripts/run_app.py     # Streamlit 终端 http://127.0.0.1:8501
python scripts/webapp/serve.py # FastAPI 录入界面 http://127.0.0.1:8765
```

两个前端共享同一套引擎；都只绑定本机、零外部资源。

## 6. 每日运行

**两条命令，先 A 后 B**（完整说明见 `docs/USER_GUIDE.md` 第 1 节）：

```bash
python scripts/quant/refresh_all.py    # A. 更新数据与信号 → 交易计划（5~7 分钟）
python scripts/run_daily.py            # B. 每日流水线 → 前瞻记录 + 日报（约 5 秒）
python scripts/run_daily.py --dry-run  # 只看检查，不写任何东西
python scripts/system_health.py        # 系统健康
```

| | A. `refresh_all.py` | B. `run_daily.py` |
|---|---|---|
| 职责 | 更新**数据与信号** | **记账与观察** |
| 会推进「信号日」吗 | **会**（只有它下载新行情） | **不会**（只读现有数据） |

**顺序不能反**：B 不下载行情，先跑 B 会对着旧的一天做记录。
B 共 14 个步骤，普通日几秒到两分钟。

---

## 7. 已知限制（如实）

1. **2024-2025 = HISTORICAL TEST**：已被评估 3 次（STEP 6 终评、step8、
   step9），**不是干净的样本外**。证据只能来自 2026-09-18 之后的前瞻观察。
2. **组合优化没有带来增量**（STEP 6 结论），最终候选退回 P0 等权。
3. **自定义因子第一轮未稳定超越 Alpha158**（STEP 4）；微结构因子有单因子
   预测力但加入组合未提升策略（STEP 8）。
4. **"加入因子反而变差"统计上不成立**（STEP 9）：24 个月的可检出最小年化
   差异约 41pp，该样本无法区分策略优劣。
5. **新闻覆盖偏薄**：SZSE 回填仅 top-60 大市值，近 30 天覆盖约 60 只。
6. **LLM 层未启用**（无 `DEEPSEEK_API_KEY`），系统按 RULE_BASED_ONLY 运行。
7. **DuckDB 单进程独占**：GUI 打开时无法跑每日流水线，需先关界面。
8. **计划任务未注册**（本机 PowerShell 策略禁止运行脚本，**未修改系统策略**）；
   手动跑第 6 节那两条命令即可，状态记 `SCHEDULER_NOT_INSTALLED`。
9. 北交所（.BJ）标的**不在股票池**；其数据存在上游侧的复权因子跳变，
   已用 `repair_factor_rebase.py` 修正（影响为零，已记录）。
10. 两个前端在"流水录入"上功能重叠，未合并。

## 8. 安全边界

| 项 | 值 |
|---|---|
| 连接券商 | **禁止** |
| 自动下单 | **禁止** |
| 自动重训 / 选因子 / 调参 | **禁止** |
| GUI 修改冻结策略 | **禁止** |
| API key | 只从环境变量读，绝不进 git / 配置 / 日志 |
| 个人财富数据 | 只在本机（`data/wealth/` 已 git 忽略） |

## 9. 如何运行

```bash
source .venv/Scripts/activate

python scripts/system_health.py        # ① 先看健康
python scripts/quant/refresh_all.py    # ② 更新数据与信号 → 交易计划
python scripts/run_daily.py            # ③ 每日流水线 → 前瞻记录 + 日报
python scripts/run_app.py              # ④ 看界面（或 webapp/serve.py）
```

## 10. 如何备份

```bash
python scripts/backup_portfolio.py              # 个人资产库
python scripts/backup_portfolio.py --export     # 额外导出 CSV
```

**只备份个人数据**；市场数据（DuckDB/Parquet）可从公开源重建，不重复备份。

## 11. 如何升级

**不要直接改生产配置。** 见 `docs/V1_FREEZE.md`：

1. 新建 `config/experiments/<实验名>.yaml`
2. 只用 2018-2023 做评估（2024-2025 只作历史对照）
3. 记录协议**先于**结果
4. 通过全部 gate 才考虑晋升生产，并同步更新 `production_freeze.yaml`

## 12. 目录速查

| 路径 | 内容 |
|---|---|
| `personal_quant/` | 数据基础设施（canonical / 财务 / 策略引擎） |
| `factors/` `news/` `portfolio/` | 因子 / 新闻 / 组合研究 |
| `paper_live/` | forward holdout 引擎 |
| `wealth/` | 个人财富账本与收益引擎 |
| `services/` | 应用服务层（GUI 唯一接触面） |
| `app/` `webapp/` | Streamlit 终端 / FastAPI 录入界面 |
| `pipeline/daily.py` | 每日流水线编排 |
| `reports/` | 全部研究报告与每日报告 |
| `docs/` | 说明文档（本文件在 `V1_RELEASE.md`） |

---

## 13. v1.0.1 修订（2026-09-20）

**不含任何策略 / 模型 / 因子变更** —— 冻结工件哈希未动（`冻结状态 一致`）。
本次只修"数据刷新与报告**可不可信**"的问题。

| 问题 | 现象 | 修复 |
|---|---|---|
| 日报 / manifest 版本字段 | 日报 §15 全是 `—`；manifest 回退成**硬编码常量**（`strategy_v2`/`s3`）—— 那是拿常量冒充生产状态 | 从 `production_freeze.yaml` 的标量读；git commit 用**本次运行**的 HEAD |
| `valuation_update` 从不更新 | 默认 `use_cache=True` → 每次把旧快照重写一遍并报成功 | 刷新任务显式 `use_cache=False` |
| 估值快照日期 | 周末运行会盖成"当天"（2026-09-20 周日），凭空造出一个不存在的交易日 | 盖章为最近一个**已收盘交易日**（查 `trading_calendar`） |
| `account_profile()` 忽略配置 | 配置写在 `account:` 层，函数只读顶层 → 用户写明的"可投资金 6.6 万 / 不做自动探测"被**静默忽略**，交易计划按财富库总资产 27.1 万下单 | 合并 `account:` 层 |
| 测试污染 DERIVED 缓存 | `test_no_future_leakage` 用 2 只股票算特征，把 `data/derived/features/2024-01.parquet`（4,943 行）**整个覆盖成 2 行** | 缓存目录隔离到 tmp；损坏文件移作 `.corrupt-20260920`，下次读取自动重算 |
| paper_prediction 状态行 | 幂等空跑也报"写入 forward_holdout（正式前瞻）" | 如实报"该日已记录，本次未写入任何东西"，并标注数字为存档值 |

### 本次数据修复

- **新闻 2026-09-14 / 09-15 两日整段缺失**：增量水位在交易日历尚未收录这两天时越过了它们，
  SZSE 从未抓取。补抓 **+1,454 份公告**（401 + 1,053），重建 derived 事件层（覆盖 4,223 → 4,630 只）。
  修复后 2026 年 **174 个交易日零缺口**。SSE 公告索引对该窗口返回空
  `{"rows": [], "total": 0}`，近期数据全部来自 SZSE —— **这是源侧事实，不是抓取失败**。
- **估值快照**刷新至 2026-09-18（4,602 只）。
- **信号 / 预测**按 2026-09-18 重算（3,016 只），交易计划与建议已重生成。

### 关于 forward holdout

`forward_holdout/observations/2026-09-18.json` **未被修改**（append-only + 幂等空跑）。
本次修复不追溯改写任何已记录的前瞻观测。

### 已知环境问题（未修）

生产信号路径的特征计算用 `qlib kernels=10`，满负荷约需 21 GB；本机同时跑其它程序
（实测空闲 18.7 GB）时会 `MemoryError` 失败。降到 `kernels=4` 可完成（本次用时 397 s）。
这是**资源适配**问题，不是逻辑错误 —— 未改动默认值，需要时在调用处降低并发。

---

## 14. v1.0.2 修订（2026-09-21）

用户按 `docs/USER_GUIDE.md` 实操后的三个反馈。**不含策略 / 模型 / 因子变更**。

| 反馈 | 真正的原因 | 修复 |
|---|---|---|
| 「run_daily 怎么还是 18 日，没更新到 21 日」 | ① 上游**根本没有 21 日的数据**（名为 `2026-09-20` 的 release，其 manifest 写着 `target_trade_date: 2026-09-18`）② 流水线判断"落后几天"用的是**本地数据 vs 本地日历**，两者同源，永远算出 0 天，于是永远说"无需下载" | 行情检查改读上游 manifest 的 `target_trade_date`；本地已是最新就明说"已是最新，没有更新的数据可下载"，上游确实更新了则报 WARNING 并给出命令 |
| 「refresh_all 没有任何反馈，不知道卡死还是正常」 | 作业循环全程无输出；行情快照 566 MB 下载也没有进度条 | 每个作业打印 `[i/n] name ... 运行中` / `-> SUCCESS (123s)`；下载按 3 秒打印百分比与 MB |
| 「8765 显示的还是 18 日的推荐」 | 页面上的日期是**信号日（数据截至哪一天）**，不是生成日期；交易计划页**完全不显示任何日期** | 交易计划页改为同时显示 `信号日（数据截至）` 与 `生成于` |

### 顺带修掉

- **白下 566 MB**：`update_market_snapshot.py` 只看 release 名字，无法判断有没有新数据。
  实测 `2026-09-20` 与上一份快照**逐字节相同**（日历、成分股、features 校验和全部一致）。
  现在比对 manifest 的 `target_trade_date`，没有新内容就直接跳过下载。
- **被强杀的作业永远停在 `running`**：`jobs.db` 里那条 `market_update` 会一直显示"在跑"。
  现在每次刷新前把遗留的 `running` 标记为 `INTERRUPTED`（不是失败，是没跑完）。
- **USER_GUIDE 只写了一个前端**：系统有**两个**（`serve.py` :8765 录入界面 /
  `run_app.py` :8501 研究终端），指南只提了前者，用户看到另一个以为找错了地址。
  现在两个都写明用途，并说明"信号日 ≠ 今天"。

---

## 15. v1.0.3 修订（2026-09-21）

用户反馈：在「交易流水」记了产品之间的转入/转出，但「资产总览」和
「每日录入」都没变，重启程序也一样。**不含策略 / 模型 / 因子变更。**

### 结论：数据模型是对的，缺的是"告诉你下一步"

`transactions`（那天*发生了什么*）与 `daily_snapshots`（那天*账户里有多少钱*）
分开是**设计**：系统不替用户推算余额（转账可能未到账，基金还有市场波动，
推算出来的数字不是事实）。P&L 恒等式 `Ending − Beginning − 外部净流入`
靠的就是这两张表各司其职。

问题是两者之间那段空档**在界面上完全不可见** —— 用户看到"上次金额"是旧的，
只能理解为"数据没刷新"。

| 改动 | 作用 |
|---|---|
| 「每日录入」新增提示条 | 列出上次录入之后的资金流（`· 2026-09-21 天天盈1号 转出到其他产品 −5,004.04 元`），并说明"请按平台 App 上的实际金额填写" |
| 「交易流水」成功消息 | 记完流水即提示：流水只影响收益口径，当前金额请到「每日录入」更新 |
| `transfer_in/out` 标签 | 原为「内部转入/转出」，与 P&L 口径的"**外部**资金流"直接矛盾，也无法与"从银行卡转入"区分；改为「从其他产品转入 / 转出到其他产品」 |
| USER_GUIDE §2 | 新增「有资金进出时要做两件事」一节 |

### 另外发现（环境，不是代码）

排查时发现 8765 端口上有一个**用系统 Python 启动的旧 serve 进程**仍在监听。
新启动的实例绑定失败（`WinError 10048`）却照样打印了访问地址 —— 浏览器
仍然连到旧进程，于是"关掉再打开还是旧页面"。**遇到界面行为不符合预期时，
先确认没有残留进程**（`netstat -ano | findstr 8765`）。

测试：`tests/webapp/test_pending_flows_hint.py`（5 例）覆盖待处理流水的
显示/不显示、内部买卖不算资金流、以及标签不得与口径矛盾。

---

## 16. v1.0.4 修订（2026-09-22）

用户 `refresh_all.py` 跑了**两个多小时**，且给出的建议里价格已经失效。
**不含策略 / 模型 / 因子变更。**

### 1. 跑 2 小时的原因：`financial_update` 不该默认跑

日志里 `financial_update -> SUCCESS (7904s)` = **2 小时 11 分**，其余作业合计
不到 5 分钟。它抓了 812 份年报 PDF、扫了 2,699 个标的。

这直接违反 spec §38「财务 lazy/按需，绝不为每天重新下载年报」，而
**S3 生产特征集根本不含财务因子**（每日流水线一直把它标为 SKIPPED）。

修复：`financial_update` 改为**按需作业**（`OPT_IN_JOBS`），默认不跑，
`--only financial_update` 仍可用。`--dry-run` 的预览同步显示 `opt_in`。

### 2. 建议里的价格失效

交易计划的价格取的是**信号日收盘**（2026-09-18），而信号日会停在上游最后
发布的那天不动 —— 于是过了两天，入场区间早就不是能成交的价格了。项目里
**本来就有** `refresh_live_prices.py`（按信号排名抓当天真实收盘价，
`price_overrides` 覆盖价格输入、排序仍停在信号日），但它**不在刷新链里**，
`live_prices.json` 停在 2026-09-14。

修复：

- 新增 `live_price_refresh` 作业，插在 `signal_refresh` 与 `portfolio_refresh`
  之间。实测抓到 **60 只 @ 2026-09-22**（102 秒），计划价随之更新。
- 抓不到（休市/断网）**不算失败**：计划照出，但报告里显式警告
  `⚠ 价格是 2026-09-18 的收盘价（4 天前），入场区间可能已经失效`。
- USER_GUIDE §6 增加「先看价格的日期」，说明**信号日**与**价格日期**的区别。

### 3. `data status after refresh` 里的 Forecast / Portfolio STALE 是误报

刚 `SUCCESS` 重算完却显示 STALE，自相矛盾。原因：这两个域的 `as_of` 是
**信号日**，而 `data_status()` 拿它和**墙上时钟**比（容差 3 天）。上游一滞后，
它们必然"过期"。本文件开头的注释其实早就写明它们应当和 Market/Valuation
一样对齐**最后一个交易日** —— 代码没照做。

修复：改与 `last_trading_day()` 比较（容差 0），并纳入 `calendar_stale`
守卫 —— 日历本身滞后 >5 天时，Market/Valuation/Forecast/Portfolio 一律 STALE
（管线停摆不能显示成新鲜）。

测试：`tests/pipeline/test_data_freshness.py`（+3）、`test_refresh_jobs.py`（+4）。

---

## 17. v1.0.5 修订（2026-09-27）

`refresh_all.py` 实测跑了 **40 分钟**，而且日报里有一处会误导人的失败。
**不含策略 / 模型 / 因子变更。**

### 整链耗时 40 分钟 → 5.3 分钟

| 作业 | 修前 | 修后 |
|---|---|---|
| `signal_refresh` | **1736s** | **222s** |
| `news_events_refresh` | （缺这一步） | **0s**（跳过） |
| `factor_rebase_repair` | （缺这一步） | 1s |
| `live_price_refresh` | 96s | 25s |
| 合计 | ≈ 40 分钟 | **5.3 分钟** |

### 1. 根因：每个特征 worker 提交 4.2 GB（BLAS 线程）

20 核机器上，qlib 的每个 joblib worker 会让 OpenBLAS 各开 **67 个线程**，
单进程提交 **4.2 GB**；`kernels=10` 就是 **42 GB commit**。物理内存还剩
15 GB 也没用 —— **提交上限（65.8 GB）被打穿**，40 秒内所有进程 CPU 增量为
0，日志里只剩 `OpenBLAS error: Memory allocation still failed after 10
retries`。这也解释了更早那些 "Unable to allocate 13 MB" 的诡异报错。

修复：worker 环境里把 `OPENBLAS_NUM_THREADS` / `OMP_NUM_THREADS` /
`MKL_NUM_THREADS` / `NUMEXPR_NUM_THREADS` 全部压到 1。并行度本来就由
10 个 joblib worker 提供，BLAS 再各自开线程纯属浪费。

结果：`kernels=10` **一次跑通 193 秒**（修前：卡死 → 超时 1200s → 降级
4 并发 501s）。

### 2. 新增降级重试阶梯

超时 / MemoryError 这类**暂时性**失败，按
`kernels=10/1200s → 4/1800s → 1/2700s` 逐级降并发重试；真正的错误立刻抛出，
不靠重试掩盖。最后一档退到单进程，不依赖 joblib 池。

### 3. 新闻派生层接进刷新链（新增 `news_events_refresh`）

`news_update` 只写 canonical，而**生产新闻因子读的是派生层**
（`factors/news_factors.py` 声明 `required_fields=["news_events",
"news_coverage"]`）。少了这一步，公告抓回来了、信号却还在用旧事件 ——
实测 canonical 已到 09-22、派生层停在 09-18，**09-24 的信号因此缺了
09-21/09-22 两天共 1,192 份公告**。

同一作业加了"canonical 没变就跳过"（用文档数 + 最新发布时间做指纹）：
全量重建 18 万条要 476 秒，而绝大多数运行没有新公告 —— 直接降到 0 秒。

### 4. 复权因子修复接进刷新链（新增 `factor_rebase_repair`）

上游快照**每次重新发布都会把 factor rebase 缺陷带回来**：原始价连续、
复权因子却跳 2~15 倍。2026-09-19、09-22、09-27 三次换快照，三次都是
同样的 48 处 / 31,240 行，其中 7 只是**股票池内**的主板/创业板标的。

现在它紧跟 `market_update`：没有跳变时是纯读操作（1 秒返回），
有跳变才重标定并写 `source_registry`；修完仍有残留就**抛错终止整条链**。

### 5. `live_price_refresh` 不再谎报失败

判据从"最后一条 bar 的日期 **== 今天**"改成"**比信号日新**"。周日运行时，
市场最后一个交易日是 09-24，旧逻辑把 60 个标的全部记成 `failed`，看着像
网络故障，其实只是没有更新的数据。现在如实说：
`无更新：最新 bar 2026-09-24 不晚于信号日 2026-09-24`。

### 6. 顺带修掉的

- `market_update` 的 `subprocess.run(text=True)` 没写 `encoding` → 子进程的
  中文输出触发 GBK 解码错误，**静默丢掉全部输出**。
- `portfolio_refresh` 改用账户口径（原先写死 `capital=500_000, top_k=20`
  的回测口径：按 50 万下单却按 6.6 万判板块权限，还会覆盖账户口径的计划）。

测试：`tests/strategy/test_quarter_worker_retry.py`（+6）、
`tests/pipeline/test_refresh_jobs.py`（+5）。`verify_step12.py` 24/24 PASS。


---

## 18. v1.1.0 — 执行链专项审计 + 独立前瞻实验（2026-10-04）

一次大更新：从"修 bug"转到"建立一个可被检验的实验对象"。
**本版之后，交易逻辑正式冻结**（见 §18.6）。

### 18.1 三个执行层 CRITICAL bug（PHASE 1–4）

对现有 monthly paper_live 做了代码级专项审计，发现它**从未真正成交过一笔**：

| # | 缺陷 | 影响 |
|---|---|---|
| **C1** | T 日晚上算不出 T+1（日历里只有已发生的交易日）→ `exec_date=None` → 下次运行 `pd.Timestamp(None)` 得到 **`NaT`** 绕过守卫 → DuckDB 类型错误被 `except Exception: return False` 吞掉；而每次运行又**无条件覆盖**挂单文件 | 3 次前瞻观测 × 20 笔订单 = 60 笔，**成交 0 笔**；09-18 / 09-24 两批挂单无声消失 |
| **C2** | `is_rebalance_date` 用 `[d-70天, d]` 的窗口算"本月最后一个交易日"，右端点就是 `d` 自己 → **任何交易日都返回 True** | 2026-08 全月 21 个交易日里 **20 个被误判**；同一个月被当成三个"月末" |
| **C3** | 特征缓存按**月**命名、内容却是"该月最后一次写入的那一天"，读取时零校验；`cache=False` 重算后**照样写共享月文件** | 请求 09-18 会静默拿到 09-29 的横截面 —— **当天正着跑时保守，事后回放时是真实的前视泄漏** |

**修复要点**

- C1：挂单三态 `READY / NOT_YET / ERROR`，判定完全显式；`except Exception: return False`
  在挂单路径上全面移除；挂单文件改**读-改-写** + 稳定 `order_id` 去重 + `attempts` 留痕；
  旧格式挂单**归档不结算**；账本成为真相（`cash == 账本重算`，对不上就 raise，**绝不自动改账**）。
- C2：改成纯函数"`d` 之后的第一个**已观测**交易日是否落在下个周期"；
  日历里还没有下一个交易日时**保守返回 False**（"本月是否结束"当天答不出来）。
  新增 `rebalance_signal_date()` 把**信号日**与**确认日/运行日**分开 ——
  调仓信号仍是上月末，执行落在下月首日开盘。
- C3：`feature_<YYYY-MM-DD>.parquet` + 文件内 `feature_date` 列，**读写两侧都校验**；
  空切片不落盘；`cache=False` 只写自己那一天的文件。旧 132 个月度文件原样保留、新 loader 永不读取。

### 18.2 历史 3 条前瞻观测的处置

**不删除、不覆盖、不重跑、不补成交。** 逐条重建时间线确认：三条观测用的是
**更旧**的特征（保守方向），**未发生前视泄漏**；但它们是被 C1/C2/C3 污染过的
记录，只能作为**缺陷证据**，不是有效业绩样本。

### 18.3 新增：`daily_exit_paper_v1` 独立前瞻实验

一套与 monthly paper_live **完全独立**（不 import、不共享状态）的 forward 实验：

```text
strategy_v2 / S3（冻结只读）
  → 每日推荐（Top-K=20，空缺席位等权）
  → T+1 限价入场（限价 = 区间上沿；开盘更低则按开盘价 = 价格改善）
  → target / stop / time-stop(40 交易日)
  → 平仓 → 现金回流 → 下一轮
```

- **9 个模块 / 2,400 余行**，order / position / cash / lifecycle 全部自己管理。
- 市场数据**注入式**（`LiveMarket` / 测试 `FakeMarket`），整条状态机毫秒级可测。
- **追加式账本** + 每次运行对账（7 条恒等式）；**先写 state 再写账本**，
  崩溃时账本落后 → 下次大声报错，**不会重放同一段交易日导致重复记账**。
- **追赶**（漏跑几天）逐日重放 —— 漏跑期间触发的止损会被补在**正确的日子**上；
  但**冷启动绝不补历史**（3 条测试锁死）。
- **人工干预三层分离**（recommendation / decision / execution），
  用户的修改**不写回系统建议**。
- **出场语义**：目标/止损是挂在市场上的 resting order，触发当天按 OHLC 原子判定
  （跳空一律用开盘价，**绝不用收盘价冒充成交价**）；同日双触发**一律按止损**（保守）；
  **同日禁卖**（A 股 T+1）；时间止损是收盘决策 → **次日开盘**成交。
- **全程可追溯**：signal → order → fill → position → exit → cash → ledger，每一环都带日期。

### 18.4 配置与冻结

`config/daily_exit_paper_v1.yaml` 的每个数值都是**继承**的，不是新选的：

```text
signal_horizon_days = 20   ← strategy_v2.label_horizon_days
top_k               = 20   ← strategy_v2.portfolio.top_k
risk_profile        = balanced  ← trade_plan 既有默认档
time_stop.days      = 40   ← plan.py 的 horizon×2 定义
transaction_costs          ← 与 paper_live 逐字相同（有测试断言）
```

首次运行锁定本金与配置哈希；之后改本金/改配置**直接拒绝**，只能新建版本。

### 18.5 本版新增的测试与验证

```text
tests/daily_exit_paper/     8 个文件 / 104 条
tests/forward/              +23 条（C1 挂单生命周期 9、C2 调仓日 14）
tests/strategy/             +13 条（C3 缓存契约）
全量                        1160 passed / 0 failed（v1.0.5 时是 1020）
```

真实数据影子验证（PHASE 6）：09-24 → 09-28 跨中秋假期 **20 笔成交**、
成交价与执行日开盘价 **20/20 精确相符**、账本现金精确对账；
目标/止损判定的**六个分支全部在真实 bar 上被走到过**。

### 18.6 代码冻结（本版最重要的变化）

从 v1.1.0 起，`daily_exit_paper_v1` 的**交易规则正式冻结**：

```text
strategy_v2 / S3 / horizon / Top-K / risk profile / 入场规则 /
target 规则 / stop 规则 / time stop / 成本模型 / 仓位规模 /
T+1 规则 / 状态机 / 记账
```

**禁止**因为最近几笔盈亏而调整任何一项。改规则 = **新建
`daily_exit_paper_v1.1`**，新目录、新账本；绝不改完继续叫 v1。
任何 bug / 人工干预 / 数据中断 / 漏跑 / 异常成交都记入
`experiments/daily_exit_paper_v1/incidents.md`。

> PersonalQuant 不再"每天被改得更好"，而是作为一个**固定的实验对象**接受市场检验。
> 只有这样，将来得到的收益率才有实验意义。
