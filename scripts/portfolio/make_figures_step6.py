# -*- coding: utf-8 -*-
"""STEP 6 figures (12, spec §58) from the study artifacts.

Palette: Okabe-Ito (colorblind-safe, fixed categorical order — a method
keeps its hue across every figure). All charts thin lines / direct
labels, no dual axes.

    PYTHONIOENCODING=utf-8 MPLBACKEND=Agg python scripts/portfolio/make_figures_step6.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from research_portfolio import EXP_DIR, run_dir_id

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT = PROJECT_ROOT / "reports" / "figures" / "step6"

# Okabe-Ito colorblind-safe categorical palette (fixed order)
PALETTE = {"equal_weight": "#0072B2", "score_weight": "#E69F00",
           "inverse_vol": "#009E73", "gmv": "#CC79A7",
           "mvo": "#56B4E9", "risk_parity": "#D55E00",
           "turnover_aware": "#F0E442"}
LABELS = {"equal_weight": "P0 Equal", "score_weight": "P1 Score",
          "inverse_vol": "P2 InvVol", "gmv": "P3 GMV",
          "mvo": "P4 MVO", "risk_parity": "P5 RiskPar",
          "turnover_aware": "P6 TurnAware"}
METHODS = list(LABELS)


def load_sel():
    return json.loads((EXP_DIR / "selection.json").read_text(
        encoding="utf-8"))


def load_nav(method, sel):
    k = sel["stage1"]["chosen_top_k"]
    c = sel["stage2"]["chosen_cash"]
    q = sel["stage4"]["chosen_frequency"] == "quarterly"
    p = EXP_DIR / run_dir_id("s3", "test", method, k, c, q) / "nav.parquet"
    if not p.exists():
        return None
    s = pd.read_parquet(p)["nav"]
    s.index = pd.to_datetime(s.index)
    return s


def style_ax(ax):
    ax.grid(alpha=0.25, linewidth=0.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def fig1(sel):
    fig, ax = plt.subplots(figsize=(10, 5))
    for m in METHODS:
        nav = load_nav(m, sel)
        if nav is not None:
            ax.plot(nav.index, nav.values / nav.values[0], lw=1.4,
                    color=PALETTE[m], label=LABELS[m])
    ax.legend(frameon=False, ncol=4, fontsize=8)
    ax.set_title("1. optimizer NAV comparison (frozen test 2024-2025)")
    ax.set_ylabel("NAV (initial = 1)")
    style_ax(ax)
    fig.savefig(OUT / "1_nav.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig2(sel):
    fig, ax = plt.subplots(figsize=(10, 5))
    for m in METHODS:
        nav = load_nav(m, sel)
        if nav is not None:
            dd = nav / nav.cummax() - 1.0
            ax.plot(dd.index, dd.values * 100, lw=1.2,
                    color=PALETTE[m], label=LABELS[m])
    ax.legend(frameon=False, ncol=4, fontsize=8)
    ax.set_title("2. drawdown comparison (%)")
    ax.set_ylabel("drawdown %")
    style_ax(ax)
    fig.savefig(OUT / "2_drawdown.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig3(sel):
    fig, ax = plt.subplots(figsize=(10, 5))
    for m in METHODS:
        nav = load_nav(m, sel)
        if nav is not None:
            vol = nav.pct_change().rolling(60).std() * np.sqrt(252)
            ax.plot(vol.index, vol.values, lw=1.2, color=PALETTE[m],
                    label=LABELS[m])
    ax.legend(frameon=False, ncol=4, fontsize=8)
    ax.set_title("3. rolling volatility (60d, annualized)")
    ax.set_ylabel("volatility")
    style_ax(ax)
    fig.savefig(OUT / "3_volatility.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig4(sel):
    fig, ax = plt.subplots(figsize=(10, 5))
    k = sel["stage1"]["chosen_top_k"]
    c = sel["stage2"]["chosen_cash"]
    q = sel["stage4"]["chosen_frequency"] == "quarterly"
    for m in METHODS:
        p = EXP_DIR / run_dir_id("s3", "test", m, k, c, q) / \
            "turnover.parquet"
        if p.exists():
            t = pd.read_parquet(p)["turnover"]
            t.index = pd.to_datetime(t.index)
            ax.plot(t.index, t.values, lw=1.2, color=PALETTE[m],
                    label=LABELS[m])
    ax.legend(frameon=False, ncol=4, fontsize=8)
    ax.set_title("4. turnover per rebalance (one-sided)")
    ax.set_ylabel("turnover")
    style_ax(ax)
    fig.savefig(OUT / "4_turnover.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def _load_daily_weights(m, sel):
    k = sel["stage1"]["chosen_top_k"]
    c = sel["stage2"]["chosen_cash"]
    q = sel["stage4"]["chosen_frequency"] == "quarterly"
    p = EXP_DIR / run_dir_id("s3", "test", m, k, c, q) / \
        "daily_weights.parquet"
    if not p.exists():
        return None
    w = pd.read_parquet(p)
    w.index = pd.to_datetime(w.index)
    return w


def fig5_6(sel):
    fig, axes = plt.subplots(2, 1, figsize=(10, 8))
    for m in METHODS:
        w = _load_daily_weights(m, sel)
        if w is None:
            continue
        hhi = (w ** 2).sum(axis=1)
        eff = 1.0 / hhi.replace(0, np.nan)
        axes[0].plot(hhi.index, hhi.values, lw=1.2, color=PALETTE[m],
                     label=LABELS[m])
        axes[1].plot(eff.index, eff.values, lw=1.2, color=PALETTE[m],
                     label=LABELS[m])
    axes[0].set_title("5. HHI (weight concentration)")
    axes[1].set_title("6. effective number of positions (1/HHI)")
    for ax in axes:
        ax.legend(frameon=False, ncol=4, fontsize=8)
        style_ax(ax)
    fig.savefig(OUT / "5_6_concentration.png", dpi=150,
                bbox_inches="tight")
    plt.close(fig)


def fig7(sel):
    fig, ax = plt.subplots(figsize=(10, 5))
    k = sel["stage1"]["chosen_top_k"]
    c = sel["stage2"]["chosen_cash"]
    q = sel["stage4"]["chosen_frequency"] == "quarterly"
    method = sel["stage3"]["chosen_method"]
    p = EXP_DIR / run_dir_id("s3", "test", method, k, c, q) / \
        "weights.parquet"
    if p.exists():
        w = pd.read_parquet(p)
        w["date"] = pd.to_datetime(w["date"])
        conc = w.groupby("date").apply(
            lambda g: g.groupby(g["industry"].fillna("UNKNOWN"))[
                "target_weight"].sum().max(), include_groups=False)
        ax.plot(conc.index, conc.values, lw=1.4, color=PALETTE[method],
                label=f"{LABELS[method]} max industry weight")
        ax.axhline(sel["stage3"].get("sector_cap", 0.20), lw=1,
                   color="#555555", ls="--", label="sector cap")
        ax.legend(frameon=False, fontsize=9)
    ax.set_title("7. industry concentration per rebalance (chosen method)")
    ax.set_ylabel("max industry weight")
    style_ax(ax)
    fig.savefig(OUT / "7_industry_concentration.png", dpi=150,
                bbox_inches="tight")
    plt.close(fig)


def fig8(sel):
    fig, ax = plt.subplots(figsize=(10, 5))
    k = sel["stage1"]["chosen_top_k"]
    c = sel["stage2"]["chosen_cash"]
    q = sel["stage4"]["chosen_frequency"] == "quarterly"
    method = sel["stage3"]["chosen_method"]
    p = EXP_DIR / run_dir_id("s3", "test", method, k, c, q) / \
        "weights.parquet"
    if p.exists():
        w = pd.read_parquet(p)
        vals = w["target_weight"].dropna()
        uniq = np.unique(np.round(vals, 6))
        if len(uniq) < 5:
            # degenerate case (e.g. equal weight: one value) — bar chart
            ax.bar([f"{u:.4f}" for u in uniq],
                   [int((np.round(vals, 6) == u).sum()) for u in uniq],
                   color=PALETTE[method], alpha=0.85)
            ax.set_xlabel(f"target weight (single value: {uniq[0]:.4f} for "
                          f"all {len(vals)} rows)")
        else:
            ax.hist(vals, bins=min(40, max(5, len(uniq))),
                    color=PALETTE[method], alpha=0.8)
            ax.set_xlabel("target weight")
    ax.set_title("8. target weight distribution (chosen method)")
    ax.set_ylabel("observations")
    style_ax(ax)
    fig.savefig(OUT / "8_weight_distribution.png", dpi=150,
                bbox_inches="tight")
    plt.close(fig)


def fig9(sel):
    fig, ax = plt.subplots(figsize=(10, 5))
    k = sel["stage1"]["chosen_top_k"]
    c = sel["stage2"]["chosen_cash"]
    q = sel["stage4"]["chosen_frequency"] == "quarterly"
    method = sel["stage3"]["chosen_method"]
    p = EXP_DIR / run_dir_id("s3", "test", method, k, c, q) / \
        "weights.parquet"
    if p.exists():
        w = pd.read_parquet(p)
        w["date"] = pd.to_datetime(w["date"])
        piv = w.pivot_table(index="date", columns="symbol",
                            values="contribution_to_risk")
        piv = piv.div(piv.sum(axis=1), axis=0)
        bot = piv.sort_index(axis=1).iloc[:, :10]
        ax.stackplot(piv.index, *[bot[col].fillna(0).values
                                  for col in bot.columns],
                     labels=bot.columns, alpha=0.85)
        ax.legend(frameon=False, fontsize=6, ncol=5)
    ax.set_title("9. risk contribution shares (chosen method, top-10 by name)")
    style_ax(ax)
    fig.savefig(OUT / "9_risk_contribution.png", dpi=150,
                bbox_inches="tight")
    plt.close(fig)


def fig10_11(sel):
    method = sel["stage3"]["chosen_method"]
    k = sel["stage1"]["chosen_top_k"]
    c = sel["stage2"]["chosen_cash"]
    q = sel["stage4"]["chosen_frequency"] == "quarterly"
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for m, ax in zip(("equal_weight", method), axes):
        nav = load_nav(m, sel)
        if nav is None:
            continue
        mr = nav.resample("ME").last().pct_change().dropna() * 100
        colors = [PALETTE[m] if v >= 0 else "#999999" for v in mr.values]
        ax.bar(range(len(mr)), mr.values, color=colors, width=0.8)
        ax.set_xticks(range(0, len(mr), 6))
        ax.set_xticklabels([d.strftime("%Y-%m") for d in mr.index[::6]],
                           rotation=45, fontsize=8)
        ax.set_title(f"10/11. monthly returns % ({LABELS[m]})")
        ax.axhline(0, color="#333333", lw=0.6)
        style_ax(ax)
    fig.savefig(OUT / "10_11_monthly_returns.png", dpi=150,
                bbox_inches="tight")
    plt.close(fig)


def fig12(sel):
    fig, ax = plt.subplots(figsize=(10, 5))
    k = sel["stage1"]["chosen_top_k"]
    c = sel["stage2"]["chosen_cash"]
    q = sel["stage4"]["chosen_frequency"] == "quarterly"
    for m in METHODS:
        p = EXP_DIR / run_dir_id("s3", "test", m, k, c, q) / \
            "trades.parquet"
        if p.exists():
            t = pd.read_parquet(p)
            t["exec_date"] = pd.to_datetime(t["exec_date"])
            cum = t.sort_values("exec_date").groupby("exec_date")[
                "fee"].sum().cumsum()
            ax.plot(cum.index, cum.values, lw=1.2, color=PALETTE[m],
                    label=LABELS[m])
    ax.legend(frameon=False, ncol=4, fontsize=8)
    ax.set_title("12. cumulative transaction cost (CNY)")
    style_ax(ax)
    fig.savefig(OUT / "12_cumulative_cost.png", dpi=150,
                bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    sel = load_sel()
    if "stage1" not in sel:
        print("ERROR: run the studies first (selection.json)")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    fig1(sel)
    fig2(sel)
    fig3(sel)
    fig4(sel)
    fig5_6(sel)
    fig7(sel)
    fig8(sel)
    fig9(sel)
    fig10_11(sel)
    fig12(sel)
    print(f"wrote 12 figures to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
