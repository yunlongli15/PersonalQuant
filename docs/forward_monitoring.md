# Forward 监控 —— 只观察，不反馈

## 核心原则

从 2026-09-18 起，系统的任务从"优化过去"变成"真实地向前走"。

**观察结果不反馈到任何决策。** 表现差 → 不改；表现好 → 也不加强。
所有异常只进入 monitoring report。

## 监控什么

### 预测质量（§16 / §19）

逐期 IC / RankIC / ICIR / 正比率、分位收益、Top-K 实际前瞻收益、
预测离散度、预测排名稳定性；滚动 20D / 60D IC、月度 IC。

### 组合业绩（§14）

日收益、累计收益、回撤、换手、成本、相对基准的 active return。

### 漂移（§20-§23）

| 类型 | 检查 |
|---|---|
| strategy | config / model / feature pack 的 sha256 vs 冻结值 |
| model | 预测分布（均值、标准差、偏度）相对历史基线的 z 距离 |
| concentration | Top-1 预测分相对截面的 z |
| news | 新闻因子分布相对历史基线的位移 |
| data | 股票数 / 缺失率 / 覆盖率的相对变化 |

**漂移只产生 WARNING，绝不自动修复。**

### 告警（§29-§31）

| code | 触发 | 级别 |
|---|---|---|
| `PIT_FAILURE` | PIT 审计 INVALID | CRITICAL |
| `STRATEGY_DRIFT` | 冻结工件哈希不一致 | CRITICAL |
| `STRATEGY_UNFROZEN` | 配置尚未冻结 | WARNING |
| `MODEL_DRIFT` | 预测分布漂移 | WARNING |
| `CONCENTRATION_WARNING` | Top-1 预测 z > 3 | WARNING |
| `DRAWDOWN_ALERT` | 回撤触及 −5% / −10% / −15% | WARNING |
| `ABNORMAL_TURNOVER` | 换手 > 历史中位数 × 3 | WARNING |
| `IC_NEGATIVE_STREAK` | 连续 2 期 IC < 0 | WARNING |
| `DATA_QUALITY_WARNING` | 审计 WARNING / 数据漂移 | WARNING |

告警文本里**不得出现任何下单动作**（`test_alerts.py` 有断言守着）。

### 样本不足时不给结论（§18 / §41）

- 前瞻窗口没走完 → 该格是 **NA**，不是 0。
- 净值序列 < 60 天 → 不给年化、不给 Sharpe。
- 年度不足 230 个观测日 → 标记 `INCOMPLETE YEAR`，不做年化。

## 事实与解释分开（§27）

报告里先把事实列全：

```
FACT：本月策略 −2.1%，CSI300 +1.3%，IC = 0.021
```

再单独给允许的解释。**禁止从短期数字自动推出"模型失效"。**
24 个月的可检出最小年化差异约 41pp（见
`reports/step9_independent_info.md`），月度样本对年化的分辨力极低。

## Dashboard 数据层（§28）

```bash
python scripts/paper_live/build_dashboard.py
```

产出 `forward_holdout/dashboard/forward_dashboard.parquet` + `.json`。
GUI 留给下一阶段，本阶段只建数据层。

## 月度报告（§26 / §40）

```bash
python scripts/paper_live/monthly_report.py --month 2026-10
```

生成 `reports/forward_holdout/2026-10.md`，含 18 个板块，其中明确写明
"本月未做任何模型/参数修改"，并附冻结校验结果。
