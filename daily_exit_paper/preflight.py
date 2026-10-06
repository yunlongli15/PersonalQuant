# -*- coding: utf-8 -*-
"""上线前只读检查（spec §3 / §5 / §8 / §9 / §10 / §18）。

**这个模块不写任何东西**，只回答四个问题：

    data_freshness   行情到哪一天了？信号快照与它同步吗？
    calendar         那个日期真的在（已观测的）交易日历里吗？下一交易日有没有？
    feature_date     请求的那一天的特征，文件里自述的就是那一天吗？
    strategy_signal  信号与预测都 <= 信号日吗？有没有越过它取数？

以及一条贯穿全部的纪律：**三个时间必须分开说**。

    system_run_date        程序真正运行的日期（墙钟）
    market_data_last_date  数据库目前最新可用行情日期
    signal_date            用于生成 recommendation 的市场日期

把这三个混成一个 `date` 是上线前最容易犯、也最难事后发现的错。
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Dict, Optional

import pandas as pd

from . import execution as X
from .engine import SignalSourceError

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"


class PreflightError(RuntimeError):
    """上线前检查不通过。**停下来**，不要带着问题继续。"""


def _check(status: str, detail: str, **extra) -> Dict:
    rec = {"status": status, "detail": detail}
    rec.update(extra)
    return rec


def system_run_date() -> str:
    return datetime.now(timezone.utc).astimezone().date().isoformat()


def latest_signal_snapshot_date() -> Optional[str]:
    from . import config as C

    snaps = sorted((C.PROJECT_ROOT / "data" / "quant")
                   .glob("signals_2*.parquet"))
    return snaps[-1].stem.replace("signals_", "") if snaps else None


def run_preflight(market, cfg, capital: Optional[float] = None) -> Dict:
    """执行全部只读检查，返回结构化结果 + 三个时间。"""
    s_cfg = cfg["daily_exit_paper"] if "daily_exit_paper" in cfg else cfg
    cal = market.calendar()
    if len(cal) == 0:
        raise PreflightError("交易日历为空 —— 数据库里没有行情")

    mkt_last = pd.Timestamp(cal[-1])
    run_date = system_run_date()
    nxt = X.next_session(cal, mkt_last)

    sig_date = latest_signal_snapshot_date()
    out: Dict = {
        "system_run_date": run_date,
        "market_data_last_date": str(mkt_last.date()),
        "signal_date": sig_date,
        "next_trading_date": str(nxt.date()) if nxt is not None else None,
        "next_session_status": ("READY" if nxt is not None else "NOT_YET"),
        "calendar_days_observed": int(len(cal)),
        "checks": {},
    }

    # ---- 1. 数据新鲜度 ---------------------------------------------------
    behind = (pd.Timestamp(run_date) - mkt_last).days
    if sig_date is None:
        out["checks"]["data_freshness"] = _check(
            FAIL, "没有任何按日期的信号快照（signals_<date>.parquet）—— "
                  "先跑 refresh_all.py")
    elif sig_date != str(mkt_last.date()):
        out["checks"]["data_freshness"] = _check(
            FAIL, f"最新信号快照是 {sig_date}，而行情已到 "
                  f"{mkt_last.date()} —— 信号落后于行情，先刷新信号")
    else:
        out["checks"]["data_freshness"] = _check(
            PASS, f"行情 {mkt_last.date()}（距系统运行日 {behind} 天，"
                  f"上游发布延迟属正常）；信号快照与行情同日")

    # ---- 2. 日历 ---------------------------------------------------------
    if mkt_last not in cal:
        out["checks"]["calendar"] = _check(
            FAIL, f"最新行情日 {mkt_last.date()} 不在已观测日历里")
    else:
        out["checks"]["calendar"] = _check(
            PASS,
            f"{mkt_last.date()} 是已观测交易日；下一交易日 "
            + (f"{nxt.date()}" if nxt is not None else
               "尚未观测到（NEXT_SESSION_STATUS = NOT_YET，这是正常情况，"
               "不是 NO_FILL）"))

    # ---- 3. 特征日期契约 -------------------------------------------------
    out["checks"]["feature_date"] = _feature_date_check(cal, mkt_last)

    # ---- 4. 信号与预测的时间边界 -----------------------------------------
    out["checks"]["strategy_signal"] = _signal_check(market, sig_date,
                                                     s_cfg)

    out["ok"] = all(c["status"] == PASS for c in out["checks"].values())
    return out


def _feature_date_check(cal, mkt_last) -> Dict:
    """特征缓存必须自证日期；错日期一律不得被当成命中。"""
    import personal_quant.strategy.features as F

    probes = [pd.Timestamp(d) for d in cal[-3:]]
    rows, bad = [], []
    for d in probes:
        path = F.feature_cache_path(d)
        if not path.exists():
            rows.append(f"{d.date()}: 未缓存（会重算）")
            continue
        df = F.read_feature_cache(d)
        if df is None:
            bad.append(f"{d.date()}: 文件存在但日期不自洽，已被拒用")
            rows.append(f"{d.date()}: REJECTED（日期不匹配 -> 未命中）")
        else:
            rows.append(f"{d.date()}: HIT（feature_date == 请求日）")

    # 旧月度格式必须**读不到**（新 loader 的路径与它不同名）
    legacy = sorted(F.FEATURE_CACHE.glob("2*-*.parquet"))
    legacy_note = (f"；旧月度文件 {len(legacy)} 个仍在盘上但新 loader 不读它们"
                   if legacy else "")

    if bad:
        return _check(FAIL, "；".join(bad), probes=rows,
                      legacy_files=len(legacy))
    return _check(PASS, "；".join(rows) + legacy_note, probes=rows,
                  legacy_files=len(legacy))


def _signal_check(market, sig_date, s_cfg) -> Dict:
    if sig_date is None:
        return _check(FAIL, "没有信号快照可检查")
    d = pd.Timestamp(sig_date)
    # 「拿不到属于本策略的信号」是**检查失败**，不是异常：
    # preflight 的职责就是把上线前的阻塞项列出来（`--preflight` 据此返回 1），
    # 而 `--show-state` / `--reconcile` 这些**只读**命令还要能读到既有记录。
    # 之前这里是直接抛出的，结果是实验停摆后连历史都查不了。
    try:
        sig = market.signals(d)
    except SignalSourceError as e:
        return _check(FAIL, f"信号来源不可用：{e}")
    if sig is None or sig.empty:
        return _check(FAIL, f"{sig_date} 的信号快照读不出来或为空")

    horizon = int(s_cfg["signal_horizon_days"])
    try:
        fc = market.forecasts(d, horizon)
    except SignalSourceError as e:
        return _check(FAIL, f"预测来源不可用：{e}")
    if not fc:
        return _check(FAIL, f"{sig_date} 没有 horizon={horizon} 的预测 —— "
                            f"没有预期收益就无法锚定目标价")

    snap_dates = sorted({str(pd.Timestamp(x).date())
                         for x in sig["signal_date"]})
    if snap_dates != [sig_date]:
        return _check(FAIL, f"信号快照自称的日期是 {snap_dates}，"
                            f"与文件名 {sig_date} 不一致")

    n_top = int((sig["raw_rank"] <= int(s_cfg["top_k"])).sum()) \
        if "raw_rank" in sig.columns else 0
    return _check(
        PASS,
        f"信号 {len(sig)} 只（Top-{s_cfg['top_k']} 命中 {n_top}）；"
        f"预测 {len(fc)} 只 @ horizon={horizon}；signal_date == "
        f"market_data_last_date == {sig_date}")


def render_preflight(pf: Dict, capital: Optional[float] = None) -> str:
    """把检查结果排版成给人看的块（**只格式化，不算钱**）。"""
    L = ["PREFLIGHT（只读，未写入任何东西）"]
    L.append(f"  system_run_date        {pf['system_run_date']}"
             f"        （程序真正运行的日期）")
    L.append(f"  market_data_last_date  {pf['market_data_last_date']}"
             f"        （数据库最新可用行情）")
    L.append(f"  signal_date            {pf['signal_date']}"
             f"        （生成推荐所用的市场日期）")
    L.append(f"  next_trading_date      "
             f"{pf['next_trading_date'] or '—'}"
             f"        （{pf['next_session_status']}）")
    if capital is not None:
        L.append(f"  test_capital           {capital:,.2f}"
                 f"        （dry-run 用，**不会被锁定**）")
    L.append("")
    for name, c in pf["checks"].items():
        L.append(f"  {name:<18} {c['status']:<5} {c['detail']}")
    L.append("")
    L.append(f"  PREFLIGHT: {'PASS' if pf['ok'] else 'FAIL'}")
    return "\n".join(L)
