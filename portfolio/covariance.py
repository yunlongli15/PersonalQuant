# -*- coding: utf-8 -*-
"""PIT covariance estimation with a sanity gate (STEP 6 spec §14/§15/§28).

Estimators: sample covariance (default), exponentially weighted covariance
(halflife in trading days, normalized weights), Ledoit-Wolf shrinkage as
the first repair step, diagonal (vols only) as the last resort. Every
estimate carries diagnostics (symmetry / PSD / positive diagonal /
condition number / NaN) and a repair trail — an unstable matrix is never
passed to an optimizer silently.

Point-in-time (spec §28): an estimate at signal date T reads only rows
<= T of the close panel. build_returns() slices by date BEFORE any
computation, so a covariance at T is invariant to future bars
(tests/portfolio/test_covariance_pit.py, test_no_future_data.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np
import pandas as pd

MIN_OBS = 20        # 有效收益数低于此 -> 股票被标记稀疏并从协方差剔除
COND_WARN = 1e5     # 条件数警告阈值
COND_FAIL = 1e6     # 条件数高于此 -> 视为不稳定，进入修复链


@dataclass
class CovarianceResult:
    cov: pd.DataFrame                 # symbol x symbol
    vols: pd.Series                   # sqrt(diag)，下限 1e-8
    method_used: str                  # sample | ewma | ledoit_wolf | diagonal
    repaired: bool
    reason: Optional[str]
    diagnostics: dict
    excluded: List[str] = field(default_factory=list)   # 历史过短的股票


def build_returns(
    close: pd.DataFrame,
    symbols: Sequence[str],
    end_date,
    window: int,
) -> pd.DataFrame:
    """Daily returns of `symbols` over the `window` trading days ending at
    `end_date` (inclusive).

    Prices are forward-filled across suspension gaps (a held stock
    contributes 0 return while halted — same convention as the NAV
    marking), then pct_change()d. All-NaN rows dropped.
    """
    if not isinstance(close.index, pd.DatetimeIndex):
        raise ValueError("close must be indexed by a DatetimeIndex "
                         "(trading calendar)")
    cols = [s for s in symbols if s in close.columns]
    if not cols:
        return pd.DataFrame()
    sub = close.loc[:pd.Timestamp(end_date), cols]
    if len(sub) > window:
        sub = sub.iloc[-window:]
    ret = sub.ffill().pct_change()
    return ret.dropna(how="all")


def _diagnose(cov: pd.DataFrame) -> dict:
    a = cov.to_numpy(dtype=float)
    sym_err = float(np.abs(a - a.T).max())
    n_nan = int(np.isnan(a).sum())
    out = {"symmetric_err": sym_err, "n_nan": n_nan,
           "min_eigenvalue": float("nan"), "min_diag": float("nan"),
           "cond": float("nan"), "n_negative_eigs": 0,
           "fail_reason": None}
    if n_nan == 0 and a.shape[0] >= 1:
        eigs = np.linalg.eigvalsh(a)
        out["min_eigenvalue"] = float(eigs.min())
        out["n_negative_eigs"] = int((eigs < -1e-9).sum())
        out["min_diag"] = float(np.diag(a).min())
        out["cond"] = float(eigs.max() / max(eigs.min(), 1e-300)) \
            if eigs.min() > 0 else float("inf")
    if n_nan > 0:
        out["fail_reason"] = "NaN in covariance"
    elif out["symmetric_err"] > 1e-8:
        out["fail_reason"] = f"asymmetric ({sym_err:.2e})"
    elif out["min_eigenvalue"] < -1e-8:
        out["fail_reason"] = "not positive semi-definite"
    elif out["min_diag"] <= 0:
        out["fail_reason"] = "non-positive diagonal"
    elif out["cond"] > COND_FAIL:
        out["fail_reason"] = f"condition number {out['cond']:.1e} > {COND_FAIL:.0e}"
    return out


def is_stable(diagnostics: dict) -> bool:
    return diagnostics["fail_reason"] is None


def _ewma_cov(ret: pd.DataFrame, halflife: float) -> pd.DataFrame:
    """Exponentially weighted covariance (normalized weights: weights sum
    to 1; halflife in trading days controls decay). Suspension gaps are
    filled with 0 returns (a held stock contributes 0 while halted)."""
    alpha = 1.0 - np.exp(np.log(0.5) / max(halflife, 1e-9))
    w = alpha * (1.0 - alpha) ** np.arange(len(ret) - 1, -1, -1)
    w = w / w.sum()
    r = ret.to_numpy(dtype=float)
    r = np.where(np.isnan(r), 0.0, r)
    mu = (r * w[:, None]).sum(axis=0)
    x = r - mu
    cov = (x.T * w) @ x
    return pd.DataFrame(cov, index=ret.columns, columns=ret.columns)


def _ledoit_wolf(ret: pd.DataFrame) -> pd.DataFrame:
    from sklearn.covariance import LedoitWolf

    r = ret.to_numpy(dtype=float)
    r = np.where(np.isnan(r), 0.0, r)
    cov = LedoitWolf().fit(r).covariance_
    return pd.DataFrame(cov, index=ret.columns, columns=ret.columns)


def _diagonal_cov(ret: pd.DataFrame) -> pd.DataFrame:
    v = ret.var(ddof=1).fillna(0.0).clip(lower=0.0)
    return pd.DataFrame(np.diag(v.to_numpy()), index=ret.columns,
                        columns=ret.columns)


def estimate_covariance(
    close: pd.DataFrame,
    symbols: Sequence[str],
    end_date,
    window: int = 60,
    method: str = "sample",
    halflife: Optional[float] = None,
) -> CovarianceResult:
    """PIT covariance for `symbols` at `end_date` (spec §14/§15).

    Repair chain on instability: method -> Ledoit-Wolf -> diagonal.
    Symbols with fewer than MIN_OBS valid returns are excluded (their vol,
    when available, stays usable via CovarianceResult.vols is NOT — they
    are excluded entirely and listed in `excluded`).
    """
    if method not in ("sample", "ewma"):
        raise ValueError(f"unknown covariance method {method}")
    ret = build_returns(close, symbols, end_date, window)
    if ret.empty:
        return CovarianceResult(
            cov=pd.DataFrame(), vols=pd.Series(dtype=float),
            method_used=method, repaired=False,
            reason="no return data in window",
            diagnostics={"fail_reason": "no return data"},
            excluded=list(symbols),
        )
    n_valid = ret.notna().sum()
    sparse = [c for c in ret.columns if n_valid.get(c, 0) < MIN_OBS]
    ret = ret[[c for c in ret.columns if c not in sparse]]
    if ret.empty:
        return CovarianceResult(
            cov=pd.DataFrame(), vols=pd.Series(dtype=float),
            method_used=method, repaired=False,
            reason="all symbols below MIN_OBS",
            diagnostics={"fail_reason": "all symbols below MIN_OBS",
                         "min_obs": int(n_valid.min()) if len(n_valid) else 0},
            excluded=list(symbols),
        )

    if method == "ewma":
        cov = _ewma_cov(ret, halflife if halflife else 30)
        used = "ewma"
    else:
        cov = ret.cov()
        used = "sample"

    d = _diagnose(cov)
    d["n_obs"] = len(ret)
    d["min_obs"] = int(n_valid.min())
    repaired = False
    reason = None
    if not is_stable(d):
        repaired = True
        first = f"unstable {used} covariance ({d['fail_reason']})"
        cov2 = _ledoit_wolf(ret)
        d2 = _diagnose(cov2)
        if is_stable(d2):
            cov, used, reason = cov2, "ledoit_wolf", first + " -> ledoit_wolf"
        else:
            cov = _diagonal_cov(ret)
            used = "diagonal"
            reason = (first + " -> ledoit_wolf failed ("
                      f"{d2['fail_reason']}) -> diagonal")
        d = _diagnose(cov)
        d["n_obs"] = len(ret)
        d["min_obs"] = int(n_valid.min())
    elif d["cond"] > COND_WARN:
        d["cond_warning"] = True

    vols = pd.Series(np.sqrt(np.clip(np.diag(cov.to_numpy()), 1e-16, None)),
                     index=cov.columns)
    return CovarianceResult(
        cov=cov, vols=vols, method_used=used, repaired=repaired,
        reason=reason, diagnostics=d, excluded=sparse,
    )
