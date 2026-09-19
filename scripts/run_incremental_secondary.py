# -*- coding: utf-8 -*-
"""次要证据（secondary evidence）：ADD / REPLACE 与特征重要性（§18 / §21）。

    python scripts/run_incremental_secondary.py

**这些结果不参与因子选择。** 选择只看主协议的 incremental IC（§16）。
本脚本回答的是"选中之后能解释什么"：

§18  ADD     : M0 + F                （= 主协议，这里复核）
     REPLACE : M0 − 最相关的既有因子 + F
     先 ADD 再 REPLACE —— 先确认 F 真的带来增量，再谈能不能替掉谁。

§21  比较 M0 与 M1_F 的 LightGBM gain 重要性，并对候选列做置换重要性。
     **importance != alpha evidence**，只作解释。

纪律：仍然只用 2018-2023；不碰 2024-2025；不重训以外的任何东西。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import numpy as np
import pandas as pd

import run_incremental_factor_selection as drv          # 复用加载逻辑
from factors.base import DERIVED, cached_rebalance_dates, load_calendar
from incremental.engine import (PanelStore, build_custom_frames, build_folds,
                                delta_ic_table, fit_predict,
                                permutation_importance)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    cfg = drv.load_config()
    scfg = drv.load_strategy_config()
    spec = cfg["factor_selection_v2"]
    outdir = PROJECT_ROOT / spec["output"]["dir"]

    final_path = outdir / "final_candidates.json"
    if not final_path.exists():
        print("先跑主协议：scripts/run_incremental_factor_selection.py")
        return 1
    final = json.loads(final_path.read_text(encoding="utf-8"))["candidates"]
    m0 = drv.m0_custom_factors()
    print(f"最终候选（{len(final)}）: {final}")

    calendar = load_calendar()
    reb = cached_rebalance_dates(*spec["selection_window"])
    folds = build_folds(cfg, calendar, reb, drv.HORIZON)
    all_dates = sorted({d for f in folds
                        for d in f.train_dates + f.valid_dates})

    from personal_quant.strategy.universe import build_universe
    universes = {d: build_universe(d, scfg)["symbol"].tolist()
                 for d in all_dates}
    features = {d: drv.load_alpha158(d).reindex(universes[d])
                for d in all_dates}
    lab = pd.read_parquet(DERIVED / "labels.parquet")
    lab = lab[lab["horizon"] == drv.HORIZON].pivot(
        index="date", columns="symbol", values="label")
    lab.index = pd.to_datetime(lab.index)
    label = {d: lab.loc[d] for d in all_dates if d in lab.index}

    data = drv.load_factor_data("2014-06-01", spec["selection_window"][1])
    need = sorted(set(m0) | set(final))
    panels = {n: drv.compute_panel(data, n, all_dates) for n in need}
    custom = build_custom_frames(panels, universes, all_dates, need)
    store = PanelStore(features=features, custom=custom, labels=label,
                       universes=universes)
    base_cols = list(features[all_dates[0]].columns) + list(m0)

    # 每个候选的"替换对象"：与它原始秩相关最高的既有因子
    corr = pd.read_csv(outdir / "redundancy_matrix.csv", index_col=0) \
        if (outdir / "redundancy_matrix.csv").exists() else pd.DataFrame()
    victim = {}
    for f in final:
        if f in corr.index:
            sub = corr.loc[f, [c for c in m0 if c in corr.columns]]
            victim[f] = sub.abs().idxmax() if len(sub) else None
    print(f"替换对象: {victim}")

    rows, imp_rows = [], []
    for fold in folds:
        r0 = fit_predict(store, fold, base_cols, cfg)
        g0 = r0["importance"] / max(r0["importance"].sum(), 1e-12)
        for name in final:
            r1 = fit_predict(store, fold, base_cols + [name], cfg)
            g1 = r1["importance"] / max(r1["importance"].sum(), 1e-12)
            add_ic = delta_ic_table(r0["prediction"], r1["prediction"])
            perm = permutation_importance(store, fold, r1,
                                          base_cols + [name], name)
            rep_ic = None
            v = victim.get(name)
            if v:
                rep_cols = [c for c in base_cols if c != v] + [name]
                r2 = fit_predict(store, fold, rep_cols, cfg)
                rep_ic = delta_ic_table(r0["prediction"], r2["prediction"])
            rows.append({
                "fold": fold.name, "factor": name, "replaced": v,
                "add_delta_ic": float(add_ic["delta_ic"].mean())
                if len(add_ic) else np.nan,
                "replace_delta_ic": float(rep_ic["delta_ic"].mean())
                if rep_ic is not None and len(rep_ic) else np.nan,
                "add_delta_rank_ic": float(add_ic["delta_rank_ic"].mean())
                if len(add_ic) else np.nan,
                "replace_delta_rank_ic": float(rep_ic["delta_rank_ic"].mean())
                if rep_ic is not None and len(rep_ic) else np.nan,
                **perm,
            })
            imp_rows.append({
                "fold": fold.name, "factor": name,
                "m0_top_gain_share": float(g0.nlargest(1).iloc[0]),
                "m1_top_feature": str(g1.nlargest(1).index[0]),
                "gain_share_rank_of_candidate": int(
                    g1.rank(ascending=False).get(name, -1)),
                "n_features_m1": int(len(g1)),
                "candidate_gain_share": float(g1.get(name, 0.0)),
            })
            print(f"  {fold.name} {name}: ADD dIC="
                  f"{rows[-1]['add_delta_ic']:+.4f}  REPLACE({v}) dIC="
                  f"{rows[-1]['replace_delta_ic']:+.4f}  "
                  f"置换 IC 降幅={perm.get('permutation_ic_drop', float('nan')):+.4f}",
                  flush=True)

    sec = pd.DataFrame(rows)
    imp = pd.DataFrame(imp_rows)
    sec.to_csv(outdir / "secondary_add_replace.csv", index=False)
    imp.to_csv(outdir / "secondary_importance.csv", index=False)

    print("\n===== ADD vs REPLACE（frozen 2018-2023 walk-forward）=====")
    agg = sec.groupby("factor").agg(
        add_delta_ic=("add_delta_ic", "mean"),
        replace_delta_ic=("replace_delta_ic", "mean"),
        add_delta_rank_ic=("add_delta_rank_ic", "mean"),
        replace_delta_rank_ic=("replace_delta_rank_ic", "mean"),
        permutation_ic_drop=("permutation_ic_drop", "mean"),
        replaced=("replaced", "first")).sort_values("add_delta_ic",
                                                    ascending=False)
    print(agg.round(5).to_string())
    print("\n注：importance / permutation 只是解释，不是 alpha 证据（§21）；"
          "它们不参与选择（§16）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
