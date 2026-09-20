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

import contextlib
import os
import sys
from typing import Callable, Dict, List, Optional

from . import jobs as jobstore

PROJECT_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


@contextlib.contextmanager
def _own_argv():
    """Hide our command-line arguments while calling another script's
    main().

    The refresh jobs reuse the existing CLI entry points, and those parse
    sys.argv with argparse: without this guard, `refresh_all.py --only X`
    would be rejected by the called script's own parser ("unrecognized
    arguments")."""
    saved = sys.argv
    sys.argv = [saved[0] if saved else "refresh"]
    try:
        yield
    finally:
        sys.argv = saved


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
    """Refresh daily bars from the upstream snapshot
    (scripts/quant/update_market_snapshot.py: download the newest
    chenditc release, swap qlib_data/, re-ingest the recent years).

    Not incremental-by-stock: the canonical layer is built from that
    snapshot, so refreshing means taking the newest snapshot. The
    previous snapshot is kept as qlib_data_old/."""
    _maybe_offline()
    import subprocess

    script = PROJECT_ROOT / "scripts" / "quant" / \
        "update_market_snapshot.py"
    r = subprocess.run([sys.executable, str(script),
                        "--years", kw.get("years", "")],
                       cwd=str(PROJECT_ROOT), capture_output=True, text=True,
                       timeout=7200)
    tail = (r.stdout or "").strip().splitlines()[-1:] or [""]
    if r.returncode != 0:
        raise RuntimeError(f"market snapshot update failed: "
                           f"{(r.stderr or r.stdout)[-400:]}")
    return tail[0]


def news_update(**kw) -> str:
    """增量公告更新（只推进已 settle 的日期）。"""
    _maybe_offline()
    from scripts.news import update_news  # type: ignore

    with _own_argv():
        return str(update_news.main())


def financial_update(**kw) -> str:
    """Lazy, chunked financial extraction (never bulk PDF download)."""
    _maybe_offline()
    from scripts import fetch_financial_universe  # type: ignore

    with _own_argv():
        return str(fetch_financial_universe.main())


def valuation_update(**kw) -> str:
    """Daily valuation snapshot (PE/PB/market cap) via the existing
    ingest entry point (Tencent rank snapshot, raw response cached).

    `use_cache=False` on purpose: with the default the "update" returned
    the raw cache and just re-wrote the old rows — a job named *update*
    that could never update.
    """
    _maybe_offline()
    from personal_quant.ingest import market_online

    df = market_online.ingest_valuation(use_cache=False)
    d = df["trade_date"].iloc[0] if len(df) else "?"
    return f"{len(df)} rows @ {d}"


def factor_refresh(**kw) -> str:
    """Rebuild the DERIVED factor caches (calendar/labels/universes/
    financial snapshot) from canonical."""
    from scripts import factor_prepare  # type: ignore

    with _own_argv():
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
