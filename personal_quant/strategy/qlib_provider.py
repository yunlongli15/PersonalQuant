# -*- coding: utf-8 -*-
"""Qlib integration (方案 A - 轻量级 Custom Provider).

Only the FeatureProvider layer is replaced: raw fields are bulk-loaded from
the canonical layer (parquet via an in-memory DuckDB connection) ONCE per
requested window into a long table, and per-instrument lookups are served
from an in-memory index. qlib's official expression/dataset machinery
(LocalExpressionProvider, LocalDatasetProvider, Alpha158 handler) runs
unchanged on top.

- single source of truth: canonical DB (data/parquet); no data copy
- no qlib core modification; STEP 1 official workflow untouched
- prices served ADJUSTED (raw * factor) because qlib's Alpha158 was designed
  for adjusted prices (same convention as the official dataset in STEP 1);
  raw prices + factor remain available via canonical directly for execution
- qlib's DiskExpressionCache/DiskDatasetCache are disabled: at full-market
  scale they write hundreds of thousands of small files (Windows stalls);
  our own DERIVED-layer cache (data/derived/features) replaces them
"""

from __future__ import annotations

import threading
from typing import Dict

import numpy as np
import pandas as pd

from .. import config
from ..providers.qlib_baseline import QLIB_DATA_DIR

# price fields are served adjusted; volume/amount as-is
PRICE_FIELDS = {"open", "high", "low", "close", "vwap"}
ALL_FIELDS = ("open", "high", "low", "close", "volume", "amount", "vwap", "factor")


class CanonicalFeatureProvider:
    """In-memory FeatureProvider backed by the canonical parquet layer."""

    def __init__(self):
        # RLock: feature() may call get_raw() while already holding the lock
        self._lock = threading.RLock()
        self._raw_cache: Dict[tuple, pd.DataFrame] = {}   # (start, end) -> long table
        self._series_cache: Dict[tuple, pd.Series] = {}   # (start, end, inst, field) -> series
        self._symbol_sets: Dict[tuple, frozenset] = {}    # (start, end) -> symbols present

    def _load_raw(self, start_time, end_time) -> pd.DataFrame:
        # pad the left side: qlib expressions (e.g. Ref(...,-60)) need history
        # BEFORE the requested window; 400 calendar days cover Alpha158's
        # longest lookback with margin.
        # NOTE: reads parquet through pyarrow (thread/process safe with
        # predicate pushdown). DuckDB in-memory connections crash inside
        # qlib's joblib workers (GIL/thread-state interaction), so the
        # feature provider does not use DuckDB at all.
        import pyarrow.parquet as pq

        lo = pd.Timestamp(start_time) - pd.Timedelta(days=180)
        hi = pd.Timestamp(end_time)
        tbl = pq.read_table(
            str(config.PARQUET_SUBDIRS["daily"]),
            filters=[("trade_date", ">=", lo.to_pydatetime()),
                     ("trade_date", "<=", hi.to_pydatetime())],
        )
        df = tbl.to_pandas()
        for c in PRICE_FIELDS:
            # adjusted prices for features; float32 keeps worker memory low
            df[c] = (df[c] * df["factor"]).astype(np.float32)
        for c in ("volume", "amount"):
            df[c] = df[c].astype(np.float32)
        if not df.empty:
            df = df.set_index(["symbol", "trade_date"]).sort_index()
        return df

    def get_raw(self, start_time, end_time) -> pd.DataFrame:
        key = (str(pd.Timestamp(start_time).date()), str(pd.Timestamp(end_time).date()))
        with self._lock:
            if key not in self._raw_cache:
                self._raw_cache[key] = self._load_raw(start_time, end_time)
            return self._raw_cache[key]

    def feature(self, instrument: str, field: str, start_index, end_index, freq) -> pd.Series:
        """Serve one field series indexed by CALENDAR POSITION (ints) — the
        convention qlib's expression engine expects (same as the official
        LocalFeatureProvider). Missing days (suspension) are NaN-filled so
        shift/rolling ops count trading days, matching the official data."""
        from qlib.data.data import Cal

        cal = Cal.calendar(freq=freq)
        if isinstance(start_index, int) and isinstance(end_index, int):
            # clamp to the calendar: expressions like Ref($close,-2) (the
            # handler's label) request a few days BEYOND the last available
            # date; serving those as NaN is the correct boundary behavior
            start_index = max(int(start_index), 0)
            end_index = min(int(end_index), len(cal) - 1)
            s_time, e_time = cal[start_index], cal[end_index]
        else:
            s_time = pd.Timestamp(start_index)
            e_time = pd.Timestamp(end_index)
            start_index = int((cal >= s_time).argmax())
            end_index = int((cal <= e_time).sum()) - 1  # LAST date <= e_time
        col = field.lstrip("$")
        key = (str(s_time.date()), str(e_time.date()), instrument, col)
        with self._lock:
            if key not in self._series_cache:
                raw = self.get_raw(s_time, e_time)
                rkey = (str(s_time.date()), str(e_time.date()))
                if rkey not in self._symbol_sets:
                    self._symbol_sets[rkey] = frozenset(
                        raw.index.get_level_values("symbol")
                    )
                if instrument not in self._symbol_sets[rkey]:
                    # instrument has no data in this window (not yet listed /
                    # long suspension): NaN series, never an exception —
                    # one missing name must not kill the whole quarter
                    s = pd.Series(
                        np.nan,
                        index=pd.to_datetime(cal[start_index : end_index + 1]),
                    )
                else:
                    s = raw.xs(instrument, level="symbol")[col]
                # align to the official calendar (NaN for suspension days)
                s = s.reindex(cal[: int(end_index) + 1])
                s = s.loc[s_time:e_time]
                self._series_cache[key] = s
            s = self._series_cache[key]
        # index by calendar position (s already spans s_time..e_time)
        out = s.copy()
        out.index = np.arange(start_index, start_index + len(out))
        out.name = None
        return out


def init_qlib_with_canonical(kernels: int = 10) -> None:
    """Initialize qlib with the canonical-backed feature provider.

    The provider is injected through the qlib config (C.feature_provider)
    as qlib.init kwargs — qlib.init resets the config to defaults first, and
    C.register() wires the provider into the FeatureD wrapper. qlib's own
    multiprocessing workers rebuild the same provider from config in child
    processes (C.register_from_C). Calendar and instruments stay local
    (qlib_data, same source as canonical).
    """
    import qlib
    from qlib.constant import REG_CN

    if getattr(qlib, "_initialized", False):
        return
    qlib.init(
        provider_uri=str(QLIB_DATA_DIR),
        region=REG_CN,
        feature_provider={
            "class": "CanonicalFeatureProvider",
            "module_path": __name__,
            "kwargs": {},
        },
        kernels=kernels,
        default_disk_cache=0,
        # qlib's DiskExpressionCache writes one small file per instrument x
        # expression; at full-market scale (~700K files) that stalls Windows.
        # Our own DERIVED-layer feature cache (data/derived/features) replaces
        # it, so the qlib-level caches are disabled.
        expression_cache=None,
        dataset_cache=None,
    )
