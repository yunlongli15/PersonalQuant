# -*- coding: utf-8 -*-
"""系统健康（spec §66 / §67）。

每一项都给出 PASS / WARNING / FAIL **加一句人话**；任何异常都被转成
一句可读的说明，绝不把 Traceback 丢给用户当首页内容。
"""

from __future__ import annotations

import sys

from ._common import PROJECT_ROOT, read_json, safe


def _probe(name: str, fn) -> dict:
    try:
        status, detail = fn()
    except Exception as e:                                     # noqa: BLE001
        status, detail = "FAIL", f"{type(e).__name__}: {e}"
    return {"name": name, "status": status, "detail": detail}


@safe(label="系统健康")
def check() -> dict:
    import os
    import platform

    from . import market_service

    items = []

    def _py():
        return "PASS", f"{sys.version.split()[0]} ({platform.system()})"

    def _qlib():
        import qlib
        return "PASS", str(getattr(qlib, "__version__", "installed"))

    def _db():
        from personal_quant import db
        r = db.connect().execute("SELECT COUNT(*) AS n FROM daily_bars"
                                 ).fetch_df()
        return "PASS", f"daily_bars {int(r['n'].iloc[0]):,} 行"

    def _market():
        d = market_service.price_date()
        if not d:
            return "FAIL", "取不到行情日期"
        stale = market_service.data_status()
        return ("WARNING" if stale.get("any_stale") else "PASS"), f"最新 {d}"

    def _news():
        from pipeline.freshness import news_latest
        d = news_latest()
        return ("PASS" if d else "WARNING"), f"最新 {d or '无数据'}"

    def _paper():
        from paper_live.config import verify_freeze
        fr = verify_freeze()
        if not fr.get("is_frozen"):
            return "WARNING", "尚未冻结"
        if fr.get("drift"):
            return "FAIL", f"冻结不一致：{fr.get('mismatches')}"
        return "PASS", "已冻结且一致"

    def _model():
        from paper_live.config import load_config, sha256_file
        s = load_config()["paper_live"]
        h = sha256_file(s["alpha"]["model"])
        if h == "MISSING":
            return "FAIL", f"模型文件缺失：{s['alpha']['model']}"
        return "PASS", f"{s['alpha']['model']} ({h[:12]}…)"

    def _wealth():
        from wealth import db
        n = len(db.table_names(db.connect()))
        return "PASS", f"{n} objects"

    def _fh():
        from paper_live.config import load_config
        s = load_config()["paper_live"]
        root = PROJECT_ROOT / s["paths"]["root"]
        if not root.exists():
            return "WARNING", "目录尚未创建"
        n = len(list((root / "observations").glob("*.json")))
        return "PASS", f"{n} 期观测（起点 {s['forward_start_date']}）"

    def _last():
        st = read_json(PROJECT_ROOT / "data" / "quant" / "signals_state.json")
        if not st:
            return "WARNING", "还没有信号快照"
        return "PASS", f"信号 {st.get('as_of')} @ {st.get('computed_at')}"

    def _git():
        import subprocess
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True,
                           cwd=str(PROJECT_ROOT), timeout=10)
        if r.returncode != 0:
            return "WARNING", "不是 git 仓库"
        return "PASS", r.stdout.strip()

    def _env():
        has = bool(os.environ.get("DEEPSEEK_API_KEY", "").strip())
        return "PASS", ("DEEPSEEK_API_KEY 已设置（不显示内容）" if has
                        else "未配置（LLM 层关闭，按规则模式运行）")

    for name, fn in (("Python", _py), ("Qlib", _qlib), ("Database", _db),
                     ("Market data", _market), ("News provider", _news),
                     ("Paper live", _paper), ("Model", _model),
                     ("Wealth DB", _wealth), ("Forward holdout", _fh),
                     ("Last update", _last), ("Git commit", _git),
                     ("Env keys", _env)):
        items.append(_probe(name, fn))

    return {"available": True, "items": items,
            "n_fail": sum(1 for i in items if i["status"] == "FAIL"),
            "n_warning": sum(1 for i in items if i["status"] == "WARNING")}


@safe(label="数据更新")
def refresh_all() -> dict:
    """跑一次 pipeline 刷新（**不重训模型、不改冻结策略**）。"""
    from pipeline.refresh import run_all
    out = run_all(continue_on_error=True)
    return {"available": True, "jobs": out, "n": len(out)}


@safe(label="每日流水线")
def daily_run() -> dict:
    """最近一次每日流水线的状态（§39：Dashboard 读它）。

    页面不直接 import pipeline —— 那违反"GUI 只经 services"的纪律
    （有 AST 测试守着）。
    """
    from pipeline.daily_report import load_latest_summary
    s = load_latest_summary()
    if not s:
        return {"available": False, "reason": "还没有跑过每日流水线"}
    sm = s.get("summary", {}) or {}
    return {
        "available": True,
        "run_id": s.get("run_id"), "date": s.get("date"),
        "status": s.get("status"), "duration_s": s.get("duration_s"),
        "forward_observation": bool(sm.get("forward_observation")),
        "failed": sm.get("failed") or [], "blocked": sm.get("blocked") or [],
        "alerts": s.get("alerts") or [],
        "alert_summary": s.get("alert_summary") or {},
        "paper_live": s.get("paper_live"),
        "timestamps": s.get("timestamps") or {},
    }
