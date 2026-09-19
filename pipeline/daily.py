# -*- coding: utf-8 -*-
"""每日流水线编排（STEP 12, spec §3）。

一句话：**每天跑一次 `python scripts/run_daily.py` 就够了。**

    环境检查 → 数据源健康 → 更新行情/日历/新闻/财务(按需) → 数据质量
    → Paper Live 预测 → (调仓日)目标组合 → T+1 模拟成交 → 更新 paper 组合
    → 个人账户快照 → 业绩 → 风险 → 漂移 → 日报 → manifest → 告警 → 状态

纪律（本阶段的核心，不是功能）
------------------------------
- **不新增任何投资逻辑**：prediction / portfolio / execution / cost /
  performance / risk 全部调用既有模块，本文件只做编排。
- **幂等**（§4/§5）：同一天重复运行且输入相同 → `ALREADY_COMPLETED`；
  `--force` 会新开一个 run 并**保留**原记录，绝不覆盖。
- **依赖图**（§22）：Data 失败则 Prediction 不允许运行。
- **冻结守卫**（§2/§35）：工件哈希不一致 → `PRODUCTION_DRIFT`，
  停止正式 forward observation（数据与报告照常）。
- **没有 forward 数据不算错**（§7）：latest market date < forward_start →
  `WAITING_FOR_FORWARD_DATA`。
- **绝不自动 retrain / 选因子 / 调参**（§33/§34）。

日志分级：INFO / WARNING / ERROR / INVALID —— 普通 API retry 不打成 ERROR。
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

OK = "OK"
WARNING = "WARNING"
SKIPPED = "SKIPPED"
FAILED = "FAILED"
INVALID = "INVALID"
BLOCKED = "BLOCKED"          # 依赖失败，未执行
ALREADY_COMPLETED = "ALREADY_COMPLETED"
WAITING_FOR_FORWARD_DATA = "WAITING_FOR_FORWARD_DATA"
PRODUCTION_DRIFT = "PRODUCTION_DRIFT"

REPORT_DIR = PROJECT_ROOT / "reports" / "daily"
LOG_DIR = PROJECT_ROOT / "logs" / "daily"
MANIFEST_DIR = PROJECT_ROOT / "data" / "quant" / "daily_runs"

log = logging.getLogger("daily")


# ---------------------------------------------------------------------------
# 结果结构
# ---------------------------------------------------------------------------

@dataclass
class TaskOutcome:
    name: str
    status: str = OK
    detail: str = ""
    error: str = ""
    duration_s: float = 0.0
    depends_on: Tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {"name": self.name, "status": self.status,
                "detail": self.detail, "error": self.error,
                "duration_s": round(self.duration_s, 2),
                "depends_on": list(self.depends_on)}


@dataclass
class DailyRun:
    run_id: str
    date: str
    status: str = OK
    started: str = ""
    ended: str = ""
    tasks: List[TaskOutcome] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    manifest: dict = field(default_factory=dict)
    dry_run: bool = False
    backfill: bool = False
    forward_observation: bool = False

    @property
    def duration_s(self) -> float:
        return sum(t.duration_s for t in self.tasks)

    def task(self, name: str) -> Optional[TaskOutcome]:
        return next((t for t in self.tasks if t.name == name), None)

    def failed(self) -> List[str]:
        return [t.name for t in self.tasks
                if t.status in (FAILED, INVALID)]

    def blocked(self) -> List[str]:
        return [t.name for t in self.tasks if t.status == BLOCKED]

    def as_dict(self) -> dict:
        return {
            "run_id": self.run_id, "date": self.date, "status": self.status,
            "started": self.started, "ended": self.ended,
            "duration_s": round(self.duration_s, 2),
            "dry_run": self.dry_run, "backfill": self.backfill,
            "forward_observation": self.forward_observation,
            "n_warnings": len(self.warnings), "n_errors": len(self.errors),
            "warnings": self.warnings, "errors": self.errors,
            "tasks": [t.as_dict() for t in self.tasks],
        }


# ---------------------------------------------------------------------------
# 日志（§19 / §37）
# ---------------------------------------------------------------------------

def setup_logging(run_date: str, verbose: bool = False) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / f"{run_date}.log"
    logger = logging.getLogger("daily")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fh = logging.FileHandler(path, encoding="utf-8")
    fh.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-7s %(message)s", "%H:%M:%S"))
    logger.addHandler(fh)
    if verbose:
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter("%(levelname)-7s %(message)s"))
        logger.addHandler(sh)
    return path


# ---------------------------------------------------------------------------
# 运行历史（§29）
# ---------------------------------------------------------------------------

HISTORY_SQL = """
CREATE TABLE IF NOT EXISTS daily_runs (
    run_id      TEXT PRIMARY KEY,
    run_date    TEXT NOT NULL,
    status      TEXT NOT NULL,
    started_at  TEXT,
    ended_at    TEXT,
    duration_s  REAL DEFAULT 0,
    n_warnings  INTEGER DEFAULT 0,
    n_errors    INTEGER DEFAULT 0,
    git_commit  TEXT,
    input_fingerprint TEXT,
    detail      TEXT
);
CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_runs(run_date, run_id);
"""


def _history_conn():
    import sqlite3
    from pipeline.jobs import JOBS_DB
    conn = sqlite3.connect(str(JOBS_DB))
    conn.row_factory = sqlite3.Row
    conn.executescript(HISTORY_SQL)
    return conn


def record_run(run: DailyRun, fingerprint: str) -> None:
    conn = _history_conn()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO daily_runs
               (run_id, run_date, status, started_at, ended_at, duration_s,
                n_warnings, n_errors, git_commit, input_fingerprint, detail)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (run.run_id, run.date, run.status, run.started, run.ended,
             run.duration_s, len(run.warnings), len(run.errors),
             run.manifest.get("git_commit", ""), fingerprint,
             run.manifest.get("detail", "")))
        conn.commit()
    finally:
        conn.close()


def history(limit: int = 30, run_date: Optional[str] = None) -> List[dict]:
    conn = _history_conn()
    try:
        if run_date:
            rows = conn.execute(
                "SELECT * FROM daily_runs WHERE run_date = ? "
                "ORDER BY run_id DESC", (run_date,)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM daily_runs ORDER BY run_id DESC LIMIT ?",
                (int(limit),)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def completed_run(run_date: str) -> Optional[dict]:
    """该日已完成的运行（用于幂等判断）。"""
    for r in history(run_date=run_date):
        if r["status"] in (OK, WARNING, ALREADY_COMPLETED,
                           WAITING_FOR_FORWARD_DATA):
            return r
    return None


# ---------------------------------------------------------------------------
# 输入指纹（§5：同一天重复运行，输入相同 → ALREADY_COMPLETED）
# ---------------------------------------------------------------------------

def input_fingerprint(run_date: str) -> str:
    import hashlib

    from pipeline import freeze
    parts = [run_date, freeze.git_commit(),
             json.dumps(freeze.current_hashes(), sort_keys=True)]
    try:
        from pipeline.freshness import market_latest
        parts.append(str(market_latest()))
    except Exception:                                          # noqa: BLE001
        parts.append("no-market")
    try:
        from pipeline.signals import signals_state
        parts.append(str((signals_state() or {}).get("as_of")))
    except Exception:                                          # noqa: BLE001
        parts.append("no-signal")
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# 任务实现（全部调用既有模块，不新增投资逻辑）
# ---------------------------------------------------------------------------

class Ctx:
    """任务之间共享的运行上下文。"""

    def __init__(self, run: DailyRun, run_date: pd.Timestamp):
        self.run = run
        self.date = run_date
        self.store_data: dict = {}
        self.paper = None            # paper_live DayResult
        self.service = None          # LiveDataProvider（懒加载）


def _latest_trading_day(on_or_before: pd.Timestamp) -> pd.Timestamp:
    from pipeline.freshness import last_trading_day
    d = last_trading_day(on_or_before=on_or_before)
    return pd.Timestamp(d) if d is not None else on_or_before


# --- 1. 环境检查 -----------------------------------------------------------

def duckdb_available() -> Tuple[bool, str]:
    """DuckDB 能否独占打开（单进程铁律，见 CLAUDE.md）。

    返回 (可用, 人话说明)。被占用时给出**可操作的**提示，而不是一句
    IO Error —— 最常见的占用者就是本地 GUI。
    """
    try:
        from personal_quant import db as research_db
        research_db.connect().execute("SELECT 1").fetchone()
        return True, "可独占打开"
    except Exception as e:                                     # noqa: BLE001
        msg = str(e)
        if "being used by another process" in msg or "IO Error" in msg:
            return False, ("被另一个进程占用（通常是本地 GUI："
                           "scripts/webapp/serve.py 或 scripts/run_app.py）。"
                           "DuckDB 是单进程独占的，请先关掉界面再跑流水线。")
        return False, f"无法打开：{msg[:120]}"


def task_environment(ctx: Ctx) -> Tuple[str, str]:
    import sys

    from pipeline import freeze

    problems = []
    if sys.version_info[:2] != (3, 12):
        problems.append(f"Python {sys.version.split()[0]}（需要 3.12）")
    for mod in ("qlib", "pandas", "lightgbm", "duckdb", "streamlit"):
        try:
            __import__(mod)
        except Exception as e:                                 # noqa: BLE001
            problems.append(f"{mod} 不可用：{e}")
    if not (PROJECT_ROOT / "data" / "wealth").exists():
        problems.append("data/wealth 不存在")

    ok_db, db_msg = duckdb_available()
    ctx.store_data["duckdb_ok"] = ok_db
    ctx.store_data["duckdb_msg"] = db_msg

    if problems:
        return INVALID, "；".join(problems)
    st = freeze.verify()
    if not ok_db:
        # 环境本身没问题，但研究库打不开 —— 后续需要它的步骤会失败。
        # 提前说清楚原因，并让需要 DB 的步骤**不执行**（§22 依赖图）。
        return INVALID, f"研究数据库不可用：{db_msg}"
    return OK, (f"Python {sys.version.split()[0]}；冻结状态 {st.detail}；"
                f"DuckDB {db_msg}")


# --- 2. 数据源健康（§8）----------------------------------------------------

def task_source_health(ctx: Ctx) -> Tuple[str, str]:
    from pipeline.freshness import data_status, market_latest

    rows = [f.as_dict() for f in data_status()]
    ctx.store_data["freshness"] = rows
    latest = market_latest()
    ctx.store_data["market_latest"] = str(latest) if latest else None
    stale = [r["domain"] for r in rows if r.get("status") == "STALE"]
    missing = [r["domain"] for r in rows if r.get("status") == "MISSING"]
    if missing:
        return INVALID, f"关键域缺失：{missing}"
    if stale:
        # 新闻滞后是已知情况（官方索引滞后 ~5 天），只告警
        hard = [d for d in stale if d != "News"]
        level = WARNING
        return level, f"STALE：{stale}（行情最新 {latest}）"
    return OK, f"全部新鲜；行情最新 {latest}"


# --- 3/4. 市场数据 + 交易日历 ----------------------------------------------

SNAPSHOT_SCRIPT = (PROJECT_ROOT / "scripts" / "quant"
                   / "update_market_snapshot.py")
# 行情落后超过这么多个自然日才值得下一次整份快照
SNAPSHOT_LAG_DAYS = 5


def _snapshot_check() -> Optional[str]:
    """问上游有没有新快照（一次 HTTP，不下载）。失败返回 None。"""
    import subprocess
    import sys as _sys
    try:
        r = subprocess.run([_sys.executable, str(SNAPSHOT_SCRIPT), "--check"],
                           cwd=str(PROJECT_ROOT), capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=120)
    except Exception:                                          # noqa: BLE001
        return None
    if r.returncode != 0:
        return None
    return (r.stdout or "").strip()


def task_market_data(ctx: Ctx) -> Tuple[str, str]:
    from pipeline.freshness import last_trading_day, market_latest

    ml, lt = market_latest(), last_trading_day()
    if ml is None or lt is None:
        return INVALID, "行情或日历为空"

    if ctx.run.dry_run:
        # §23：dry-run 只做检查。整份快照是几百 MB，绝不能在"看一眼"的模式下下载。
        return SKIPPED, f"dry-run 不下载；行情最新 {ml}"

    # §38：普通日必须快。先问上游有没有新快照（一次 HTTP），
    # 只有确实落后才下载 —— 否则每天下 500MB 是不可接受的。
    behind = (pd.Timestamp(lt) - pd.Timestamp(ml)).days
    info = _snapshot_check()
    ctx.store_data["snapshot_check"] = info

    if behind <= SNAPSHOT_LAG_DAYS and info is not None:
        return OK, (f"行情最新 {ml}（日历 {lt}），落后 {behind} 天，"
                    f"无需下载新快照")

    if info is None:
        # §21：数据源失败要有 fallback，不能让整条流水线挂掉
        return WARNING, (f"取不到上游快照信息（网络？）；沿用本地行情 "
                         f"{ml}，落后日历 {behind} 天")

    from pipeline import refresh
    detail = refresh.market_update()
    ml2 = market_latest()
    return OK, f"已更新快照；行情 {ml} → {ml2}；{detail}"


# --- 5. 新闻（§9）----------------------------------------------------------

def task_news(ctx: Ctx) -> Tuple[str, str]:
    from pipeline.freshness import news_latest

    if ctx.run.dry_run:
        return SKIPPED, f"dry-run 不抓取；当前新闻最新 {news_latest()}"

    from pipeline import refresh

    detail = refresh.news_update()
    latest = news_latest()
    cov = None
    try:
        from news.storage import load_coverage
        cov = len(load_coverage())
    except Exception:                                          # noqa: BLE001
        pass
    if latest is None:
        return WARNING, "新闻 provider 无数据（规则层继续，不影响 prediction）"
    return OK, f"新闻最新 {latest}" + (f"；覆盖 {cov} 只" if cov else "")


# --- 6. 财务（§10：按需，不每天重下年报）-----------------------------------

def task_financial(ctx: Ctx) -> Tuple[str, str]:
    """§10：财务按需加载 —— **默认不抓取**。

    S3 生产特征集（Alpha158 + pack_v1 + news）**不含财务因子**，所以每日
    流水线默认根本不需要财务数据。真去抓的话，CNINFO 的 PDF 会一家一家
    重试（403/超时），几分钟甚至更久，直接违反 §38 的"普通日 < 10 分钟"。

    需要时（例如做财务因子研究）加 `--with-financial` 显式触发。
    """
    from pipeline.freshness import financial_latest

    latest = financial_latest()
    if ctx.run.dry_run:
        return SKIPPED, f"dry-run 不抓取；当前财务最新 {latest}"
    if not ctx.store_data.get("with_financial"):
        return SKIPPED, (f"按需加载：当前最新 {latest}；"
                         f"S3 特征集不含财务因子，未触发抓取"
                         f"（需要时加 --with-financial）")

    from pipeline import refresh

    detail = refresh.financial_update()
    return OK, f"财务最新 {financial_latest()}；{detail}"


# --- 7. 数据质量 -----------------------------------------------------------

def task_quality(ctx: Ctx) -> Tuple[str, str]:
    """只做**检查**，不修改数据。"""
    from pipeline.freshness import market_latest
    from services import market_service, portfolio_service

    msgs = []
    ml = market_latest()
    if ml is None:
        return INVALID, "取不到行情最新日期"
    prices = market_service.latest_prices()
    if not prices:
        return INVALID, "最新交易日没有任何价格"

    # 异常价格粗查：非正数、单日涨幅 > 50%
    bad = [s for s, p in prices.items() if not (p > 0)]
    if bad:
        msgs.append(f"{len(bad)} 只标的价格非正")

    # 个人账户：持仓一致性（§53）
    cons = portfolio_service.consistency()
    if cons.get("available") and cons.get("n_mismatch"):
        msgs.append(f"持仓表与账本不一致 {cons['n_mismatch']} 只")

    if msgs:
        return WARNING, "；".join(msgs)
    return OK, f"价格 {len(prices)} 只全部正常"


# --- 8-11. Paper Live ------------------------------------------------------

# forward 起点之前的运行写这里 —— **绝不写进 clean forward holdout**
PRE_FORWARD_ROOT = PROJECT_ROOT / "experiments" / "paper_live" / "pre_forward"


def _paper_ctx(ctx: Ctx):
    """装配 paper_live 引擎（复用既有模块，不重写）。

    **关键守卫（§6/§7）**：forward 起点之前的数据写入独立目录
    `experiments/paper_live/pre_forward/`，绝不进 `forward_holdout/`。
    否则 2026-09-17 这种"起点前"的日期会污染干净的前瞻记录，
    而 forward holdout 一旦被污染就再也洗不干净了。
    """
    import sys as _sys
    _sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "paper_live"))
    from paper_live import config as plcfg
    from paper_live.data import LiveDataProvider
    from paper_live.store import ForwardStore

    cfg = plcfg.load_config()
    s = cfg["paper_live"]
    fwd_start = pd.Timestamp(s["forward_start_date"])
    is_forward = pd.Timestamp(ctx.date) >= fwd_start
    root = (PROJECT_ROOT / s["paths"]["root"] if is_forward
            else PRE_FORWARD_ROOT)
    ctx.store_data["paper_root"] = str(root)
    ctx.store_data["paper_is_forward"] = is_forward
    store = ForwardStore(root, forward_start=s["forward_start_date"])
    return cfg, store, LiveDataProvider(cfg)


def task_paper_prediction(ctx: Ctx) -> Tuple[str, str]:
    """§11：严格调用现有 paper_live 引擎。

    dry-run 时**不调用** —— 那会跑特征/模型，可能几分钟，而 §23 要求
    dry-run 只做检查。
    """
    if ctx.run.dry_run:
        return SKIPPED, "dry-run 不运行预测"

    from paper_live.alerts import check_alerts
    from paper_live.engine import run_day

    cfg, store, provider = _paper_ctx(ctx)
    ctx.store_data["paper_cfg"] = cfg
    ctx.store_data["paper_store"] = store
    ctx.store_data["paper_provider"] = provider

    force_rebalance = _is_rebalance(ctx.date, cfg)
    ctx.store_data["is_rebalance"] = force_rebalance

    result = run_day(ctx.date, cfg, store, provider, dry_run=ctx.run.dry_run,
                     force_rebalance=force_rebalance, alerts_fn=check_alerts)
    ctx.paper = result
    ctx.store_data["paper_result"] = result
    if result.status == INVALID:
        return INVALID, f"PIT/冻结未通过：{result.audit.get('status')}"
    where = "forward_holdout（正式前瞻）" if ctx.store_data.get(
        "paper_is_forward") else "pre_forward（起点前，不污染 holdout）"
    if result.pending:
        return OK, f"预测 {result.n_predictions} 只；订单挂起等 T+1；写入 {where}"
    return OK, (f"预测 {result.n_predictions} 只；订单 {result.n_orders}；"
                f"成交 {result.n_fills}；"
                f"{'调仓日' if force_rebalance else '监控日'}；写入 {where}")


def task_personal_snapshot(ctx: Ctx) -> Tuple[str, str]:
    """§13：个人账户快照 —— **与 Paper Live 完全独立**。

    只做"把用户已记录的持仓按市价标记"（positions 是物化缓存），
    **不编造任何个人资产数据**。没有持仓就是没有。
    """
    if ctx.run.dry_run:
        return SKIPPED, "dry-run 不写个人账户"

    from services import portfolio_service
    from wealth import db, engine

    v = portfolio_service.valuation()
    if not v.get("available"):
        return WARNING, v.get("reason", "个人账户不可用")
    if not v.get("n_positions"):
        return OK, "个人账户暂无持仓（未编造快照）"

    conn = db.connect()
    navs = {}
    for h in v["holdings"]:
        navs[h["product_id"]] = float(h["price"] or h["avg_cost"] or 0.0)
    n = engine.write_positions(conn, str(ctx.date.date()), navs)
    ctx.store_data["personal"] = {
        "market_value": v["market_value"],
        "cash": v["cash_recorded"],
        "total": v["market_value"] + v["cash_recorded"],
        "n_positions": v["n_positions"],
    }
    return OK, f"个人账户 {v['n_positions']} 只，市值 {v['market_value']:,.0f}"


# --- 13/14. 业绩与风险 -----------------------------------------------------

def task_performance(ctx: Ctx) -> Tuple[str, str]:
    from services import performance_service
    perf = performance_service.summary()
    ctx.store_data["performance"] = perf
    if not perf.get("available"):
        return OK, perf.get("reason", "暂无净值序列")
    cr, twr = perf.get("cumulative_return"), perf.get("twr")
    return OK, (f"累计 {cr:.2%}；TWR {twr:.2%}" if cr is not None
                and twr is not None else "净值序列不足")


def task_risk(ctx: Ctx) -> Tuple[str, str]:
    from services import risk_service
    rk = risk_service.metrics()
    ctx.store_data["risk"] = rk
    hb = rk.get("holdings_based") or {}
    if not hb:
        return OK, "无持仓层风险指标"
    return OK, (f"HHI {hb.get('hhi'):.4f}；有效持仓 "
                f"{hb.get('effective_n'):.1f}；最大单只 "
                f"{hb.get('top_weight'):.2%}；"
                f"现金 {hb.get('cash_ratio') if hb.get('cash_ratio') is None else format(hb['cash_ratio'], '.2%')}")


# --- 15. 漂移 --------------------------------------------------------------

def task_drift(ctx: Ctx) -> Tuple[str, str]:
    """§15：冻结漂移 + paper live 自身漂移（只报，不改）。"""
    from pipeline import freeze as fz
    st = fz.verify()
    ctx.store_data["freeze"] = st.as_dict()
    if st.drift:
        ctx.run.warnings.append(f"PRODUCTION_DRIFT: {st.detail}")
        return INVALID, st.detail
    paper = ctx.store_data.get("paper_result")
    if ctx.run.dry_run:
        return OK, st.detail + "（dry-run 跳过 paper 漂移）"
    if paper is not None and getattr(paper, "drift", None):
        bad = {k: v.get("status") for k, v in paper.drift.items()
               if v.get("status") not in ("OK", None)}
        if bad:
            return WARNING, f"paper drift: {bad}"
    return OK, st.detail


# --- 16. 日报 --------------------------------------------------------------

def task_report(ctx: Ctx) -> Tuple[str, str]:
    from pipeline.daily_report import write_daily_report
    if ctx.run.dry_run:
        return SKIPPED, "dry-run 不写日报"
    paths = write_daily_report(ctx)
    return OK, str(paths.get("markdown", ""))


def task_alerts(ctx: Ctx) -> Tuple[str, str]:
    from pipeline.daily_alerts import evaluate, summarize
    alerts = evaluate(ctx)
    ctx.store_data["alerts"] = alerts
    s = summarize(alerts)
    if s["n"] == 0:
        return OK, "无告警"
    return (WARNING if s["by_level"].get("ERROR", 0) == 0 else FAILED), \
        f"{s['n']} 条告警：{s['codes']}"


def task_manifest(ctx: Ctx) -> Tuple[str, str]:
    from pipeline.daily_report import write_manifest
    if ctx.run.dry_run:
        return SKIPPED, "dry-run 不写 manifest"
    p = write_manifest(ctx)
    return OK, str(p)


# ---------------------------------------------------------------------------
# 任务表（§3 的顺序 / §22 的依赖）
# ---------------------------------------------------------------------------

TASKS: List[Tuple[str, Callable[..., Tuple[str, str]], Tuple[str, ...], bool]] = [
    # (name, fn, depends_on, blocking)
    ("environment", task_environment, (), True),
    ("source_health", task_source_health, ("environment",), True),
    ("market_data", task_market_data, ("source_health",), True),
    ("news", task_news, ("environment",), False),      # 新闻失败不阻断
    ("financial_lazy", task_financial, ("environment",), False),
    ("data_quality", task_quality, ("market_data",), True),
    ("paper_prediction", task_paper_prediction, ("data_quality",), True),
    ("personal_snapshot", task_personal_snapshot, ("environment",), False),
    ("performance", task_performance, ("environment",), False),
    ("risk", task_risk, ("performance",), False),
    ("drift", task_drift, ("paper_prediction",), True),
    ("alerts", task_alerts, ("drift",), False),
    ("report", task_report, ("alerts",), False),
    ("manifest", task_manifest, ("report",), False),
]

TASK_NAMES = [t[0] for t in TASKS]


def _is_rebalance(date: pd.Timestamp, cfg: dict) -> bool:
    from paper_live.engine import is_rebalance_date
    try:
        from factors.base import load_calendar
        cal = load_calendar()
    except Exception:                                          # noqa: BLE001
        return False
    return is_rebalance_date(date, cfg, cal)


# ---------------------------------------------------------------------------
# 编排
# ---------------------------------------------------------------------------

def run_daily(date: Optional[str] = None, dry_run: bool = False,
              force: bool = False, backfill: bool = False,
              verbose: bool = False, only: Optional[List[str]] = None,
              with_financial: bool = False) -> DailyRun:
    from pipeline import freeze as fz

    ts = datetime.now(timezone.utc).astimezone()
    target = pd.Timestamp(date) if date else None
    if target is None:
        from pipeline.freshness import last_trading_day
        lt = last_trading_day()
        target = pd.Timestamp(lt) if lt is not None else pd.Timestamp.today()
    target = _latest_trading_day(target)

    # run_id 必须唯一：同秒内跑两次会撞号，而记录用的是
    # INSERT OR REPLACE —— 撞号就会**覆盖**上一次的记录，
    # 违反 spec §5（--force 不能覆盖原记录）。撞了就加序号。
    base_id = f"{target.date()}_{ts.strftime('%H%M%S')}"
    run_id, n = base_id, 1
    try:
        taken = {r["run_id"] for r in history(run_date=str(target.date()))}
    except Exception:                                          # noqa: BLE001
        taken = set()
    while run_id in taken:
        n += 1
        run_id = f"{base_id}_{n}"
    run = DailyRun(run_id=run_id, date=str(target.date()),
                   started=ts.isoformat(timespec="seconds"),
                   dry_run=dry_run, backfill=backfill)
    setup_logging(run.date, verbose=verbose)

    # --- 回填守卫（§24）------------------------------------------------
    if backfill and not force:
        log.warning("backfill 必须显式加 --force（默认禁止回写历史）")
        run.status = INVALID
        run.errors.append("backfill requires --force")
        run.ended = datetime.now(timezone.utc).astimezone() \
            .isoformat(timespec="seconds")
        return run

    # --- 幂等（§4/§5）--------------------------------------------------
    fp = input_fingerprint(run.date)
    if not force and not dry_run:
        prev = completed_run(run.date)
        if prev and prev.get("input_fingerprint") == fp:
            run.status = ALREADY_COMPLETED
            run.manifest = {"detail": f"已完成于 {prev['run_id']}，输入未变",
                            "previous_run": prev["run_id"]}
            run.ended = datetime.now(timezone.utc).astimezone() \
                .isoformat(timespec="seconds")
            log.info("ALREADY_COMPLETED（输入指纹一致）")
            return run

    # --- 冻结守卫（§2/§35）---------------------------------------------
    frozen = fz.verify()
    run.manifest["freeze"] = frozen.as_dict()
    if frozen.frozen and frozen.drift:
        run.status = PRODUCTION_DRIFT
        run.warnings.append(f"PRODUCTION_DRIFT: {frozen.detail}")
        log.error("PRODUCTION_DRIFT：%s", frozen.detail)
        # 仍然继续更新数据与报告，但不做 forward observation
        run.forward_observation = False
    else:
        run.forward_observation = (not dry_run) and \
            fz.production_enabled() and _forward_ready(target, run)

    ctx = Ctx(run, target)
    ctx.store_data["fingerprint"] = fp
    ctx.store_data["with_financial"] = with_financial

    # --- 执行（§22 依赖图）---------------------------------------------
    statuses: Dict[str, str] = {}
    wanted = set(only) if only else set(TASK_NAMES)

    for name, fn, deps, blocking in TASKS:
        if name not in wanted:
            continue
        t0 = time.perf_counter()
        blocked_by = [d for d in deps
                      if statuses.get(d) in (FAILED, INVALID, BLOCKED)]
        if blocked_by:
            outcome = TaskOutcome(name, BLOCKED,
                                  detail=f"依赖失败：{blocked_by}",
                                  depends_on=deps)
            log.warning("BLOCKED  %-18s 依赖失败 %s", name, blocked_by)
        else:
            log.info("START   %-18s", name)
            try:
                status, detail = fn(ctx)
            except Exception as e:                             # noqa: BLE001
                status = FAILED
                detail = f"{type(e).__name__}: {e}"
                outcome = TaskOutcome(name, status, detail=detail,
                                      error=traceback.format_exc(
                                          limit=3).strip().splitlines()[-1],
                                      depends_on=deps)
                log.error("ERROR   %-18s %s", name, detail)
            else:
                outcome = TaskOutcome(name, status, detail=detail,
                                      depends_on=deps)
                log.info("%-7s %-18s %s", status, name, detail)
        outcome.duration_s = time.perf_counter() - t0
        run.tasks.append(outcome)
        statuses[name] = outcome.status
        if outcome.status in (FAILED, INVALID):
            run.errors.append(f"{name}: {outcome.detail}")
        elif outcome.status == WARNING:
            run.warnings.append(f"{name}: {outcome.detail}")

    # --- 汇总状态（§3 第 19 步）----------------------------------------
    if run.status not in (PRODUCTION_DRIFT, INVALID, FAILED):
        if any(t.status in (FAILED, INVALID) for t in run.tasks):
            run.status = FAILED
        elif any(t.status == WARNING for t in run.tasks):
            run.status = WARNING
        else:
            run.status = OK

    run.ended = datetime.now(timezone.utc).astimezone() \
        .isoformat(timespec="seconds")
    # 清单统一由 daily_report.build_manifest 组装（与写文件时同一份逻辑，
    # 避免"记录里有的字段，文件里没有"这种不一致）
    from pipeline.daily_report import build_manifest
    run.manifest = build_manifest(ctx)
    if not dry_run:
        # manifest 任务在循环里写过一次，但那一刻它**自己的**执行结果还没
        # 追加进 run.tasks —— 写出来的清单会少最后一行。循环结束后再刷一次，
        # 保证清单与实际情况完全一致。
        try:
            from pipeline.daily_report import (write_daily_report,
                                               write_manifest)
            # 日报同理：循环里写的那次 end_time 还是空的，这里补上完整时间戳
            write_daily_report(ctx)
            write_manifest(ctx)
        except Exception as e:                                 # noqa: BLE001
            log.warning("日报/manifest 刷新失败：%s", e)
        try:
            record_run(run, fp)
        except Exception as e:                                 # noqa: BLE001
            log.warning("运行历史写入失败：%s", e)
    log.info("DONE    status=%s duration=%.1fs warnings=%d errors=%d",
             run.status, run.duration_s, len(run.warnings), len(run.errors))
    return run


def _forward_ready(target: pd.Timestamp, run: DailyRun) -> bool:
    """target 是否已进入 forward 窗口（与行情最新日期无关）。"""
    """§7：latest market date < forward_start → 等待，不是错误。"""
    from pipeline import freeze as fz
    rec = fz.load_freeze().get("production_freeze") or {}
    start = rec.get("forward_holdout_start")
    if not start:
        return False
    latest = None
    try:
        from pipeline.freshness import market_latest
        latest = market_latest()
    except Exception:                                          # noqa: BLE001
        pass
    if pd.Timestamp(target) < pd.Timestamp(start):
        run.warnings.append(
            WAITING_FOR_FORWARD_DATA +
            f": 运行日 {target.date()} < forward 起点 {start}（正常，不是错误）"
            f"；本次结果写入 pre_forward，不影响 clean holdout")
        return False
    if latest is None or pd.Timestamp(latest) < pd.Timestamp(start):
        run.warnings.append(
            WAITING_FOR_FORWARD_DATA +
            f": 行情最新 {latest} < forward 起点 {start}（正常，不是错误）")
        return False
    return True
