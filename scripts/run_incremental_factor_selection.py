# -*- coding: utf-8 -*-
"""Incremental IC Factor Selection Protocol V2 —— 驱动脚本。

    python scripts/run_incremental_factor_selection.py            # 完整两阶段
    python scripts/run_incremental_factor_selection.py --stage-a-only
    python scripts/run_incremental_factor_selection.py --only limit_up_count_20

核心问题（不是"这个因子单独强不强"）：

    把 F 加进已有模型 M0 之后，模型对未来横截面收益的预测信息**是否真的增加**？

评价量是 DeltaIC = IC1 − IC0（配对），不是 IC1。

流程
----
Stage A（2018-2021 研究期快速排除）：coverage / 极端缺失 / 极端数值 /
  极端换手 / PIT 投毒检验 → 至多 20 个进入 Stage B。
Stage B（2018-2023 walk-forward 配对）：4 折逐年外推，每折 M0 与 M1
  严格同数据同参数同种子，唯一差别是 M1 多一列候选因子。

纪律
----
- 选择窗口只有 2018-2023；2024-2025 是 HISTORICAL TEST，任何日期进入
  选择路径都会由 `assert_selection_window` / `assert_not_historical_test`
  直接抛错（tests/factors/test_no_test_usage.py 覆盖）。
- 2026 只登记进 forward holdout，不参与选择。
- 所有阈值/权重来自 config/factor_selection_v2.yaml，不写死在代码里。
- portfolio 收益**不参与**选择，只作 secondary evidence。
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from factors.base import (DERIVED, cached_rebalance_dates, load_calendar,
                          load_factor_data)
from factors.registry import FACTOR_REGISTRY, FACTORS
from incremental import assert_selection_window
from incremental.engine import (PanelStore, build_custom_frames,
                                build_folds, candidate_metrics,
                                delta_ic_table, fit_predict,
                                prediction_impact)
from incremental.holdout import ForwardHoldout
from incremental.redundancy import (_mean_spearman,
                                    redundancy_diagnostics,
                                    residual_ic)
from incremental.stats import block_bootstrap, evaluate_gates, evidence_score
from personal_quant.strategy.features import flatten_columns
from personal_quant.strategy.universe import build_universe

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURE_CACHE = PROJECT_ROOT / "data" / "derived" / "features"
M0_PACKS = [
    ("experiments/factors/factor_run_001/factor_pack_v1.json", "selected"),
    ("experiments/news/news_factor_run_001/factor_pack_news_v1.json",
     "selected"),
]
HORIZON = 20


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------

def load_config() -> dict:
    import yaml
    return yaml.safe_load(
        (PROJECT_ROOT / "config" / "factor_selection_v2.yaml").read_text(
            encoding="utf-8"))


def load_strategy_config() -> dict:
    import yaml
    return yaml.safe_load(
        (PROJECT_ROOT / "config" / "strategy_v1.yaml").read_text(
            encoding="utf-8"))


def load_alpha158(date: pd.Timestamp) -> pd.DataFrame:
    f = FEATURE_CACHE / f"{date.strftime('%Y-%m')}.parquet"
    if not f.exists():
        raise FileNotFoundError(f"Alpha158 缓存缺失 {date:%Y-%m}")
    return flatten_columns(pd.read_parquet(f))


def m0_custom_factors() -> list:
    names = []
    for rel, key in M0_PACKS:
        names += json.loads((PROJECT_ROOT / rel).read_text(
            encoding="utf-8"))[key]
    out, seen = [], set()
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"],
                              capture_output=True, text=True,
                              cwd=PROJECT_ROOT).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# factors
# ---------------------------------------------------------------------------

def compute_panel(data, name: str, dates) -> pd.DataFrame:
    """Raw panel (date × symbol). 归一化在需要时再做——Stage A 要用原始值
    判断极端数值，Stage B 用 rank 归一化值。"""
    raw = FACTORS[name](data, dates=list(pd.DatetimeIndex(dates)))
    return raw.reindex(pd.DatetimeIndex(dates))


def stage_a_stats(panel: pd.DataFrame, label: pd.DataFrame,
                  universes: dict, dates) -> dict:
    cov, ic = [], []
    for d in dates:
        univ = universes.get(d)
        if not univ:
            continue
        x = panel.loc[d].reindex(univ)
        cov.append(float(x.notna().mean()))
        y = label.loc[d].reindex(univ) if d in label.index else None
        if y is None:
            continue
        m = pd.concat([x.rename("f"), y.rename("l")], axis=1).dropna()
        if len(m) < 30 or m["f"].std() == 0 or m["l"].std() == 0:
            continue
        ic.append(m["f"].corr(m["l"], method="spearman"))
    ic = pd.Series(ic, dtype=float).dropna()
    sd = ic.std(ddof=0)
    return {
        "coverage": float(np.mean(cov)) if cov else 0.0,
        "raw_ic_mean": float(ic.mean()) if len(ic) else np.nan,
        "raw_icir": float(ic.mean() / sd) if len(ic) and sd > 0 else np.nan,
        "n_dates": int(len(ic)),
    }


def factor_turnover(panel: pd.DataFrame, dates, universes: dict,
                    top_frac: float = 0.2) -> float:
    """Top-20% 名单在两个信号日之间的平均换手。"""
    prev = None
    vals = []
    for d in dates:
        univ = universes.get(d)
        if not univ:
            continue
        x = panel.loc[d].reindex(univ).dropna()
        if x.empty:
            continue
        k = max(int(len(x) * top_frac), 1)
        cur = set(x.nlargest(k).index)
        if prev is not None:
            denom = len(prev | cur)
            if denom:
                vals.append(1 - len(prev & cur) / denom)
        prev = cur
    return float(np.mean(vals)) if vals else np.nan


def extreme_value_ratio(panel: pd.DataFrame, dates, universes: dict,
                        max_z: float) -> float:
    """|值 − 截面中位数| > max_z × MAD 的占比（极端数值检查）。"""
    hits, total = 0, 0
    for d in dates:
        univ = universes.get(d)
        if not univ:
            continue
        x = panel.loc[d].reindex(univ).dropna()
        if len(x) < 30:
            continue
        mad = (x - x.median()).abs().median()
        if mad <= 0:
            continue
        hits += int(((x - x.median()).abs() > max_z * mad).sum())
        total += len(x)
    return float(hits / total) if total else np.nan


def pit_check(name: str, t: pd.Timestamp, horizon: int) -> tuple:
    """未来数据投毒：把 t 之后的所有行乘 7 加 3，重算因子，值必须不变。

    §32 要求的 "no future leakage" 实测。用一段紧凑窗口跑真实数据，
    而不是只信 registry 里的 pit 标记。
    """
    import copy
    start = (t - pd.Timedelta(days=400)).strftime("%Y-%m-%d")
    end = (t + pd.Timedelta(days=200)).strftime("%Y-%m-%d")
    data = load_factor_data(start, end)
    intact = FACTORS[name](data, dates=[t])
    t2 = copy.deepcopy(data)
    mask = t2.calendar > t
    for attr in ("adj_close", "close_raw", "volume_raw", "volume_shares",
                 "amount_cny"):
        fr = getattr(t2, attr)
        fr.loc[mask] = fr.loc[mask] * 7.0 + 3.0
    if len(t2.bars):
        bm = t2.bars["trade_date"] > t
        for c in ("open", "high", "low", "close", "volume", "amount"):
            if c in t2.bars.columns:
                t2.bars.loc[bm, c] = t2.bars.loc[bm, c] * 7.0 + 3.0
    corrupted = FACTORS[name](t2, dates=[t])
    a = intact.iloc[0] if len(intact) else pd.Series(dtype=float)
    b = corrupted.iloc[0] if len(corrupted) else pd.Series(dtype=float)
    both = pd.concat([a, b], axis=1).dropna()
    if both.empty:
        return True, "no comparable values"
    same = np.allclose(both.iloc[:, 0], both.iloc[:, 1], rtol=1e-9,
                       atol=1e-12)
    if same:
        return True, f"{len(both)} 只标的通过投毒检验"
    bad = int((~np.isclose(both.iloc[:, 0], both.iloc[:, 1], rtol=1e-9)).sum())
    return False, f"{bad}/{len(both)} 只标的值随未来数据改变"


# ---------------------------------------------------------------------------
# stage A
# ---------------------------------------------------------------------------

def run_stage_a(cfg, panels, label, universes, research_dates) -> pd.DataFrame:
    a = cfg["factor_selection_v2"]["stage_a"]
    rows = []
    t_pit = pd.Timestamp(a["pit_check_window"][1]) - pd.Timedelta(days=180)
    for name, panel in panels.items():
        st = stage_a_stats(panel, label, universes, research_dates)
        rows.append({
            "factor": name,
            "category": FACTOR_REGISTRY[name]["category"],
            **st,
            "turnover": factor_turnover(panel, research_dates, universes),
            "extreme_ratio": extreme_value_ratio(
                panel, research_dates, universes, float(a["max_abs_value_z"])),
            "pit_pass": None, "pit_note": "",
        })
    tab = pd.DataFrame(rows)
    if a.get("pit_check"):
        for i, r in tab.iterrows():
            ok, note = pit_check(r["factor"], t_pit, HORIZON)
            tab.at[i, "pit_pass"] = ok
            tab.at[i, "pit_note"] = note
    return tab


def stage_a_select(tab: pd.DataFrame, cfg: dict) -> tuple:
    a = cfg["factor_selection_v2"]["stage_a"]
    reasons = {}
    ok = []
    for _, r in tab.iterrows():
        f = r["factor"]
        if np.isfinite(r["coverage"]) is False:
            reasons[f] = "coverage 无法计算"
        elif r["coverage"] < float(a["min_coverage"]):
            reasons[f] = f"coverage {r['coverage']:.2f} < {a['min_coverage']}"
        elif not np.isfinite(r["raw_icir"]) or abs(r["raw_icir"]) < 1e-9:
            reasons[f] = "IC 无法计算"
        elif np.isfinite(r["turnover"]) and r["turnover"] > float(a["max_turnover"]):
            reasons[f] = f"turnover {r['turnover']:.2f} > {a['max_turnover']}"
        elif (np.isfinite(r["extreme_ratio"]) and
              r["extreme_ratio"] > float(a["max_extreme_ratio"])):
            reasons[f] = (f"极端数值占比 {r['extreme_ratio']:.3f} > "
                          f"{a['max_extreme_ratio']}")
        elif r["pit_pass"] is False:
            reasons[f] = f"PIT FAIL: {r['pit_note']}"
        else:
            ok.append(f)
    keep = sorted(ok, key=lambda f: -abs(
        float(tab.set_index("factor").loc[f, "raw_icir"])))
    cap = int(a["max_candidates_to_stage_b"])
    dropped = keep[cap:]
    keep = keep[:cap]
    for f in dropped:
        reasons[f] = f"Stage A 通过但超出前 {cap}（按 |raw ICIR| 排序）"
    return keep, reasons


# ---------------------------------------------------------------------------
# stage B
# ---------------------------------------------------------------------------

def run_stage_b(cfg, store, folds, base_cols, candidates) -> dict:
    b = cfg["factor_selection_v2"]["stage_b"]
    bs = b["bootstrap"]
    out = {}
    m0_cache = {}
    for fold in folds:
        if len(fold.valid_dates) < int(b["min_dates_per_fold"]):
            print(f"  [warn] {fold.name} 有效信号日只有 "
                  f"{len(fold.valid_dates)} 个，仍继续但结果不可靠")
        res = fit_predict(store, fold, base_cols, cfg)
        m0_cache[fold.name] = res
        print(f"  M0 {fold.name}: train {res['n_train_rows']} 行, "
              f"valid {len(res['prediction'])} 条预测", flush=True)

    for i, name in enumerate(candidates, 1):
        fold_ics, impacts, per_fold_pred = {}, [], {}
        for fold in folds:
            res0 = m0_cache[fold.name]
            try:
                res1 = fit_predict(store, fold, list(base_cols) + [name], cfg)
            except RuntimeError as e:
                print(f"  [skip] {name} {fold.name}: {e}")
                continue
            if res1["prediction"].empty or res0["prediction"].empty:
                continue
            ic = delta_ic_table(res0["prediction"], res1["prediction"])
            fold_ics[fold.name] = ic
            impacts.append(prediction_impact(res0["prediction"],
                                             res1["prediction"]))
            per_fold_pred[fold.name] = res1["prediction"].assign(fold=fold.name)
            gain = res1["importance"]
            out.setdefault("_importance", {}).setdefault(name, {})[
                fold.name] = {
                "candidate_gain_share": float(
                    gain.get(name, 0.0) / gain.sum()) if gain.sum() else np.nan,
                "candidate_gain_rank": int(
                    gain.rank(ascending=False).get(name, np.nan))
                if np.isfinite(gain.get(name, np.nan)) else None,
            }
        m = candidate_metrics(fold_ics, impacts)
        m["factor"] = name
        if m.get("n_dates"):
            m["bootstrap"] = block_bootstrap(
                m["ic_series"]["delta_ic"],
                block=int(bs["block_months"]),
                n_resamples=int(bs["n_resamples"]),
                confidence=float(bs["confidence"]),
                seed=int(bs["seed"]))
        else:
            m["bootstrap"] = {}
        out[name] = m
        out.setdefault("_fold_predictions", {})[name] = per_fold_pred
        print(f"  [{i}/{len(candidates)}] {name}: "
              f"dIC={m.get('delta_ic_mean', float('nan')):+.4f} "
              f"dRankIC={m.get('delta_rank_ic_mean', float('nan')):+.4f} "
              f"CI=[{m['bootstrap'].get('ci_low', float('nan')):+.4f},"
              f"{m['bootstrap'].get('ci_high', float('nan')):+.4f}]",
              flush=True)
    return out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage-a-only", action="store_true")
    ap.add_argument("--only", default=None,
                    help="跳过 Stage A，直接测这些因子（逗号分隔，调试用）")
    ap.add_argument("--max-candidates", type=int, default=None)
    args = ap.parse_args()

    cfg = load_config()
    scfg = load_strategy_config()
    spec = cfg["factor_selection_v2"]
    outdir = PROJECT_ROOT / spec["output"]["dir"]
    outdir.mkdir(parents=True, exist_ok=True)

    calendar = load_calendar()
    reb = cached_rebalance_dates(*spec["selection_window"])
    assert_selection_window(reb, "rebalance dates")
    folds = build_folds(cfg, calendar, reb, HORIZON)
    all_dates = sorted({d for f in folds for d in f.train_dates + f.valid_dates})
    research_dates = [d for d in all_dates
                      if d <= pd.Timestamp(spec["stage_a"]["window"][1])]
    print(f"折: {[(f.name, len(f.train_dates), len(f.valid_dates)) for f in folds]}")
    print(f"信号日合计 {len(all_dates)}（research {len(research_dates)}）")

    m0 = m0_custom_factors()
    print(f"M0 自定义因子 ({len(m0)}): {m0}")

    print("加载股票池 / Alpha158 / 标签 ...", flush=True)
    universes = {d: build_universe(d, scfg)["symbol"].tolist()
                 for d in all_dates}
    features = {d: load_alpha158(d).reindex(universes[d]) for d in all_dates}
    lab = pd.read_parquet(DERIVED / "labels.parquet")
    lab = lab[lab["horizon"] == HORIZON].pivot(
        index="date", columns="symbol", values="label")
    lab.index = pd.to_datetime(lab.index)
    label = {d: lab.loc[d] for d in all_dates if d in lab.index}

    names = sorted(FACTOR_REGISTRY)
    if args.only:
        names = [n for n in args.only.split(",") if n in FACTOR_REGISTRY]
    else:
        names = [n for n in names if n not in m0]
    print(f"候选因子 {len(names)}（已排除 M0 已有的 {len(m0)} 个）")

    print("计算因子面板 ...", flush=True)
    data = load_factor_data("2014-06-01", spec["selection_window"][1])
    panels = {n: compute_panel(data, n, all_dates) for n in set(names) | set(m0)}
    print(f"  {len(panels)} 个面板", flush=True)

    # ---------------------------------------------------------- Stage A
    tab = run_stage_a(cfg, {n: panels[n] for n in names}, lab, universes,
                      research_dates)
    tab.to_csv(outdir / "stage_a_screen.csv", index=False)
    if args.only:
        keep, reasons = list(names), {}
    else:
        keep, reasons = stage_a_select(tab, cfg)
    if args.max_candidates:
        keep = keep[:args.max_candidates]
    print(f"\nStage A: {len(keep)} 个进入 Stage B -> {keep}")
    (outdir / "stage_a_rejected.json").write_text(
        json.dumps(reasons, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.stage_a_only:
        print("--stage-a-only：停在这里。")
        return 0

    # ---------------------------------------------------------- 设计矩阵
    need = sorted(set(m0) | set(keep))
    custom = build_custom_frames(panels, universes, all_dates, need)
    # 特征必须真的进了矩阵：常数列的 DeltaIC 会精确等于 0，看起来像
    # "这个因子没用"，其实是列退化了（这个坑踩过两次）。
    bad = []
    for n in need:
        const = [d for d in all_dates
                 if d in custom and n in custom[d]
                 and custom[d][n].notna().sum() > 10
                 and custom[d][n].std() == 0]
        if const:
            bad.append(f"{n}（{len(const)}/{len(all_dates)} 个日期为常数，"
                       f"如 {const[0].date()}）")
    if bad:
        raise RuntimeError(
            "设计矩阵里有常数因子列 —— 特征构建有误，DeltaIC 会假性为 0："
            + "；".join(bad))
    print(f"设计矩阵自定义因子 {len(need)} 列，已校验非常数")
    store = PanelStore(features=features, custom=custom, labels=label,
                       universes=universes)
    base_cols = list(features[all_dates[0]].columns) + list(m0)

    # ---------------------------------------------------------- Stage B
    print(f"\nStage B: {len(keep)} 个候选 × {len(folds)} 折配对回测 ...",
          flush=True)
    results = run_stage_b(cfg, store, folds, base_cols, keep)

    # ---------------------------------------------------- 冗余 + 打分
    # 冗余的两个判据必须对**同一个**"既有信息集"计算，否则 require_both
    # 是在拿苹果比橘子：原始秩相关看的是 M0 的 10 个自定义因子，
    # 而回归 R² 若只喂 Alpha158，就会漏掉"候选 ≈ 某个既有自定义因子"
    # 这种最典型的冗余（实测 amihud_20 与 amount_20 秩相关 0.92，
    # 但只对 Alpha158 回归时 R² 仅 0.47，于是逃过了判据）。
    feat_by_date = {d: pd.concat([features[d], custom[d][m0]], axis=1)
                    for d in all_dates}
    rows, ric_series, fold_rows, ic_rows = [], {}, [], []
    all_needed = sorted(set(m0) | set(keep))
    for name in keep:
        m = results.get(name) or {}
        if not m.get("n_dates"):
            continue
        panel = panels[name]
        rd = redundancy_diagnostics(panel, {k: panels[k] for k in m0},
                                    feat_by_date, cfg)
        m.update(rd)
        ric = residual_ic(panel, feat_by_date, lab, min_stocks=30)
        m["residual_ic_mean"] = ric["residual_ic_mean"]
        m["residual_icir"] = ric["residual_icir"]
        ric_series[name] = ric["residual_ic_series"]
        m["coverage"] = float(tab.set_index("factor").loc[name, "coverage"])
        m["turnover"] = float(tab.set_index("factor").loc[name, "turnover"])
        m["raw_icir"] = float(tab.set_index("factor").loc[name, "raw_icir"])
        m["raw_ic_mean"] = float(tab.set_index("factor").loc[name, "raw_ic_mean"])
        pit_ok = bool(tab.set_index("factor").loc[name, "pit_pass"])
        es = evidence_score(m, cfg)
        g = evaluate_gates(m, cfg, pit_pass=pit_ok, redundant=rd["redundant"])
        m.update(es)
        m.update(g)
        rows.append(m)

    res = pd.DataFrame([{k: v for k, v in r.items()
                         if k not in ("ic_series", "per_fold", "components",
                                      "gates", "bootstrap",
                                      "corr_with_existing")}
                        for r in rows])
    bs_rows = [{"factor": r["factor"], **(r.get("bootstrap") or {})}
               for r in rows if r.get("bootstrap")]
    if bs_rows:
        pd.DataFrame(bs_rows).to_csv(outdir / "bootstrap.csv", index=False)

    # 交付给报告的候选表（§33 要求的字段名，一份不重命名两次）
    bs_by = {b["factor"]: b for b in bs_rows}
    out_rows = []
    for r in rows:
        b = bs_by.get(r["factor"], {})
        out_rows.append({
            "factor": r["factor"],
            "research_ic": r.get("raw_ic_mean"),
            "research_icir": r.get("raw_icir"),
            "incremental_ic": r.get("delta_ic_mean"),
            "incremental_rank_ic": r.get("delta_rank_ic_mean"),
            "incremental_icir": r.get("delta_icir"),
            "residual_ic": r.get("residual_ic_mean"),
            "residual_icir": r.get("residual_icir"),
            "positive_fold_ratio": r.get("positive_fold_ratio"),
            "positive_month_ratio": r.get("delta_ic_positive_ratio"),
            "bootstrap_ci_low": b.get("ci_low"),
            "bootstrap_ci_high": b.get("ci_high"),
            "iid_ci_low": b.get("iid_ci_low"),
            "iid_ci_high": b.get("iid_ci_high"),
            "max_corr_existing": r.get("max_corr_existing"),
            "r2_existing": r.get("r2_existing"),
            "prediction_corr": r.get("prediction_corr"),
            "prediction_delta": r.get("prediction_delta"),
            "topk_turnover": r.get("topk_turnover"),
            "coverage": r.get("coverage"),
            "turnover": r.get("turnover"),
            "evidence_score": r.get("evidence_score"),
            "gates_passed": r.get("gates_passed"),
            "status": r.get("status"),
        })
    cand_csv = PROJECT_ROOT / spec["output"]["candidates_csv"]
    cand_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(out_rows).to_csv(cand_csv, index=False)
    print(f"候选表 -> {cand_csv}")
    res = res.sort_values("evidence_score", ascending=False)
    res.to_csv(outdir / "candidate_metrics.csv", index=False)

    # 每折 DeltaIC（§6 / 稳定性图）、逐日 DeltaIC（§34 分布图）、
    # 原始因子相关矩阵（§10 冗余图，主判据）、残差 IC（§19 辅助）
    for name in keep:
        mm = results.get(name) or {}
        for fname, fv in (mm.get("per_fold") or {}).items():
            fold_rows.append({"factor": name, "fold": fname, **fv})
        ics = mm.get("ic_series")
        if ics is not None and not ics.empty:
            ic_rows.append(ics.assign(factor=name))
        if name in ric_series and len(ric_series[name]):
            s2 = ric_series[name]
            ic_rows.append(pd.DataFrame({
                "factor": name, "date": s2.index.to_numpy(),
                "residual_ic": s2.to_numpy()}))
    if fold_rows:
        pd.DataFrame(fold_rows).to_csv(outdir / "per_fold.csv", index=False)
    if ic_rows:
        pd.concat(ic_rows, ignore_index=True).to_csv(
            outdir / "delta_ic_series.csv", index=False)
    # 主判据是**原始因子**秩相关（§10）——不是残差相关
    cm = pd.DataFrame(index=all_needed, columns=all_needed, dtype=float)
    for i, a in enumerate(all_needed):
        for b in all_needed[i + 1:]:
            c = _mean_spearman(panels[a], panels[b])
            cm.loc[a, b] = cm.loc[b, a] = c
    np.fill_diagonal(cm.values, 1.0)
    cm.to_csv(outdir / "redundancy_matrix.csv")

    # ------------------------------------------------------- 最终候选
    n_final = int(spec["final"]["max_candidates"])
    final = res[(res["status"] == "PASS")].head(n_final)["factor"].tolist() \
        if "status" in res.columns else []
    (outdir / "final_candidates.json").write_text(
        json.dumps({
            "candidates": final,
            "status": spec["final"]["status"],
            "note": "research candidate；不得直接进入 strategy_v2",
            "selected_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    # ------------------------------------------------------- manifest
    manifest = {
        "protocol": spec["protocol_name"],
        "version": spec["version"],
        "selected_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "config_sha256": __import__("hashlib").sha256(
            (PROJECT_ROOT / "config" / "factor_selection_v2.yaml")
            .read_bytes()).hexdigest(),
        "data_snapshot": {"features": "data/derived/features",
                          "label": "data/derived/factors/labels.parquet"},
        "selection_window": spec["selection_window"],
        "forbidden_window": spec["forbidden_window"],
        "model": spec["model"],
        "folds": [f.as_dict() for f in folds],
        "m0_features": {"alpha158": f"{len(base_cols) - len(m0)} 列",
                        "custom": m0},
        "stage_a_kept": keep,
        "stage_a_rejected": reasons,
        "final_candidates": final,
        "n_candidates_tested": len(rows),
        "historical_test_status": (
            "2024-2025 已被评估多次（STEP 6 终评、step8、step9），"
            "降级为 HISTORICAL TEST，本轮未使用其任何数据"),
        "forward_holdout_start": spec["forward_holdout_start"],
    }
    (PROJECT_ROOT / spec["final"]["manifest"]).parent.mkdir(
        parents=True, exist_ok=True)
    (PROJECT_ROOT / spec["final"]["manifest"]).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")

    holdout = ForwardHoldout.load(cfg)
    holdout.save()

    print("\n===== Incremental IC 排行（DeltaIC 降序）=====")
    cols = ["factor", "raw_icir", "delta_ic_mean", "delta_rank_ic_mean",
            "delta_icir", "positive_fold_ratio", "bootstrap_ci_low",
            "bootstrap_ci_high", "prediction_corr", "r2_existing",
            "max_corr_existing", "evidence_score", "status"]
    show = res.copy()
    show["bootstrap_ci_low"] = [r.get("bootstrap", {}).get("ci_low")
                                for r in rows]
    show["bootstrap_ci_high"] = [r.get("bootstrap", {}).get("ci_high")
                                 for r in rows]
    print(show[[c for c in cols if c in show.columns]].to_string(index=False))
    print(f"\n最终候选（research candidate）：{final}")
    print(f"产物目录：{outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
