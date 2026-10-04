# -*- coding: utf-8 -*-
"""独立信息研究（incremental information）—— 为什么"大量加入反而变差"。

    python scripts/research_independent_info.py            # 完整分析
    python scripts/research_independent_info.py --only limit_up_count_20

问题
----
微结构因子消融（reports/步骤8-微结构因子.md）显示：
  S3 = Alpha158 + pack_v1 + news            年化 0.2812 / Sharpe 1.022
  N  = S3 + 5 个新因子（直接叠加）            年化 0.1592 / Sharpe 0.657  ← 崩了
  M  = Alpha158 + 11 个因子（换掉一部分）     年化 0.3053 / Sharpe 1.148  ← 反而好
同样一批新因子，**叠加**变差、**替换**变好。假设：问题不是"信息不够"，
而是"信息不独立"——新因子与既有特征高度共线，模型在训练集上把分裂
方差分给了噪声方向，样本外退化。

度量（每个候选因子 c、每个信号日 t，只看当日横截面，天然 PIT）
------------------------------------------------------------
  x_t = rank(c)                      股票池横截面百分位，缺失填中位数（中性）
  Z_t = rank([Alpha158 158 列, S3 的 10 个自定义因子])
  r_t = x_t − Z_t β                  β 由最小二乘（伪逆）给出，
                                     r_t 即"既有信息解释不掉的部分"
  R²_t = 1 − var(r_t)/var(x_t)       c 被既有信息解释的比例
  raw_IC_t   = spearman(x_t, 未来 20 日收益)
  resid_IC_t = spearman(r_t, 未来 20 日收益)

汇总：raw ICIR / resid ICIR / 平均 R²（research 2018-2021 定选，
valid 2022-2023 复核）。两者都在同一横截面上计算，唯一差别就是正交化。

选择协议（**先于结果写死，不得看结果改**）
----------------------------------------
  G1 coverage >= 0.6
  G2 |research resid ICIR| >= 0.3
  G3 方向一致率 max(P(IC>0), P(IC<0)) >= 0.5（resid IC 序列）
  G4 research 与 valid 的 resid IC 均值同号
  G5 残差相关性聚类 |corr| >= 0.8，每簇只留 |resid ICIR| 最强的
  G6 最多保留 5 个（刻意保持小规模——N 的教训就是"多"）
  通过 G2-G5 的因子 < 3 个 → 如实报告并放弃消融。

对照消融（脚本只产出因子清单，回测走同一个引擎）
----------------------------------------------
  S3  冻结基线（锚点 0.2812 / 1.022，必须复现）
  I   S3 + 独立信息包      （resid ICIR 最强）
  R   S3 + "强但冗余"对照   （被 G2 拒绝者中 raw ICIR 最强的等量因子）
  I vs R 只差"独立性"，数量与构造方式相同 —— 分离"独立性"与"原始强度"。

纪律
----
- 选择只用 research + valid；frozen test 2024-2025 只做一次最终确认。
- **snooping 披露**：test 集在此之前已被评估过 2 次（STEP 6 终评、
  step8 微结构消融）。每多看一眼，假阳性的概率就高一分，报告必须写明。
- 2026 paper live 永远不进入本脚本。
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from factors.base import DERIVED, cached_rebalance_dates, load_factor_data
from factors.normalization import normalize_panel
from factors.registry import FACTOR_REGISTRY, FACTORS
from personal_quant.strategy.features import flatten_columns, read_feature_cache
from personal_quant.strategy.universe import build_universe

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT = PROJECT_ROOT / "experiments" / "factors" / "independent_info"
# 本脚本只产出**数据表**（run artifact）；结论与解读写在
# reports/步骤9-独立信息研究.md，不由此脚本覆盖。
REPORT = OUT / "tables.md"
S3_PACK = [
    ("experiments/factors/factor_run_001/factor_pack_v1.json", "selected"),
    ("experiments/news/news_factor_run_001/factor_pack_news_v1.json",
     "selected"),
]

# --- 协议常量（写死；改动 = 新开 run 并在报告中说明）----------------------
MIN_COVERAGE = 0.6
MIN_RESID_ICIR = 0.3
MIN_DIR_CONSISTENCY = 0.5
CLUSTER_THRESHOLD = 0.8
MAX_PACK = 5
MIN_STOCKS = 30
HORIZON = 20
RESEARCH = ("2018-01-01", "2021-12-31")
VALID = ("2022-01-01", "2023-12-31")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _rank_cross_section(frame: pd.DataFrame) -> pd.DataFrame:
    """Rank each COLUMN across the stocks of the day (symbols are rows).

    axis=0 is essential: `rank(axis=1)` would rank across *features* within
    one stock, and on a single-column frame it degenerates to a constant —
    which silently turns the candidate into a missing-data indicator.
    """
    return frame.rank(axis=0, pct=True, method="average")


def _corr_cols(mat: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Pearson correlation of every column of `mat` with the vector `y`."""
    m = mat - mat.mean(axis=0, keepdims=True)
    yc = y - y.mean()
    num = m.T @ yc
    den = np.sqrt((m ** 2).sum(axis=0)) * np.sqrt((yc ** 2).sum())
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


def _spearman_cols(mat: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Column-wise Spearman = Pearson on ranks."""
    mr = pd.DataFrame(mat).rank(axis=0).to_numpy()
    return _corr_cols(mr, pd.Series(y).rank().to_numpy())


def _summary(series: pd.Series) -> dict:
    s = series.dropna()
    if s.empty:
        return {"n": 0, "mean": np.nan, "icir": np.nan, "consistency": np.nan}
    sd = s.std(ddof=0)
    return {
        "n": int(len(s)),
        "mean": float(s.mean()),
        "icir": float(s.mean() / sd) if sd > 0 else np.nan,
        "consistency": float(max((s > 0).mean(), (s < 0).mean())),
    }


def _load_alpha158(date: pd.Timestamp) -> pd.DataFrame:
    """读按**日期**存档的特征缓存（feature_YYYY-MM-DD.parquet）。

    这里以前自己拼 `YYYY-MM.parquet`（按月）的路径、不做日期校验 ——
    同月不同日会互相覆盖，读到的是"该月最后一次写入的那一天"。
    现在统一走 `read_feature_cache`：任何日期不自洽都视为未命中。
    """
    sub = read_feature_cache(date)
    if sub is None:
        raise FileNotFoundError(
            f"Alpha158 缓存缺失 {pd.Timestamp(date):%Y-%m-%d}"
            f"（按日期存档）；先跑一次 scripts/backtest_strategy.py 生成 "
            f"data/derived/features/feature_YYYY-MM-DD.parquet")
    return flatten_columns(sub)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None,
                    help="逗号分隔的因子子集（调试用）")
    ap.add_argument("--min-dates", type=int, default=None,
                    help="只跑前 N 个日期（调试用）")
    args = ap.parse_args()

    import yaml

    cfg = yaml.safe_load(
        (PROJECT_ROOT / "config" / "strategy_v1.yaml").read_text(
            encoding="utf-8"))

    r_dates = cached_rebalance_dates(*RESEARCH)
    v_dates = cached_rebalance_dates(*VALID)
    all_dates = sorted(set(r_dates + v_dates))
    if args.min_dates:
        all_dates = all_dates[:args.min_dates]
        r_dates = [d for d in r_dates if d in all_dates]
        v_dates = [d for d in v_dates if d in all_dates]

    s3_custom = []
    for rel, key in S3_PACK:
        s3_custom += json.loads(
            (PROJECT_ROOT / rel).read_text(encoding="utf-8"))[key]
    print(f"S3 自定义因子 ({len(s3_custom)}): {s3_custom}")

    names = sorted(FACTOR_REGISTRY)
    if args.only:
        names = [n for n in args.only.split(",") if n in FACTOR_REGISTRY]
    print(f"候选因子: {len(names)}；信号日: research {len(r_dates)} + "
          f"valid {len(v_dates)}")

    print("加载股票池 ...", flush=True)
    universes = {d: build_universe(d, cfg)["symbol"].tolist()
                 for d in all_dates}
    print(f"  平均股票池 {np.mean([len(v) for v in universes.values()]):.0f} 只")

    labels = pd.read_parquet(DERIVED / "labels.parquet")
    labels = labels[labels["horizon"] == HORIZON].pivot(
        index="date", columns="symbol", values="label")
    labels.index = pd.to_datetime(labels.index)

    print("计算候选因子面板 ...", flush=True)
    data = load_factor_data("2014-06-01", VALID[1])
    panels = {}
    for name in names:
        raw = FACTORS[name](data, dates=list(pd.DatetimeIndex(all_dates)))
        panels[name] = raw.reindex(pd.DatetimeIndex(all_dates))
    print(f"  {len(panels)} 个面板", flush=True)

    # per-date cross-section: raw rank-IC, residual rank-IC, R²
    per_date: dict = {n: {"date": [], "raw_ic": [], "resid_ic": [],
                          "r2": [], "coverage": [], "n": []}
                      for n in names}
    resid_panels: dict = {n: {} for n in names}

    for i, d in enumerate(all_dates):
        univ = universes[d]
        y = labels.loc[d].reindex(univ) if d in labels.index else \
            pd.Series(dtype=float, index=univ)
        keep = y.notna().to_numpy()
        if keep.sum() < MIN_STOCKS:
            continue
        univ = [s for s, k in zip(univ, keep) if k]
        y = y.reindex(univ)

        # basis: Alpha158 + S3's own custom factors (the model's input space)
        a158 = _load_alpha158(d).reindex(univ)
        z_cols = [a158] + [panels[c].loc[d].reindex(univ).to_frame(c)
                           for c in s3_custom if c in panels]
        Z = pd.concat(z_cols, axis=1)
        Z = _rank_cross_section(Z)
        Z = Z.fillna(Z.median())
        Zn = Z.to_numpy(dtype=float)
        Zn = np.nan_to_num(Zn, nan=0.5)
        Zpinv = np.linalg.pinv(Zn)

        X, avail = [], []
        for n in names:
            x = panels[n].loc[d].reindex(univ)
            cov = float(x.notna().mean())
            if x.notna().sum() < MIN_STOCKS:
                continue
            # candidate 必须和 basis 同尺度（都是横截面 rank），否则投影
            # 不是在"既有信息张成的空间"里做的，残差没有意义。
            x = x.rank(pct=True, method="average").fillna(0.5)
            X.append(x.to_numpy(dtype=float))
            avail.append((n, cov))
        if not X:
            continue
        X = np.column_stack(X)
        R = X - Zn @ (Zpinv @ X)

        raw_ic = _spearman_cols(X, y.to_numpy(dtype=float))
        resid_ic = _spearman_cols(R, y.to_numpy(dtype=float))
        for j, (n, cov) in enumerate(avail):
            vx = X[:, j].var()
            per_date[n]["date"].append(d)
            per_date[n]["raw_ic"].append(raw_ic[j])
            per_date[n]["resid_ic"].append(resid_ic[j])
            per_date[n]["r2"].append(
                float(1 - R[:, j].var() / vx) if vx > 0 else np.nan)
            per_date[n]["coverage"].append(cov)
            per_date[n]["n"].append(len(univ))
            resid_panels[n][d] = pd.Series(R[:, j], index=univ)
        if (i + 1) % 12 == 0:
            print(f"  {i + 1}/{len(all_dates)} 日", flush=True)

    # ---------------------------------------------------------------- summary
    rows = []
    for n in names:
        d = per_date[n]
        if not d["date"]:
            continue
        s = pd.DataFrame(d).set_index("date")
        rs = s[s.index.isin(r_dates)]
        vs = s[s.index.isin(v_dates)]
        rows.append({
            "factor": n,
            "category": FACTOR_REGISTRY[n]["category"],
            "coverage": float(s["coverage"].mean()),
            "raw_ic_research": _summary(rs["raw_ic"])["mean"],
            "raw_icir_research": _summary(rs["raw_ic"])["icir"],
            "resid_ic_research": _summary(rs["resid_ic"])["mean"],
            "resid_icir_research": _summary(rs["resid_ic"])["icir"],
            "resid_consistency": _summary(rs["resid_ic"])["consistency"],
            "resid_icir_valid": _summary(vs["resid_ic"])["icir"],
            "resid_ic_valid": _summary(vs["resid_ic"])["mean"],
            "r2": float(rs["r2"].mean()),
            "independence": float(1 - rs["r2"].mean()),
        })
    tab = pd.DataFrame(rows).sort_values(
        "resid_icir_research", key=lambda s: s.abs(), ascending=False)
    OUT.mkdir(parents=True, exist_ok=True)
    tab.to_csv(OUT / "residual_ic.csv", index=False)

    # -------------------------------------------------------------- selection
    passed, rejected = [], []
    for _, r in tab.iterrows():
        if args.min_dates:
            break
        if r["coverage"] < MIN_COVERAGE:
            rejected.append((r["factor"], f"coverage {r['coverage']:.2f}"))
            continue
        if not np.isfinite(r["resid_icir_research"]) or \
                abs(r["resid_icir_research"]) < MIN_RESID_ICIR:
            rejected.append((r["factor"],
                             f"|resid ICIR| {abs(r['resid_icir_research']):.3f}"))
            continue
        if r["resid_consistency"] < MIN_DIR_CONSISTENCY:
            rejected.append((r["factor"],
                             f"方向一致率 {r['resid_consistency']:.2f}"))
            continue
        if np.isfinite(r["resid_ic_valid"]) and \
                np.isfinite(r["resid_ic_research"]) and \
                r["resid_ic_research"] * r["resid_ic_valid"] < 0:
            rejected.append((r["factor"],
                             f"research {r['resid_ic_research']:+.4f} vs "
                             f"valid {r['resid_ic_valid']:+.4f} 变号"))
            continue
        passed.append(r["factor"])

    # G5: redundancy clustering on the RESIDUAL panels
    keep = []
    if passed:
        rp = {n: pd.DataFrame(
            {d: s for d, s in resid_panels[n].items()}).T for n in passed}
        corr = pd.DataFrame(index=passed, columns=passed, dtype=float)
        for a_i, a in enumerate(passed):
            for b in passed[a_i:]:
                vals = []
                for d in rp[a].index.intersection(rp[b].index):
                    m = pd.concat([rp[a].loc[d], rp[b].loc[d]], axis=1).dropna()
                    if len(m) < MIN_STOCKS:
                        continue
                    vals.append(m.iloc[:, 0].corr(m.iloc[:, 1],
                                                  method="spearman"))
                c = float(np.nanmean(vals)) if vals else np.nan
                corr.loc[a, b] = corr.loc[b, a] = c
        np.fill_diagonal(corr.values, 1.0)
        corr.to_csv(OUT / "residual_correlation.csv")
        parent = {n: n for n in passed}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for a_i, a in enumerate(passed):
            for b in passed[a_i + 1:]:
                if abs(corr.loc[a, b]) >= CLUSTER_THRESHOLD:
                    parent[find(a)] = find(b)
        groups: dict = {}
        for n in passed:
            groups.setdefault(find(n), []).append(n)
        icir = dict(zip(tab["factor"], tab["resid_icir_research"]))
        for g in groups.values():
            best = max(g, key=lambda n: abs(icir[n]))
            keep.append(best)
            for o in g:
                if o != best:
                    rejected.append((o, f"残差 |corr| >= {CLUSTER_THRESHOLD} "
                                        f"with {best}"))
        keep.sort(key=lambda n: -abs(icir[n]))
        if len(keep) > MAX_PACK:
            for o in keep[MAX_PACK:]:
                rejected.append((o, f"超出 MAX_PACK={MAX_PACK}"))
            keep = keep[:MAX_PACK]

    # R: strongest rejected-by-G2 factors by RAW icir (same count as I).
    # Factors already inside S3 are excluded — "adding" them is a no-op after
    # dedup, which would silently make the control pack smaller than I.
    raw_icir = dict(zip(tab["factor"], tab["raw_icir_research"]))
    g2_rejected = [n for n, why in rejected
                   if why.startswith("|resid ICIR|") and n not in s3_custom]
    control = sorted(g2_rejected, key=lambda n: -abs(raw_icir[n]))[:len(keep)]

    print(f"\n通过 G2-G4（{len(passed)}）: {passed}")

    print("\n===== 独立信息（research 2018-2021 / valid 2022-2023）=====")
    show = ["factor", "coverage", "raw_icir_research", "resid_icir_research",
            "resid_icir_valid", "r2"]
    print(tab[show].head(25).to_string(index=False))
    print(f"\n通过 G2-G4: {len(passed)} 个；聚类去冗 + 上限后保留 {len(keep)}: "
          f"{keep}")
    print(f"对照 R（强但冗余）: {control}")

    variants = {"I": keep, "R": control}
    (OUT / "variants.json").write_text(
        json.dumps(variants, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------------------------------------------------------------- report
    lines = [
        "# 独立信息研究（2026-09-19）", "",
        "> 问题：把新因子直接叠加到 S3 上，年化从 0.2812 掉到 0.1592；",
        "> 换成替换式组合反而升到 0.3053。本报告度量**既有信息解释不掉的部分**。", "",
        "## 方法", "",
        "对每个候选因子、每个信号日，在当日股票池横截面上：",
        "",
        "```",
        "x = rank(因子)                    缺失填中位数（中性）",
        "Z = rank([Alpha158 158 列, S3 的 10 个自定义因子])",
        "r = x − Z·β                       β 由伪逆最小二乘给出",
        "R² = 1 − var(r)/var(x)            被既有信息解释的比例",
        "raw_IC   = spearman(x, 未来 20 日收益)",
        "resid_IC = spearman(r, 未来 20 日收益)   ← 独立信息",
        "```", "",
        f"选因子只用 research {RESEARCH[0][:7]}~{RESEARCH[1][:7]}，valid "
        f"{VALID[0][:7]}~{VALID[1][:7]} 复核；2026 paper live 未参与。", "",
        "## 结果（按 |resid ICIR| 排序，前 25）", "",
        "| " + " | ".join(show) + " |",
        "|" + "---|" * len(show),
    ]
    for _, r in tab.head(25).iterrows():
        lines.append("| " + " | ".join([
            str(r["factor"]), f"{r['coverage']:.2f}",
            f"{r['raw_icir_research']:+.3f}", f"{r['resid_icir_research']:+.3f}",
            f"{r['resid_icir_valid']:+.3f}", f"{r['r2']:.2f}"]) + " |")
    lines += [
        "", "`r2` 越接近 1 表示这个因子越是被既有特征复述；",
        "`resid_icir` 才是它真正新增的信息。", "",
        "## 选中的因子", "",
        f"- **I（独立信息包，共 {len(keep)} 个）**: {keep}",
        f"- **R（强但冗余对照，共 {len(control)} 个）**: {control}", "",
        "## 被拒绝的因子（前 20）", "",
        "| 因子 | 原因 |", "|---|---|",
    ]
    for n, why in rejected[:20]:
        lines.append(f"| {n} | {why} |")
    lines += [
        "", "## 复现", "", "```bash",
        "python scripts/research_independent_info.py",
        "python scripts/portfolio/run_micro_ablation.py "
        "--variants S3,I,R --variants-file "
        "experiments/factors/independent_info/variants.json "
        "--out-dir experiments/factors/independent_ablation",
        "```", "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n写出 {OUT/'residual_ic.csv'}\n写出 {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
