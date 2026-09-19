# PersonalQuant V1.0.0 发布说明

**发布日期：2026-09-19** ｜ `cat VERSION` → `1.0.0`

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

```bash
python scripts/run_daily.py            # 每天跑这一条
python scripts/run_daily.py --dry-run  # 只看检查，不写任何东西
python scripts/system_health.py        # 系统健康
```

14 个步骤，普通日约 30 秒 ~ 2 分钟。

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
   手动跑 `run_daily.py` 即可，状态记 `SCHEDULER_NOT_INSTALLED`。
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
python scripts/run_daily.py --dry-run  # ② 干跑一遍
python scripts/run_daily.py            # ③ 正式跑
python scripts/run_app.py              # ④ 看界面
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
