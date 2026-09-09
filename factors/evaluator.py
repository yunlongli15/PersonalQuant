# -*- coding: utf-8 -*-
"""Factor evaluator: IC / RankIC / ICIR / decay / quantiles / long-short /
stability / turnover / coverage / correlation.

All metrics are computed on the given signal dates with a per-date
cross-sectional join of factor values and forward returns, restricted to
the universe at that date. Evaluation is normalized-per-config: raw values
are the input, and each configured normalization method (rank,
winsorized_zscore) is evaluated separately — the method used is always
recorded in the output (never a silent transform).

Direction convention: factors are evaluated as-is (no sign flip). The
declared economic direction lives in the registry; the report stores the
EMPIRICAL sign separately and flags agreement (spec: never flip signs to
make IC look better).
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .base import FactorData
from .normalization import fill_missing, normalize_panel


# ---------------------------------------------------------------------------
# cross-sectional joins
# ---------------------------------------------------------------------------

def _mask_universe(panel: pd.DataFrame, universe: Dict) -> pd.DataFrame:
    """Keep only universe members per date; others NaN."""
    out = panel.copy()
    for d, syms in universe.items():
        if d in out.index:
            cols = out.columns.intersection(syms)
            out.loc[d, out.columns.difference(cols)] = np.nan
    return out


def ic_series(factor: pd.DataFrame, label: pd.DataFrame,
              min_stocks: int = 30) -> pd.DataFrame:
    """Per-date cross-sectional IC / RankIC between factor and label."""
    rows = []
    for d in factor.index.intersection(label.index):
        f = factor.loc[d]
        l = label.loc[d]
        m = pd.concat([f, l], axis=1, keys=["f", "l"]).dropna()
        if len(m) < min_stocks or m["l"].std() == 0 or m["f"].std() == 0:
            continue
        ic = m["f"].corr(m["l"])
        ric = m["f"].corr(m["l"], method="spearman")
        rows.append({"date": d, "ic": ic, "rank_ic": ric, "n": len(m)})
    return pd.DataFrame(rows)


def _summarize(ic: pd.DataFrame, col: str) -> dict:
    if ic.empty:
        return {"n": 0, "mean": np.nan, "std": np.nan, "icir": np.nan,
                "positive_ratio": np.nan}
    s = ic[col]
    return {
        "n": int(len(s)),
        "mean": float(s.mean()),
        "std": float(s.std(ddof=0)),
        "icir": float(s.mean() / s.std(ddof=0)) if s.std(ddof=0) > 0 else np.nan,
        "positive_ratio": float((s > 0).mean()),
    }


def yearly_ic(ic: pd.DataFrame, col: str = "rank_ic") -> pd.DataFrame:
    if ic.empty:
        return pd.DataFrame(columns=["year", "n", "mean", "icir",
                                     "positive_ratio"])
    out = []
    for year, g in ic.groupby(ic["date"].dt.year):
        s = g[col]
        out.append({
            "year": int(year), "n": len(s), "mean": s.mean(),
            "icir": s.mean() / s.std(ddof=0) if s.std(ddof=0) > 0 else np.nan,
            "positive_ratio": (s > 0).mean(),
        })
    return pd.DataFrame(out)


def rolling_ic(ic: pd.DataFrame, window: int = 12, col: str = "rank_ic") -> pd.Series:
    if ic.empty:
        return pd.Series(dtype=float)
    return ic.set_index("date")[col].rolling(window).mean()


# ---------------------------------------------------------------------------
# quantiles / long-short / turnover
# ---------------------------------------------------------------------------

def quantile_returns(factor: pd.DataFrame, label: pd.DataFrame,
                     universe: Optional[Dict] = None, n_q: int = 5) -> dict:
    """Per-date quintile mean forward returns (bucketed on factor rank)."""
    if universe is not None:
        factor = _mask_universe(factor, universe)
    q_rows = {}
    spread_rows = {}
    for d in factor.index.intersection(label.index):
        f = factor.loc[d]
        l = label.loc[d]
        m = pd.concat([f, l], axis=1, keys=["f", "l"]).dropna()
        if len(m) < n_q * 10:
            continue
        q = pd.qcut(m["f"].rank(method="first"), n_q, labels=False)
        means = m.groupby(q)["l"].mean()
        q_rows[d] = means
        spread_rows[d] = means.iloc[-1] - means.iloc[0]
    if not q_rows:
        return {"n_dates": 0}
    qdf = pd.DataFrame(q_rows).T
    qdf.columns = [f"Q{i+1}" for i in range(n_q)]
    spread = pd.Series(spread_rows, name="q5_q1")
    return {
        "n_dates": int(len(qdf)),
        "quantile_means": qdf.mean().to_dict(),
        "q5_q1_mean": float(spread.mean()),
        "q5_q1_positive_ratio": float((spread > 0).mean()),
        "q5_q1_series": spread,
        "q5_q1_std": float(spread.std(ddof=0)),
    }


def long_short_stats(spread: pd.Series) -> dict:
    """Monthly non-overlapping Q5-Q1 spread: NAV-based stats (gross of cost)."""
    if spread.empty or spread.std() == 0:
        return {"n": int(len(spread))}
    nav = (1.0 + spread).cumprod()
    periods_per_year = 12
    total = nav.iloc[-1] / nav.iloc[0]
    years = max(len(spread) / periods_per_year, 1e-9)
    ann = total ** (1 / years) - 1
    vol = spread.std(ddof=0) * np.sqrt(periods_per_year)
    sharpe = ann / vol if vol > 0 else np.nan
    mdd = float((nav / nav.cummax() - 1).min())
    return {
        "n": int(len(spread)),
        "ann_return": float(ann),
        "ann_vol": float(vol),
        "sharpe": float(sharpe),
        "max_drawdown": mdd,
        "win_ratio": float((spread > 0).mean()),
    }


def factor_turnover(factor: pd.DataFrame, universe: Optional[Dict] = None,
                    top_frac: float = 0.2) -> dict:
    """Average 1 - overlap of the top-quintile set between consecutive dates."""
    if universe is not None:
        factor = _mask_universe(factor, universe)
    dates = factor.index
    overlaps = []
    for i in range(1, len(dates)):
        prev = factor.loc[dates[i - 1]].dropna()
        cur = factor.loc[dates[i]].dropna()
        if prev.empty or cur.empty:
            continue
        k_prev = max(int(len(prev) * top_frac), 1)
        k_cur = max(int(len(cur) * top_frac), 1)
        prev_top = set(prev.nlargest(k_prev).index)
        cur_top = set(cur.nlargest(k_cur).index)
        denom = len(prev_top | cur_top)
        if denom == 0:
            continue
        overlaps.append(len(prev_top & cur_top) / denom)
    if not overlaps:
        return {"n_pairs": 0}
    return {"n_pairs": len(overlaps),
            "avg_top_frac_overlap": float(np.mean(overlaps)),
            "avg_turnover": float(1 - np.mean(overlaps))}


# ---------------------------------------------------------------------------
# regime stability
# ---------------------------------------------------------------------------

def regime_ic(ic: pd.DataFrame, market_returns: pd.Series) -> dict:
    """IC in up-market vs down-market months (regime-independent check).

    market_returns: Series indexed by signal date (equal-weight forward
    return of the universe at that date).
    """
    if ic.empty:
        return {}
    m = market_returns.reindex(ic["date"]).fillna(0.0)
    mask = (m > 0).to_numpy()
    up = ic[mask]
    dn = ic[~mask]
    return {
        "up_mean": float(up["rank_ic"].mean()) if len(up) else np.nan,
        "up_n": int(len(up)),
        "down_mean": float(dn["rank_ic"].mean()) if len(dn) else np.nan,
        "down_n": int(len(dn)),
    }


# ---------------------------------------------------------------------------
# correlation
# ---------------------------------------------------------------------------

def pairwise_correlation(panels: Dict[str, pd.DataFrame],
                         dates: Optional[List] = None,
                         method: str = "spearman") -> pd.DataFrame:
    """Average per-date cross-sectional correlation matrix between factors."""
    names = list(panels)
    mat = pd.DataFrame(index=names, columns=names, dtype=float)
    if dates is not None:
        panels = {k: v.reindex(pd.DatetimeIndex(dates)) for k, v in panels.items()}
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            if i < j:
                va, vb = panels[a], panels[b]
                vals = []
                for d in va.index.intersection(vb.index):
                    m = pd.concat([va.loc[d], vb.loc[d]], axis=1).dropna()
                    if len(m) < 30:
                        continue
                    if method == "spearman":
                        vals.append(m.iloc[:, 0].corr(m.iloc[:, 1],
                                                      method="spearman"))
                    else:
                        vals.append(m.iloc[:, 0].corr(m.iloc[:, 1]))
                c = float(np.nanmean(vals)) if vals else np.nan
                mat.loc[a, b] = c
                mat.loc[b, a] = c
    np.fill_diagonal(mat.values, 1.0)
    return mat


def cluster_correlated(corr: pd.DataFrame, threshold: float) -> List[List[str]]:
    """Union-find clustering of factors with |corr| >= threshold."""
    parent = {n: n for n in corr.index}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a in corr.index:
        for b in corr.columns:
            if a < b and abs(corr.loc[a, b]) >= threshold:
                parent[find(a)] = find(b)
    groups: Dict[str, list] = {}
    for n in corr.index:
        groups.setdefault(find(n), []).append(n)
    return sorted((sorted(v) for v in groups.values()), key=len, reverse=True)


# ---------------------------------------------------------------------------
# top-level evaluation
# ---------------------------------------------------------------------------

def evaluate_factor(
    data: FactorData,
    name: str,
    dates: List[pd.Timestamp],
    labels: Dict[int, pd.DataFrame],
    universe: Optional[Dict] = None,
    config: Optional[dict] = None,
    compute: Optional[callable] = None,
) -> dict:
    """Full evaluation of one factor over `dates`.

    labels: {horizon: wide panel (dates x symbols) of forward returns}.
    Returns per-horizon IC summaries + primary-horizon quantiles/long-short/
    turnover/stability + coverage, for each configured normalization method.
    """
    from .registry import FACTORS

    cfg = config or {}
    horizons = list(labels)
    primary = int(cfg.get("labels", {}).get("primary_horizon", 20))
    norm_methods = cfg.get("normalization", {}).get("methods",
                                                     ["rank", "winsorized_zscore"])
    missing = cfg.get("missing", {}).get("method", "sector_median")
    min_stocks = int(cfg.get("evaluation", {}).get("min_stocks_per_date", 30))

    fn = compute or FACTORS[name]
    raw = fn(data, dates=list(pd.DatetimeIndex(dates)))
    raw = raw.reindex(pd.DatetimeIndex(dates))
    if universe is not None:
        # align the panel to the FULL universe (financial factors only carry
        # their covered symbols as columns — the coverage denominator must
        # count every universe cell, missing columns included)
        univ_cols = sorted({s for syms in universe.values() for s in syms})
        raw = raw.reindex(columns=raw.columns.union(univ_cols))
        raw_masked = _mask_universe(raw, universe)
        in_univ = pd.DataFrame(False, index=raw_masked.index,
                               columns=raw_masked.columns)
        for d, syms in universe.items():
            if d in in_univ.index:
                in_univ.loc[d, in_univ.columns.intersection(syms)] = True
        denom = int(in_univ.sum().sum())
        coverage = float((raw_masked.notna() & in_univ).sum().sum()
                         / denom) if denom else 0.0
    else:
        raw_masked = raw
        coverage = float(raw_masked.notna().sum().sum()
                         / raw_masked.size) if raw_masked.size else 0.0

    out = {
        "factor": name,
        "dates": [str(d.date()) for d in dates],
        "n_dates": len(dates),
        "coverage": coverage,
        "missing_method": missing,
        "normalizations": {},
    }
    if universe is not None:
        market = _mask_universe(
            labels[primary], universe).reindex(
            pd.DatetimeIndex(dates)).mean(axis=1)
    else:
        market = labels[primary].reindex(pd.DatetimeIndex(dates)).mean(axis=1)
    for method in norm_methods:
        norm = normalize_panel(raw_masked, method,
                               float(cfg.get("normalization", {})
                                     .get("winsor_sigma", 3.0)))
        norm = fill_missing(norm, missing, data.industries)
        per_horizon = {}
        for h in horizons:
            lab = labels[h].reindex(pd.DatetimeIndex(dates))
            ic = ic_series(norm, lab, min_stocks)
            per_horizon[str(h)] = {
                "ic": _summarize(ic, "ic"),
                "rank_ic": _summarize(ic, "rank_ic"),
                "yearly": yearly_ic(ic).to_dict("records"),
                "rolling_ic": {str(k.date()): float(v) for k, v in
                               rolling_ic(ic).dropna().items()},
                "regime": regime_ic(ic, market),
            }
        lab_p = labels[primary].reindex(pd.DatetimeIndex(dates))
        qr = quantile_returns(norm, lab_p, None, 5)
        spread = qr.pop("q5_q1_series", pd.Series(dtype=float))
        out["normalizations"][method] = {
            "horizons": per_horizon,
            "primary_horizon": primary,
            "quantiles": qr,
            "long_short": long_short_stats(spread),
            "long_short_series": {
                str(k.date()): float(v) for k, v in spread.items()},
            "turnover": factor_turnover(norm, None),
        }
    # empirical direction: sign of the research rank IC at the primary horizon
    best = out["normalizations"].get("rank") or next(iter(
        out["normalizations"].values()))
    hh = best["horizons"].get(str(primary), {})
    emp_mean = hh.get("rank_ic", {}).get("mean", np.nan)
    out["empirical_direction"] = ("positive" if emp_mean > 0 else
                                  "negative" if emp_mean < 0 else "neutral")
    return out
