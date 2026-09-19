# -*- coding: utf-8 -*-
"""Incremental IC 研究图表（§34）。

    MPLBACKEND=Agg python scripts/make_incremental_figures.py

产出 8 张图到 reports/figures/incremental_v2/。配色用 Okabe-Ito
（色盲安全）；有正负之分的量用发散色（两个色相 + 中性灰中点），
单向量用单色相深浅；不使用彩虹色、不使用双 Y 轴。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((PROJECT_ROOT / "config" / "factor_selection_v2.yaml")
                     .read_text(encoding="utf-8"))["factor_selection_v2"]
OUTDIR = PROJECT_ROOT / CFG["output"]["figures_dir"]
EXP = PROJECT_ROOT / CFG["output"]["dir"]

# Okabe-Ito：色盲安全分类色
BLUE, VERMIL, GREEN, PINK, ORANGE, SKY = (
    "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9")
GREY = "#9E9E9E"
plt.rcParams.update({
    # 中文字形：matplotlib 默认的 DejaVu Sans 没有 CJK，中文会渲染成方框
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC",
                        "DejaVu Sans"],
    "axes.unicode_minus": False,
    "figure.dpi": 130, "savefig.dpi": 130, "font.size": 9,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#E8E8E8", "grid.linewidth": 0.7,
    "axes.axisbelow": True, "figure.autolayout": True,
})


def _save(fig, name):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    p = OUTDIR / name
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    print(f"  {p.relative_to(PROJECT_ROOT)}")


def _diverging(vals, vmax):
    """两色相 + 中性中点（不是彩虹）。"""
    from matplotlib.colors import LinearSegmentedColormap
    return LinearSegmentedColormap.from_list(
        "div", [BLUE, "#F2F2F2", VERMIL])((np.asarray(vals) / vmax + 1) / 2)


def main() -> int:
    met = pd.read_csv(EXP / "candidate_metrics.csv")
    if met.empty:
        print("candidate_metrics.csv 为空，先跑选择流程")
        return 1
    series = pd.read_csv(EXP / "delta_ic_series.csv") \
        if (EXP / "delta_ic_series.csv").exists() else pd.DataFrame()
    folds = pd.read_csv(EXP / "per_fold.csv") \
        if (EXP / "per_fold.csv").exists() else pd.DataFrame()
    bs = pd.read_csv(EXP / "bootstrap.csv") \
        if (EXP / "bootstrap.csv").exists() else pd.DataFrame()
    print(f"候选 {len(met)} 个，图表输出到 {OUTDIR}")

    # 1 / 2. DeltaIC 与 DeltaRankIC 分布 --------------------------------
    for col, title, fname in (
            ("delta_ic", "ΔIC（加入候选因子带来的 IC 增量）",
             "01_delta_ic_distribution.png"),
            ("delta_rank_ic", "ΔRankIC（加入候选因子带来的排序 IC 增量）",
             "02_delta_rank_ic_distribution.png")):
        d = series[col].dropna() if col in series.columns else pd.Series(dtype=float)
        if d.empty:
            continue
        fig, ax = plt.subplots(figsize=(6.4, 3.6))
        ax.hist(d, bins=40, color=BLUE, alpha=0.85, edgecolor="white",
                linewidth=0.4)
        ax.axvline(0, color=VERMIL, linewidth=2)
        ax.axvline(d.mean(), color=GREEN, linewidth=2, linestyle="--")
        ax.annotate(f"均值 {d.mean():+.4f}", xy=(d.mean(), ax.get_ylim()[1]),
                    xytext=(6, -10), textcoords="offset points",
                    color=GREEN)
        ax.annotate("0", xy=(0, ax.get_ylim()[1]), xytext=(4, -10),
                    textcoords="offset points", color=VERMIL)
        ax.set_xlabel("Δ 值"); ax.set_ylabel("信号日数")
        ax.set_title(f"{title}\n（全部候选 × 全部 walk-forward 信号日，"
                     f"n={len(d)}）")
        _save(fig, fname)

    # 3. 逐折稳定性热图（有正负 -> 发散色）-----------------------------
    if not folds.empty:
        piv = folds.pivot(index="factor", columns="fold",
                          values="delta_ic_mean")
        piv = piv.reindex(piv.mean(axis=1).sort_values(ascending=False).index)
        vmax = float(np.nanmax(np.abs(piv.to_numpy()))) or 1e-9
        fig, ax = plt.subplots(figsize=(6.8, max(3.0, 0.28 * len(piv) + 1.4)))
        im = ax.imshow(piv.to_numpy(), cmap="RdBu_r", vmin=-vmax, vmax=vmax,
                       aspect="auto")
        ax.set_xticks(range(len(piv.columns)))
        ax.set_xticklabels(piv.columns)
        ax.set_yticks(range(len(piv.index)))
        ax.set_yticklabels(piv.index)
        for i in range(piv.shape[0]):
            for j in range(piv.shape[1]):
                v = piv.iloc[i, j]
                if np.isfinite(v):
                    ax.text(j, i, f"{v:+.3f}", ha="center", va="center",
                            fontsize=7,
                            color="white" if abs(v) > vmax * 0.6 else "#222")
        ax.grid(False)
        ax.set_title("逐折 ΔIC：候选因子在不同时间段是否持续提供增量")
        fig.colorbar(im, ax=ax, shrink=0.8, label="ΔIC 均值")
        _save(fig, "03_fold_stability.png")

    # 4. block bootstrap 置信区间 --------------------------------------
    if not bs.empty:
        b = bs.sort_values("mean")
        fig, ax = plt.subplots(figsize=(6.8, max(3.0, 0.28 * len(b) + 1.6)))
        y = np.arange(len(b))
        ax.errorbar(b["mean"], y,
                    xerr=[b["mean"] - b["ci_low"], b["ci_high"] - b["mean"]],
                    fmt="o", color=BLUE, ecolor=GREY, elinewidth=2,
                    capsize=3, markersize=5, label="block bootstrap 95% CI")
        ax.errorbar(b["mean"], y,
                    xerr=[b["mean"] - b["iid_ci_low"],
                          b["iid_ci_high"] - b["mean"]],
                    fmt="none", ecolor=ORANGE, elinewidth=1.2, capsize=2,
                    label="iid bootstrap 95% CI（对照：忽略时间相关性会偏窄）")
        ax.axvline(0, color=VERMIL, linewidth=2)
        ax.set_yticks(y); ax.set_yticklabels(b["factor"])
        ax.set_xlabel("ΔIC 均值与 95% 置信区间")
        ax.set_title("ΔIC 的 block bootstrap 置信区间（按月分块）")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=1,
                  frameon=False, fontsize=8)
        _save(fig, "04_bootstrap_ci.png")

    # 5. 预测影响 vs ΔIC -----------------------------------------------
    if "prediction_corr" in met.columns:
        m = met.dropna(subset=["prediction_corr", "delta_ic_mean"])
        fig, ax = plt.subplots(figsize=(6.0, 4.0))
        pos = m["delta_ic_mean"] > 0
        ax.scatter(m.loc[pos, "prediction_corr"], m.loc[pos, "delta_ic_mean"],
                   s=48, color=GREEN, edgecolor="white", linewidth=0.6,
                   label="ΔIC > 0（有增量）", zorder=3)
        ax.scatter(m.loc[~pos, "prediction_corr"],
                   m.loc[~pos, "delta_ic_mean"], s=48, color=GREY,
                   edgecolor="white", linewidth=0.6, label="ΔIC ≤ 0", zorder=3)
        ax.axhline(0, color=VERMIL, linewidth=1.6)
        for _, r in m.iterrows():
            ax.annotate(r["factor"], (r["prediction_corr"],
                                      r["delta_ic_mean"]), fontsize=6,
                        xytext=(4, 3), textcoords="offset points")
        ax.set_xlabel("corr(预测_0, 预测_1)  —— 越接近 1 表示候选几乎没改变模型")
        ax.set_ylabel("ΔIC 均值")
        ax.set_title("候选因子对模型输出的实际影响 vs 增量信息")
        ax.legend(frameon=False, fontsize=8)
        _save(fig, "05_prediction_impact.png")

    # 6. 原始因子相关热图（主判据）-------------------------------------
    rp = EXP / "redundancy_matrix.csv"
    if rp.exists():
        cm = pd.read_csv(rp, index_col=0)
        if len(cm) > 1:
            fig, ax = plt.subplots(figsize=(8.6, 7.4))
            im = ax.imshow(cm.to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1)
            ax.set_xticks(range(len(cm))); ax.set_xticklabels(
                cm.columns, rotation=90, fontsize=6)
            ax.set_yticks(range(len(cm))); ax.set_yticklabels(
                cm.index, fontsize=6)
            ax.grid(False)
            ax.set_title("原始因子横截面秩相关（冗余主判据）\n"
                         "M0 内的既有因子排在最前")
            fig.colorbar(im, ax=ax, shrink=0.75, label="平均秩相关")
            _save(fig, "06_redundancy_heatmap.png")

    # 7. raw vs residual vs incremental --------------------------------
    need = {"raw_icir", "residual_icir", "delta_icir", "factor"}
    if need.issubset(met.columns):
        m = met.dropna(subset=["raw_icir", "delta_icir"]).copy()
        m = m.reindex(m["delta_icir"].abs().sort_values(
            ascending=False).index).head(15)
        x = np.arange(len(m)); w = 0.27
        fig, ax = plt.subplots(figsize=(7.6, 4.0))
        ax.bar(x - w, m["raw_icir"].abs(), w, color=GREY,
               label="|raw ICIR|（单独看强不强）")
        ax.bar(x, m["residual_icir"].abs(), w, color=SKY,
               label="|residual ICIR|（剔除既有信息后）")
        ax.bar(x + w, m["delta_icir"], w, color=GREEN,
               label="incremental ICIR（加进模型后）")
        ax.axhline(0, color="#444", linewidth=1)
        ax.set_xticks(x); ax.set_xticklabels(m["factor"], rotation=90,
                                             fontsize=7)
        ax.set_ylabel("ICIR（绝对值为原始/残差，带符号为增量）")
        ax.set_title("为什么\"单因子很强\"不等于\"加入模型有效\"\n"
                     "（按 |incremental ICIR| 排序，前 15）")
        ax.legend(frameon=False, fontsize=8)
        _save(fig, "07_raw_residual_incremental.png")

    # 8. 候选综合比较 ---------------------------------------------------
    if "evidence_score" in met.columns:
        m = met.sort_values("evidence_score", ascending=True).tail(15)
        fig, ax = plt.subplots(figsize=(6.8, max(3.0, 0.3 * len(m) + 1.4)))
        y = np.arange(len(m))
        cols = [("delta_icir", "incremental ICIR", BLUE),
                ("delta_rank_icir", "incremental RankICIR", SKY),
                ("positive_fold_ratio", "正向 fold 比例", GREEN),
                ("delta_ic_positive_ratio", "正向月份比例", PINK)]
        left = np.zeros(len(m))
        for key, lab, col in cols:
            if key not in m.columns:
                continue
            v = m[key].fillna(0).clip(lower=0).to_numpy() / (
                0.6 if "icir" in key else 1.0)
            ax.barh(y, v, left=left, color=col, label=lab, height=0.68)
            left += v
        ax.set_yticks(y); ax.set_yticklabels(m["factor"], fontsize=7)
        ax.set_xlabel("归一分量（ICIR 类按 cap=0.6 截断）")
        ax.set_title("候选综合比较（Evidence Score 构成）")
        ax.legend(frameon=False, fontsize=7, loc="lower right")
        _save(fig, "08_candidate_comparison.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
