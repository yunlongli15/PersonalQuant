# 数据与模型清单

本仓库包含 PersonalQuant 的**全部代码、模型与可复现数据**。
大体积、可再生成或第三方来源的数据按下面的规则处理。

> 数据快照：行情到 **2026-09-11**，新闻到 2026-09-09，
> 信号/预测/交易计划到 **2026-09-11**。

---

## ✅ 仓库中包含（可直接使用）

| 路径 | 内容 | 大小 |
|---|---|---|
| `experiments/**/model.txt` | **训练好的 LightGBM 模型**（strategy_v1、S3 生产模型、各消融变体） | ~1 MB |
| `experiments/**/*.json` | 每次实验的指标、manifest、选择协议、gates | ~10 MB |
| `data/parquet/daily/` | **canonical 日线**（原始价 + factor，2000–2026，按年分区） | ~450 MB |
| `data/parquet/{securities,calendar,valuation,industry,...}` | 证券主表、交易日历、估值快照、行业、公司行为 | ~1 MB |
| `data/derived/factors/` | 因子平台缓存：日历、标签、股票池、财务快照、行业 | ~26 MB |
| `data/derived/news/` | 新闻事件、覆盖率、新闻因子（171,667 条公告派生） | ~11 MB |
| `data/derived/labels/` | 预测标签 | ~6 MB |
| `data/quant/` | **信号快照、预测、交易计划、闭环报告、job 记录** | ~0.6 MB |
| `reports/` | 全部研究报告、图表、paper-live 建议 | ~15 MB |
| `config/` | 策略/组合/新闻/账户档案配置 | — |

## ⛔ 仓库中不包含（附原因与再生成方式）

| 路径 | 大小 | 为什么不入库 | 怎么拿回来 |
|---|---|---|---|
| `qlib_data/` | 845 MB | 第三方数据集（chenditc/investment_data），可直接下载 | `python scripts/quant/update_market_snapshot.py` |
| `data/raw/` | 589 MB | 原始 HTTP 响应缓存，可重新抓取 | 重新运行对应 provider |
| `data/derived/features/` | 357 MB | Alpha158 特征月度缓存，可从 canonical 重算 | `scripts/factor_prepare.py` + 策略特征计算 |
| `data/duckdb/personal_quant.duckdb` | 112 MB | **超过 GitHub 单文件 100 MB 硬限制**；且它只是 parquet 之上的 SQL 视图层 | `python scripts/bootstrap_data.py --skip-bars` |
| `data/wealth/wealth.db` | — | **个人真实资产数据，按设计不出本机**（safety §41） | 本地自行录入 |
| `backup/` | — | 财富库备份 | 本地生成 |

## 🔁 从零重建（新机器）

```bash
# 1) 环境
py -3.12 -m venv .venv && source .venv/Scripts/activate
python -m pip install -i https://pypi.org/simple pyqlib==0.9.7 lightgbm matplotlib mlflow fire \
    duckdb pyarrow pandas==2.2.3 fastapi uvicorn akshare pymupdf pdfplumber scikit-learn

# 2) 市场数据（约 565 MB 下载）
python scripts/quant/update_market_snapshot.py

# 3) 派生数据（日历/标签/股票池/财务快照/特征缓存）
python scripts/factor_prepare.py

# 4) 验证
python scripts/verify_step1.py … scripts/verify_step7.py
python -m pytest tests/ -q
```

## 🧭 数据版本与出处

| 数据 | 来源 | 版本/快照 |
|---|---|---|
| 日线行情 | chenditc/investment_data（qlib 官方 README 推荐） | release 2026-09-12（行情至 2026-09-11） |
| 交易日历 | 同上 | 同上 |
| 证券主表 | SSE/SZSE 官方 + 腾讯 | 见 `source_registry` |
| 估值快照 | 腾讯行情（东财 push2 有 WAF） | 2026-09-13 抓取 |
| 新闻公告 | SSE/SZSE/CNINFO 官方 | 171,667 条，2018–2026 |
| 财务指标 | 年报 PDF 按需提取（PIT） | 见 `reports/step4_financial_factor_coverage.md` |

每次导入都登记在 DuckDB 的 `source_registry` 表（来源、URL、版本、解析器版本）。
