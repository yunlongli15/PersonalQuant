# 步骤 1 基线实验：Qlib LightGBM + Alpha158

实验日期：2026-09-05
本报告由 `config/workflow_config_lightgbm_Alpha158.yaml` 的一次完整运行生成，
完整日志见 `logs/step1_qlib_workflow.log`。

## 运行时间

| 阶段 | 耗时 |
| --- | --- |
| 数据加载 + Alpha158 特征计算 | ~45 s |
| 数据处理（fit & process） | ~2 s |
| LightGBM 训练（早停） | ~4 s（60 轮，best_iteration=23） |
| 测试集预测 + 信号分析 | ~1 s |
| 回测（871 个交易日） | ~31 s |
| **总计** | **约 90 s**（20 线程 CPU，无 GPU） |

## 环境

| 项目 | 值 |
| --- | --- |
| 操作系统 | Windows 11 Pro 23H2 |
| CPU / 内存 | Intel i5-14600KF（14C/20T）/ 32 GB |
| Python | 3.12.10（项目虚拟环境 `.venv`，用户级安装，系统 3.13 未动） |
| Qlib | pyqlib 0.9.7（官方 PyPI，cp312 win_amd64 wheel） |
| LightGBM | 4.7.0（CPU 版，num_threads=20） |
| 其他关键依赖 | pandas 2.2.3（为兼容 qlib 0.9.7 从 3.0.5 降级）、numpy 2.5.2、mlflow 3.16.0 |

## 数据

| 项目 | 值 |
| --- | --- |
| 数据位置 | `qlib_data/`（calendars / instruments / features） |
| 数据来源 | qlib 官方 README 推荐数据源 chenditc/investment_data，release 2026-09-04（`qlib_bin.tar.gz`，538 MB，SHA256 校验一致） |
| 选择原因 | qlib 官方 CLI 数据集已按官方声明暂时禁用；CLI 回退数据包（SunsetWolf v2/latest）实测缺少 Alpha158 必需的 `vwap` 字段，无法跑通 workflow |
| 交易日历 | 2000-01-04 ~ 2026-09-04（6,465 个交易日） |
| instrument 总数 | 6,148（SH 2,468 / SZ 3,089 / BJ 等），含 csi300 等指数成分列表 |
| 每只股票字段 | open, high, low, close, volume, amount, vwap, adjclose, factor, change |

## 股票池 / 模型 / 因子

| 项目 | 值 |
| --- | --- |
| 股票池 | csi300（动态成分，按日期区间） |
| 基准 | SH000300 |
| 因子 | Alpha158（158 个特征，含 price/rolling/kbar 组） |
| 模型 | LightGBM（`qlib.contrib.model.gbdt.LGBModel`） |
| 模型参数 | loss=mse, lr=0.2, colsample=0.8879, subsample=0.8789, lambda_l1=205.7, lambda_l2=580.98, max_depth=8, num_leaves=210, num_threads=20 |
| 标签 | `Ref($close,-2)/Ref($close,-1)-1` |

## 时间区间（与官方 workflow 完全一致）

| 区间 | 起止 |
| --- | --- |
| 特征窗口 | 2008-01-01 ~ 2020-08-01 |
| train | 2008-01-01 ~ 2014-12-31 |
| valid | 2015-01-01 ~ 2016-12-31 |
| test | 2017-01-01 ~ 2020-08-01 |
| 回测 | 2017-01-01 ~ 2020-08-01 |

## 模型与信号结果

| 指标 | 值 |
| --- | --- |
| 训练轮数 | 60（早停于 best_iteration=23） |
| train l2 | 0.9792 |
| valid l2 | 0.9934 |
| IC | 0.0470 |
| ICIR | 0.3816 |
| Rank IC | 0.0487 |
| Rank ICIR | 0.4057 |
| 测试集预测行数 | 261,207（871 只股票） |

## 回测结果（TopkDropoutStrategy, topk=50, n_drop=5）

回测配置：初始资金 1 亿元；deal_price=close；open_cost=0.05%；close_cost=0.15%；min_cost=5 元；
limit_threshold=0.095；871 个交易日中 870 天持有 50 只股票。

| 指标 | 基准 SH000300 | 超额收益（无成本） | 超额收益（含成本） |
| --- | --- | --- | --- |
| 日均收益 | 0.0477% | 0.0619% | 0.0465% |
| 日波动率 | 1.23% | 0.55% | 0.55% |
| 年化收益 | 11.36% | 14.73% | 11.06% |
| 信息比率 IR | 0.599 | 1.738 | 1.305 |
| 最大回撤 | -37.05% | -7.83% | -8.58% |

- 期末账户：2.073 亿元（初始 1 亿元，约 3.58 年）
- 指标分析：ffr（订单成交率）=1.0（全部成交）；pa（价格优势）=0.0、pos（正优势占比）=0.0
  ——因为 deal_price=close 按收盘价成交，无执行价格优势，属预期值。

## 成功判定

| 验收项 | 结果 |
| --- | --- |
| 数据加载 | ✅ 45 s |
| Alpha158 特征生成 | ✅ |
| LightGBM 训练 | ✅ 60 轮早停 |
| 测试集预测 | ✅ 261,207 行 |
| 回测执行 | ✅ 871 天 |
| 预测结果产出 | ✅ pred.pkl（mlflow artifact） |
| 回测/绩效指标产出 | ✅ port_analysis + indicator_analysis |
| 日志保存 | ✅ logs/step1_qlib_workflow.log |
| mlflow 记录 | ✅ experiment 776714041301577799（mlruns/） |

## 警告与异常说明

| 警告 | 说明 | 处置 |
| --- | --- | --- |
| `MlflowException: filesystem tracking backend in maintenance mode` | mlflow 3.x 默认禁用文件存储后端，qlib 0.9.7 默认用 `./mlruns` | 设置 `MLFLOW_ALLOW_FILE_STORE=true`（官方提供的 opt-out），重跑成功 |
| `common_infra is not set`（SimulatorExecutor） | 0.9.7 中 executor 初始化时序的正常提示，`backtest()` 随后会创建并注入 common_infra | 无需处理 |
| `$close field data contains nan`（×2，回测第 1 日） | 个别股票在回测首日缺 close（停牌等），按官方逻辑跳过 | 无需处理 |
| numpy timedelta DeprecationWarning（qlib.constant） | qlib 内部 `pd.Timedelta("1day")` 等写法在新 numpy 下的弃用警告 | 上游问题，不影响结果 |
| Gym 卸载提示（gym 0.26.2 已不维护） | 由 mlflow 3.16 依赖链带入，qlib workflow 不使用 gym | 后续阶段如需 RL 换用 gymnasium |
| pandas 3.0.5 曾被 pip 自动安装 | qlib 0.9.7 发布于 pandas 2.x 时代，3.0 存在运行时兼容风险 | 已降级并固定 pandas==2.2.3 |

## 复现方式

```bash
source .venv/Scripts/activate
python scripts/verify_step1.py
PYTHONIOENCODING=utf-8 MPLBACKEND=Agg MLFLOW_DISABLE_AGENT_HINT=1 MLFLOW_ALLOW_FILE_STORE=true \
    qrun config/workflow_config_lightgbm_Alpha158.yaml
```

workflow 配置与官方 `qlib v0.9.7 examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml`
逐项一致，唯一改动为 `provider_uri` 指向本项目 `qlib_data/`。

## 结论

STEP 1 目标达成：稳定、可重复的 Qlib 量化研究环境已建立，官方 LightGBM + Alpha158
workflow 完整运行并通过回测，全部验收项满足。
