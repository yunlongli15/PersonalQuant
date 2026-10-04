# 步骤 3 Qlib 集成方案（决策记录）

## 决策：方案 A —— 轻量级 Custom FeatureProvider（代码最少、稳定性最高）

在方案 A（Custom Qlib Provider）与方案 B（生成 Qlib 可读的中间数据视图）之间，
选择了 **A 的最小变体**：只替换 qlib 的 **FeatureProvider** 一层。

### 为什么选 A

| 考量 | 结论 |
| --- | --- |
| 代码量 | A：约 130 行（一个类 + 一个 init 函数）；B：需要实现 bin 格式写入器 + 全量数据复制 |
| 数据复制 | A：零复制，直接读 canonical parquet；B：产生第二份 GB 级数据副本，违背"单一事实来源" |
| 稳定性 | A：qlib 的 expression/dataset/缓存机制全部保持官方原样，只换数据入口；B：自制格式容易与 qlib 版本脱钩 |
| 维护 | A：canonical 层变更自动生效；B：每次数据变更都要重新生成视图 |
| qlib 核心 | 两者都不修改 qlib 源码、不 fork qlib、不破坏 STEP 1 官方 workflow |

### 数据流（canonical → model）

```
canonical DB（data/parquet + DuckDB）      <- 单一事实来源
   │  CanonicalFeatureProvider.feature()   （pyarrow 直读 parquet，谓词下推，
   │                                           价格字段即时调整为 raw×factor）
   ▼
qlib FeatureD wrapper（qlib.init kwargs 注入 C.feature_provider）
   ▼
qlib 官方 Expression 引擎 / Alpha158 handler（原样，含日历对齐、NaN 填充）
   ▼
月度特征切片 → data/derived/features/YYYY-MM.parquet（DERIVED 层缓存）
   ▼
LightGBM（train 2015-2021 / valid 2022-2023 / test 2024-2025）
   ▼
月度 Top-20 信号 → T+1 开盘执行（执行/股票池/标签全部直接读 canonical）
```

### 关键实现点

1. **注入方式**：`qlib.init(feature_provider={"class": ..., "module_path": ...}, ...)`。
   qlib.init 会重置默认配置，只有通过 init kwargs 传入的 provider 配置才会被
   `C.register()` 注册；子进程（joblib worker）通过 `C.register_from_C` 重建同一
   provider——这是 qlib 0.9.7 官方支持的自定义数据通道。
2. **口径一致**：特征用**调整价**（raw × factor，与 qlib Alpha158 设计一致，
   和 STEP 1 官方数据行为相同）；执行/标签/股票池用 canonical 原始价与 factor。
3. **日历对齐**：provider 按官方日历返回"日历位置索引 + 停牌日 NaN"的序列，
   与官方 LocalFeatureProvider 行为一致（shift/rolling 按交易日计数）。
4. **禁用 qlib 磁盘缓存**：`expression_cache=None, dataset_cache=None` ——
   全市场规模下 DiskExpressionCache 会写 ~70 万个小文件（Windows 上极慢），
   由我们自己的 DERIVED 层缓存（data/derived/features）替代。
5. **多进程安全**：worker 用 pyarrow 直读 parquet（任意线程/进程安全）；
   DuckDB 文件为单进程独占，故 provider 不使用 DuckDB（避免锁与 GIL 崩溃）。
6. **缺失数据**：季度窗口内无数据的股票返回全 NaN 序列（不抛异常），
   保证单个股票缺数据不杀死整个季度任务。

### 如何加入财务/新闻因子（未来）

- **财务因子**：STEP 2 的 `financial_metrics` 表已带 PIT 语义；未来在
  `personal_quant/strategy/features.py` 增加一个因子加载器，按 signal date
  做 `as_of_date > availability_date` 过滤后并入特征矩阵即可——不需要动 qlib
  集成层（特征侧可独立于 qlib 扩展）。
- **新闻因子**：后续阶段在 DERIVED 层生成新闻因子切片，同样在 features.py
  并入。

### 不做什么

- 不修改 qlib 源码、不 fork、不 monkeypatch qlib 核心路径（仅用官方
  provider 注册通道）。
- 不为让 qlib 直接读 DuckDB 而改 qlib（DuckDB 单写者模型与 qlib 多进程
  读取冲突，parquet 直读是正确边界）。
- STEP 1 的 qrun workflow 完全不受影响（独立进程、默认配置）。
