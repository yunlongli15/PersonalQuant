# -*- coding: utf-8 -*-
"""Incremental IC Factor Selection Protocol V2 —— 验收检查（§35）。

    PYTHONIOENCODING=utf-8 python scripts/verify_incremental_factor_selection.py

11 项检查 + 重跑 tests/factors 的增量协议测试；逐项 PASS/FAIL。
不写 DuckDB、不联网、不使用 2024-2025 数据。
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
CFG_PATH = PROJECT_ROOT / "config" / "factor_selection_v2.yaml"

checks = []


def check(name, ok, detail=""):
    checks.append({"name": name, "ok": bool(ok), "detail": str(detail)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}"
          + (f" — {detail}" if detail and not ok else ""))


def main() -> int:
    spec = yaml.safe_load(CFG_PATH.read_text(encoding="utf-8"))[
        "factor_selection_v2"]
    m = {}
    outdir = PROJECT_ROOT / spec["output"]["dir"]
    manifest_path = PROJECT_ROOT / spec["final"]["manifest"]

    from factors.registry import FACTOR_REGISTRY
    from incremental.holdout import ForwardHoldout
    from incremental.windows import assert_not_historical_test

    # 1. candidate registry ------------------------------------------------
    ok, detail = False, "manifest 不存在"
    final = []
    if manifest_path.exists():
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
        final = m.get("final_candidates", [])
        unknown = [f for f in final if f not in FACTOR_REGISTRY]
        ok = not unknown
        detail = f"{len(final)} 个候选，未注册: {unknown}" if unknown else \
            f"{final}"
    check("candidate registry", ok, detail)

    # 2. walk-forward ------------------------------------------------------
    ok, detail = False, "manifest 不存在"
    if manifest_path.exists():
        folds = m.get("folds", [])
        bad = [f["name"] for f in folds if not f["train"][1] < f["valid"][0]]
        n_ok = all(f["n_valid_dates"] > 0 for f in folds)
        ok = bool(folds) and not bad and n_ok
        detail = f"{len(folds)} 折；违规 {bad}" if bad else \
            f"{[(f['name'], f['n_train_dates'], f['n_valid_dates']) for f in folds]}"
    check("walk-forward folds", ok, detail)

    # 3. delta IC ----------------------------------------------------------
    metrics_path = outdir / "candidate_metrics.csv"
    met = pd.read_csv(metrics_path) if metrics_path.exists() else pd.DataFrame()
    cols_ic = {"delta_ic_mean", "delta_ic_median", "delta_ic_std",
               "delta_icir", "delta_ic_positive_ratio"}
    ok = not met.empty and cols_ic.issubset(met.columns)
    check("delta IC metrics", ok,
          f"{len(met)} 行" if ok else f"缺列 {cols_ic - set(met.columns)}")

    # 4. delta RankIC ------------------------------------------------------
    cols_r = {"delta_rank_ic_mean", "delta_rank_ic_median",
              "delta_rank_ic_std", "delta_rank_icir",
              "delta_rank_ic_positive_ratio"}
    ok = not met.empty and cols_r.issubset(met.columns)
    check("delta RankIC metrics", ok,
          f"{len(met)} 行" if ok else f"缺列 {cols_r - set(met.columns)}")

    # 5. block bootstrap ---------------------------------------------------
    ok, detail = False, "候选指标缺失"
    if not met.empty:
        bs_path = outdir / "bootstrap.csv"
        if bs_path.exists():
            bs = pd.read_csv(bs_path)
            ok = (bs["block"] > 1).all() and (bs["n_resamples"] >= 1000).all() \
                and (bs["ci_low"] <= bs["ci_high"]).all()
            detail = (f"block={int(bs['block'].iloc[0])}, "
                      f"n={int(bs['n_resamples'].iloc[0])}, "
                      f"平均 block 区间宽 {bs['ci_width'].mean():.4f} vs "
                      f"iid {bs['iid_ci_width'].mean():.4f}")
        else:
            detail = "bootstrap.csv 不存在"
    check("block bootstrap", ok, detail)

    # 6. prediction impact -------------------------------------------------
    ok, detail = False, "候选指标缺失"
    if not met.empty and "prediction_corr" in met.columns:
        s = met["prediction_corr"].dropna()
        ok = len(s) > 0 and bool(((s >= -1.001) & (s <= 1.001)).all())
        detail = f"corr 范围 [{s.min():.3f}, {s.max():.3f}]，中位 {s.median():.3f}"
    check("prediction impact", ok, detail)

    # 7. redundancy --------------------------------------------------------
    ok, detail = False, "候选指标缺失"
    if not met.empty:
        need = {"max_corr_existing", "r2_existing", "redundant"}
        ok = need.issubset(met.columns) and \
            spec["redundancy"]["method"] == "raw_rank_correlation"
        detail = ("主判据 = 原始秩相关（修正了 step9 的残差聚类错误）"
                  if ok else f"缺列 {need - set(met.columns)}")
    check("redundancy (raw rank correlation)", ok, detail)

    # 8. no test usage -----------------------------------------------------
    ok, detail = True, "选择路径无 2024-2025 字面量"
    try:
        assert_not_historical_test(pd.DatetimeIndex(["2024-06-28"]), "verify")
        ok, detail = False, "守卫未拦截 2024 日期"
    except ValueError:
        pass
    if ok:
        import re
        for rel in ("incremental/engine.py", "incremental/stats.py",
                    "incremental/redundancy.py",
                    "scripts/run_incremental_factor_selection.py"):
            text = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
            if re.search(r"['\"]20(24|25)-\d{2}-\d{2}['\"]", text):
                ok, detail = False, f"{rel} 含 2024/2025 字面量"
                break
    check("no 2024-2025 selection", ok, detail)

    # 9. PIT ---------------------------------------------------------------
    stage_a = outdir / "stage_a_screen.csv"
    ok, detail = False, "stage_a_screen.csv 不存在"
    if stage_a.exists():
        sa = pd.read_csv(stage_a)
        kept = m.get("stage_a_kept", []) if manifest_path.exists() else []
        sub = sa[sa["factor"].isin(kept)]
        bad = sub[sub["pit_pass"] == False]["factor"].tolist()  # noqa: E712
        ok = len(sub) > 0 and not bad
        detail = f"{len(sub)} 个进入 Stage B 的因子全部通过投毒检验" if ok \
            else f"PIT FAIL: {bad}"
    check("PIT (future-corruption) for stage B", ok, detail)

    # 10. freeze manifest --------------------------------------------------
    ok, detail = False, "manifest 不存在"
    if manifest_path.exists():
        need = ["protocol", "version", "selected_at", "git_commit",
                "config_sha256", "data_snapshot", "selection_window", "model",
                "folds", "m0_features", "final_candidates", "stage_a_kept",
                "historical_test_status", "forward_holdout_start"]
        missing = [k for k in need if k not in m]
        import hashlib
        sha_ok = m.get("config_sha256") == hashlib.sha256(
            CFG_PATH.read_bytes()).hexdigest()
        ok = not missing and sha_ok
        detail = f"缺 {missing}" if missing else (
            "配置未在 freeze 后被改动" if sha_ok else "config 在 freeze 后变了")
    check("candidate freeze manifest", ok, detail)

    # 11. forward holdout --------------------------------------------------
    h = ForwardHoldout.load({"factor_selection_v2": spec})
    s = h.summary()
    ok = (h.mode == "record_only"
          and h.start_ts > pd.Timestamp("2023-12-31")
          and h.registry.exists())
    check("forward holdout", ok,
          f"start={s['start']} mode={s['mode']} 记录 {s['n_records']} 期 / "
          f"已实现 {s['n_realized']} 期")

    # ---- rerun the incremental protocol tests ----------------------------
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/factors/", "-q",
         "-k", "incremental or walk_forward or block_bootstrap or "
               "prediction_impact or redundancy or factor_selection_freeze "
               "or no_test_usage"],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=900)
    tail = (r.stdout + r.stderr).strip().splitlines()
    check("protocol tests", r.returncode == 0, tail[-1] if tail else "no output")

    n_pass = sum(1 for c in checks if c["ok"])
    print(f"\nSUMMARY: {n_pass} PASS / {len(checks) - n_pass} FAIL / "
          f"OVERALL: {'PASS' if n_pass == len(checks) else 'FAIL'}")
    return 0 if n_pass == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
