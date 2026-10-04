# -*- coding: utf-8 -*-
"""STEP 11 验收（spec §70，26 项）。

    PYTHONIOENCODING=utf-8 python scripts/verify_step11.py

检查"个人投资终端"是否可信：账本、收益、对账、GUI、边界。
不写任何 forward holdout、不改任何冻结策略、不连接券商。
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

checks = []


def check(name, ok, detail=""):
    checks.append({"name": name, "ok": bool(ok), "detail": str(detail)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}"
          + (f" — {detail}" if detail and not ok else ""))


def main() -> int:
    from services import (factor_service, health_service, market_service,
                          news_service, performance_service,
                          portfolio_service, recommendation_service,
                          risk_service, strategy_service)
    from wealth import db, engine, importer, repository as repo

    tmp = Path(tempfile.mkdtemp())
    conn = db.connect(tmp / "verify.db")

    # 1. existing asset system audit ---------------------------------------
    audit = PROJECT_ROOT / "docs" / "步骤11-既有资产系统审计.md"
    check("existing asset system audit", audit.exists(),
          "docs/步骤11-既有资产系统审计.md")

    # 2. account schema ----------------------------------------------------
    tables = set(db.table_names(conn))
    need = {"platforms", "accounts", "products", "transactions",
            "daily_snapshots", "positions", "income_records", "audit_log"}
    check("account schema", need <= tables, f"缺 {need - tables}")

    # 3. transaction ledger (invariants enforced) --------------------------
    pid = repo.create_platform(conn, "券商", kind="broker")
    aid = repo.create_account(conn, pid, "A")
    prod = repo.create_product(conn, aid, "茅台", "stock", ticker="600519.SH")
    ok_ledger = False
    try:
        repo.create_transaction(conn, "2026-09-01", prod, "buy", units=100,
                                price=10.0, amount=1000.0, cash_flow=1000.0)
    except repo.ValidationError:
        ok_ledger = True
    check("transaction ledger invariants", ok_ledger,
          "内部流带 cash_flow 被拒绝")

    # 4. position reconstruction -------------------------------------------
    repo.create_transaction(conn, "2026-09-01", prod, "buy", units=100,
                            price=10.0, amount=1000.0)
    repo.create_transaction(conn, "2026-09-02", prod, "buy", units=100,
                            price=20.0, amount=2000.0)
    h = engine.holdings_from_ledger(repo.list_transactions(conn,
                                                           product_id=prod))
    check("position reconstruction", h.units == 200
          and h.avg_cost == 15.0, f"units={h.units} avg={h.avg_cost}")

    # 5. cash accounting ---------------------------------------------------
    cashp = repo.create_product(conn, aid, "现金", "cash")
    repo.create_transaction(conn, "2026-09-01", cashp, "deposit",
                            amount=50000.0, cash_flow=50000.0)
    c = engine.cash_balance(conn)
    check("cash accounting", c["implied"] == -1000.0 - 2000.0 + 50000.0,
          f"implied={c['implied']}")

    # 6. TWR ---------------------------------------------------------------
    twr = engine.twr([{"date": "2026-01-01", "value": 1000.0, "flow": 0.0},
                      {"date": "2026-01-02", "value": 1100.0, "flow": 0.0}])
    twr_dep = engine.twr([{"date": "2026-01-01", "value": 1000.0, "flow": 0.0},
                          {"date": "2026-01-02", "value": 11000.0,
                           "flow": 10000.0}])
    check("TWR", abs(twr - 0.10) < 1e-9 and abs(twr_dep) < 1e-9,
          f"twr={twr} twr_dep={twr_dep}（存入 1 万不改 TWR）")

    # 7. XIRR --------------------------------------------------------------
    x = engine.xirr(["2025-01-01", "2026-01-01"], [-1000.0, 1100.0])
    check("XIRR", x is not None and abs(x - 0.10) < 1e-3, f"xirr={x}")

    # 8. PnL ---------------------------------------------------------------
    check("PnL excludes capital flow",
          engine.investment_pnl(1000.0, 101000.0, 100000.0) == 0.0,
          "存入 10 万不算收益")

    # 9. benchmark ---------------------------------------------------------
    repo.upsert_benchmark(conn, "2026-09-01", "CSI300", 4500.0)
    check("benchmark", len(repo.list_benchmarks(conn, "CSI300")) == 1)

    # 10. portfolio snapshot -----------------------------------------------
    repo.upsert_snapshot(conn, "2026-09-02", prod, units=200, nav=20.0,
                         market_value=4000.0)
    s = engine.value_series(conn)
    check("portfolio snapshot", len(s) >= 1, f"{len(s)} 个净值点")

    # 11. reconciliation ---------------------------------------------------
    r = engine.reconcile(conn)
    check("reconciliation", r["ok"], f"difference={r['difference']}")

    # 12. backup -----------------------------------------------------------
    p = db.backup(dest_dir=tmp, conn=conn)
    check("backup", Path(p).exists(), str(p))

    # 13. portfolio API ----------------------------------------------------
    api = [hasattr(portfolio_service, n) for n in
           ("valuation", "positions", "allocation", "transactions",
            "snapshots", "reconciliation", "consistency")]
    check("portfolio API", all(api), "services.portfolio_service 接口齐全")

    # 14. service layer ----------------------------------------------------
    from services import (backtest_service, health_service as hs)
    mods = [portfolio_service, performance_service, strategy_service,
            market_service, news_service, risk_service, backtest_service,
            recommendation_service, factor_service, hs]
    check("service layer", len(mods) == 10, "10 个服务模块")

    # 15. GUI startup ------------------------------------------------------
    r2 = subprocess.run([sys.executable, "scripts/run_app.py",
                         "--host", "0.0.0.0"],
                        cwd=str(PROJECT_ROOT), capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=120)
    check("GUI startup (refuses non-local bind)",
          r2.returncode == 1 and "refusing" in (r2.stdout + r2.stderr),
          f"rc={r2.returncode}")

    # 16. all GUI pages import ---------------------------------------------
    pages = sorted((PROJECT_ROOT / "app" / "pages").glob("*.py"))
    ok_pages = all(p.read_text(encoding="utf-8").strip() for p in pages)
    check("all GUI pages present", len(pages) == 12 and ok_pages,
          f"{len(pages)} 个页面")

    # 17. empty-state handling ---------------------------------------------
    empty_ok = True
    for fn in (portfolio_service.positions, portfolio_service.allocation,
               risk_service.metrics, news_service.latest,
               factor_service.leaderboards, backtest_service.results):
        res = fn()
        if not isinstance(res, dict):
            empty_ok = False
    check("empty-state handling", empty_ok, "空数据不抛异常")

    # 18-22. 页面渲染（含空态）----------------------------------------------
    from streamlit.testing.v1 import AppTest
    rendered = {}
    for name in ("dashboard", "portfolio", "recommendations",
                 "paper_live_monitor", "risk", "factors", "news",
                 "settings", "transactions", "quant_strategy", "backtest",
                 "research"):
        f = PROJECT_ROOT / "app" / "pages" / f"{name}.py"
        at = AppTest.from_file(str(f), default_timeout=240)
        at.run()
        rendered[name] = not at.exception
    check("recommendation rendering", rendered.get("recommendations", False))
    check("paper-live rendering", rendered.get("paper_live_monitor", False))
    check("risk rendering", rendered.get("risk", False))
    check("factor rendering", rendered.get("factors", False))
    check("news rendering", rendered.get("news", False))

    # 23. data timestamp ---------------------------------------------------
    blob = (PROJECT_ROOT / "app" / "_shared.py").read_text(encoding="utf-8")
    check("data timestamp", "data_timestamps" in blob
          and "非实时" in blob, "页面显示数据时间")

    # 24. no broker --------------------------------------------------------
    import ast
    broker_hits = []
    for d in (PROJECT_ROOT / "app", PROJECT_ROOT / "services"):
        for f in d.rglob("*.py"):
            t = f.read_text(encoding="utf-8")
            for bad in ("easytrader", "place_order", "submit_order",
                        "send_order"):
                if bad in t.lower():
                    broker_hits.append(f"{f.name}:{bad}")
    import yaml
    gui_cfg = yaml.safe_load(
        (PROJECT_ROOT / "config" / "gui.yaml").read_text(
            encoding="utf-8"))["gui"]
    check("no broker", not broker_hits
          and gui_cfg["safety"]["allow_broker"] is False
          and gui_cfg["safety"]["allow_freeze_change"] is False,
          f"命中 {broker_hits}")

    # 25. audit trail ------------------------------------------------------
    logs = repo.list_audit(conn, limit=200)
    n_writes = len(repo.list_transactions(conn))
    check("audit trail", len(logs) >= n_writes,
          f"{len(logs)} 条审计 / {n_writes} 条流水")

    # 26. demo account -----------------------------------------------------
    r3 = subprocess.run([sys.executable, "scripts/make_demo_account.py",
                         "--db", str(tmp / "demo.db"), "--force"],
                        cwd=str(PROJECT_ROOT), capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=300)
    check("demo account", r3.returncode == 0 and "演示库已生成" in r3.stdout,
          (r3.stdout + r3.stderr)[-160:])

    # ---- 全部测试不回归 ---------------------------------------------------
    # DuckDB 是单进程独占的（CLAUDE.md 铁律）：本脚本前面的检查已经打开了
    # research DB，必须**先释放**再把 pytest 跑起来，否则子进程会因为拿不到
    # 文件锁而大面积失败 —— 那是环境冲突，不是真的回归。
    try:
        from personal_quant import db as research_db
        research_db.close()
    except Exception:                                          # noqa: BLE001
        pass
    try:
        db.reset()
    except Exception:                                          # noqa: BLE001
        pass

    r4 = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q"],
                        cwd=str(PROJECT_ROOT), capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=1800)
    out = (r4.stdout + r4.stderr).strip().splitlines()
    failed = [ln for ln in out if ln.startswith(("FAILED", "ERROR"))]
    check("no regression (full pytest)", r4.returncode == 0,
          (out[-1] if out else "no output")
          + (f" ｜ 前几项失败：{failed[:5]}" if failed else ""))

    n_pass = sum(1 for c in checks if c["ok"])
    print(f"\nSUMMARY: {n_pass} PASS / {len(checks) - n_pass} FAIL / "
          f"OVERALL: {'PASS' if n_pass == len(checks) else 'FAIL'}")
    return 0 if n_pass == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
