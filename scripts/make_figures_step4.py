# -*- coding: utf-8 -*-
"""STEP 4 figures -> reports/figures/step4_*.png

Reads experiments/factors/factor_run_001 (+ mining/ablation outputs) and
the financial coverage CSV. 10 figures per the STEP 4 spec:
 1 factor IC distribution      6 Q5-Q1 long-short NAV
 2 ICIR distribution           7 rolling IC
 3 IC decay curves             8 factor coverage
 4 factor correlation heatmap  9 financial factor coverage
 5 quantile returns           10 model ablation comparison
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN = PROJECT_ROOT / "experiments" / "factors" / "factor_run_001"
OUT = PROJECT_ROOT / "reports" / "figures"

# Okabe-Ito CVD-safe palette (sequential ramps built from a single hue)
BLUE, ORANGE, GREEN, RED, PURPLE, SKY, GREY = (
    "#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#999999")


def load_evaluations():
    evals = {}
    for f in (RUN / "evaluations").glob("*.json"):
        evals[f.stem] = json.loads(f.read_text(encoding="utf-8"))
    return evals


def rank_ic_horizons(ev, period="research"):
    norm = ev[period]["normalizations"]["rank"]
    return {int(h): v["rank_ic"] for h, v in norm["horizons"].items()}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    evals = load_evaluations()
    names = sorted(evals)
    print(f"evaluations: {len(names)} factors")

    def ric_series(period):
        out = {n: evals[n][period]["normalizations"]["rank"]["horizons"]["20"]
               ["rank_ic"]["mean"] for n in names
               if "20" in evals[n][period]["normalizations"]["rank"]["horizons"]}
        return {k: v for k, v in out.items() if np.isfinite(v)}

    ric_r = ric_series("research")
    ric_t = {n: evals[n]["test"]["normalizations"]["rank"]["horizons"]["20"]
             ["rank_ic"]["mean"] for n in names
             if "20" in evals[n]["test"]["normalizations"]["rank"]["horizons"]}

    # ---- 1. IC distribution -------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.hist(list(ric_r.values()), bins=18, alpha=0.55, color=BLUE,
            label="research 2018-2021")
    ax.hist(list(ric_t.values()), bins=18, alpha=0.55, color=ORANGE,
            label="test 2024-2025 (frozen)")
    ax.axvline(0, color=GREY, lw=1)
    ax.set_xlabel("mean cross-sectional RankIC (20d)")
    ax.set_ylabel("n factors")
    ax.legend(frameon=False)
    ax.set_title("Factor RankIC distribution")
    fig.tight_layout()
    fig.savefig(OUT / "step4_1_ic_distribution.png", dpi=130)
    plt.close(fig)

    # ---- 2. ICIR distribution ------------------------------------------
    icir = {n: evals[n]["research"]["normalizations"]["rank"]["horizons"]["20"]
            ["rank_ic"]["icir"] for n in names
            if "20" in evals[n]["research"]["normalizations"]["rank"]["horizons"]}
    icir = {k: v for k, v in icir.items() if np.isfinite(v)}
    order = sorted(icir, key=icir.get)
    fig, ax = plt.subplots(figsize=(9, 5))
    vals = [icir[n] for n in order]
    colors = [BLUE if v >= 0 else RED for v in vals]
    ax.barh(range(len(order)), vals, color=colors, height=0.7)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order, fontsize=8)
    ax.axvline(0, color=GREY, lw=1)
    ax.set_xlabel("research RankICIR (20d)")
    ax.set_title("Factor ICIR (research)")
    fig.tight_layout()
    fig.savefig(OUT / "step4_2_icir_distribution.png", dpi=130)
    plt.close(fig)

    # ---- 3. IC decay curves --------------------------------------------
    top = sorted(ric_r, key=lambda n: abs(ric_r[n]), reverse=True)[:8]
    fig, ax = plt.subplots(figsize=(9, 5))
    for i, n in enumerate(top):
        hh = rank_ic_horizons(evals[n])
        xs = sorted(hh)
        ys = [hh[x]["mean"] for x in xs]
        ax.plot(xs, ys, marker="o", ms=4, lw=1.5, color=[BLUE, ORANGE, GREEN,
                 RED, PURPLE, SKY, GREY, "#F0E442"][i], label=n)
    ax.axhline(0, color=GREY, lw=1)
    ax.set_xlabel("horizon (trading days)")
    ax.set_ylabel("mean RankIC")
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("IC decay (research)")
    fig.tight_layout()
    fig.savefig(OUT / "step4_3_ic_decay.png", dpi=130)
    plt.close(fig)

    # ---- 4. correlation heatmap ----------------------------------------
    corr = pd.read_csv(RUN / "correlation_matrix.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.index)))
    ax.set_xticklabels(corr.columns, rotation=90, fontsize=7)
    ax.set_yticklabels(corr.index, fontsize=7)
    fig.colorbar(im, ax=ax, shrink=0.8, label="avg cross-sectional spearman")
    ax.set_title("Factor correlation (research)")
    fig.tight_layout()
    fig.savefig(OUT / "step4_4_correlation_heatmap.png", dpi=130)
    plt.close(fig)

    # ---- 5. quantile returns -------------------------------------------
    top5 = sorted(ric_r, key=lambda n: abs(ric_r[n]), reverse=True)[:5]
    fig, axes = plt.subplots(1, len(top5), figsize=(13, 3), sharey=True)
    for i, n in enumerate(top5):
        ax = axes[i]
        qm = evals[n]["research"]["normalizations"]["rank"]["quantiles"]["quantile_means"]
        qs = [qm[f"Q{k}"] for k in range(1, 6)]
        ax.bar(range(1, 6), qs, color=[BLUE, SKY, "#8fc8e8", "#bcdcf2", GREY])
        ax.set_title(n, fontsize=9)
        ax.axhline(0, color=GREY, lw=1)
        ax.set_xlabel("quantile")
    axes[0].set_ylabel("mean fwd 20d return")
    fig.suptitle("Quantile returns (research)")
    fig.tight_layout()
    fig.savefig(OUT / "step4_5_quantile_returns.png", dpi=130)
    plt.close(fig)

    # ---- 6. Q5-Q1 long-short NAV ---------------------------------------
    fig, ax = plt.subplots(figsize=(9, 4))
    for i, n in enumerate(top):
        ls = evals[n]["research"]["normalizations"]["rank"].get("long_short_series", {})
        if not ls:
            continue
        s = pd.Series({pd.Timestamp(k): v for k, v in ls.items()}).sort_index()
        nav = (1 + s).cumprod()
        ax.plot(nav.index, nav.values, lw=1.5, label=n,
                color=[BLUE, ORANGE, GREEN, RED, PURPLE, SKY, GREY, "#F0E442"][i])
    ax.set_ylabel("long-short NAV (gross)")
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("Q5-Q1 long-short (research)")
    fig.tight_layout()
    fig.savefig(OUT / "step4_6_longshort_nav.png", dpi=130)
    plt.close(fig)

    # ---- 7. rolling IC --------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 4))
    for i, n in enumerate(top):
        rc = evals[n]["research"]["normalizations"]["rank"]["horizons"]["20"]["rolling_ic"]
        if not rc:
            continue
        s = pd.Series({pd.Timestamp(k): v for k, v in rc.items()}).sort_index()
        ax.plot(s.index, s.values, lw=1.5, label=n,
                color=[BLUE, ORANGE, GREEN, RED, PURPLE, SKY, GREY, "#F0E442"][i])
    ax.axhline(0, color=GREY, lw=1)
    ax.set_ylabel("12-month rolling RankIC")
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("Rolling IC (research)")
    fig.tight_layout()
    fig.savefig(OUT / "step4_7_rolling_ic.png", dpi=130)
    plt.close(fig)

    # ---- 8. coverage ----------------------------------------------------
    cov = {n: evals[n]["research"]["coverage"] for n in names}
    order = sorted(cov, key=cov.get)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(range(len(order)), [cov[n] for n in order], color=BLUE, height=0.7)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order, fontsize=8)
    ax.set_xlabel("coverage (research, full universe)")
    ax.set_title("Factor coverage")
    fig.tight_layout()
    fig.savefig(OUT / "step4_8_coverage.png", dpi=130)
    plt.close(fig)

    # ---- 9. financial factor coverage ----------------------------------
    cov_csv = PROJECT_ROOT / "reports" / "step4_financial_factor_coverage.csv"
    if cov_csv.exists():
        fc = pd.read_csv(cov_csv)
        piv = fc.pivot(index="year", columns="factor", values="coverage_ratio")
        fig, ax = plt.subplots(figsize=(10, 5))
        cmap = plt.get_cmap("Blues")
        im = ax.imshow(piv.T.values, cmap=cmap, aspect="auto", vmin=0, vmax=1)
        ax.set_xticks(range(len(piv.index)))
        ax.set_xticklabels(piv.index)
        ax.set_yticks(range(len(piv.columns)))
        ax.set_yticklabels(piv.columns, fontsize=8)
        fig.colorbar(im, ax=ax, shrink=0.8, label="coverage")
        ax.set_title("Financial factor coverage (financial universe)")
        fig.tight_layout()
        fig.savefig(OUT / "step4_9_financial_coverage.png", dpi=130)
        plt.close(fig)

    # ---- 10. ablation comparison ---------------------------------------
    comp_csv = PROJECT_ROOT / "experiments" / "factors" / "ablation" / \
        "comparison.csv"
    if comp_csv.exists():
        comp = pd.read_csv(comp_csv)
        fig, axes = plt.subplots(1, 3, figsize=(14, 4))
        for ax, col, title in [(axes[0], "ann_return", "annualized return"),
                               (axes[1], "sharpe", "sharpe"),
                               (axes[2], "max_drawdown", "max drawdown")]:
            ax.bar(comp["variant"], comp[col], color=BLUE, width=0.65)
            ax.set_title(title)
            ax.tick_params(axis="x", rotation=45)
        fig.suptitle("Model ablation (frozen test 2024-2025)")
        fig.tight_layout()
        fig.savefig(OUT / "step4_10_ablation.png", dpi=130)
        plt.close(fig)

    print(f"figures written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
