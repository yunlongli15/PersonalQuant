# -*- coding: utf-8 -*-
"""Refresh jobs (spec §20): market -> news -> financial -> valuation ->
factors -> signals -> forecast -> portfolio.

Design rules:
- **Thin wrappers.** Each job calls the existing STEP 2-6 code (ingest
  providers, news updater, factor_prepare, the frozen strategy model).
  Nothing is reimplemented here; this module only orchestrates and
  records.
- **Offline-safe.** Jobs that need the network refuse to run when
  `PQ_MODE=offline` (they raise OfflineMode, which run_all records as
  SKIPPED-OFFLINE and the pipeline reports as a gap — never as success).
- **Ordered + fail-fast.** `run_all` executes in dependency order and
  raises on the first real failure: a recommendation must never be built
  on a factor set whose inputs failed to update.
"""

from __future__ import annotations

import os
from typing import Callable, Dict, List, Optional

from . import jobs as jobstore

PROJECT_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


class OfflineMode(RuntimeError):
    """Raised when a network refresh is attempted with PQ_MODE=offline."""


def _is_offline() -> bool:
    return os.environ.get("PQ_MODE", "").lower() == "offline"


def _maybe_offline():
    if _is_offline():
        raise OfflineMode("PQ_MODE=offline — network refresh skipped "
                          "(recorded, never silently ignored)")


# ---------------------------------------------------------------------------
# individual jobs
# ---------------------------------------------------------------------------

def market_update(**kw) -> str:
    """Incremental daily bars from the canonical online providers."""
    _maybe_offline()
    from personal_quant.ingest import market_online

    fn = getattr(market_online, "update_daily_bars", None) or \
        getattr(market_online, "fetch_recent", None)
    if fn is None:
        raise RuntimeError(
            "personal_quant.ingest.market_online has no incremental entry "
            "point (available: "
            f"{[n for n in dir(market_online) if not n.startswith('_')][:8]}). "
            "Use scripts/bootstrap_data.py for a rebuild instead.")
    return str(fn(**kw))


def news_update(**kw) -> str:
    """增量公告更新（只推进已 settle 的日期）。"""
    _maybe_offline()
    from scripts.news import update_news  # type: ignore

    return str(update_news.main())


def financial_update(**kw) -> str:
    """Lazy, chunked financial extraction (never bulk PDF download)."""
    _maybe_offline()
    from scripts import fetch_financial_universe  # type: ignore

    return str(fetch_financial_universe.main())


def valuation_update(**kw) -> str:
    _maybe_offline()
    from personal_quant.ingest import market_online

    fn = getattr(market_online, "update_valuation", None)
    if fn is None:
        raise RuntimeError("no incremental valuation entry point in "
                           "personal_quant.ingest.market_online")
    return str(fn(**kw))


def factor_refresh(**kw) -> str:
    """Rebuild the DERIVED factor caches (calendar/labels/universes/
    financial snapshot) from canonical."""
    from scripts import factor_prepare  # type: ignore

    return str(factor_prepare.main())


def signal_refresh(**kw) -> str:
    """Rebuild today's alpha signals from the frozen production model."""
    from pipeline.signals import refresh_signals

    return str(refresh_signals(**kw))


def forecast_refresh(**kw) -> str:
    from pipeline.forecast import refresh_forecasts

    return str(refresh_forecasts(**kw))


def portfolio_refresh(**kw) -> str:
    from pipeline.signals import refresh_portfolio_state

    return str(refresh_portfolio_state(**kw))


#: dependency order (spec §20) — later jobs consume earlier outputs
REFRESH_JOBS: List[tuple] = [
    ("market_update", market_update),
    ("news_update", news_update),
    ("financial_update", financial_update),
    ("valuation_update", valuation_update),
    ("factor_refresh", factor_refresh),
    ("signal_refresh", signal_refresh),
    ("forecast_refresh", forecast_refresh),
    ("portfolio_refresh", portfolio_refresh),
]

JOB_NAMES = [n for n, _ in REFRESH_JOBS]


def run_all(only: Optional[List[str]] = None,
            conn=None,
            jobs: Optional[Dict[str, Callable]] = None,
            continue_on_error: bool = False) -> List[dict]:
    """One-click update (spec §20/§37).

    Returns the per-job result rows. Offline jobs are recorded SKIPPED.
    A real failure raises unless `continue_on_error` (the GUI's Manual
    Update passes it so the user sees every domain's state at once).
    """
    table = jobs or dict(REFRESH_JOBS)
    results = []
    for name, fn in table.items():
        if only and name not in only:
            continue
        try:
            run = jobstore.run_job(name, fn, conn=conn)
            results.append({"job": name, "status": run.status,
                            "detail": run.detail, "error": run.error,
                            "duration_s": run.duration_s})
        except OfflineMode as e:
            jobstore.skip_job(name, f"SKIPPED_OFFLINE: {e}", conn=conn)
            results.append({"job": name, "status": "SKIPPED_OFFLINE",
                            "detail": str(e), "error": None,
                            "duration_s": 0.0})
        except Exception as e:                       # noqa: BLE001
            results.append({"job": name, "status": "FAILED",
                            "detail": None,
                            "error": f"{type(e).__name__}: {e}",
                            "duration_s": None})
            if not continue_on_error:
                raise
    return results
