# INCIDENT — 2026-10-04 · `news_events_refresh` 因 DuckDB 索引失配失败

> 类型：**数据层故障**（不是交易 bug）
> 影响：刷新链停在 4/10；**未影响任何历史交易状态**（正式实验尚未启动，
> `experiments/daily_exit_paper_v1/` 当时不存在）
> 状态：**已恢复；同类隐患（5 处成组写入）已全部加固**

---

## 1. 症状

`python scripts/quant/refresh_all.py` 在 `news_events_refresh` 上**连续两次**失败：

```text
[4/10] news_events_refresh -> FAILED FatalException: FATAL Error:
Invalid Input Error: Failed to delete all rows from index.
Only deleted 318 out of 2048 rows.
```

失败点：`news/storage.py` 的 `replace_events()` 执行 `DELETE FROM news_events`
（全表 184,873 行）。

因为 `run_all` 是 **fail-fast**，链条停在 4/10：`valuation_update`、
`factor_refresh`、`signal_refresh`、`live_price_refresh`、`forecast_refresh`、
`portfolio_refresh` 全部没有运行，当天（2026-09-30）的信号/预测/交易计划没有刷新。

## 2. 影响面

| 项 | 结论 |
|---|---|
| 历史交易状态 | **未受影响** —— 正式实验尚未启动，实验目录不存在 |
| `news_documents` | **未受影响** —— 那 1,130 条新公告已正常提交（186,003 份） |
| `news_events` | 停留在旧的 184,873 行（未重建），已在本轮恢复中重建为 186,003 行 |
| 下游产物 | 当天未刷新；已在恢复时补齐（见 §5） |
| 备份 | 恢复前已备份 `backup/personal_quant.duckdb.20261004-1844`（含当时的 WAL）与 `…-1930` |

## 3. 根因（已证实）

**二级索引 `idx_news_events_symbol` 与表不一致。**

隔离过程（每一步都在副本上先备份，事务全部 ROLLBACK，未改数据）：

| 试验 | 结果 |
|---|---|
| 重新打开数据库 + WAL 回放 + 干净 checkpoint 后 `DELETE` | 成功 —— **WAL 回放不是根因**（随后重跑作业仍然失败，推翻了这一假设） |
| 无二级索引时 `DELETE` | 成功 |
| **`DROP INDEX idx_news_events_symbol` 后 `CREATE INDEX`（从表重建）** | **成功**；之后连做三次删除测试全部成功 |
| 用**真实作业**复跑 | `news_events_refresh -> SUCCESS`，随后 7 个作业全部 SUCCESS |

**修复动作**：把那个二级索引从表重建了一次。索引现在由表本身生成，天然自洽。

## 4. 触发原因（**未证实**，如实记录）

最可能的诱因是 **PHASE 7 期间我杀掉过一次 `refresh_all.py`** ——
后台任务默认 30 分钟时限到点被终止，当时进程正停在 `signal_refresh`
算特征的中途，DuckDB 会话被硬中断。

**但我无法证明这一点**，也不能排除 DuckDB 在"整表删除 + 重建"模式下的
自身缺陷。记录为"未证实"，不做结论。

## 5. 恢复步骤（可重复）

```bash
# 1) 备份（backup/ 已被 .gitignore 忽略）
cp data/duckdb/personal_quant.duckdb backup/personal_quant.duckdb.<时间戳>

# 2) 重建失配的二级索引（在 Python 里执行，或 duckdb CLI）
python - <<'PY'
import duckdb
con = duckdb.connect("data/duckdb/personal_quant.duckdb")
con.execute("DROP INDEX IF EXISTS idx_news_events_symbol")
con.execute("CREATE INDEX IF NOT EXISTS idx_news_events_symbol "
            "ON news_events(symbol)")
con.close()
PY

# 3) 从失败的那一步续跑（不必整条重来）
python scripts/quant/refresh_all.py --only \
    news_events_refresh,valuation_update,factor_refresh,signal_refresh,\
live_price_refresh,forecast_refresh,portfolio_refresh
```

恢复后数据状态：

```text
| Market Data | 2026-09-30 | ✓ |      | News     | 2026-09-30 | ✓ |
| Valuation   | 2026-09-30 | ✓ |      | Forecast | 2026-09-30 | ✓ |
| Factors     | 2026-10-04 | ✓ |      | Portfolio| 2026-09-30 | ✓ |
```

## 6. 顺带发现并修掉的真实缺陷（代码级）

### 6.1 `replace_events` 没有事务 —— 会造成**静默**的空表

```python
conn.execute("DELETE FROM news_events")     # 自动提交
conn.executemany("INSERT INTO news_events ...", rows)   # 另一条自动提交
```

这两步之间崩溃（Ctrl-C / 进程被杀 / DuckDB 报错）会留下**空的 `news_events`**。
而空表在下游**看不出来**：计数类新闻因子 0 是"真的没有事件"的合法取值
（`docs/step5_news_pit.md`），所以信号会**静默退化**，没有任何一层会报警。

**已修**：把 DELETE + INSERT 包进一个事务，异常（含 `KeyboardInterrupt`）一律
`ROLLBACK`。已验证：事务内删除 186,003 行后模拟中断 → 回滚 → 表原样 186,003 行。

### 6.2 仓库里**没有任何一处使用 `BEGIN`/`COMMIT`**（已全部加固）

根因是 **DuckDB 的 Python 客户端每条语句自动提交**：任何"先清空、再灌入"
的写法都是两次独立提交，中途失败就留下空表。同类共 5 处，全部已修：

| 位置 | 删什么 | 崩溃后果 | 状态 |
|---|---|---|---|
| `news/storage.py` | `news_events` | 新闻因子静默退化为 0 | **已修** |
| `personal_quant/ingest/qlib_baseline.py` | `trading_calendar` | 日历变空 → 全系统取不到交易日 | **已修** |
| `personal_quant/ingest/sse_reports.py` | `report_documents` | 公告索引变空 | **已修** |
| `personal_quant/ingest/sse_reports.py` | `company_lifecycle` | 生命周期变空 | **已修** |
| `personal_quant/storage/parquet.py` | 任意表 | 同上 | **已修** |

做法是 `personal_quant/db.py` 新增一个共享的 `db.transaction()` 上下文管理器
（`BEGIN` → 块内成功才 `COMMIT`；块内抛出的任何异常，含 `KeyboardInterrupt`，
一律 `ROLLBACK` 后重新抛出），上面 5 处全部改用它 —— 保证只有一份实现，
`news/storage.py` 里那份手抄的版本也已并进来。

`DB` 层之外的同类删除**不需要改**：`wealth/` 用的是 SQLite，其 Python 驱动
对 DML 默认开隐式事务、由 `conn.commit()` 收口，所以
`repository.replace_positions` 的"按日删除 + 重插 + 一次 commit"本来就是原子的
（`financial/query.py` 等按 key 限定的单条 DELETE 同理）。这是两种数据库的
语义差异，不是同一类缺陷。

**验证**（tests/test_duckdb_transaction.py，9 条）：

1. 机制本身：提交成功 / 出错回滚 / `KeyboardInterrupt` 回滚。断言比对的是
   **内容**而不是行数 —— 只看行数是抓不住这个 bug 的：自动提交时 DELETE 已经
   生效、后面那半截 INSERT 又灌了行进去，行数照样对得上。
2. 四处整表重建各一条：写入失败时旧数据必须原样还在（跑在一次性 DuckDB 上，
   不碰 canonical 库）。
3. **反证**：把 `db.transaction()` 换回加固前的自动提交行为重跑，**7/9 失败**，
   每一条的失败信息都是"旧数据没了"。不这样验一遍，通过只能说明测试是空的。
4. 真实库上另做两点确认：共享原语在长驻单例连接上提交/回滚正常；
   `replace_events` 对着真实的 186,003 行 `news_events`（含二级索引）失败时，
   行数与 `MIN/MAX(event_id)` 前后完全一致。

## 7. 流程层面的教训

1. **后台长任务必须显式给足超时。** 我在 PHASE 7 启动 `refresh_all.py`
   时没设 `timeout`，被默认的 30 分钟杀掉 —— 这是本次事故最可能的诱因。
   `refresh_all.py` 整条链的正常耗时是 5~7 分钟，但换快照时要下载 540 MB
   （实测约 1 小时），远超前者的预算。
2. **fail-fast 的表现是对的。** 链条停下来而不是带着空的新闻事件层继续跑，
   这正是设计意图。失败被 job store 如实记为 `FAILED`。
3. **诊断顺序是对的**：先备份 → 再只读隔离 → 再在事务里试删并回滚 →
   最后才动真格。全程没有"猜着修"，也没有删任何记录。
