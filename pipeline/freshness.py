# -*- coding: utf-8 -*-
"""Data freshness / staleness detection (spec §21).

Every domain reports:
    latest        newest data date found
    expected      newest date the domain SHOULD have (trading calendar)
    age_days      calendar days behind
    status        OK | STALE | MISSING | UNKNOWN

Rules (documented, tested):
- market / valuation / factors / forecast / portfolio are compared with
  the last trading day: behind by more than `tolerance_days` (default 1)
  -> STALE.
- news is compared with today (publication lag ~ days is normal, so the
  default tolerance is larger).
- financials are reported by fiscal period, not by day: status is OK as
  long as the newest available report is not older than
  `financial_tolerance_days` (default 200 days, i.e. ~2 quarters).
- an unreadable/absent artifact is MISSING or UNKNOWN — never OK.

All reads are read-only and DB-free where possible (parquet via pyarrow),
so the freshness panel keeps working while a backfill holds DuckDB.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PARQUET = PROJECT_ROOT / "data" / "parquet"
DERIVED = PROJECT_ROOT / "data" / "derived"

OK, STALE, MISSING, UNKNOWN = "OK", "STALE", "MISSING", "UNKNOWN"


@dataclass
class Freshness:
    domain: str
    status: str
    latest: Optional[str] = None
    expected: Optional[str] = None
    age_days: Optional[int] = None
    detail: Optional[str] = None

    @property
    def is_stale(self) -> bool:
        return self.status == STALE

    def as_dict(self) -> dict:
        return {"domain": self.domain, "status": self.status,
                "latest": self.latest, "expected": self.expected,
                "age_days": self.age_days, "detail": self.detail}


# ---------------------------------------------------------------------------
# calendar helpers
# ---------------------------------------------------------------------------

def trading_calendar(calendar_path: Optional[Path] = None
                     ) -> pd.DatetimeIndex:
    """Official calendar (parquet cache first; DuckDB only as fallback)."""
    p = calendar_path or DERIVED / "factors" / "calendar.parquet"
    if p.exists():
        df = pd.read_parquet(p)
        col = "trade_date" if "trade_date" in df.columns else df.columns[0]
        return pd.DatetimeIndex(pd.to_datetime(df[col])).sort_values()
    from personal_quant import db

    df = db.connect().execute(
        "SELECT trade_date FROM trading_calendar WHERE is_open "
        "ORDER BY trade_date").fetch_df()
    return pd.DatetimeIndex(pd.to_datetime(df["trade_date"]))


def last_trading_day(on_or_before=None) -> Optional[pd.Timestamp]:
    cal = trading_calendar()
    if len(cal) == 0:
        return None
    ref = pd.Timestamp(on_or_before) if on_or_before is not None \
        else pd.Timestamp.today().normalize()
    eligible = cal[cal <= ref]
    return eligible[-1] if len(eligible) else None


# ---------------------------------------------------------------------------
# per-domain probes (each returns the newest data date or None)
# ---------------------------------------------------------------------------

def _latest_parquet_date(directory: Path, column: str,
                         lo: Optional[str] = None) -> Optional[str]:
    if not directory.exists():
        return None
    try:
        import pyarrow.parquet as pq

        ds = pq.ParquetDataset(str(directory))
        dates = []
        for frag in ds.fragments:
            t = pq.read_table(frag.path, columns=[column])
            if len(t):
                dates.append(t.column(column).to_pandas().max())
        if not dates:
            return None
        return str(pd.Timestamp(max(dates)).date())
    except Exception:
        return None


def market_latest() -> Optional[str]:
    return _latest_parquet_date(PARQUET / "daily", "trade_date")


def valuation_latest() -> Optional[str]:
    return _latest_parquet_date(PARQUET / "valuation", "trade_date")


def news_latest() -> Optional[str]:
    p = DERIVED / "news" / "news_events.parquet"
    if not p.exists():
        return None
    try:
        df = pd.read_parquet(p, columns=["publication_time"])
        if df.empty:
            return None
        return str(pd.to_datetime(df["publication_time"]).max().date())
    except Exception:
        return None


def financial_latest() -> Optional[str]:
    p = DERIVED / "factors" / "financial_metrics.parquet"
    if not p.exists():
        return None
    try:
        df = pd.read_parquet(p, columns=["availability_date"])
        if df.empty:
            return None
        return str(pd.to_datetime(df["availability_date"]).max().date())
    except Exception:
        return None


def _state_file_date(path: Path, keys: List[str]) -> Optional[str]:
    import json

    if not path.exists():
        return None
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        for k in keys:
            if k in d and d[k]:
                return str(pd.Timestamp(d[k]).date())
        if d:
            # take the max of any ISO-looking date values
            vals = [str(v) for v in d.values() if isinstance(v, str)]
            cand = [v for v in vals if len(v) >= 10 and v[4] == "-"]
            if cand:
                return str(pd.Timestamp(max(cand)).date())
    except Exception:
        return None
    return None


def factors_latest() -> Optional[str]:
    """When the factor caches were last (re)generated."""
    import os

    p = DERIVED / "factors" / "universes.parquet"
    if not p.exists():
        return None
    ts = datetime.fromtimestamp(os.path.getmtime(p))
    return str(ts.date())


def features_latest() -> Optional[str]:
    import os

    d = DERIVED / "features"
    if not d.exists():
        return None
    files = sorted(d.glob("*.parquet"))
    if not files:
        return None
    return str(datetime.fromtimestamp(
        os.path.getmtime(files[-1])).date())


def forecast_latest() -> Optional[str]:
    return _state_file_date(PROJECT_ROOT / "data" / "quant"
                            / "forecast_state.json", ["as_of"])


def portfolio_latest() -> Optional[str]:
    return _state_file_date(PROJECT_ROOT / "data" / "quant"
                            / "portfolio_state.json", ["as_of"])


# ---------------------------------------------------------------------------
# aggregation
# ---------------------------------------------------------------------------

def _compare(domain: str, latest: Optional[str], expected: pd.Timestamp,
             tolerance_days: int, missing_status: str = MISSING,
             detail: Optional[str] = None) -> Freshness:
    if latest is None:
        return Freshness(domain, missing_status, None,
                         str(expected.date()) if expected is not None else None,
                         None, detail)
    d = pd.Timestamp(latest)
    age = int((expected - d).days) if expected is not None else None
    status = OK
    if expected is not None and age is not None and age > tolerance_days:
        status = STALE
    return Freshness(domain, status, latest,
                     str(expected.date()) if expected is not None else None,
                     age, detail)


def data_status(now: Optional[str] = None,
                market_tolerance_days: int = 1,
                news_tolerance_days: int = 5,
                financial_tolerance_days: int = 200,
                calendar_gap_days: int = 5) -> List[Freshness]:
    """The GUI's Data Status panel (spec §21) as a list of domains.

    Blind spot handled explicitly: the trading calendar is itself data.
    When it ends more than `calendar_gap_days` before the reference date
    (an update pipeline that has not run), every market-based domain is
    reported STALE with the calendar lag as the reason — otherwise a
    stalled pipeline would look perfectly fresh because "the newest data
    equals the newest known trading day".
    """
    ref = pd.Timestamp(now) if now else pd.Timestamp.today().normalize()
    cal = trading_calendar()
    cal_last = cal[-1] if len(cal) else None
    cal_lag = int((ref - cal_last).days) if cal_last is not None else None
    calendar_stale = cal_lag is not None and cal_lag > calendar_gap_days
    ltd = last_trading_day(ref)

    out = [
        _compare("Market Data", market_latest(), ltd, market_tolerance_days),
        _compare("Valuation", valuation_latest(), ltd, market_tolerance_days),
        _compare("Financial Reports", financial_latest(), ref,
                 financial_tolerance_days,
                 detail="fiscal availability date (announcement)"),
        _compare("News", news_latest(), ref, news_tolerance_days),
        _compare("Factors", factors_latest(), ref, 3),
        _compare("Forecast", forecast_latest(), ref, 3, missing_status=UNKNOWN,
                 detail="not computed yet" if forecast_latest() is None
                 else None),
        _compare("Portfolio", portfolio_latest(), ref, 3,
                 missing_status=UNKNOWN,
                 detail="not computed yet" if portfolio_latest() is None
                 else None),
    ]
    if calendar_stale:
        for f in out:
            if f.domain in ("Market Data", "Valuation") and \
                    f.status == OK:
                f.status = STALE
                f.age_days = int((ref - pd.Timestamp(f.latest)).days) \
                    if f.latest else cal_lag
                f.detail = (f"trading calendar itself lags today by "
                            f"{cal_lag} days — market data cannot be "
                            f"verified as fresh")
    return out


def status_dict(now: Optional[str] = None) -> Dict[str, dict]:
    return {f.domain: f.as_dict() for f in data_status(now)}


def any_stale(now: Optional[str] = None) -> bool:
    return any(f.is_stale for f in data_status(now))


def render_status_table(now: Optional[str] = None) -> str:
    lines = ["| domain | latest | expected | status |", "| --- | --- | --- | --- |"]
    for f in data_status(now):
        mark = {"OK": "✓", "STALE": "⚠ DATA STALE", "MISSING": "✗ missing",
                "UNKNOWN": "— not computed"}[f.status]
        lines.append(f"| {f.domain} | {f.latest or '—'} | "
                     f"{f.expected or '—'} | {mark} |")
    return "\n".join(lines)
