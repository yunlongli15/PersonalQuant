# Personal A-Share Quantitative Investment System

个人用 A 股低频量化投资研究与决策系统。完全本地运行，不涉及实盘交易。

## 项目目标（总览）

```
A股数据 → 数据清洗与本地数据库 → 因子计算与因子挖掘 → 机器学习 Alpha 模型
→ 新闻/公告 NLP 因子 → 历史回测 → 组合优化 → 每周/每月调仓建议
→ 具体股票与目标持仓数量 → 个人真实持仓管理 → 可视化 GUI
```

分阶段推进，**当前处于 STEP 1**，绝不超前开发。

## 当前状态

**STEP 1（进行中）：建立稳定、可重复的 Qlib 量化研究环境**

- ✅ 环境检查（Windows 11 + i5-14600KF / 32GB / RTX 4070 Ti）
- ✅ 项目结构建立
- ✅ 隔离虚拟环境（`.venv`，Python 3.12，用户级安装，不动系统 3.13）
- ✅ Qlib（pyqlib 0.9.7）安装与 import 验证
- ✅ 官方中国市场示例数据（`qlib_data/cn_data`）
- ✅ 数据读取验证（`tests/test_qlib_data.py`）
- ✅ 官方 LightGBM + Alpha158 workflow 与回测
- ✅ 基线报告（`reports/step1_qlib_baseline.md`）
- ✅ 自动化验证脚本（`scripts/verify_step1.py`）
- ✅ Git 初始化与提交

详细进度见 [ROADMAP.md](ROADMAP.md)。

## 环境要求

- Windows 10/11 x64（Linux/macOS 亦可，命令略有差异）
- Python 3.12（pyqlib 0.9.7 官方 wheel 支持 cp38–cp312，**不支持 3.13**）
- git
- 磁盘空间 ≥ 10 GB（Qlib cn 数据约 3–4 GB）

## 安装方法

```bash
# 1. 创建虚拟环境（如 .venv 不存在）
py -3.12 -m venv .venv        # 或: python3.12 -m venv .venv
source .venv/Scripts/activate  # Windows Git Bash
# Linux/macOS: source .venv/bin/activate

# 2. 安装依赖（使用官方 PyPI 索引，清华镜像缺 pyqlib）
python -m pip install --upgrade pip
python -m pip install -i https://pypi.org/simple pyqlib==0.9.7 lightgbm matplotlib mlflow fire

# 3. 下载中国市场示例数据（qlib 官方 README 推荐的数据源）
#    注意：qlib 官方 CLI 数据集已暂停（详见 docs/environment_check.md），
#    官方 README 指引使用 chenditc/investment_data 社区数据源：
curl -L -o /tmp/qlib_bin.tar.gz https://github.com/chenditc/investment_data/releases/latest/download/qlib_bin.tar.gz
tar -xzf /tmp/qlib_bin.tar.gz -C qlib_data --strip-components=1
rm /tmp/qlib_bin.tar.gz
```

## 运行方法

```bash
source .venv/Scripts/activate   # 激活虚拟环境

# 一键验证整个 STEP 1 环境
python scripts/verify_step1.py

# 数据读取测试
python -m pytest tests/ -v

# 运行官方 LightGBM + Alpha158 workflow（完整回测）
# MLFLOW_ALLOW_FILE_STORE=true 是必需的：mlflow 3.x 默认禁用 qlib 0.9.7 使用的
# 文件存储后端 ./mlruns（详见 reports/step1_qlib_baseline.md 警告说明）
PYTHONIOENCODING=utf-8 MPLBACKEND=Agg MLFLOW_DISABLE_AGENT_HINT=1 MLFLOW_ALLOW_FILE_STORE=true \
    qrun config/workflow_config_lightgbm_Alpha158.yaml
```

workflow 完整运行一次在本机（20 线程 CPU）约需 2 分钟，基线结果见
`reports/step1_qlib_baseline.md`，日志示例见 `logs/step1_qlib_workflow.log`。

## 目录结构

```
PersonalQuant/
├── README.md            # 本文件
├── CLAUDE.md            # AI 协作开发规范
├── ROADMAP.md           # 阶段路线图与进度
├── pyproject.toml       # 项目元信息与依赖声明
├── config/              # workflow 等运行配置
├── scripts/             # 验证/辅助脚本
├── tests/               # 测试
├── docs/                # 文档与检查报告
├── data/                # 后续阶段的本地数据（STEP 1 不使用）
├── qlib_data/           # Qlib 官方 cn 数据（git 忽略）
├── reports/             # 实验报告
├── logs/                # 运行日志
└── .venv/               # 项目虚拟环境（git 忽略）
```

## 重要约定

- 本阶段（STEP 1）仅使用 Qlib 官方示例数据与官方 workflow，不自行开发策略。
- 严禁实盘交易、券商 API、自动下单。
- 数据与模型结果仅用于研究，不构成投资建议。
