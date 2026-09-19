# Forward Holdout —— 从 2026-09-18 起的干净样本外

## 为什么需要它

2024-2025 这个"测试集"已经被评估过三次：

| 时间 | 用途 |
|---|---|
| STEP 6 | strategy_v2 的 9 项 candidate gates 终评 |
| step8 | 微结构因子消融（S3 / M / N） |
| step9 | 独立信息研究（S3 / I / R + 五变体检验） |

每看一眼，它就少一分样本外性质。继续把它当成"没碰过的测试集"是自欺。

**结论：2024-2025 降级为 `HISTORICAL_TEST_OBSERVED`**，只读、只报告。
干净的样本外证据只能来自此后新增的数据。

## 三个角色，不得混淆

```
历史研究     →  DISCOVERY    （找想法，随便看）
Validation   →  SELECTION    （做选择，只看 2018-2023）
Forward      →  OBSERVATION  （只观察，绝不回头改）
```

代码层面各有一条守卫：

| 守卫 | 拦截什么 |
|---|---|
| `incremental/windows.py::assert_selection_window` | 选择路径上出现 2018-2023 之外的日期 |
| `incremental/holdout.py::ForwardHoldout.assert_not_selection` | 选择路径上出现 2026-09-18 之后的日期 |
| `paper_live/config.py::assert_not_used_for_selection` + `FORWARD_HOLDOUT_READ_ONLY` | forward 数据流入因子/模型/优化器选择 |

## 起点为什么是 2026-09-18

- 2026-01-01 ~ 2026-09-17 用于生成 paper-live 建议（不是选择，但已被观察）。
- 数据快照截至 2026-09-17。
- 因此干净起点取**最后一个已被观察日期的次日**：`2026-09-18`。

## 数据结构

```
forward_holdout/
├── predictions/<date>.parquet     forward_predictions（§3 字段）
├── portfolio/<date>.parquet       当日持仓与市值
├── trades/<date>.parquet          下单 + 成交结果
├── metrics/<date>.parquet         逐日业绩事实
├── manifests/daily_manifest_<date>.json
├── observations/<date>.json       完整性日志（append-only）
├── alerts/<date>.json
├── state/paper_portfolio.json     账户指针（可更新）
├── state/state_log.jsonl          指针的历史版本
├── revisions.jsonl                每一次 revision 的原因
└── recommendations/<date>.csv     调仓日买卖清单
```

**数据目录不入 git**（`spec §51`）；`reports/forward_holdout/*.md` 入库。

### forward_predictions 字段

`prediction_date, signal_date, symbol, predicted_return, rank,
target_weight, model_version, feature_version, strategy_version,
data_snapshot_id`（+ `predicted_return` 的同义列由引擎填充）

### forward_realized_returns

由 `paper_live.metrics.realized_returns()` **按需派生**，不单独存储：
`realized_return_1d / 5d / 20d / 60d`。

**窗口没走完就是 NA，绝不填 0**（§18）。填 0 会把"还不知道"伪装成
"收益为零"，直接污染任何后续统计。

## append-only 与 revision（§25 / §34）

1. **不可覆盖**：同一天同一类数据写出第二次且内容不同 → 直接 `PermissionError`。
2. **不可回填**：新写入日期不得早于已记录的最大 forward 日期。
3. **revision 需要理由**：确实遇到数据源 bug 时用
   `write_frame(..., allow_revision=True, reason="...")`，旧版本保留，
   新版本写成 `<date>__rev<N>.parquet`，并在 `revisions.jsonl` 记一行。
4. **幂等**：`run_day` 对已记录过的日期直接返回，不重复交易
   （调度器重复触发不会把账户交易两次）。
5. **`created_at` 不参与比较**：否则同一天重跑会因为时间戳不同而报 revision。

## 当前状态

forward holdout 尚无观测数据 —— 数据快照截至 2026-09-17，起点是 09-18。
这是**预期状态**，不是故障。按 §26：不要因为样本短就急着评估。

```bash
python scripts/monitor_forward_holdout.py     # 看状态
python scripts/paper_live/build_dashboard.py  # 生成 dashboard 数据层
```
