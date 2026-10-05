# -*- coding: utf-8 -*-
"""新闻因子的截面 IC 到底来自哪里？-> reports/news_factor_crosssection.md

    python scripts/news/diagnose_news_crosssection.py

**动机。** v2 修好 SSE 采集之后，新闻因子的 IC 全部翻转了符号：

    announcement_count_20d   v1 research ICIR +0.388  ->  v2 -0.184
    news_risk_20d            v1 +0.346               ->  v2 -0.050
    regulatory_event_count_20d  v1 +0.020            ->  v2 -0.556

符号翻转可能是两件完全不同的事：

  (a) **真的信号变了** —— 旧语料只含定期报告，新语料含真实公告流；
  (b) **因子其实是个"交易所哑变量"** —— v2 里沪市公告密度是深市的
      ~20 倍（沪市全量 785 条/股，深市仅市值前 ~60 家 40 条/股）。
      截面 rank 之后，因子值主要由"是不是沪市"决定，IC 反映的是
      沪深收益差，跟新闻没有关系。

这两者必须分开。做法：**把 IC 拆到同组内部再算一遍。**

- 全样本 IC：混合沪深，和评估器口径一致；
- 沪市内 IC / 深市内 IC：组内排名，组间差异被消掉；
- 流动性分组内 IC：按 20 日均成交额分 5 组，组内排名，
  消掉"因子其实是规模/流动性代理"的可能。

**判据**：如果全样本 IC 显著而组内 IC 全部接近 0，那就是 (b) ——
这个因子不能进生产，必须如实记录。
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd

from factors.base import (DERIVED, cached_rebalance_dates, load_factor_data,
                          set_news_version)
from factors.registry import FACTOR_REGISTRY, FACTORS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT = PROJECT_ROOT / "reports" / "news_factor_crosssection.md"

RESEARCH = ("2018-01-01", "2021-12-31")
HORIZON = 20
N_LIQ_BUCKETS = 5


def load_labels() -> dict:
    lab = pd.read_parquet(DERIVED / "labels.parquet")
    lab = lab[lab["horizon"] == HORIZON]
    return {pd.Timestamp(d): g.set_index("symbol")["label"]
            for d, g in lab.groupby("date")}


def exchange(sym: str) -> str:
    return "SH" if sym.startswith("6") else "SZ"


def _spearman(a: pd.Series, b: pd.Series) -> float:
    """两个已对齐 Series 的 Spearman 相关（样本 <10 时返回 NaN）。"""
    df = pd.concat([a.rename("f"), b.rename("y")], axis=1).dropna()
    if len(df) < 10 or df["f"].nunique() < 3 or df["y"].nunique() < 3:
        return np.nan
    return float(df["f"].rank().corr(df["y"].rank()))


def per_date_ic(panel: pd.DataFrame, labels: dict, liq: pd.DataFrame,
                dates) -> pd.DataFrame:
    rows = []
    for d in dates:
        if d not in panel.index or d not in labels:
            continue
        f = panel.loc[d].dropna()
        y = labels[d]
        both = f.index.intersection(y.index)
        if len(both) < 30:
            continue
        f, y = f[both], y[both]
        row = {"date": d, "n": len(both),
               "ic_full": _spearman(f, y)}
        for ex in ("SH", "SZ"):
            m = f.index.map(exchange) == ex
            row[f"ic_{ex}"] = _spearman(f[m], y[m])
            row[f"n_{ex}"] = int(m.sum())
        # 流动性分组内（消掉规模代理的可能）
        if liq is not None and d in liq.index:
            q = liq.loc[d].reindex(f.index)
            try:
                bucket = pd.qcut(q, N_LIQ_BUCKETS, labels=False,
                                 duplicates="drop")
            except ValueError:
                bucket = None
            ics = []
            if bucket is not None:
                for b in pd.unique(bucket.dropna()):
                    m = (bucket == b).to_numpy()
                    v = _spearman(f[m], y[m])
                    if not np.isnan(v):
                        ics.append(v)
            row["ic_within_liq"] = float(np.mean(ics)) if ics else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def _agg(s: pd.Series) -> dict:
    s = s.dropna()
    if s.empty:
        return {"n": 0, "mean": np.nan, "icir": np.nan, "pos": np.nan}
    return {"n": int(len(s)), "mean": float(s.mean()),
            "icir": float(s.mean() / s.std()) if s.std() else np.nan,
            "pos": float((s > 0).mean())}


def run(version: str, names: list) -> dict:
    set_news_version(version)
    data = load_factor_data("2017-01-01", RESEARCH[1])
    dates = [pd.Timestamp(d) for d in cached_rebalance_dates(*RESEARCH)]
    labels = load_labels()

    # 流动性代理：20 日均成交额（规模/活跃度的代理，不是市值本身）
    liq = data.amount_cny.rolling(20, min_periods=5).mean()

    out = {"version": version, "factors": {}}
    for name in names:
        panel = FACTORS[name](data, dates=dates)
        df = per_date_ic(panel, labels, liq, dates)
        if df.empty:
            out["factors"][name] = {"error": "没有可用截面"}
            continue
        out["factors"][name] = {
            "n_dates": len(df),
            "ic_full": _agg(df["ic_full"]),
            "ic_SH": _agg(df["ic_SH"]),
            "ic_SZ": _agg(df["ic_SZ"]),
            "ic_within_liq": _agg(df["ic_within_liq"]),
        }
        f = out["factors"][name]
        print(f"[{version}] {name}: full {f['ic_full']['mean']:+.4f} | "
              f"SH {f['ic_SH']['mean']:+.4f} | SZ {f['ic_SZ']['mean']:+.4f} | "
              f"within-liq {f['ic_within_liq']['mean']:+.4f}", flush=True)
    return out


def verdict(f: dict) -> str:
    """全样本有信号、组内没有 = 交易所/规模哑变量，不是新闻信息。"""
    full = f.get("ic_full", {}).get("mean")
    if full is None or (isinstance(full, float) and np.isnan(full)):
        return "—"
    within = [f.get(k, {}).get("mean") for k in
              ("ic_SH", "ic_SZ", "ic_within_liq")]
    within = [w for w in within if w is not None and not np.isnan(w)]
    if not within:
        return "—"
    keep = max(abs(w) for w in within)
    if abs(full) < 0.005:
        return "无信号"
    if keep < 0.3 * abs(full):
        return "**组内消失 → 哑变量伪信号**"
    if keep < 0.6 * abs(full):
        return "部分来自组间差异"
    return "组内仍在"


def render(results: list) -> str:
    L = ["# 新闻因子截面 IC 拆解 — 信号还是哑变量？", "",
         "> 生成：`python scripts/news/diagnose_news_crosssection.py`",
         "> 研究期 2018-2021，持有期 20 日，Spearman rank IC。", "",
         "**为什么要做这个**：v2 修好 SSE 采集后新闻因子的 IC 集体翻转符号。",
         "但 v2 里沪市公告密度是深市的约 20 倍（沪市全量、深市仅市值前 ~60 家），",
         "而深市被覆盖的那部分又都是大盘股 —— 所以因子的截面排名有可能",
         "主要反映的是「沪市/深市」「大盘/小盘」，而不是公告本身的信息。",
         "把 IC 拆到组内重算就能分辨。", "",
         "| 列 | 含义 |", "|---|---|",
         "| 全样本 | 混合沪深，与评估器口径一致 |",
         "| 沪市内 / 深市内 | 组内排名，组间差异被消掉 |",
         "| 流动性分组内 | 按 20 日均成交额分 5 组后组内排名 |",
         "", "---", ""]
    for r in results:
        L += [f"## {r['version']}", "",
              "| 因子 | 全样本 | 沪市内 | 深市内 | 流动性分组内 | 判定 |",
              "|---|---|---|---|---|---|"]
        for name, f in r["factors"].items():
            if "error" in f:
                L.append(f"| `{name}` | — | — | — | — | {f['error']} |")
                continue

            def c(k):
                a = f[k]
                return "—" if not a["n"] else (
                    f"{a['mean']:+.4f} (ICIR {a['icir']:+.2f})")

            L.append(f"| `{name}` | {c('ic_full')} | {c('ic_SH')} | "
                     f"{c('ic_SZ')} | {c('ic_within_liq')} | {verdict(f)} |")
        n_dates = max((f.get("n_dates", 0) for f in r["factors"].values()),
                      default=0)
        L += ["", f"研究期信号日 {n_dates} 个。", "", "---", ""]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--versions", default="v1,v2")
    ap.add_argument("--factors", default=None,
                    help="逗号分隔；默认全部新闻因子")
    args = ap.parse_args()
    names = (args.factors.split(",") if args.factors else
             sorted(n for n, m in FACTOR_REGISTRY.items()
                    if m["category"] == "news"))
    results = [run(v.strip(), names) for v in args.versions.split(",")
               if v.strip()]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(results), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
