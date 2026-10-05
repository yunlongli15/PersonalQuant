# -*- coding: utf-8 -*-
"""被点名的几只股票：旧数据 vs 新数据 -> reports/news_flagged_stocks.md

    python scripts/news/diagnose_flagged_stocks.py [--dates 2026-09-30]

用户看着 `reports/paper_live/recommendation_*.md` 里的推荐买了模拟盘，
发现推荐里有跌停的、ST 的、大股东出事的。这个脚本只回答一个问题：

**换成修好的新闻数据之后，这几只股票在系统眼里的样子变了没有？**

对每只股票、每个推荐日，三件事并排：

1. 旧/新新闻数据：该股在两个版本的事件量、事件类型、有没有负向事件；
2. 旧/新新闻特征：S3 实际消费的那些因子值，两个版本各是多少；
3. 旧/新 S3 预测与排名：两个模型给这只股票打多少分、排第几。

**注意：本脚本不参与任何筛选。** 不因为某只股票跌了就把它从策略里剔掉 ——
那不是修 bug，是对着结果改规则（CLAUDE.md 铁律 3）。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT = PROJECT_ROOT / "reports" / "news_flagged_stocks.md"
NEWS = PROJECT_ROOT / "data" / "derived" / "news"

SYMBOLS = ["605179.SH", "600363.SH", "603256.SH",
           "002484.SZ", "002674.SZ", "603880.SH"]
DATES = ["2026-09-11", "2026-09-17", "2026-09-18", "2026-09-22",
         "2026-09-24", "2026-09-29", "2026-09-30"]

#: 事件窗：推荐日往前 90 个自然日（新闻因子最长 60 日 + 余量）
WINDOW_DAYS = 90


def names() -> dict:
    import pyarrow.parquet as pq

    try:
        d = pq.read_table(PROJECT_ROOT / "data" / "parquet" / "securities",
                          columns=["symbol", "name"]).to_pandas()
        return d.drop_duplicates("symbol").set_index("symbol")["name"].to_dict()
    except Exception:                                          # noqa: BLE001
        return {}


def events_for_sym(version: str, sym: str, lo, hi) -> pd.DataFrame:
    p = NEWS / ("news_events.parquet" if version == "v1"
                else f"news_events_{version}.parquet")
    if not p.exists():
        return pd.DataFrame()
    ev = pd.read_parquet(p, columns=["symbol", "event_type", "direction",
                                     "availability_time", "risk"])
    ev = ev[ev["symbol"] == sym]
    t = pd.to_datetime(ev["availability_time"], errors="coerce") \
        .dt.tz_localize(None)
    return ev[(t >= lo) & (t <= hi)]


def news_event_table(dates) -> pd.DataFrame:
    rows = []
    for d in dates:
        hi = pd.Timestamp(d) + pd.Timedelta(hours=23, minutes=59)
        lo = hi - pd.Timedelta(days=WINDOW_DAYS)
        for sym in SYMBOLS:
            r = {"date": d, "symbol": sym}
            for ver in ("v1", "v2"):
                ev = events_for_sym(ver, sym, lo, hi)
                r[f"{ver}_n"] = len(ev)
                r[f"{ver}_neg"] = int((ev["direction"] == "negative").sum()) \
                    if len(ev) else 0
                r[f"{ver}_types"] = ", ".join(sorted(ev["event_type"].unique()))
            rows.append(r)
    return pd.DataFrame(rows)


def factor_values(dates, factor_names) -> pd.DataFrame:
    """旧/新数据下，这些新闻因子的取值（原值，未归一化）。"""
    from factors.base import load_factor_data, set_news_version
    from factors.registry import FACTORS

    rows = []
    for ver in ("v1", "v2"):
        set_news_version(ver)
        data = load_factor_data("2014-06-01", max(dates))
        panels = {}
        for name in factor_names:
            panel = FACTORS[name](data, dates=list(pd.DatetimeIndex(dates)))
            panels[name] = panel.reindex(pd.DatetimeIndex(dates))
        for d in dates:
            for sym in SYMBOLS:
                r = {"date": d, "symbol": sym, "news_version": ver}
                for name in factor_names:
                    v = panels[name].loc[pd.Timestamp(d)].get(sym, np.nan)
                    r[name] = v
                rows.append(r)
    return pd.DataFrame(rows)


def s3_predictions(dates) -> pd.DataFrame:
    """两个模型对这些股票的打分与排名。

    S3_v1 直接读已落盘的信号快照（production 每天写的就是它）；
    S3_v2 用同一套特征（Alpha158 + factor_pack_v1 + 该版本的新闻 pack）
    现算 —— 特征只算一次，两个模型共用，免得跑两遍 qlib。
    """
    import json

    import yaml

    from personal_quant.strategy.features import compute_features
    from personal_quant.strategy.features import flatten_columns
    from personal_quant.strategy.model import AlphaModel
    from personal_quant.strategy.universe import build_universe

    sys.path.insert(0, str(PROJECT_ROOT))
    from pipeline.signals import STRATEGIES, strategy_spec

    from factors.base import load_factor_data, set_news_version
    from factors.normalization import fill_missing, normalize_panel
    from factors.registry import FACTOR_REGISTRY, FACTORS

    cfg = yaml.safe_load((PROJECT_ROOT / "config" / "strategy_v1.yaml")
                         .read_text(encoding="utf-8"))
    cfg["universe"]["st_filter"]["enabled"] = True
    step4 = json.loads((PROJECT_ROOT / "experiments" / "factors"
                        / "factor_run_001" / "factor_pack_v1.json")
                       .read_text(encoding="utf-8"))

    # 两个版本的 FactorData **只加载一次**。load_factor_data 每次要读
    # 115MB 的事件快照（v2）约 30 秒，set_news_version 又会清缓存 ——
    # 放进日期循环里等于每天读两遍，7 个日期多花好几分钟。
    # 直接持有对象引用传给 FACTORS 就不会再触发加载。
    data_by_ver = {}
    for ver in ("v1", "v2"):
        set_news_version(ver)
        data_by_ver[ver] = load_factor_data("2014-06-01", max(dates))
    packs = {}
    for sname, spec in STRATEGIES.items():
        ver = spec["news_version"]
        packs[sname] = json.loads(
            (PROJECT_ROOT / "experiments" / "news"
             / ("news_factor_run_001" if ver == "v1"
                else "news_factor_run_002")
             / f"factor_pack_news_{ver}.json").read_text(encoding="utf-8"))

    frames = []
    for d in dates:
        ts = pd.Timestamp(d)
        universe = build_universe(ts, cfg)
        syms = universe["symbol"].tolist()
        feats = compute_features(syms, [ts], cache=True)
        f0 = feats.get(ts)
        if f0 is None or f0.empty:
            print(f"[skip] {d}: 没有特征")
            continue
        f0 = flatten_columns(f0)
        for sname, spec in STRATEGIES.items():
            data = data_by_ver[spec["news_version"]]
            news_pack = packs[sname]
            f = f0.copy()
            for name in step4["selected"] + news_pack["selected"]:
                panel = FACTORS[name](data, dates=[ts]).reindex([ts])
                if FACTOR_REGISTRY[name]["category"] == "news":
                    panel = fill_missing(normalize_panel(panel, "rank"),
                                         "drop", data.industries)
                else:
                    panel = fill_missing(normalize_panel(panel, "rank"),
                                         "sector_median", data.industries)
                f = f.join(panel.loc[ts].rename(name), how="left")
            model = AlphaModel.load(strategy_spec(sname)["model_path"],
                                    dict(cfg["model"]["params"]),
                                    seed=cfg["model"]["seed"])
            m = f.dropna(how="all")
            pred = pd.Series(model.predict(m[model.feature_columns]),
                             index=m.index)
            rank = pred.rank(ascending=False)
            for sym in SYMBOLS:
                frames.append({"date": d, "symbol": sym, "strategy": sname,
                               "prediction": pred.get(sym, np.nan),
                               "rank": rank.get(sym, np.nan),
                               "n_universe": len(pred)})
        print(f"[s3] {d} 完成", flush=True)
    return pd.DataFrame(frames)


def render(ev: pd.DataFrame, fv: pd.DataFrame, pred: pd.DataFrame) -> str:
    nm = names()
    L = ["# 被点名的股票：修新闻数据前后，系统眼里的它们", "",
         "> 生成：`python scripts/news/diagnose_flagged_stocks.py`", "",
         "这几只来自 `reports/paper_live/recommendation_*.md` 的实际推荐 —— "
         "用户发现里面有跌停股、ST 股、大股东出事的股票。", "",
         "**本页只做诊断，不参与筛选。** 不因为某只股票跌了就把它从策略里"
         "剔掉 —— 那是对着结果改规则。", "",
         "股票：",
         ""]
    for s in SYMBOLS:
        L.append(f"- `{s}` {nm.get(s, '')}")
    L += ["", "---", "",
          f"## 1. 新闻数据：推荐日往前 {WINDOW_DAYS} 天，两个版本各看到什么", "",
          "| 日期 | 股票 | v1 条数 | v1 负向 | v2 条数 | v2 负向 | v2 事件类型 |",
          "|---|---|---|---|---|---|---|"]
    for _, r in ev.iterrows():
        L.append(f"| {r['date']} | `{r['symbol']}` | {r['v1_n']} | "
                 f"{r['v1_neg']} | **{r['v2_n']}** | **{r['v2_neg']}** | "
                 f"{r['v2_types'] or '—'} |")
    L += ["", "> 这张表就是最初的答案：v1 里这些股票**几乎没有公告**，"
              "v2 里它们有名有姓。", "", "---", ""]

    L += ["## 2. 新闻特征值：旧数据 vs 新数据", ""]
    fnames = [c for c in fv.columns
              if c not in ("date", "symbol", "news_version")]
    for nmv in ("v1", "v2"):
        sub = fv[fv["news_version"] == nmv].set_index(["date", "symbol"])
        other = fv[fv["news_version"] != nmv].set_index(["date", "symbol"])
        L += [f"### {nmv} 数据下", "",
              "| 日期 | 股票 | " + " | ".join(f"`{c}`" for c in fnames) + " |",
              "|---|---|" + "---|" * len(fnames)]
        for (d, s), r in sub.iterrows():
            o = other.loc[(d, s)] if (d, s) in other.index else None
            cells = []
            for c in fnames:
                a = r[c]
                b = o[c] if o is not None else np.nan
                if pd.isna(a):
                    cells.append("—")
                elif pd.notna(b) and not np.isclose(a, b):
                    cells.append(f"**{a:g}**（v{'2' if nmv=='v1' else '1'} "
                                 f"{b:g}）")
                else:
                    cells.append(f"{a:g}")
            L.append(f"| {d} | `{s}` | " + " | ".join(cells) + " |")
        L.append("")
    L += ["---", ""]

    if pred is not None and len(pred):
        L += ["## 3. S3 预测与排名：两个模型怎么看", "",
              "| 日期 | 股票 | S3_v1 分数 | S3_v1 排名 | S3_v2 分数 | "
              "S3_v2 排名 | 排名变化 |", "|---|---|---|---|---|---|---|"]
        nuniv = {}
        for _, r in pred.iterrows():
            nuniv[r["strategy"]] = max(nuniv.get(r["strategy"], 0),
                                       int(r["n_universe"]))
        piv = pred.pivot_table(index=["date", "symbol"], columns="strategy",
                               values=["prediction", "rank"])
        for (d, s), r in piv.iterrows():
            try:
                p1, p2 = r[("prediction", "S3_v1")], r[("prediction", "S3_v2")]
                k1, k2 = r[("rank", "S3_v1")], r[("rank", "S3_v2")]
            except KeyError:
                continue
            dk = "" if pd.isna(k1) or pd.isna(k2) else f"{int(k2 - k1):+d}"
            L.append(f"| {d} | `{s}` | {p1:.4f} | {int(k1)} | {p2:.4f} | "
                     f"{int(k2)} | {dk} |")
        L += ["", "> 排名是**全股票池**里的名次（越小越靠前），"
                  f"股票池规模 "
                  + "、".join(f"{k}={v}" for k, v in sorted(nuniv.items()))
                  + "。两个模型用的是同一套 Alpha158 与量价特征，"
                  "只有新闻那部分不同。", ""]
    else:
        L += ["## 3. S3 预测与排名", "", "（未计算 —— 需要 qlib 特征）", ""]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dates", default=",".join(DATES))
    ap.add_argument("--skip-s3", action="store_true")
    args = ap.parse_args()
    dates = [d.strip() for d in args.dates.split(",") if d.strip()]

    from factors.registry import FACTOR_REGISTRY

    fnames = sorted(n for n, m in FACTOR_REGISTRY.items()
                    if m["category"] == "news")
    keep = ["announcement_count_20d", "news_risk_20d",
            "shareholder_change_count_20d", "regulatory_event_count_20d"]
    fnames = [n for n in keep if n in fnames]

    ev = news_event_table(dates)
    fv = factor_values(dates, fnames)
    pred = pd.DataFrame() if args.skip_s3 else s3_predictions(dates)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(ev, fv, pred), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
