# -*- coding: utf-8 -*-
"""STEP 1 一键环境验证脚本。

检查项：
1. Python 环境（版本 3.11/3.12）
2. Qlib import 与版本
3. Qlib 数据目录结构（calendars / instruments / features）
4. qlib.init() 成功
5. 交易日历可读
6. A 股 instrument 列表可读
7. 样本股票日线数据可读
8. LightGBM 可用
9. Alpha158 handler / workflow 相关依赖可用

用法：
    source .venv/Scripts/activate
    python scripts/verify_step1.py

退出码：全部 PASS 为 0，任一 FAIL 为 1。
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
QLIB_DATA_DIR = PROJECT_ROOT / "qlib_data"

RESULTS = []  # (name, ok, detail)


def check(name: str, ok: bool, detail: str = ""):
    RESULTS.append((name, ok, detail))
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" -- {detail}" if detail else ""))


def main() -> int:
    print("=" * 60)
    print("STEP 1 verification: Qlib research environment")
    print("=" * 60)

    # --- 1. Python 环境 ---
    pyver = sys.version_info
    check(
        "Python version (3.11/3.12)",
        pyver.major == 3 and pyver.minor in (11, 12),
        f"{sys.version.split()[0]} @ {sys.executable}",
    )

    # --- 2. Qlib import / version ---
    try:
        import qlib

        check(
            "Qlib import",
            True,
            f"version {qlib.__version__}",
        )
        check("Qlib version is 0.9.x", qlib.__version__.startswith("0.9"), qlib.__version__)
    except Exception as e:
        check("Qlib import", False, f"{type(e).__name__}: {e}")
        print_summary()
        return 1

    # --- 3. 数据目录结构 ---
    subdirs = ["calendars", "instruments", "features"]
    for sub in subdirs:
        p = QLIB_DATA_DIR / sub
        ok = p.is_dir() and any(p.iterdir())
        check(f"Data dir qlib_data/{sub}", ok, str(p))

    # --- 4. qlib.init() ---
    try:
        qlib.init(provider_uri=str(QLIB_DATA_DIR), region="cn")
        from qlib.config import C

        data_path = str(C.provider_uri["__DEFAULT_FREQ"])
        ok_init = Path(data_path).resolve() == QLIB_DATA_DIR.resolve() and C.region == "cn"
        check("qlib.init()", ok_init, f"provider={data_path}, region={C.region}")
    except Exception as e:
        check("qlib.init()", False, f"{type(e).__name__}: {e}")
        print_summary()
        return 1

    from qlib.data import D

    # --- 5. 交易日历 ---
    try:
        cal = D.calendar(start_time="2020-01-01", end_time="2020-12-31", freq="day")
        check("Trading calendar", len(cal) > 200, f"{len(cal)} trading days in 2020")
    except Exception as e:
        check("Trading calendar", False, f"{type(e).__name__}: {e}")

    # --- 6. A 股 instrument 列表 ---
    try:
        inst = D.list_instruments(instruments=D.instruments(market="all"), as_list=True)
        n_sh = sum(i.startswith("SH") for i in inst)
        n_sz = sum(i.startswith("SZ") for i in inst)
        check("A-share instruments", len(inst) > 2000, f"total={len(inst)}, SH={n_sh}, SZ={n_sz}")
        check("Known stock SH600519 listed", "SH600519" in inst)
    except Exception as e:
        check("A-share instruments", False, f"{type(e).__name__}: {e}")

    # --- 7. 样本股票日线数据 ---
    try:
        df = D.features(
            ["SH600519", "SZ000001"],
            ["$close", "$volume"],
            start_time="2020-01-01",
            end_time="2020-06-30",
            freq="day",
        )
        check(
            "Sample stock daily data",
            df is not None and not df.empty and len(df) > 200,
            f"{len(df)} rows (SH600519 + SZ000001, 2020 H1)",
        )
    except Exception as e:
        check("Sample stock daily data", False, f"{type(e).__name__}: {e}")

    # --- 8. LightGBM ---
    try:
        import lightgbm

        check("LightGBM", True, f"version {lightgbm.__version__}")
    except Exception as e:
        check("LightGBM", False, f"{type(e).__name__}: {e}")

    # --- 9. Alpha158 / workflow 依赖 ---
    for label, obj in [
        ("Alpha158 handler", "qlib.contrib.data.handler.Alpha158"),
        ("LGBModel", "qlib.contrib.model.gbdt.LGBModel"),
        ("TopkDropoutStrategy", "qlib.contrib.strategy.TopkDropoutStrategy"),
        ("SignalRecord", "qlib.workflow.record_temp.SignalRecord"),
        ("SigAnaRecord", "qlib.workflow.record_temp.SigAnaRecord"),
        ("PortAnaRecord", "qlib.workflow.record_temp.PortAnaRecord"),
        ("workflow R (recorder)", "qlib.workflow.R"),
    ]:
        try:
            import importlib

            mod_name, cls_name = obj.rsplit(".", 1)
            mod = importlib.import_module(mod_name)
            getattr(mod, cls_name)
            check(label, True)
        except Exception as e:
            check(label, False, f"{type(e).__name__}: {e}")

    # --- 10. workflow 配置文件 ---
    wf = PROJECT_ROOT / "config" / "workflow_config_lightgbm_Alpha158.yaml"
    check("Workflow config exists", wf.is_file(), str(wf))
    if wf.is_file():
        import re

        text = wf.read_text(encoding="utf-8")
        ok_provider = re.search(r'provider_uri:\s*"([^"]+)"', text)
        if ok_provider:
            provider = ok_provider.group(1)
            ok_path = Path(provider).resolve() == QLIB_DATA_DIR.resolve()
        else:
            provider, ok_path = "not found", False
        check(
            "Workflow provider_uri points to project data",
            ok_path,
            provider,
        )

    print_summary()
    return 0 if all(ok for _, ok, _ in RESULTS) else 1


def print_summary():
    n_pass = sum(1 for _, ok, _ in RESULTS if ok)
    n_fail = sum(1 for _, ok, _ in RESULTS if not ok)
    print("-" * 60)
    print(f"SUMMARY: {n_pass} PASS / {n_fail} FAIL")
    print("OVERALL: PASS" if n_fail == 0 else "OVERALL: FAIL")
    if n_fail:
        print("Failed items:")
        for name, ok, detail in RESULTS:
            if not ok:
                print(f"  - {name}: {detail}")


if __name__ == "__main__":
    sys.exit(main())
