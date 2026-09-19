# -*- coding: utf-8 -*-
"""STEP 10 验收（spec §49，21 项）。

    PYTHONIOENCODING=utf-8 python scripts/verify_step10.py

检查的是"这套 forward 观察系统是否可信"，不是"策略赚不赚钱"。
不写 forward holdout、不联网、不触碰 2024-2025 的任何选择路径。
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CFG_PATH = PROJECT_ROOT / "config" / "paper_live.yaml"
VALIDATION = PROJECT_ROOT / "experiments" / "paper_live" / "engine_validation"

checks = []


def check(name, ok, detail=""):
    checks.append({"name": name, "ok": bool(ok), "detail": str(detail)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}"
          + (f" — {detail}" if detail and not ok else ""))


def main() -> int:
    from paper_live import config as C
    from paper_live import metrics as pm
    from paper_live.alerts import check_alerts
    from paper_live.drift import strategy_drift
    from paper_live.execution import round_lots
    from paper_live.store import ForwardStore
    from personal_quant.strategy.costs import TransactionCostModel

    cfg = C.load_config()
    s = C.spec(cfg)

    # 1. clean forward start date -----------------------------------------
    check("clean forward start date",
          s["forward_start_date"] == "2026-09-18"
          and s["record_only"] is True,
          f"start={s['forward_start_date']} record_only={s['record_only']}")

    # 2. frozen strategy ---------------------------------------------------
    v = C.verify_freeze(cfg)
    check("frozen strategy", v["is_frozen"] and not v["drift"], v["detail"])

    # 3. config hash -------------------------------------------------------
    import hashlib
    stripped = C._strip_freeze_block(CFG_PATH.read_text(encoding="utf-8"))
    cur = hashlib.sha256(stripped.encode("utf-8")).hexdigest()
    check("config hash (no self-reference)",
          cur == s["freeze"]["paper_live_config"]
          and "freeze" not in C._strip_freeze_block("  freeze: {}"),
          "config 哈希不含 freeze 块，写入 freeze 不会改变它")

    # 4. model hash --------------------------------------------------------
    from paper_live.config import sha256_file
    check("model hash", sha256_file(s["alpha"]["model"]) == s["freeze"]["model"],
          s["alpha"]["model"])

    # 5. PIT ---------------------------------------------------------------
    from paper_live import audit as A

    class Ping:
        def latest_bar_date(self, symbols=None, on_or_before=None):
            return on_or_before

        def financial_availability(self, symbols):
            return pd.DataFrame(columns=["symbol", "availability_date"])

        def news_availability(self, symbols, on_or_before=None):
            return pd.DataFrame({"symbol": list(symbols),
                                 "published_at": [on_or_before]})

    ok_pit = A.pit_audit(Ping(), pd.Timestamp("2025-06-30"), ["A.SH"],
                         pd.DataFrame({"f": [1.0]}),
                         pd.DataFrame({"g": [1.0]})).status != "INVALID"
    bad_pit = A.pit_audit(Ping(), pd.Timestamp("2025-06-30"), [], None,
                          None).status == "INVALID"
    check("PIT audit", ok_pit and bad_pit,
          "正常输入 VALID；空股票池 INVALID")

    # 6. prediction schema -------------------------------------------------
    need = {"prediction_date", "signal_date", "symbol", "predicted_return",
            "rank", "target_weight", "model_version", "feature_version",
            "strategy_version", "data_snapshot_id"}
    src = (PROJECT_ROOT / "paper_live" / "engine.py").read_text(encoding="utf-8")
    missing = [c for c in need if c not in src]
    check("prediction schema", not missing, f"engine 未写出 {missing}")

    # 7. rebalance ---------------------------------------------------------
    from personal_quant.strategy.rebalance import rebalance_dates
    rb = rebalance_dates("2025-01-01", "2025-12-31", "monthly",
                         "last_trading_day")
    check("rebalance calendar", len(rb) == 12,
          f"2025 年 {len(rb)} 个调仓日（月度 last_trading_day）")

    # 8. execution ---------------------------------------------------------
    from personal_quant.strategy.execution import execute_order
    check("T+1 execution wired",
          callable(execute_order)
          and "execute_order" in (PROJECT_ROOT / "paper_live" /
                                  "execution.py").read_text(encoding="utf-8"),
          "复用 strategy_v1/6 的 execute_order")

    # 9. lot size ----------------------------------------------------------
    check("lot size", round_lots(150) == 100 and round_lots(99) == 0
          and round_lots(200) == 200,
          "100 股整数倍，向下取整，永不向上")

    # 10. costs ------------------------------------------------------------
    pl_cm = TransactionCostModel.from_config(
        {"transaction_costs": s["transaction_costs"]})
    v1 = TransactionCostModel(commission_rate=0.00025, min_commission=5.0,
                              stamp_duty=0.0005, transfer_fee=0.00001,
                              slippage=0.0005)
    check("transaction costs", pl_cm == v1, "与 strategy_v1 逐项同参")

    # 11. paper portfolio --------------------------------------------------
    from paper_live.engine import PaperPortfolio
    pf = PaperPortfolio(cash=100.0, capital_initial=100.0)
    check("paper portfolio state",
          PaperPortfolio.from_dict(pf.as_dict()).cash == 100.0,
          "状态可往返序列化")

    # 12. realized returns -------------------------------------------------
    preds = pd.DataFrame({"signal_date": pd.to_datetime(["2025-01-31"] * 3),
                          "symbol": ["A", "B", "C"]})
    lab = {20: pd.DataFrame({"A": [0.1], "B": [np.nan], "C": [0.2]},
                            index=pd.to_datetime(["2025-01-31"]))}
    rr = pm.realized_returns(preds, lab, horizons=(20,))
    check("realized returns (NA not 0)",
          "realized_return_20d" in rr.columns
          and np.isnan(rr["realized_return_20d"].iloc[1]),
          "窗口未走完记 NA，绝不填 0")

    # 13. benchmark --------------------------------------------------------
    labels = {b["label"] for b in s["benchmarks"]}
    check("benchmarks", {"CSI300", "CSI500", "CSI1000"} <= labels,
          f"{sorted(labels)}")

    # 14 / 15. IC / RankIC -------------------------------------------------
    p = pd.DataFrame({"signal_date": pd.to_datetime(["2025-01-31"] * 40),
                      "symbol": [f"S{i:02d}" for i in range(40)],
                      "prediction": np.linspace(1, 0, 40)})
    lab20 = pd.DataFrame(
        {f"S{i:02d}": [np.linspace(1, 0, 40)[i] * 0.01 + 0.001]
         for i in range(40)}, index=pd.to_datetime(["2025-01-31"]))
    tab = pm.ic_table(p, lab20)
    check("IC", "ic" in tab.columns and tab["ic"].iloc[0] > 0.9,
          f"n={len(tab)}")
    check("RankIC", "rank_ic" in tab.columns
          and tab["rank_ic"].iloc[0] > 0.9, f"n={len(tab)}")

    # 16. drift ------------------------------------------------------------
    d = strategy_drift(cfg)
    from paper_live.drift import model_drift
    rng = np.random.default_rng(0)
    mdrift = model_drift(pd.Series(rng.normal(6, 1, 200)),
                         pd.Series(rng.normal(0, 1, 2000)))
    check("drift detection",
          d["status"] == "OK" and mdrift["status"] == "MODEL_DRIFT_WARNING",
          f"strategy={d['status']} model={mdrift['status']}")

    # 17. append-only ------------------------------------------------------
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        st = ForwardStore(Path(td) / "fh")
        st.write_frame("predictions", "2026-09-18", pd.DataFrame({"a": [1]}))
        try:
            st.write_frame("predictions", "2026-09-18", pd.DataFrame({"a": [2]}))
            ok_ao = False
        except PermissionError:
            ok_ao = True
    check("append-only", ok_ao, "覆盖被拒绝")

    # 18. reproducibility --------------------------------------------------
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/forward/", "-q"],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=900)
    tail = (r.stdout + r.stderr).strip().splitlines()
    check("forward tests (incl. reproducibility)", r.returncode == 0,
          tail[-1] if tail else "no output")

    # 19. no retrospective selection --------------------------------------
    ok_nrs = C.FORWARD_HOLDOUT_READ_ONLY is True
    try:
        C.assert_not_used_for_selection(pd.DatetimeIndex(["2026-09-18"]), "v")
        ok_nrs = False
    except ValueError:
        pass
    check("no retrospective selection", ok_nrs,
          "FORWARD_HOLDOUT_READ_ONLY + 日期守卫")

    # 20. historical engine validation ------------------------------------
    runs = VALIDATION / "validation_runs.csv"
    if runs.exists():
        df = pd.read_csv(runs)
        t1_ok = bool((pd.to_datetime(df["execution_date"])
                      > pd.to_datetime(df["signal_date"])).all())
        check("historical engine validation", len(df) >= 20 and t1_ok,
              f"{len(df)} 个调仓日，T+1 全部成立")
    else:
        check("historical engine validation", False,
              "先跑 scripts/paper_live/validate_engine.py --n 24")

    # 21. scheduler (dry-run by default, never touches a broker) -----------
    ps1 = PROJECT_ROOT / "scripts" / "install_scheduler.ps1"
    ok_sched, detail = False, "install_scheduler.ps1 不存在"
    if ps1.exists():
        raw = ps1.read_bytes()
        text = raw.decode("utf-8-sig")
        # 默认必须是 dry-run：只有显式 -Apply 才注册
        default_dry = "$Apply" in text and "DRY-RUN" in text
        # 只看**真正会做事的行**。
        # 注释（含 <# #> 块）与 Write-Host 只是在"说"，不是在"做"——
        # 脚本里那句 "never does: broker API" 是打印给人的说明。
        code_lines, in_block = [], False
        for ln in text.splitlines():
            t = ln.strip()
            if t.startswith("<#"):
                in_block = True
            if in_block:
                if t.endswith("#>"):
                    in_block = False
                continue
            if not t or t.startswith("#") or t.startswith("Write-"):
                continue
            code_lines.append(t)
        code = "\n".join(code_lines).lower()
        no_broker = not any(k in code for k in
                            ("easytrader", "broker", "place_order",
                             "invoke-restmethod", "invoke-webrequest",
                             "start-process", "curl", "http://", "https://"))
        # 只允许调用这三个既定脚本
        only_known = all(k in text for k in
                         ("refresh_all.py", "run_daily.py",
                          "check_alerts.py"))
        # Windows PowerShell 5.1 读无 BOM 的 UTF-8 会按 ANSI 解析，中文注释
        # 会破坏语法 —— 脚本必须带 BOM
        import codecs
        has_bom = raw.startswith(codecs.BOM_UTF8)
        rs = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "$e=$null; $null=[System.Management.Automation.Language.Parser]"
             "::ParseFile((Resolve-Path 'scripts/install_scheduler.ps1').Path,"
             "[ref]$null,[ref]$e); if($e.Count -eq 0){'OK'}else{'BAD'}"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=120)
        parses = "OK" in (rs.stdout or "")
        ok_sched = (default_dry and no_broker and only_known and has_bom
                    and parses)
        detail = (f"dry-run 默认={default_dry} 可执行行无券商调用={no_broker} "
                  f"仅调用既定脚本={only_known} BOM={has_bom} 语法={parses}")
    check("scheduler script (dry-run safe)", ok_sched, detail)

    n_pass = sum(1 for c in checks if c["ok"])
    print(f"\nSUMMARY: {n_pass} PASS / {len(checks) - n_pass} FAIL / "
          f"OVERALL: {'PASS' if n_pass == len(checks) else 'FAIL'}")
    return 0 if n_pass == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
