# -*- coding: utf-8 -*-
"""Factor report generation: per-factor markdown + leaderboard CSV +
dashboard parquet.

Every report carries definition, coverage, missingness, IC/RankIC/ICIR,
decay, quantiles, long-short, turnover, correlation, stability,
interpretation (economic vs empirical direction), and limitations — the
empirical direction is stored separately from the declared direction and
is never used to flip the factor.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .registry import FACTOR_REGISTRY


def _fmt(x, digits: int = 4) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    return f"{x:.{digits}f}"


def factor_report_md(name: str, evals: Dict[str, dict],
                     horizons: List[int], corr_row: Optional[dict] = None,
                     cluster: Optional[List[str]] = None) -> str:
    """evals: {'research': eval, 'valid': eval, 'test': eval}."""
    meta = FACTOR_REGISTRY[name]
    lines = [f"# factor_report_{name}.md", ""]

    lines.append(f"## definition")
    lines.append("")
    lines.append(f"- factor: `{name}`  ·  category: {meta['category']}  ·  "
                 f"version {meta['version']}")
    lines.append(f"- formula: `{meta['formula']}`")
    lines.append(f"- source: {meta['source']}  ·  PIT: {meta['pit']}")
    lines.append(f"- required fields: {', '.join(meta['required_fields'])}")
    lines.append(f"- description: {meta['description']}")
    lines.append(f"- declared (economic) direction: **{meta['direction']}**")
    lines.append("")

    for period in ("research", "valid", "test"):
        ev = evals.get(period)
        if not ev:
            continue
        lines.append(f"## {period} ({len(ev['dates'])} monthly dates "
                     f"{ev['dates'][0] if ev['dates'] else ''} .. "
                     f"{ev['dates'][-1] if ev['dates'] else ''})")
        lines.append("")
        lines.append(f"- coverage: {ev.get('coverage', 0):.3f}")
        lines.append(f"- empirical direction: {ev.get('empirical_direction')}"
                     + ("  ⚠️ disagrees with declared direction"
                        if ev.get("empirical_direction")
                        and ev["empirical_direction"] != meta["direction"]
                        and meta["direction"] != "neutral" else ""))
        for method, res in ev.get("normalizations", {}).items():
            lines.append(f"\n### normalization: {method} "
                         f"(missing: {ev.get('missing_method')})")
            lines.append("")
            lines.append("| horizon | IC mean | IC std | ICIR | IC>0 | "
                         "RankIC mean | RankICIR | RankIC>0 |")
            lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
            for h in horizons:
                hh = res.get("horizons", {}).get(str(h), {})
                ic = hh.get("ic", {})
                ric = hh.get("rank_ic", {})
                lines.append(
                    f"| {h} | {_fmt(ic.get('mean'))} | {_fmt(ic.get('std'))} "
                    f"| {_fmt(ic.get('icir'))} | {_fmt(ic.get('positive_ratio'), 3)} "
                    f"| {_fmt(ric.get('mean'))} | {_fmt(ric.get('icir'))} "
                    f"| {_fmt(ric.get('positive_ratio'), 3)} |")
            lines.append("")
            q = res.get("quantiles", {})
            if q and q.get("n_dates"):
                qm = q.get("quantile_means", {})
                lines.append(f"quantile mean forward {res.get('primary_horizon')}d "
                             f"returns: " + "  ".join(
                                 f"Q{k}: {_fmt(qm.get(f'Q{k}'), 5)}"
                                 for k in range(1, 6)))
                ls = res.get("long_short", {})
                lines.append(f"Q5-Q1 long-short (gross, monthly): mean "
                             f"{_fmt(q.get('q5_q1_mean'), 5)}, ann "
                             f"{_fmt(ls.get('ann_return'), 4)}, Sharpe "
                             f"{_fmt(ls.get('sharpe'), 3)}, MDD "
                             f"{_fmt(ls.get('max_drawdown'), 4)}")
                to = res.get("turnover", {})
                lines.append(f"top-quintile turnover: "
                             f"{_fmt(to.get('avg_turnover'), 3)}")
            hh = res.get("horizons", {}).get(
                str(res.get("primary_horizon", 20)), {})
            yearly = hh.get("yearly", [])
            if yearly:
                lines.append("")
                lines.append("| year | n | rank IC mean | ICIR | IC>0 |")
                lines.append("| --- | --- | --- | --- | --- |")
                for y in yearly:
                    lines.append(f"| {y['year']} | {y['n']} | "
                                 f"{_fmt(y['mean'], 4)} | {_fmt(y['icir'], 3)} | "
                                 f"{_fmt(y['positive_ratio'], 3)} |")
            reg = hh.get("regime", {})
            if reg:
                lines.append("")
                lines.append(f"regime split: up-market IC {_fmt(reg.get('up_mean'), 4)} "
                             f"(n={reg.get('up_n')}) / down-market IC "
                             f"{_fmt(reg.get('down_mean'), 4)} "
                             f"(n={reg.get('down_n')})")
            lines.append("")
        lines.append("---")
        lines.append("")

    if corr_row:
        peers = {k: _fmt(v, 3) for k, v in sorted(
            corr_row.items(), key=lambda kv: -abs(kv[1]))[:5]}
        lines.append(f"## correlation with other factors (avg cross-sectional "
                     f"spearman, research)")
        lines.append("")
        lines.append("  ".join(f"`{k}`: {v}" for k, v in peers.items()))
        lines.append("")
    if cluster:
        lines.append(f"## redundancy cluster")
        lines.append("")
        lines.append("cluster members: " + ", ".join(f"`{c}`" for c in cluster))
        lines.append("")
    lines.append("## interpretation & limitations")
    lines.append("")
    lines.append(f"- declared direction `{meta['direction']}` is the economic "
                 "intuition; the empirical sign is reported per period above "
                 "and is never used to flip the factor.")
    lines.append("- coverage limits follow the underlying data (see the "
                 "financial coverage report for financial factors).")
    lines.append("- long-short is gross of transaction costs.")
    return "\n".join(lines)


def leaderboard_df(evals: Dict[str, dict], period: str = "research",
                   primary: int = 20) -> pd.DataFrame:
    rows = []
    for name, ev in evals.items():
        norm = ev.get("normalizations", {}).get("rank")
        if norm is None:
            continue
        hh = norm.get("horizons", {}).get(str(primary), {})
        ric = hh.get("rank_ic", {})
        q = norm.get("quantiles", {})
        ls = norm.get("long_short", {})
        to = norm.get("turnover", {})
        reg = hh.get("regime", {})
        rows.append({
            "factor": name,
            "category": FACTOR_REGISTRY[name]["category"],
            "direction_declared": FACTOR_REGISTRY[name]["direction"],
            "direction_empirical": ev.get("empirical_direction"),
            f"IC_{period}": ric.get("mean"),
            f"RankIC_{period}": ric.get("mean"),
            f"ICIR_{period}": ric.get("icir"),
            f"IC_pos_ratio_{period}": ric.get("positive_ratio"),
            "decay_20d": ric.get("mean"),
            "Q5_Q1": q.get("q5_q1_mean"),
            "ls_sharpe": ls.get("sharpe"),
            "turnover": to.get("avg_turnover"),
            "coverage": ev.get("coverage"),
            "regime_up_ic": reg.get("up_mean"),
            "regime_down_ic": reg.get("down_mean"),
            "n_dates": len(ev.get("dates", [])),
        })
    return pd.DataFrame(rows)


def dashboard_df(evals: Dict[str, dict], horizons: List[int]) -> pd.DataFrame:
    rows = []
    for name, ev in evals.items():
        for method, res in ev.get("normalizations", {}).items():
            for h in horizons:
                hh = res.get("horizons", {}).get(str(h), {})
                for col in ("ic", "rank_ic"):
                    s = hh.get(col, {})
                    rows.append({
                        "factor": name,
                        "period": "research",
                        "normalization": method,
                        "horizon": h,
                        "metric": f"{col}_mean",
                        "value": s.get("mean"),
                        "n": s.get("n"),
                    })
    return pd.DataFrame(rows)
