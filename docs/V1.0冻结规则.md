# V1.0 冻结规则

**发布日期：2026-09-19**（V1.0.0）

从发布日起，**生产策略不允许直接修改**。

## 什么是"生产"

`config/production_freeze.yaml` 里的哈希覆盖的工件，就是生产：

| 工件 | 内容 |
|---|---|
| `config/paper_live.yaml` | paper live 参数（本金 / Top-K / 成本 / 执行） |
| `config/strategy_v2.yaml` | 冻结 alpha + 分配方法 |
| `config/strategy_v1.yaml` | 模型参数与股票池规则 |
| `feature_pack_v1` | STEP 4 选定的因子包 |
| `news_factor_pack` | STEP 5 选定的新闻因子包 |
| `production_model` | S3 生产模型权重 |

每天跑流水线前自动校验。不一致 → `PRODUCTION_DRIFT` → **停止正式 forward
observation**（数据与报告照常产出，用户能看到发生了什么）。

## 想改怎么办

**不要改生产配置。** 新建一个 experiment：

```
config/experiments/<你的实验名>.yaml     # 从生产配置复制后修改
```

并在报告里记录：改了什么、为什么、用什么数据评估。

评估纪律：

- 只能用 **2018-2023**（research + valid）
- **2024-2025 = HISTORICAL TEST**（已被观察多次），只作对照，不作选择依据
- **2026-09-18 起的 forward holdout 只观察，绝不回流到选择**

## 冻结记录长什么样

```yaml
production_freeze:
  version: "1.0.0"
  freeze_date: "2026-09-19"
  git_commit: "<commit>"
  production_enabled: true          # 一键停止开关
  strategy_version: strategy_v2
  feature_version: alpha158+factor_pack_v1
  news_feature_version: factor_pack_news_v1
  model_version: s3
  allocation_method: equal_weight
  execution_model: T1_open
  forward_holdout_start: "2026-09-18"
  hashes: {...}                     # 每个工件的 sha256
```

## 一键停止

把 `production_enabled` 改成 `false`：流水线照常更新数据、生成报告，
但**不产生正式 forward observation**。

## 命令

```bash
python scripts/freeze_production.py --check   # 校验
python scripts/freeze_production.py           # 首次冻结（已冻结且不一致时拒绝覆盖）
```

`write_freeze()` 在"已冻结但哈希不一致"时**抛异常拒绝覆盖** ——
冻结只能做一次；要变更请新开 experiment，而不是悄悄改掉哈希。
