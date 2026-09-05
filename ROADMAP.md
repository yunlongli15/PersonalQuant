# ROADMAP — Personal A-Share Quantitative Investment System

每个阶段只有在验收标准全部满足后才标记 COMPLETED。
每次完成一个阶段后，先停下来汇报，未经允许不自动开始下一阶段。

## STEP 1: Establish Qlib research environment

> 目标：在本机建立稳定、可重复的 Qlib 量化研究环境，使用 Qlib 官方中国 A 股
> 示例数据，完整运行一次官方 LightGBM + Alpha158 workflow 和回测。

状态：**COMPLETED**（2026-09-05）

### 做了什么

- 检查机器环境（Windows 11、i5-14600KF 20 线程、32GB 内存、RTX 4070 Ti），
  写入 `docs/environment_check.md`。
- 建立项目目录结构（README / CLAUDE.md / ROADMAP / pyproject.toml / config /
  scripts / tests / docs / data / qlib_data / reports / logs）。
- 因系统 Python 3.13 无 pyqlib wheel，通过 winget 用户级安装 Python 3.12，
  在项目内创建 `.venv` 虚拟环境（不触碰系统 Python）。
- 安装 pyqlib 0.9.7（官方 PyPI）、lightgbm、matplotlib、mlflow、fire，
  并将 pandas 固定在 2.2.3（qlib 0.9.7 与 pandas 3.x 不兼容）。
- 下载中国市场示例数据：qlib 官方 CLI 数据集已按官方声明暂停，且其回退数据包
  （SunsetWolf v2/latest）实测缺少 Alpha158 必需的 `vwap` 字段；按官方 README
  指引改用社区数据源 chenditc/investment_data（release 2026-09-04，538 MB，
  SHA256 校验一致），解压到项目 `qlib_data/`。日历 2000-01-04 ~ 2026-09-04，
  6,148 个 instrument，字段含 open/high/low/close/volume/amount/vwap/adjclose/
  factor/change。
- 编写 `tests/test_qlib_data.py`：验证 init / 交易日历 / instrument 列表 /
  个股日线读取 / 时间索引 / 数据完整性。
- 复制官方 workflow 配置到 `config/workflow_config_lightgbm_Alpha158.yaml`
  （仅把 provider_uri 指向本项目 `qlib_data/cn_data`，其余与官方完全一致），
  完整运行 LightGBM + Alpha158 workflow 与回测。
- 生成 `reports/step1_qlib_baseline.md` 基线报告；日志存于
  `logs/step1_qlib_workflow.log`。
- 编写 `scripts/verify_step1.py` 一键验证脚本（PASS/FAIL 输出）。
- git init、.gitignore（排除 venv/qlib_data/logs/缓存等）、首次 commit。

### 使用环境

- Windows 11 Pro 23H2；Intel i5-14600KF（14C/20T）；32GB RAM；RTX 4070 Ti
- Python 3.12.x（用户级安装）→ 项目虚拟环境 `.venv`
- pyqlib 0.9.7 + lightgbm 4.7.0（CPU 版，workflow 用 20 线程）+ mlflow 3.16 + pandas 2.2.3
- 中国市场数据：`qlib_data/`（1d 频率，chenditc/investment_data 2026-09-04）

### 基线结果（官方 workflow，详见 reports/step1_qlib_baseline.md）

- 训练：2008–2014；验证：2015–2016；测试/回测：2017-01-01 ~ 2020-08-01
- IC 0.047 / ICIR 0.382 / RankIC 0.049
- 回测（topk=50，含双边成本）：超额年化 11.06%、IR 1.31、最大回撤 -8.6%
- 期末账户 2.073 亿（初始 1 亿）；总运行时间约 90 秒

### 解决的问题

1. Python 3.13 无 pyqlib wheel → 用户级安装 Python 3.12 建 venv。
2. 清华 pip 镜像缺 pyqlib → 安装时显式指定官方 PyPI 索引。
3. wmic 在 Win11 上不可用 → 改用 PowerShell Get-CimInstance。
4. pandas 3.0.5 被 pip 自动安装，与 qlib 0.9.7 存在兼容风险 → 固定 pandas==2.2.3。
5. mlflow 3.x 默认禁用文件存储后端，qlib recorder 直接报错 →
   设置 `MLFLOW_ALLOW_FILE_STORE=true` 重跑成功。
6. 官方 CLI 数据暂停且回退包缺 vwap 字段 → 按官方 README 改用 chenditc 数据源。

### 如何重新运行

```bash
source .venv/Scripts/activate
python scripts/verify_step1.py                 # 一键验证环境（21 项 PASS/FAIL）
# 重跑官方 workflow（本机约 2 分钟）
PYTHONIOENCODING=utf-8 MPLBACKEND=Agg MLFLOW_ALLOW_FILE_STORE=true \
    qrun config/workflow_config_lightgbm_Alpha158.yaml
```

### 下一步

**STEP 2: Build local A-share data infrastructure**（未开始）

设计目标（暂定，届时细化）：

- 确定 A 股历史 + 每日增量行情数据源与获取方式
- 数据清洗管线（停牌/复牌、除权除息、ST、上市退市日期等）
- 本地数据库（如 SQLite/Parquet）与更新任务
- 将清洗后数据接入 Qlib 自定义 provider 的可行性验证

---

## 后续阶段草案（远期待定，不在当前开发范围）

- STEP 3: Factor calculation & mining（基于 Qlib Alpha158 扩展）
- STEP 4: ML Alpha models（LightGBM/神经网络等）
- STEP 5: News/announcement NLP factors
- STEP 6: Backtesting framework refinement
- STEP 7: Portfolio optimization
- STEP 8: Weekly/monthly rebalance suggestions
- STEP 9: Real personal holdings management
- STEP 10: GUI visualization
