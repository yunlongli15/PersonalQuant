# -*- coding: utf-8 -*-
"""系统健康检查（STEP 12, spec §28）。

    python scripts/system_health.py
    python scripts/system_health.py --json

逐项 PASS / WARNING / FAIL，**每一项都给人话**，不把 Traceback 丢给用户。
只读，不修改任何东西。
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import health_service

EXTRA_CHECKS = ("Qlib", "Database", "Market data", "News", "Financial",
                "Model", "Paper live", "Forward holdout", "Portfolio",
                "Scheduler")


def _extra() -> list:
    """§28 要求但 health_service 还没覆盖的几项。"""
    out = []

    # Financial
    try:
        from pipeline.freshness import financial_latest
        d = financial_latest()
        out.append({"name": "Financial",
                    "status": "PASS" if d else "WARNING",
                    "detail": f"最新可用 {d or '无数据'}"})
    except Exception as e:                                     # noqa: BLE001
        out.append({"name": "Financial", "status": "FAIL",
                    "detail": str(e)[:80]})

    # Portfolio（个人账户）
    try:
        from services import portfolio_service
        pos = portfolio_service.positions()
        rec = portfolio_service.reconciliation()
        n = pos.get("n") or 0
        ok = rec.get("ok", True)
        out.append({"name": "Portfolio",
                    "status": "PASS" if ok else "WARNING",
                    "detail": f"{n} 只持仓；对账 "
                              f"{'一致' if ok else '不平'}"})
    except Exception as e:                                     # noqa: BLE001
        out.append({"name": "Portfolio", "status": "FAIL",
                    "detail": str(e)[:80]})

    # Scheduler
    try:
        import subprocess
        r = subprocess.run(
            ["schtasks", "/Query", "/TN", "PersonalQuant-Daily"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=30)
        if r.returncode == 0:
            out.append({"name": "Scheduler", "status": "PASS",
                        "detail": "计划任务 PersonalQuant-Daily 已注册"})
        else:
            out.append({"name": "Scheduler", "status": "WARNING",
                        "detail": "SCHEDULER_NOT_INSTALLED（手动跑 "
                                  "python scripts/run_daily.py 即可）"})
    except Exception:                                          # noqa: BLE001
        out.append({"name": "Scheduler", "status": "WARNING",
                    "detail": "SCHEDULER_NOT_INSTALLED"})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    h = health_service.check()
    # spec §28 用的是 "News"，health_service 里叫 "News provider" ——
    # 对外统一成 §28 的名字，避免同一样东西两个名字
    alias = {"News provider": "News"}
    items = [{"name": alias.get(i["name"], i["name"]), **{
        k: v for k, v in i.items() if k != "name"}}
        for i in h.get("items", [])]
    items += _extra()

    if args.json:
        print(json.dumps({"items": items,
                          "n_fail": sum(1 for i in items
                                        if i["status"] == "FAIL"),
                          "n_warning": sum(1 for i in items
                                           if i["status"] == "WARNING")},
                         ensure_ascii=False, indent=2))
        return 0

    print(f"{'检查项':<18}{'状态':<10}说明")
    print("-" * 78)
    for i in items:
        print(f"{i['name']:<18}{i['status']:<10}{i['detail'][:48]}")
    n_fail = sum(1 for i in items if i["status"] == "FAIL")
    n_warn = sum(1 for i in items if i["status"] == "WARNING")
    print("-" * 78)
    overall = "FAIL" if n_fail else ("WARNING" if n_warn else "PASS")
    print(f"总体：{overall}（{n_fail} FAIL / {n_warn} WARNING / "
          f"{len(items) - n_fail - n_warn} PASS）")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
