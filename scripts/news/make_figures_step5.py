# -*- coding: utf-8 -*-
"""STEP 5 figures -> reports/figures/step5_*.png (10 figures)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
NEWS_RUN = PROJECT_ROOT / "experiments" / "news" / "news_factor_run_001"
NEWS_ABL = PROJECT_ROOT / "experiments" / "news" / "ablation"
OUT = PROJECT_ROOT / "reports" / "figures"

BLUE, ORANGE, GREEN, RED, PURPLE, SKY, GREY = (
    "#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#999999")


def load_events() -> pd.DataFrame:
    from news.storage import load_events_snapshot

    ev = load_events_snapshot()
    if ev.empty:
        return ev
    ev["pub"] = pd.to_datetime(ev["publication_time"], errors="coerce")
    return ev.dropna(subset=["pub"])


def load_evals():
    evals = {}
    for f in (NEWS_RUN / "evaluations").glob("*.json"):
        evals[f.stem] = json.loads(f.read_text(encoding="utf-8"))
    return evals


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ev = load_events()

    # 1. news volume over time
    if not ev.empty:
        fig, ax = plt.subplots(figsize=(9, 4))
        vol = ev.set_index("pub").resample("ME").size()
        ax.plot(vol.index, vol.values, color=BLUE, lw=1.5)
        ax.set_ylabel("announcements / month")
        ax.set_title("News volume (announcements)")
        fig.tight_layout()
        fig.savefig(OUT / "step5_1_news_volume.png", dpi=130)
        plt.close(fig)

        # 2. coverage by year
        fig, ax = plt.subplots(figsize=(9, 4))
        cov = ev.groupby(ev["pub"].dt.year)["symbol"].nunique()
        ax.bar(cov.index.astype(str), cov.values, color=BLUE, width=0.65)
        ax.set_ylabel("distinct symbols")
        ax.set_title("News coverage by year")
        fig.tight_layout()
        fig.savefig(OUT / "step5_2_news_coverage.png", dpi=130)
        plt.close(fig)

        # 3. event type distribution
        fig, ax = plt.subplots(figsize=(10, 5))
        types = ev["event_type"].value_counts().head(16)
        ax.barh(types.index[::-1], types.values[::-1], color=BLUE, height=0.7)
        ax.set_xlabel("events")
        ax.set_title("Event type distribution (rule tier)")
        fig.tight_layout()
        fig.savefig(OUT / "step5_3_event_types.png", dpi=130)
        plt.close(fig)

        # 4. sentiment distribution
        fig, ax = plt.subplots(figsize=(9, 4))
        sent = ev["sentiment"].where(ev["sentiment"].notna(),
                                     ev["direction"].map(
                                         {"positive": 0.5, "negative": -0.5,
                                          "neutral": 0.0}))
        ax.hist(sent.dropna(), bins=11, color=BLUE, alpha=0.8)
        ax.set_xlabel("rule sentiment")
        ax.set_title("Sentiment distribution")
        fig.tight_layout()
        fig.savefig(OUT / "step5_4_sentiment_dist.png", dpi=130)
        plt.close(fig)

        # 5. sentiment decay (mean sentiment by event age)
        fig, ax = plt.subplots(figsize=(9, 4))
        sent5 = ev.groupby("symbol")["pub"].diff().dt.days
        mask = sent5.notna() & (sent5 <= 90)
        ax.plot(range(1, 91), [ev["sentiment"].where(
            ev["sentiment"].notna(),
            ev["direction"].map({"positive": 0.5, "negative": -0.5,
                                 "neutral": 0.0}))[mask & (sent5 == d)].mean()
            for d in range(1, 91)], color=BLUE, lw=1.5)
        ax.set_xlabel("days since previous event")
        ax.set_ylabel("mean sentiment")
        ax.set_title("Sentiment by event age")
        fig.tight_layout()
        fig.savefig(OUT / "step5_5_sentiment_decay.png", dpi=130)
        plt.close(fig)

    # 6-9. news factor evaluation figures
    evals = load_evals()
    if evals:
        names = sorted(evals)
        ric_r = {n: evals[n]["research"]["normalizations"]["rank"]
                 ["horizons"]["20"]["rank_ic"]["icir"] for n in names
                 if "20" in evals[n]["research"]["normalizations"]["rank"]
                 ["horizons"]}
        ric_r = {k: v for k, v in ric_r.items() if np.isfinite(v)}
        ric_t = {n: evals[n]["test"]["normalizations"]["rank"]["horizons"]
                 ["20"]["rank_ic"]["icir"] for n in names
                 if "20" in evals[n]["test"]["normalizations"]["rank"]
                 ["horizons"]}
        ric_t = {k: v for k, v in ric_t.items() if np.isfinite(v)}

        # 6. news IC distribution
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.hist(list(ric_r.values()), bins=14, alpha=0.55, color=BLUE,
                label="research 2018-2021")
        ax.hist(list(ric_t.values()), bins=14, alpha=0.55, color=ORANGE,
                label="test 2024-2025 (frozen)")
        ax.axvline(0, color=GREY, lw=1)
        ax.legend(frameon=False)
        ax.set_xlabel("rank ICIR (20d)")
        ax.set_title("News factor ICIR distribution")
        fig.tight_layout()
        fig.savefig(OUT / "step5_6_news_ic_dist.png", dpi=130)
        plt.close(fig)

        # 7. news IC decay (top factors)
        top = sorted(ric_r, key=lambda n: abs(ric_r[n]), reverse=True)[:6]
        fig, ax = plt.subplots(figsize=(9, 5))
        for i, n in enumerate(top):
            hh = evals[n]["research"]["normalizations"]["rank"]["horizons"]
            xs = sorted(int(h) for h in hh)
            ys = [hh[str(x)]["rank_ic"]["mean"] for x in xs]
            ax.plot(xs, ys, marker="o", ms=4, lw=1.5,
                    color=[BLUE, ORANGE, GREEN, RED, PURPLE, SKY][i],
                    label=n)
        ax.axhline(0, color=GREY, lw=1)
        ax.legend(frameon=False, fontsize=8)
        ax.set_xlabel("horizon (trading days)")
        ax.set_ylabel("mean rank IC")
        ax.set_title("News factor IC decay (research)")
        fig.tight_layout()
        fig.savefig(OUT / "step5_7_news_ic_decay.png", dpi=130)
        plt.close(fig)

        # 8. Q1-Q5 (top factor)
        if top:
            n = top[0]
            qm = evals[n]["research"]["normalizations"]["rank"]["quantiles"]
            if qm.get("n_dates"):
                fig, ax = plt.subplots(figsize=(6, 4))
                qs = [qm["quantile_means"][f"Q{k}"] for k in range(1, 6)]
                ax.bar(range(1, 6), qs, color=[BLUE, SKY, "#8fc8e8",
                                               "#bcdcf2", GREY])
                ax.axhline(0, color=GREY, lw=1)
                ax.set_xlabel("quantile")
                ax.set_ylabel("mean fwd 20d return")
                ax.set_title(f"Q1-Q5: {n}")
                fig.tight_layout()
                fig.savefig(OUT / "step5_8_news_quantiles.png", dpi=130)
                plt.close(fig)

        # 9. news factor correlation
        corr_path = NEWS_RUN / "correlation_news.csv"
        if corr_path.exists():
            corr = pd.read_csv(corr_path, index_col=0)
            fig, ax = plt.subplots(figsize=(10, 8))
            im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
            ax.set_xticks(range(len(corr.columns)))
            ax.set_yticks(range(len(corr.index)))
            ax.set_xticklabels(corr.columns, rotation=90, fontsize=7)
            ax.set_yticklabels(corr.index, fontsize=7)
            fig.colorbar(im, ax=ax, shrink=0.8)
            ax.set_title("News factor correlation (research)")
            fig.tight_layout()
            fig.savefig(OUT / "step5_9_news_correlation.png", dpi=130)
            plt.close(fig)

    # 10. model ablation comparison
    comp_path = NEWS_ABL / "comparison.csv"
    if comp_path.exists():
        comp = pd.read_csv(comp_path)
        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        axes[0].bar(comp["variant"], comp["ann_return"], color=BLUE,
                    width=0.65)
        axes[0].set_title("annualized return")
        axes[0].tick_params(axis="x", rotation=45)
        axes[1].bar(comp["variant"], comp["sharpe"], color=GREEN, width=0.65)
        axes[1].set_title("sharpe")
        axes[1].tick_params(axis="x", rotation=45)
        fig.suptitle("News ablation (frozen test 2024-2025)")
        fig.tight_layout()
        fig.savefig(OUT / "step5_10_news_ablation.png", dpi=130)
        plt.close(fig)
    print(f"figures written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
