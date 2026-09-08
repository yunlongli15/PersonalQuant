# -*- coding: utf-8 -*-
"""Generate STEP 3 figures from a strategy_v1 experiment run.

    python scripts/make_figures.py [--run-id run_001]

Outputs reports/figures/*.png (matplotlib, research-report style):
 1 nav_curve.png            2 drawdown.png
 3 vs_csi300.png            4 vs_csi500.png
 5 monthly_returns.png      6 annual_returns.png
 7 ic_series.png            8 rank_ic_series.png
 9 quantile_returns.png    10 turnover.png

Palette: validated categorical set (fixed order), sequential blue ramp for
quantiles, single axis per chart, legends for >=2 series.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = PROJECT_ROOT / "reports" / "figures"

C = {
    "strategy": "#2a78d6",
    "momentum": "#eb6834",
    "csi300": "#1baf7a",
    "csi500": "#c98500",
    "csi1000": "#d55181",
    "ew": "#008300",
    "drawdown": "#e34948",
    "ink": "#1c2b36",
    "muted": "#7a8794",
    "grid": "#dfe5ea",
}
QL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#2a78d6", "#184f95"]


def style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, color=C["grid"], linewidth=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(colors=C["muted"])


def save(fig, name):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / name, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {name}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="run_001")
    args = ap.parse_args()
    run_dir = PROJECT_ROOT / "experiments" / "strategy_v1" / args.run_id

    nav = pd.read_parquet(run_dir / "nav.parquet").iloc[:, 0]
    bench = pd.read_parquet(run_dir / "benchmarks.parquet")
    ic = pd.read_parquet(run_dir / "ic.parquet")
    qa = pd.read_parquet(run_dir / "quantiles.parquet")
    turn = pd.read_parquet(run_dir / "turnover.parquet").iloc[:, 0]
    nav_m = (pd.read_parquet(run_dir / "nav_momentum.parquet").iloc[:, 0]
             if (run_dir / "nav_momentum.parquet").exists() else None)

    # 1) NAV curve (strategy vs momentum vs benchmarks)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for col, color, label in [
        ("000300.SH", C["csi300"], "CSI300"),
        ("000905.SH", C["csi500"], "CSI500"),
        ("000852.SH", C["csi1000"], "CSI1000"),
    ]:
        if col in bench:
            (bench[col] / bench[col].iloc[0]).plot(ax=ax, color=color,
                                                   linewidth=1.2, label=label)
    if nav_m is not None:
        (nav_m / nav_m.iloc[0]).plot(ax=ax, color=C["momentum"], linewidth=1.4,
                                     label="Momentum 60d baseline")
    (nav / nav.iloc[0]).plot(ax=ax, color=C["strategy"], linewidth=2.0,
                             label="strategy_v1")
    style_ax(ax)
    ax.set_title("NAV curve (normalized to 1.0)")
    ax.legend(frameon=False, ncol=2)
    save(fig, "1_nav_curve.png")

    # 2) drawdown
    dd = nav / nav.cummax() - 1.0
    fig, ax = plt.subplots(figsize=(9, 3.2))
    ax.fill_between(dd.index, dd.values, 0, color=C["drawdown"], alpha=0.35)
    ax.plot(dd.index, dd.values, color=C["drawdown"], linewidth=1.2)
    style_ax(ax)
    ax.set_title(f"Drawdown (max {dd.min():.1%})")
    save(fig, "2_drawdown.png")

    # 3/4) vs CSI300 / CSI500
    for idx, fname in [("000300.SH", "3_vs_csi300.png"),
                       ("000905.SH", "4_vs_csi500.png")]:
        if idx not in bench:
            continue
        fig, ax = plt.subplots(figsize=(9, 4.5))
        (bench[idx] / bench[idx].iloc[0]).plot(ax=ax, color=C["csi300" if idx.endswith("300") else "csi500"],
                                               linewidth=1.4, label=idx)
        (nav / nav.iloc[0]).plot(ax=ax, color=C["strategy"], linewidth=2.0,
                                 label="strategy_v1")
        style_ax(ax)
        ax.set_title(f"strategy_v1 vs {idx}")
        ax.legend(frameon=False)
        save(fig, fname)

    # 5) monthly returns bars
    m = nav.resample("ME").last().pct_change().dropna()
    fig, ax = plt.subplots(figsize=(9, 3.6))
    colors = [C["strategy"] if v >= 0 else C["drawdown"] for v in m]
    ax.bar(m.index.strftime("%Y-%m"), m.values, color=colors, width=0.7)
    style_ax(ax)
    ax.set_title("Monthly returns (strategy_v1)")
    ax.tick_params(axis="x", rotation=45, labelsize=7)
    save(fig, "5_monthly_returns.png")

    # 6) annual returns bars
    y = nav.resample("YE").last().pct_change().dropna()
    fig, ax = plt.subplots(figsize=(8, 3.6))
    colors = [C["strategy"] if v >= 0 else C["drawdown"] for v in y]
    ax.bar([str(i.year) for i in y.index], y.values, color=colors, width=0.55)
    for i, v in enumerate(y.values):
        ax.text(i, v + (0.02 if v >= 0 else -0.06), f"{v:.1%}",
                ha="center", fontsize=8, color=C["ink"])
    style_ax(ax)
    ax.set_title("Annual returns (strategy_v1)")
    save(fig, "6_annual_returns.png")

    # 7/8) IC / RankIC series
    for col, fname, title in [
        ("ic", "7_ic_series.png", "Monthly IC"),
        ("rank_ic", "8_rank_ic_series.png", "Monthly Rank IC"),
    ]:
        fig, ax = plt.subplots(figsize=(9, 3.4))
        ax.axhline(0, color=C["muted"], linewidth=0.9)
        ax.plot(ic["date"], ic[col], color=C["strategy"], linewidth=1.4,
                marker="o", markersize=3.5)
        ax.plot(ic["date"], ic[col].rolling(6).mean(), color=C["momentum"],
                linewidth=1.6, label="6-month mean")
        style_ax(ax)
        ax.set_title(f"{title} (mean {ic[col].mean():.4f})")
        ax.legend(frameon=False)
        save(fig, fname)

    # 9) quantile returns
    piv = qa.pivot_table(index="quantile", values="mean_return", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    ax.bar([f"Q{i}" for i in piv.index], piv["mean_return"],
           color=[QL[int(i) - 1] for i in piv.index], width=0.6)
    for i, v in enumerate(piv["mean_return"]):
        ax.text(i, v + (0.001 if v >= 0 else -0.003), f"{v:.3f}",
                ha="center", fontsize=9, color=C["ink"])
    style_ax(ax)
    ax.set_title("Mean future 20d return by prediction quantile")
    save(fig, "9_quantile_returns.png")

    # 10) turnover
    fig, ax = plt.subplots(figsize=(9, 3.2))
    ax.bar(turn.index.strftime("%Y-%m"), turn.values, color=C["strategy"], width=0.7)
    style_ax(ax)
    ax.set_title(f"One-sided turnover per rebalance (avg {turn.mean():.1%})")
    ax.tick_params(axis="x", rotation=45, labelsize=7)
    save(fig, "10_turnover.png")
    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
