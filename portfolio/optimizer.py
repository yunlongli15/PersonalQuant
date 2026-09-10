# -*- coding: utf-8 -*-
"""Shared numerical optimizer (scipy SLSQP) + weight finalization.

One solver for GMV / MVO / risk parity / turnover-aware; direct methods
(equal weight / score / inverse vol) only go through the finalization
pipeline. Finalization enforces every constraint again after the solve
(max weight, liquidity cap, sector cap) with iterative water-filling, so
weights that violate the constraints never reach the backtest — an
infeasible problem raises AllocationFailure and the allocator's fallback
chain takes over (spec §44).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .constraints import PortfolioConstraints


class AllocationFailure(Exception):
    """No feasible weights for the method (fallback chain handles it)."""


# ---------------------------------------------------------------------------
# numerical solve
# ---------------------------------------------------------------------------

def solve_slsqp(
    fun,
    x0: np.ndarray,
    bounds: Sequence[Tuple[float, float]],
    constraints: Sequence[dict],
    maxiter: int = 500,
):
    """Deterministic SLSQP solve (fixed x0 -> fixed result; reproducibility
    relies on this)."""
    return minimize(
        fun, x0, method="SLSQP", bounds=list(bounds),
        constraints=list(constraints),
        options={"maxiter": maxiter, "ftol": 1e-10, "disp": False},
    )


# ---------------------------------------------------------------------------
# constraint enforcement (water-filling)
# ---------------------------------------------------------------------------

def _waterfill(w: np.ndarray, caps: np.ndarray, budget: float,
               max_iter: int = 200) -> np.ndarray:
    """Scale/cap `w >= 0` so that w <= caps and sum(w) == budget when
    feasible. Handles both directions: scales down proportionally when the
    current sum exceeds the budget, and redistributes a deficit among
    names with remaining room. If caps sum to less than budget the result
    saturates at the caps (infeasible — detected by the caller)."""
    w = np.asarray(w, dtype=float).copy()
    caps = np.maximum(np.asarray(caps, dtype=float), 0.0)
    w = np.minimum(w, caps)
    if w.sum() > 0 and budget < w.sum():
        w = w * (budget / w.sum())
    for _ in range(max_iter):
        excess = budget - w.sum()
        if excess <= 1e-12 * max(budget, 1.0):
            break
        room = caps - w
        free = room > 1e-12
        if not free.any():
            break
        share = room[free] / room[free].sum()
        add = np.minimum(excess * share, room[free])
        w[free] += add
        if excess - add.sum() <= 1e-12 * max(budget, 1.0):
            break
    return w


def _group_indices(industries: pd.Series) -> Dict[str, np.ndarray]:
    inds = industries.fillna("UNKNOWN")
    return {g: np.where(inds.to_numpy() == g)[0]
            for g in inds.unique()}


def finalize_weights(
    raw: pd.Series,
    cons: PortfolioConstraints,
    industries: Optional[pd.Series] = None,
    liq_caps: Optional[pd.Series] = None,
) -> pd.Series:
    """Clip + enforce caps + renormalize to invest_target (exact, single
    pass).

    Without sector caps: water-fill at the per-stock caps to
    invest_target. With sector caps: first water-fill group budgets at the
    sector cap to invest_target (a saturated group cannot take more),
    then water-fill each group's stocks to the group budget under the
    per-stock caps. Raises AllocationFailure when the caps make
    invest_target infeasible (never returns garbage weights).
    """
    syms = raw.index
    w = raw.clip(lower=cons.min_weight).astype(float)
    if not len(w) or w.sum() <= 0:
        raise AllocationFailure("all weights zero")

    caps = pd.Series(cons.max_weight, index=syms, dtype=float)
    if liq_caps is not None:
        lc = liq_caps.reindex(syms)
        caps = pd.concat([caps, lc], axis=1).min(axis=1)
    if (caps <= 0).any():
        # a zero cap on some name: that name is forced to 0
        keep = caps > 0
        if not keep.any():
            raise AllocationFailure("all candidates liquidity-capped to 0")
        w = w[keep]
        caps = caps[keep]
        if industries is not None:
            industries = industries.reindex(w.index)

    if industries is None or not cons.sector_cap or cons.sector_cap >= 1.0:
        w = pd.Series(_waterfill(w.to_numpy(), caps.to_numpy(),
                                 cons.invest_target), index=w.index)
        if abs(w.sum() - cons.invest_target) > 1e-6:
            raise AllocationFailure(
                f"constraints infeasible: caps allow {w.sum():.4f} < "
                f"invest_target {cons.invest_target}")
        return w[w > 1e-12]

    groups = _group_indices(industries)
    inds = industries.fillna("UNKNOWN")
    g_raw = w.groupby(inds).sum()
    g_budget = _waterfill(g_raw.to_numpy(),
                          np.full(len(g_raw), cons.sector_cap),
                          cons.invest_target)
    pieces = {}
    for j, g in enumerate(g_raw.index):
        idx = groups[g]
        pieces[g] = _waterfill(w.iloc[idx].to_numpy(),
                               caps.iloc[idx].to_numpy(), g_budget[j])
    w = pd.concat([pd.Series(pieces[g], index=w.index[groups[g]])
                   for g in g_raw.index])
    w = w.reindex(syms)
    if abs(w.sum() - cons.invest_target) > 1e-6:
        raise AllocationFailure(
            f"constraints infeasible: caps allow {w.sum():.4f} < "
            f"invest_target {cons.invest_target}")
    return w[w > 1e-12]


# ---------------------------------------------------------------------------
# shared SLSQP problem builder
# ---------------------------------------------------------------------------

def build_slsqp_problem(
    cons: PortfolioConstraints,
    industries: Optional[pd.Series],
    liq_caps: Optional[pd.Series],
    syms: pd.Index,
) -> Tuple[List[Tuple[float, float]], List[dict]]:
    """Bounds (0, per-stock cap] + sum-eq + per-industry caps."""
    caps = pd.Series(cons.max_weight, index=syms, dtype=float)
    if liq_caps is not None:
        lc = liq_caps.reindex(syms)
        caps = pd.concat([caps, lc], axis=1).min(axis=1)
    bounds = [(0.0, max(float(c), 0.0)) for c in caps.to_numpy()]
    constraints = [{"type": "eq",
                    "fun": lambda w: w.sum() - cons.invest_target}]
    if industries is not None and cons.sector_cap and cons.sector_cap < 1.0:
        for idx in _group_indices(industries.reindex(syms)).values():
            constraints.append({
                "type": "ineq",
                "fun": lambda w, idx=idx: cons.sector_cap - w[idx].sum(),
            })
    return bounds, constraints
