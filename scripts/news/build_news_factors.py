# -*- coding: utf-8 -*-
"""News factor evaluation -> factor_pack_news_{v1,v2} (selection 2018-2023 only).

    python scripts/news/build_news_factors.py [--version v1|v2]

Reuses the STEP 4 factor engine: every registered news factor is evaluated
on research/valid/test with the full research universe; the pack selection
uses RESEARCH + VALID only (same gates as STEP 4, news coverage threshold
from config/news_v1.yaml). After selection, the factor store
(data/derived/news/news_factors{,_v2}.parquet: symbol/signal_date/
factor_name/factor_value/source_event_count/lookback_days/decay_half_life/
feature_version) is written for the selected factors over all signal
dates (strategy/ablation input). Test results are recorded but NEVER used
for selection.

--version v2 reads the repaired announcement set (news_events_v2) and writes
to a SEPARATE run dir + pack + store. v1 的产物一个字节都不动 —— 旧 pack 被
config/production_freeze.yaml 冻结着，覆盖它等于伪造历史。
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd

from factors.base import DERIVED, cached_rebalance_dates, load_factor_data
from factors.evaluator import evaluate_factor
from factors.registry import FACTOR_REGISTRY, FACTORS
from factors.selection import select_factor_pack
from factors.reports import leaderboard_df

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = PROJECT_ROOT / "experiments" / "news" / "news_factor_run_001"
#: v2 另开一个 run 目录 —— 实验记录不允许覆盖，旧 pack 还被冻结着。
RUN_DIRS = {
    "v1": RUN_DIR,
    "v2": PROJECT_ROOT / "experiments" / "news" / "news_factor_run_002",
}


def news_factors():
    return sorted(n for n, m in FACTOR_REGISTRY.items()
                  if m["category"] == "news")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--version", default="v1", choices=["v1", "v2"],
                    help="读哪一版新闻数据：v1=原始（SSE 只含定期报告），"
                         "v2=修复 SSE 采集后的重建集")
    args = ap.parse_args()

    version = args.version
    run_dir = RUN_DIRS[version]
    pack_name = f"factor_pack_news_{version}.json"
    store_name = "news_factors.parquet" if version == "v1" \
        else f"news_factors_{version}.parquet"
    if version == "v2":
        from factors.base import set_news_version, news_version

        set_news_version("v2")
        print(f"[news] 使用 news_{news_version()}（修复 SSE 采集后的公告集）")

    import yaml

    cfg = yaml.safe_load((PROJECT_ROOT / "config" / "news_v1.yaml").read_text(
        encoding="utf-8"))["news"]
    labels = pd.read_parquet(DERIVED / "labels.parquet")
    labels = {int(h): g.pivot(index="date", columns="symbol", values="label")
              for h, g in labels.groupby("horizon")}
    univ = pd.read_parquet(DERIVED / "universes.parquet")
    univ["date"] = pd.to_datetime(univ["date"])
    universes = {pd.Timestamp(d): sorted(s) for d, s in
                 univ[univ["universe"] == "full"].groupby("date")["symbol"]}

    ts = cfg["time_split"]
    r_dates = cached_rebalance_dates(ts["research"][0], ts["research"][1])
    v_dates = cached_rebalance_dates(ts["valid"][0], ts["valid"][1])
    t_dates = cached_rebalance_dates(ts["test"][0], ts["test"][1])

    data = load_factor_data("2017-01-01", ts["test"][1])
    print(f"news events: {0 if data.news is None else len(data.news)}, "
          f"coverage symbols: "
          f"{0 if data.news_cov is None else len(data.news_cov)}")

    names = news_factors()
    if args.only:
        names = [n for n in args.only.split(",") if n in names]
    print(f"news factors: {len(names)}")

    cfg_eff = {"labels": {"horizons": [1, 5, 20, 40, 60],
                          "primary_horizon": 20},
               "normalization": {"methods": ["rank", "winsorized_zscore"],
                                 "winsor_sigma": 3.0},
               "missing": {"method": "drop"},
               "evaluation": {"min_stocks_per_date": 30}}

    research, valid, test = {}, {}, {}
    for i, name in enumerate(names):
        research[name] = evaluate_factor(data, name, r_dates, labels,
                                         universes, cfg_eff,
                                         compute=FACTORS[name])
        valid[name] = evaluate_factor(data, name, v_dates, labels,
                                      universes, cfg_eff,
                                      compute=FACTORS[name])
        ric = research[name]["normalizations"]["rank"]["horizons"]["20"][
            "rank_ic"]
        print(f"[{i+1}/{len(names)}] {name}: research rank-ICIR(20d) "
              f"{ric['icir']:+.3f}, coverage {research[name]['coverage']:.2f}",
              flush=True)

    # ---- pack selection: research + valid ONLY --------------------------
    cfg_sel = dict(cfg)
    cfg_sel["selection"] = cfg["selection"]
    corr = pd.DataFrame(index=names, columns=names, dtype=float)
    # correlation computed on the raw panels for redundancy (rank IC basis)
    panels = {}
    for n in names:
        raw = FACTORS[n](data, dates=list(pd.DatetimeIndex(r_dates)))
        panels[n] = raw.reindex(pd.DatetimeIndex(r_dates))
    from factors.evaluator import pairwise_correlation

    corr = pairwise_correlation(panels, method="spearman")
    pack = select_factor_pack(research, valid, corr, cfg_sel)

    # ---- frozen test: single final evaluation (never for selection) -----
    for name in names:
        test[name] = evaluate_factor(data, name, t_dates, labels,
                                     universes, cfg_eff,
                                     compute=FACTORS[name])

    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "evaluations").mkdir(parents=True, exist_ok=True)
    for name in names:
        with open(run_dir / "evaluations" / f"{name}.json", "w",
                  encoding="utf-8") as f:
            json.dump({"research": research[name], "valid": valid[name],
                       "test": test[name]}, f, ensure_ascii=False,
                      default=str)
    (run_dir / pack_name).write_text(
        json.dumps(pack, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")
    lb = leaderboard_df(research, "research")
    lb.to_csv(run_dir / "leaderboard_news.csv", index=False)
    corr.to_csv(run_dir / "correlation_news.csv")

    manifest = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "n_news_factors": len(names),
        "n_selected": len(pack["selected"]),
        "news_events_rows": 0 if data.news is None else len(data.news),
        "news_coverage_symbols": 0 if data.news_cov is None
        else len(data.news_cov),
        "periods": {k: ts[k] for k in ("research", "valid", "test")},
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8")

    print(f"\n{pack_name}: selected {len(pack['selected'])}/"
          f"{len(names)}:")
    print("  " + ", ".join(pack["selected"]))
    for d in pack["discarded"]:
        print(f"  discarded {d['factor']}: {d['reason']}")

    # ---- time-decay half-life study (research period ONLY, spec 26) ------
    from news.decay import HALF_LIFE_CANDIDATES, decay_weights

    ev = data.news.copy() if data.news is not None else pd.DataFrame()
    decay_rows = []
    if not ev.empty:
        ev["avail"] = pd.to_datetime(ev["availability_time"], errors="coerce")
        ev = ev.dropna(subset=["avail"])
        ev["avail"] = ev["avail"].dt.tz_localize(None)
        for hl in HALF_LIFE_CANDIDATES:

            def make_panel(data, dates, hl=hl, ev=ev):
                idx = pd.DatetimeIndex(dates)
                out = pd.DataFrame(index=idx, dtype=float)
                for d in idx:
                    lo = d - pd.Timedelta(days=20)
                    sub = ev[(ev["avail"] <= d) & (ev["avail"] > lo)]
                    if sub.empty:
                        continue
                    ages = (d - sub["avail"]).dt.days.values
                    w = decay_weights(ages.astype(float), hl)
                    vals = pd.Series(w, index=sub["symbol"].values).groupby(
                        level=0).sum()
                    out.loc[d, vals.index] = vals.values
                return out

            res = evaluate_factor(data, "decay_study", r_dates, labels,
                                  universes, cfg_eff, compute=make_panel)
            ric = res["normalizations"]["rank"]["horizons"]["20"]["rank_ic"]
            decay_rows.append({"half_life_days": hl,
                               "research_rank_ic": ric["mean"],
                               "research_icir": ric["icir"],
                               "coverage": res["coverage"]})
            print(f"[decay study] half-life {hl}d: research rank-IC "
                  f"{ric['mean']:+.4f} (ICIR {ric['icir']:+.3f})",
                  flush=True)
    decay_df = pd.DataFrame(decay_rows)
    (run_dir / "decay_study.csv").write_text(
        decay_df.to_csv(index=False) if len(decay_df)
        else "half_life_days,research_rank_ic,research_icir,coverage\n",
        encoding="utf-8")

    # ---- factor store for the selected factors (all signal dates) --------
    all_dates = cached_rebalance_dates("2015-01-01", ts["test"][1])
    store_rows = []
    for name in pack["selected"]:
        panel = FACTORS[name](data, dates=list(pd.DatetimeIndex(all_dates)))
        panel = panel.reindex(pd.DatetimeIndex(all_dates))
        for d in pd.DatetimeIndex(all_dates):
            s = panel.loc[d].dropna()
            for sym, v in s.items():
                store_rows.append({
                    "symbol": sym, "signal_date": d, "factor_name": name,
                    "factor_value": float(v), "source_event_count": None,
                    "lookback_days": None, "decay_half_life": None,
                    "feature_version": "1.0",
                })
    store = pd.DataFrame(store_rows)
    store_dir = PROJECT_ROOT / "data" / "derived" / "news"
    store_dir.mkdir(parents=True, exist_ok=True)
    store.to_parquet(store_dir / store_name, index=False)
    print(f"factor store: {len(store)} rows -> "
          f"{store_dir / store_name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
