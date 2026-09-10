# -*- coding: utf-8 -*-
"""Portfolio allocation methods P0-P6 + fallback chain (spec §6-§13/§44).

Signal（alpha 排名 -> Top-K 候选）与 allocation 严格分离：allocator 只对
给定的候选分配权重，绝不重新训练 alpha、绝不静默改变 alpha 排名
（raw_rank 全程保存）。优化器可以把 rank-1 压到 3%，但不能把它换到
rank-2（spec §22）。

每个方法返回满足约束的权重（sum = invest_target、long-only、上限）；
失败时回退链：方法 → inverse_vol → equal_weight，最终结果始终携带
optimizer_status + fallback_reason（spec §44）。

Turnover 定义（spec §24，全局唯一）：
    T = 0.5 * Σ|w_new - w_old|（对候选 + 被清出的持仓求和；
    w_old 以 T 日实际持仓权重计）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np
import pandas as pd

from .constraints import PortfolioConstraints
from .covariance import CovarianceResult
from .optimizer import (AllocationFailure, build_slsqp_problem,
                        finalize_weights, solve_slsqp)
from .risk_model import component_risk, marginal_risk, portfolio_vol
from .transaction_cost import round_trip_rate

MVO_LAMBDA_TIERS = {"small": 0.5, "medium": 2.0, "large": 8.0}
# 归一化效用（见 _mvo_impl 文档）：max μ̄'w - λ·w'Σ̄w

DEFAULTS = {
    "score_weight": {"variant": "rank"},
    "mvo": {"lambda_tier": "medium"},
    "turnover_aware": {"lambda_risk": 2.0, "lambda_turn": 0.5,
                       "lambda_cost": 1.0},
}


@dataclass
class AllocationInput:
    date: pd.Timestamp
    candidates: pd.DataFrame        # index=symbol; cols: prediction, vol,
                                    # industry, liq_cap(可选)
    cov: CovarianceResult
    prev_weights: pd.Series         # T 日实际持仓权重（symbol -> w）
    constraints: PortfolioConstraints
    cost_model: object                  # TransactionCostModel（共享）
    method: str = "equal_weight"
    params: Dict = field(default_factory=dict)

    @property
    def k(self) -> int:
        return len(self.candidates)


@dataclass
class AllocationResult:
    weights: pd.Series              # 目标权重，sum = invest_target
    method: str
    optimizer_status: str           # optimal | fallback_inverse_vol |
                                    # fallback_equal_weight
    fallback_reason: Optional[str]
    extras: Dict = field(default_factory=dict)   # 风险贡献/换手等


# ---------------------------------------------------------------------------
# direct methods
# ---------------------------------------------------------------------------

def _score_raw(preds: pd.Series, variant: str) -> Optional[np.ndarray]:
    """Raw weights from predictions (before finalize). None -> equal."""
    k = len(preds)
    if k == 0:
        return None
    if variant == "rank":
        ranks = preds.rank(ascending=True, method="first").to_numpy()
        return ranks / ranks.sum()
    if variant == "raw_positive":
        v = preds.clip(lower=0.0).to_numpy()
        return v / v.sum() if v.sum() > 0 else None
    if variant == "softmax":
        t = preds.std() if preds.std() > 1e-12 else 1.0
        e = np.exp(preds.to_numpy() / t)
        return e / e.sum()
    raise ValueError(f"unknown score variant {variant}")


def _equal_raw(inp: AllocationInput) -> np.ndarray:
    return np.full(inp.k, 1.0 / max(inp.k, 1))


def _direct_finalize(inp: AllocationInput, raw: np.ndarray,
                     method: str) -> AllocationResult:
    # P0 equal weight is the frozen strategy_v1 baseline allocation:
    # pure 等权 without sector caps (anchors must reproduce the frozen
    # backtests). Sector caps apply to P1-P6 (documented).
    industries = None if method == "equal_weight" else (
        inp.candidates["industry"] if "industry" in inp.candidates else None)
    w = finalize_weights(
        pd.Series(raw, index=inp.candidates.index), inp.constraints,
        industries,
        inp.candidates["liq_cap"] if "liq_cap" in inp.candidates else None)
    return _with_extras(inp, w, method)


def _with_extras(inp: AllocationInput, w: pd.Series,
                 method: str, status: str = "optimal",
                 reason: Optional[str] = None) -> AllocationResult:
    extras = {}
    if inp.cov is not None and len(inp.cov.cov.columns):
        m = marginal_risk(inp.cov, w)
        c = component_risk(inp.cov, w)
        pv = portfolio_vol(inp.cov, w)
        extras = {
            "portfolio_vol": float(pv),
            "marginal_risk": m,
            "component_risk": c,
            "risk_share": c / c.sum() if abs(c.sum()) > 1e-16
            else pd.Series(0.0, index=c.index),
        }
    prev = inp.prev_weights.reindex(w.index).fillna(0.0)
    extras["turnover_from_previous"] = 0.5 * (w - prev).abs()
    extras["turnover_total"] = float(
        0.5 * ((w - prev).abs().sum()
               + inp.prev_weights.drop(w.index, errors="ignore").abs().sum()))
    return AllocationResult(w, method, status, reason, extras)


# ---------------------------------------------------------------------------
# optimizer-based methods
# ---------------------------------------------------------------------------

def _cov_aligned(inp: AllocationInput) -> AllocationInput:
    """Optimizer methods need a covariance row/column per candidate.

    Candidates with too little history are excluded from the covariance
    (portfolio/covariance.py MIN_OBS). Following the frozen under-invest
    semantics (each pick targets invest_target/top_k), the effective
    target is scaled by the surviving fraction — the dropped names stay
    in cash instead of being forced into the optimizer with a made-up
    variance.
    """
    import dataclasses

    cols = inp.cov.cov.columns
    missing = [s for s in inp.candidates.index if s not in cols]
    if not missing:
        return inp
    kept = [s for s in inp.candidates.index if s in cols]
    if not kept:
        raise AllocationFailure(
            "no candidate has enough history for the covariance")
    scale = len(kept) / len(inp.candidates)
    eff_target = inp.constraints.invest_target * scale
    new = dataclasses.replace(
        inp,
        candidates=inp.candidates.loc[kept],
        constraints=dataclasses.replace(
            inp.constraints, invest_target=eff_target,
            cash_buffer=1.0 - eff_target))
    return new


def _optimize(inp: AllocationInput, fun, x0: np.ndarray,
              method: str) -> AllocationResult:
    bounds, constraints = build_slsqp_problem(
        inp.constraints,
        inp.candidates["industry"] if "industry" in inp.candidates else None,
        inp.candidates["liq_cap"] if "liq_cap" in inp.candidates else None,
        inp.candidates.index)
    caps = np.array([b[1] for b in bounds], dtype=float)
    # feasible warm start: water-fill x0 to the caps and the target
    from .optimizer import _waterfill

    x0 = _waterfill(np.clip(np.asarray(x0, dtype=float), 0.0, caps), caps,
                    inp.constraints.invest_target)
    res = solve_slsqp(fun, x0, bounds, constraints)
    if not res.success or not np.all(np.isfinite(res.x)):
        raise AllocationFailure(f"SLSQP failed: {res.message}")
    w = finalize_weights(
        pd.Series(res.x, index=inp.candidates.index), inp.constraints,
        inp.candidates["industry"] if "industry" in inp.candidates else None,
        inp.candidates["liq_cap"] if "liq_cap" in inp.candidates else None)
    return _with_extras(inp, w, method)


def _gmv_impl(inp: AllocationInput) -> AllocationResult:
    inp = _cov_aligned(inp)
    cov = inp.cov.cov.to_numpy()
    x0 = _equal_raw(inp)
    return _optimize(inp, lambda w: float(w @ cov @ w), x0, "gmv")


def _mvo_impl(inp: AllocationInput) -> AllocationResult:
    """Normalized mean-variance: max μ̄'w - λ·w'Σ̄w with
    μ̄ = μ/mean(|μ|), Σ̄ = Σ/mean(diag Σ) — both terms unit scale, so λ
    tiers {0.5, 2.0, 8.0} are comparable across periods/stocks (spec §11:
    small/medium/large only, no tuning grid)."""
    inp = _cov_aligned(inp)
    tier = inp.params.get("lambda_tier", "medium")
    lam = MVO_LAMBDA_TIERS.get(tier)
    if lam is None:
        raise AllocationFailure(f"unknown mvo lambda_tier {tier}")
    mu = inp.candidates["prediction"].to_numpy(dtype=float)
    mu_hat = mu / max(np.abs(mu).mean(), 1e-12)
    cov_hat = inp.cov.cov.to_numpy() / max(
        np.diag(inp.cov.cov.to_numpy()).mean(), 1e-12)
    x0 = pd.Series(_score_raw(inp.candidates["prediction"], "rank"),
                   index=inp.candidates.index)
    x0 = (x0 * (inp.constraints.invest_target / x0.sum())).to_numpy()

    def fun(w):
        return float(-(mu_hat @ w) + lam * (w @ cov_hat @ w))

    return _optimize(inp, fun, x0, "mvo")


def _risk_parity_impl(inp: AllocationInput) -> AllocationResult:
    """Long-only equal risk contribution (spec §12): minimize
    Σ_i (rc_i / Σrc - 1/k)², rc = w ∘ (Σw)."""
    inp = _cov_aligned(inp)
    cov = inp.cov.cov.to_numpy()
    k = inp.k
    vols = inp.candidates["vol"].replace(0, np.nan).fillna(
        np.nanmean(inp.candidates["vol"]) if inp.candidates["vol"].notna().any()
        else 1.0)
    x0 = (1.0 / vols).to_numpy()
    x0 = x0 / x0.sum() * inp.constraints.invest_target

    def fun(w):
        rc = w * (cov @ w)
        tot = rc.sum()
        if abs(tot) < 1e-16:
            return float(np.sum((1.0 / k) ** 2))
        share = rc / tot
        return float(np.sum((share - 1.0 / k) ** 2))

    return _optimize(inp, fun, x0, "risk_parity")


def _turnover_aware_impl(inp: AllocationInput) -> AllocationResult:
    """max μ̄'w - λrisk·w'Σ̄w - λturn·T - λcost·(round-trip rate)·T
    with T = 0.5·Σ|w - w_prev| over candidates plus the weights of held
    names being sold (spec §13/§24; single fixed definition)."""
    inp = _cov_aligned(inp)
    p = inp.params
    lam_risk = float(p.get("lambda_risk", 2.0))
    lam_turn = float(p.get("lambda_turn", 0.5))
    lam_cost = float(p.get("lambda_cost", 1.0))
    mu = inp.candidates["prediction"].to_numpy(dtype=float)
    mu_hat = mu / max(np.abs(mu).mean(), 1e-12)
    cov_hat = inp.cov.cov.to_numpy() / max(
        np.diag(inp.cov.cov.to_numpy()).mean(), 1e-12)
    prev = inp.prev_weights.reindex(inp.candidates.index).fillna(0.0)
    prev_c = prev.to_numpy()
    # weight of held names not in the candidate set (fully sold): their
    # |w_new - w_old| = w_old contributes to T
    held_out = float(inp.prev_weights.drop(
        inp.candidates.index, errors="ignore").abs().sum())
    rate = round_trip_rate(inp.cost_model)
    x0 = pd.Series(prev_c, index=inp.candidates.index)
    if x0.sum() <= 0:
        x0 = pd.Series(_equal_raw(inp), index=inp.candidates.index)
    x0 = (x0 * (inp.constraints.invest_target / x0.sum())).to_numpy()

    def fun(w):
        turn = 0.5 * (np.abs(w - prev_c).sum() + held_out)
        return float(-(mu_hat @ w) + lam_risk * (w @ cov_hat @ w)
                     + (lam_turn + lam_cost * rate) * turn)

    return _optimize(inp, fun, x0, "turnover_aware")


# ---------------------------------------------------------------------------
# dispatch + fallback chain (spec §44)
# ---------------------------------------------------------------------------

METHOD_FUNCS = {
    "equal_weight": None,     # direct
    "score_weight": None,     # direct
    "inverse_vol": None,      # direct
    "gmv": _gmv_impl,
    "mvo": _mvo_impl,
    "risk_parity": _risk_parity_impl,
    "turnover_aware": _turnover_aware_impl,
}


def _method_impl(inp: AllocationInput) -> AllocationResult:
    name = inp.method
    if name == "equal_weight":
        return _direct_finalize(inp, _equal_raw(inp), name)
    if name == "score_weight":
        raw = _score_raw(inp.candidates["prediction"],
                         inp.params.get("variant", "rank"))
        if raw is None:
            raw = _equal_raw(inp)
        return _direct_finalize(inp, raw, name)
    if name == "inverse_vol":
        v = inp.candidates["vol"].replace(0, np.nan)
        if v.notna().sum() == 0:
            return _direct_finalize(inp, _equal_raw(inp), name)
        v = v.fillna(v.mean())
        raw = (1.0 / v).to_numpy()
        return _direct_finalize(inp, raw, name)
    fn = METHOD_FUNCS.get(name)
    if fn is None:
        raise ValueError(f"unknown allocation method {name}")
    return fn(inp)


def _fallback(inp: AllocationInput, res: AllocationResult, method: str,
              reason: str) -> AllocationResult:
    res.method = method
    res.optimizer_status = f"fallback_{method}"
    res.fallback_reason = reason
    return res


def allocate(inp: AllocationInput) -> AllocationResult:
    """Dispatch with the fallback chain: method -> inverse_vol ->
    equal_weight (spec §44). Raises AllocationFailure only when even
    equal weight is infeasible — the caller then skips the rebalance and
    records the reason (never garbage weights)."""
    first_reason = None
    try:
        return _method_impl(inp)
    except AllocationFailure as e:
        first_reason = f"{inp.method} infeasible: {e}"
    if inp.method != "inverse_vol":
        try:
            res = _method_impl(_renamed_input(inp, "inverse_vol"))
            return _fallback(inp, res, "inverse_vol", first_reason)
        except AllocationFailure as e:
            first_reason += f"; inverse_vol infeasible: {e}"
    try:
        res = _method_impl(_renamed_input(inp, "equal_weight"))
        return _fallback(inp, res, "equal_weight", first_reason)
    except AllocationFailure as e:
        raise AllocationFailure(first_reason + f"; equal_weight infeasible: "
                                f"{e}")


def _renamed_input(inp: AllocationInput, method: str) -> AllocationInput:
    """Copy of inp with a different method (params reset to defaults)."""
    import dataclasses

    new = dataclasses.replace(inp)
    new.method = method
    new.params = dict(DEFAULTS.get(method, {}))
    return new
