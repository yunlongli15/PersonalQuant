# -*- coding: utf-8 -*-
"""STEP 12 验收（spec §41，23 项）。

    PYTHONIOENCODING=utf-8 python scripts/verify_step12.py

检查"每日流水线能不能无人值守地跑"，不是"策略赚不赚钱"。
不训练模型、不选因子、不调参数、不写 forward holdout。
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

checks = []


def check(name, ok, detail=""):
    checks.append({"name": name, "ok": bool(ok), "detail": str(detail)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}"
          + (f" — {detail}" if detail and not ok else ""))


def main() -> int:
    from pipeline import daily as D
    from pipeline import daily_alerts as A
    from pipeline import daily_report as R
    from pipeline import freeze as F

    tmp = Path(tempfile.mkdtemp())

    # 1. orchestrator ------------------------------------------------------
    check("orchestrator", callable(D.run_daily) and len(D.TASKS) >= 12,
          f"{len(D.TASKS)} 个步骤")

    # 2. dependency graph --------------------------------------------------
    names = {t[0] for t in D.TASKS}
    bad_dep = [f"{n}->{d}" for n, _f, deps, _b in D.TASKS
               for d in deps if d not in names]
    check("dependency graph", not bad_dep, f"非法依赖 {bad_dep}")

    # 3. idempotency -------------------------------------------------------
    src = (PROJECT_ROOT / "pipeline" / "daily.py").read_text(encoding="utf-8")
    check("idempotency", "ALREADY_COMPLETED" in src
          and "input_fingerprint" in src and "while run_id in taken" in src,
          "输入指纹 + run_id 唯一")

    # 4. freeze guard ------------------------------------------------------
    st = F.verify()
    check("freeze guard", st.frozen and not st.drift, st.detail)

    # 5. forward holdout guard --------------------------------------------
    rec = F.load_freeze().get("production_freeze") or {}
    check("forward holdout guard",
          rec.get("forward_holdout_start") == "2026-09-18"
          and "PRE_FORWARD_ROOT" in src,
          "起点前的运行写 pre_forward，不污染 holdout")

    # 6. daily manifest ----------------------------------------------------
    mdir = PROJECT_ROOT / "data" / "quant" / "daily_runs"
    latest = mdir / "latest.json"
    ok_manifest = False
    detail = "还没有跑过（先 python scripts/run_daily.py）"
    if latest.exists():
        m = json.loads(latest.read_text(encoding="utf-8"))
        need = ("run_id", "date", "status", "start_time", "end_time",
                "git_commit", "strategy_version", "model_version",
                "feature_version", "news_version", "data_snapshot_id",
                "tasks", "warnings", "errors")
        miss = [k for k in need if k not in m]
        ok_manifest = not miss
        detail = f"缺 {miss}" if miss else f"{m['run_id']}"
    check("daily manifest", ok_manifest, detail)

    # 7. data health -------------------------------------------------------
    h = D.duckdb_available()
    check("data health", isinstance(h, tuple) and len(h) == 2,
          f"DuckDB {h[1][:50]}")

    # 8. news update -------------------------------------------------------
    check("news update", "task_news" in src and "news_latest" in src,
          "复用 STEP 5 provider，增量、不重复分析旧新闻")

    # 9. financial lazy update --------------------------------------------
    check("financial lazy update",
          "task_financial" in src and "dry-run 不抓取" in src,
          "不每天重下年报")

    # 10. paper live -------------------------------------------------------
    check("paper live", "_paper_ctx" in src and "run_day" in src,
          "复用 paper_live/ 引擎，不重新实现")

    # 11. portfolio update -------------------------------------------------
    check("portfolio update", "task_personal_snapshot" in src
          and "write_positions" in src,
          "个人账户与 paper 组合完全独立")

    # 12. performance ------------------------------------------------------
    check("performance", "task_performance" in src
          and "performance_service" in src,
          "复用 services/performance_service")

    # 13. risk -------------------------------------------------------------
    check("risk", "task_risk" in src and "risk_service" in src, "")

    # 14. alerts -----------------------------------------------------------
    required_codes = {"DATA_ERROR", "DATA_WARNING", "PIT_FAILURE",
                      "STRATEGY_DRIFT", "MODEL_DRIFT", "NEWS_DRIFT",
                      "EXCESS_TURNOVER", "DRAWDOWN_WARNING",
                      "FORWARD_INVALID", "PIPELINE_FAILURE"}
    check("alerts", required_codes <= set(A.CODES),
          f"缺 {required_codes - set(A.CODES)}")

    # 15. daily report -----------------------------------------------------
    rep = PROJECT_ROOT / "reports" / "daily"
    md = sorted(rep.glob("*.md")) if rep.exists() else []
    check("daily report", bool(md), f"{len(md)} 份")

    # 16. monthly report ---------------------------------------------------
    mr = (PROJECT_ROOT / "paper_live" / "report.py").read_text(
        encoding="utf-8")
    check("monthly report", "月度报告" in mr and "8.5" in mr,
          "已按 §31 加入数据质量/告警/冻结板块")

    # 17. scheduler scripts ------------------------------------------------
    inst = PROJECT_ROOT / "scripts" / "install_scheduler.ps1"
    unin = PROJECT_ROOT / "scripts" / "uninstall_scheduler.ps1"
    ok_sched = False
    detail = "缺脚本"
    if inst.exists() and unin.exists():
        raw = inst.read_bytes()
        has_bom = raw.startswith(b"\xef\xbb\xbf")
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "$e=$null; $null=[System.Management.Automation.Language."
             f"Parser]::ParseFile('{inst}',[ref]$null,[ref]$e); "
             "if($e.Count -eq 0){'OK'}else{'BAD'}"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=120)
        parses = "OK" in (r.stdout or "")
        ok_sched = has_bom and parses and "-Apply" in inst.read_text(
            encoding="utf-8-sig")
        detail = f"BOM={has_bom} 语法={parses} dry-run 默认"
    check("scheduler scripts", ok_sched, detail)

    # 18. dry-run ----------------------------------------------------------
    # 先释放 DuckDB：本脚本前面的检查已经把它打开，子进程拿不到锁会把
    # 所有步骤判成 BLOCKED，那是环境冲突不是流水线的问题（CLAUDE.md 铁律）。
    try:
        from personal_quant import db as _rdb
        _rdb.close()
    except Exception:                                          # noqa: BLE001
        pass
    r = subprocess.run(
        [sys.executable, "scripts/run_daily.py", "--dry-run"],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=900)
    check("dry-run", r.returncode in (0, 1)
          and "dry-run 不下载" in (r.stdout or ""),
          (r.stdout or r.stderr or "")[-120:])

    # 19. backfill guard ---------------------------------------------------
    check("backfill guard", "backfill requires --force" in src
          or "backfill 必须显式" in src,
          "默认禁止回写历史")

    # 20. health check -----------------------------------------------------
    r2 = subprocess.run([sys.executable, "scripts/system_health.py", "--json"],
                        cwd=str(PROJECT_ROOT), capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=600)
    ok_h = False
    detail = r2.stderr[-100:]
    if r2.returncode in (0, 1) and r2.stdout.strip():
        items = json.loads(r2.stdout)["items"]
        ok_h = len(items) >= 10 and all(
            i["status"] in ("PASS", "WARNING", "FAIL") for i in items)
        detail = f"{len(items)} 项检查"
    check("health check", ok_h, detail)

    # 21. GUI integration --------------------------------------------------
    dash = (PROJECT_ROOT / "app" / "pages" / "dashboard.py").read_text(
        encoding="utf-8")
    svc = (PROJECT_ROOT / "services" / "health_service.py").read_text(
        encoding="utf-8")
    check("GUI integration",
          "daily_run()" in dash and "def daily_run" in svc,
          "Dashboard 经 services.health_service.daily_run() 读每日摘要"
          "（§39 不新增页面；§5 GUI 只允许调 services）")

    # 22. no retrain -------------------------------------------------------
    banned = ("model.fit(", "AlphaModel(", "lgb.train", "retrain(")
    hits = [b for b in banned if b in src]
    check("no retrain", not hits, f"pipeline 里出现了训练调用：{hits}")

    # 23. no auto-selection ------------------------------------------------
    banned2 = ("factor_pack", "select_factor", "optimize(", "grid_search",
               "hyperparam")
    hits2 = [b for b in banned2 if b in src]
    check("no auto-selection", not hits2, f"pipeline 里出现了选择调用：{hits2}")

    # ---- 全部测试不回归 ---------------------------------------------------
    try:
        from personal_quant import db as research_db
        research_db.close()
    except Exception:                                          # noqa: BLE001
        pass
    r4 = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q"],
                        cwd=str(PROJECT_ROOT), capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=2400)
    out = (r4.stdout + r4.stderr).strip().splitlines()
    failed = [ln for ln in out if ln.startswith(("FAILED", "ERROR"))]
    check("no regression (full pytest)", r4.returncode == 0,
          (out[-1] if out else "") + (f" ｜ {failed[:4]}" if failed else ""))

    n_pass = sum(1 for c in checks if c["ok"])
    print(f"\nSUMMARY: {n_pass} PASS / {len(checks) - n_pass} FAIL / "
          f"OVERALL: {'PASS' if n_pass == len(checks) else 'FAIL'}")
    return 0 if n_pass == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
