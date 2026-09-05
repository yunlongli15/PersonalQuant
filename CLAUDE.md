# CLAUDE.md — 本项目 AI 协作开发规范

本文件给后续在此项目中工作的 Claude 提供开发规范。

## 项目定位

个人用 A 股低频量化投资研究与决策系统。**完全本地运行**，按 ROADMAP.md 分阶段推进。
当前阶段定义见 ROADMAP.md 顶部，**严禁超前开发未开始的阶段**。

## 铁律

1. **分阶段开发**：只做当前阶段（见 ROADMAP.md 状态行）。完成一个阶段后停下来
   汇报，未经用户明确指示不得自动开始下一阶段。
2. **严禁实盘交易**：任何阶段都不得接入券商 API、自动下单或涉及真实资金操作。
3. **不伪造结果**：不得修改官方示例/基准逻辑来“制造更好结果”；不得使用未来数据
   （标签与特征的时间对齐以 Qlib 官方实现为准）。
4. **不污染系统 Python**：所有 Python 工作都在项目虚拟环境 `.venv` 中进行。
   `.venv` 基于用户级安装的 Python 3.12（见 docs/environment_check.md 的决策）。
5. **不删除用户已有文件**：修改/删除前先查看内容，重要操作前确认。
6. **不跳过错误**：安装、导入、数据、workflow 任何一步失败都必须诊断并修复，
   不得静默绕过或降低标准。
7. **Qlib 版本锁定**：pyqlib 固定 0.9.7（官方最新，含 cp312 win wheel）。
   官方 Python 支持上限为 3.12，**不要升级到 3.13**。

## 环境速查

```bash
# 激活虚拟环境（Windows Git Bash）
source .venv/Scripts/activate

# 安装依赖（必须用官方 PyPI 索引——清华镜像缺 pyqlib）
python -m pip install -i https://pypi.org/simple <pkg>

# 验证环境
python scripts/verify_step1.py

# 官方 workflow（数据路径指向 qlib_data）
PYTHONIOENCODING=utf-8 MPLBACKEND=Agg MLFLOW_ALLOW_FILE_STORE=true \
    qrun config/workflow_config_lightgbm_Alpha158.yaml
```

- 数据目录：`qlib_data/`（来源 chenditc/investment_data 2026-09-04 release，
  qlib 官方 README 推荐数据源；官方 CLI 数据集已按官方声明暂停，且其回退包缺
  Alpha158 必需的 `vwap` 字段，勿再使用。日历 2000-01-04 ~ 2026-09-04）
- workflow 配置：`config/workflow_config_lightgbm_Alpha158.yaml`
  （内容与官方 `qlib v0.9.7 examples/benchmarks/LightGBM/` 中的配置一致，
  仅 `provider_uri` 指向项目本地数据目录）
- 日志：`logs/`；实验报告：`reports/`；mlflow 产物：`mlruns/`（git 忽略）
- **mlflow 3.x 必须加 `MLFLOW_ALLOW_FILE_STORE=true`**，否则 qlib 0.9.7 的
  文件存储 recorder 直接报 MlflowException（详见 reports/step1_qlib_baseline.md）

## 关键背景（决策记录）

- 系统原有 Python 3.13.8 无 pyqlib wheel（官方最高 cp312），因此用 winget 用户级
  安装了 Python 3.12 并创建项目 `.venv`。系统 Python 3.13 保持不动。
- pip 默认清华镜像缺 pyqlib，凡装 Qlib 相关包必须 `-i https://pypi.org/simple`。
- Win11 上 wmic 已被移除，系统信息查询用 `Get-CimInstance`。
- 机器 20 线程 / 32GB / RTX 4070 Ti：LightGBM 用 20 线程跑官方 workflow 可行；
  GPU 留给后续深度学习阶段。
- 官方 workflow 在本机（20 线程）完整跑一次约 2 分钟；跑之前先
  `python scripts/verify_step1.py`。
- **pandas 必须固定在 2.2.x**（qlib 0.9.7 为 pandas 2.x 时代产物，
  pip 会自动装 3.x，需显式 `pip install pandas==2.2.3`）。

## 本阶段（STEP 1）红线

以下内容属于后续阶段，**STEP 1 内不得开发**：实盘/券商 API/自动下单、新闻系统、
LLM 新闻分析、自定义复杂因子、Transformer、强化学习、GUI、Tushare、AkShare、
自动因子挖掘。
