# -*- coding: utf-8 -*-
"""回测结果浏览（spec §33）。

**只读。** GUI 不允许自动修改参数（§33）—— 本模块没有任何写入路径。
"""

from __future__ import annotations

from ._common import PROJECT_ROOT, read_json, read_parquet, safe, unavailable

RUNS = [
    ("strategy_v1/run_001", "strategy_v1（STEP 3，月度 Top-20 等权）"),
    ("strategy_v1/run_001_wf", "strategy_v1 walk-forward"),
]


@safe(label="回测")
def results() -> dict:
    out = []
    base = PROJECT_ROOT / "experiments"
    for rel, label in RUNS:
        s = read_json(base / rel / "summary.json")
        if not s:
            continue
        out.append({"key": rel, "label": label,
                    "strategy": s.get("strategy"),
                    "benchmarks": s.get("benchmarks"),
                    "momentum": s.get("momentum_baseline")})
    pf = base / "portfolio"
    if pf.exists():
        for d in sorted(pf.iterdir()):
            m = read_json(d / "metrics.json")
            if m:
                out.append({"key": f"portfolio/{d.name}", "label": d.name,
                            "strategy": m})
    if not out:
        return unavailable("还没有回测结果")
    return {"available": True, "runs": out, "n": len(out)}


@safe(label="净值曲线")
def nav_curve(run_key: str) -> dict:
    df = read_parquet(PROJECT_ROOT / "experiments" / run_key / "nav.parquet")
    if df is None or df.empty:
        return unavailable(f"{run_key} 没有 nav.parquet")
    col = "nav" if "nav" in df.columns else df.columns[0]
    return {"available": True, "key": run_key,
            "series": [{"date": str(idx)[:10], "value": float(v)}
                       for idx, v in df[col].items()]}
