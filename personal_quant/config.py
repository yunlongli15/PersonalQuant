# -*- coding: utf-8 -*-
"""Central configuration: paths, run modes, network policy."""

import os
from pathlib import Path

from . import PROJECT_ROOT

# --------------------------------------------------------------------------
# Data layer paths (RAW / CANONICAL / query DB)
# --------------------------------------------------------------------------
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PARQUET_DIR = PROJECT_ROOT / "data" / "parquet"
DUCKDB_PATH = PROJECT_ROOT / "data" / "duckdb" / "personal_quant.duckdb"
PDF_CACHE_DIR = RAW_DIR / "reports"          # LEVEL 3 PDF cache (default OFF)
SSE_ARCHIVE_DIR = RAW_DIR / "sse-reports-archive"

PARQUET_SUBDIRS = {
    "securities": PARQUET_DIR / "securities",
    "daily": PARQUET_DIR / "daily",
    "valuation": PARQUET_DIR / "valuation",
    "financial": PARQUET_DIR / "financial",
    "reports": PARQUET_DIR / "reports",
    "industry": PARQUET_DIR / "industry",
    "corporate_actions": PARQUET_DIR / "corporate_actions",
    "calendar": PARQUET_DIR / "calendar",
}

# --------------------------------------------------------------------------
# Proxy policy
# --------------------------------------------------------------------------
# This machine has a Windows system proxy (127.0.0.1:7890) that intermittently
# refuses connections; all required hosts (PyPI, GitHub, CNINFO, EastMoney)
# are reachable directly, so we default to DIRECT connections. Set
# PQ_USE_SYSTEM_PROXY=1 to opt back into the system proxy.
if os.environ.get("PQ_USE_SYSTEM_PROXY", "0") != "1":
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"

# --------------------------------------------------------------------------
# Run modes
# --------------------------------------------------------------------------
# OFFLINE_MODE: only cached/local data may be used; any network call raises
# OfflineModeError. Historical research/backtests must use OFFLINE_MODE so a
# run never changes results because remote data changed.
# ONLINE_MODE: allows metadata queries, on-demand PDF fetches, extractions.
_mode = (os.environ.get("PQ_MODE") or "online").strip().lower()
if _mode not in ("offline", "online"):
    raise ValueError(f"PQ_MODE must be 'offline' or 'online', got {_mode!r}")
MODE = _mode


def is_offline() -> bool:
    return MODE == "offline"


def require_online(what: str) -> None:
    from .errors import OfflineModeError

    if is_offline():
        raise OfflineModeError(
            f"OFFLINE_MODE is active; network operation not allowed: {what}"
        )


# --------------------------------------------------------------------------
# Network policy (polite, single-connection, per the project rules)
# --------------------------------------------------------------------------
HTTP_TIMEOUT = 60
MAX_RETRIES = 3
BACKOFF_FACTOR = 2.0
MIN_DELAY_SECONDS = 1.0
MAX_DELAY_SECONDS = 3.0
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 PersonalQuant/0.1"
)

# CNINFO static host (per sse-reports-archive config; https works too)
CNINFO_STATIC_BASE = "https://static.cninfo.com.cn"

# PDF cache policy: default OFF (LEVEL 3). Even when enabled, only PDFs that
# were actually fetched through the lazy pipeline are cached — never bulk.
PDF_CACHE_ENABLED = os.environ.get("PQ_PDF_CACHE", "0") == "1"


def ensure_dirs() -> None:
    for p in [RAW_DIR, PARQUET_DIR, DUCKDB_PATH.parent, PDF_CACHE_DIR] + list(
        PARQUET_SUBDIRS.values()
    ):
        p.mkdir(parents=True, exist_ok=True)
