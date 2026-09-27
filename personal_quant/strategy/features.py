# -*- coding: utf-8 -*-
"""Alpha158 feature pipeline over the canonical layer + 20d label.

- features: qlib official Alpha158 handler, computed per QUARTER (the handler
  needs trailing windows), month-end slices cached to data/derived/features
- label: future 20-trading-day adjusted return computed from canonical
  (close[t+20]*factor[t+20])/(close[t]*factor[t]) - 1; strictly future-only
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from .. import PROJECT_ROOT, db
from .qlib_provider import init_qlib_with_canonical
from .rebalance import trading_days

FEATURE_CACHE = PROJECT_ROOT / "data" / "derived" / "features"
LABEL_CACHE = PROJECT_ROOT / "data" / "derived" / "labels"

ALPHA158_COLS = None  # populated on first computation


def flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Alpha158 columns are ('feature','KMID') tuples; pandas join/merge
    misbehaves with MultiIndex columns, so flatten to 'feature_KMID'.
    Also defensively drops any residual label column (future data)."""
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = ["_".join(str(c) for c in col) for col in df.columns]
    else:
        df = df.copy()
    label_cols = [c for c in df.columns if str(c).startswith("label")]
    if label_cols:
        df = df.drop(columns=label_cols)
    return df


def _handler_range_for(date: pd.Timestamp, lookback_days: int = 80):
    """Quarter start (with lookback) .. date, for handler windows."""
    start = date - pd.Timedelta(days=lookback_days * 2)
    return start, date


_QUARTER_WORKER = r"""
import sys
from pathlib import Path
sys.path.insert(0, r"{project_root}")


def main():
    import pandas as pd
    from personal_quant.strategy.qlib_provider import init_qlib_with_canonical
    init_qlib_with_canonical(kernels={kernels})
    from qlib.contrib.data.handler import Alpha158
    from personal_quant.symbols import normalize_symbol

    instruments = {instruments!r}
    lo = "{lo}"
    hi = "{hi}"
    dates = [pd.Timestamp(d) for d in {dates!r}]
    handler = Alpha158(instruments=instruments, start_time=lo, end_time=hi,
                       freq="day", learn_processors=[], infer_processors=[])
    raw = handler.fetch(col_set=handler.CS_RAW, data_key=handler.DK_R)
    raw = raw.reset_index()
    raw = raw.rename(columns={{"instrument": "qlib_symbol"}})
    raw["symbol"] = raw["qlib_symbol"].map(
        lambda s: normalize_symbol(s) if isinstance(s, str) else None)
    raw = raw.drop(columns=["qlib_symbol"])
    for d in dates:
        sub = raw[raw["datetime"] == d].drop(columns=["datetime"])
        sub = sub.set_index("symbol").sort_index()
        # DROP the handler's label column: in qlib semantics
        # Ref($close,-2)/Ref($close,-1) is the 2-day FORWARD return (future
        # data). It must never enter the feature matrix.
        label_cols = [c for c in sub.columns if str(c[0]) == "label"]
        if label_cols:
            sub = sub.drop(columns=label_cols)
        sub.to_parquet(Path(r"{cache_dir}") / f"{{d.strftime('%Y-%m')}}.parquet")
    print("WROTE", len(raw))


if __name__ == "__main__":
    main()
"""


#: 季度 worker 的降级阶梯：(kernels, 超时秒数)。
#:
#: 这两种失败都是**暂时性**的，降并发重跑一次通常就过：
#:   * 超时 —— qlib 的 joblib 池在 Windows 上会偶发死锁（CPU 归零、
#:     一直不返回），并发越高越容易撞上；
#:   * MemoryError —— 并发 worker 的内存峰值超了可用量。
#: 直接抛出去会让整条刷新链断在中途（2026-09-22 实际发生：signal_refresh
#: 超时 1800s，后面的实时价/预测/交易计划全都没跑）。
#: 健康的一次是 156~400s，所以第一档留了 3 倍以上余量。
WORKER_LADDER = ((10, 1200), (4, 1800), (1, 2700))


def _worker_attempts(kernels: int) -> List[tuple]:
    """首档用调用方给的并发，之后只降不升。"""
    lower = [(k, t) for k, t in WORKER_LADDER if k < kernels]
    return [(kernels, WORKER_LADDER[0][1])] + lower


def _worker_env() -> dict:
    """worker 的环境变量：把 BLAS 线程压到 1。

    并行度已经由 qlib 的 `kernels` 个 joblib worker 提供了，BLAS 再按
    核数各自开线程纯属浪费，而且代价直接体现在**提交内存**上：20 核机器
    上每个 worker 会开 67 个线程、提交 4.2 GB，10 个 worker 要 42 GB
    commit —— 超过 65.8 GB 的提交上限就整体卡死（2026-09-27 实际发生：
    40 秒内所有进程 CPU 增量为 0，日志里只剩 OpenBLAS 分配失败）。
    这些变量必须在 worker 导入 numpy 之前生效，所以走 subprocess 环境。
    """
    import os

    env = dict(os.environ)
    for k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS",
              "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        env[k] = "1"
    return env


def _compute_quarter_subprocess(
    instruments: List[str],
    dates: List[pd.Timestamp],
    kernels: int = 10,
    verbose: bool = True,
) -> None:
    """Compute one quarter's Alpha158 slices in a FRESH subprocess.

    qlib's joblib multiprocessing pool deadlocks on Windows when reused for a
    second dataset() call in the same process; a per-quarter subprocess gives
    each pool a brand-new interpreter (deterministic, no reuse). The worker
    code is written to a temp .py file: Windows CreateProcess rejects long
    command lines (WinError 206) with thousands of inline instruments.

    Failures that are known to be transient (timeout / MemoryError) are
    retried down `WORKER_LADDER`; a genuine error raises immediately.
    """
    import subprocess

    q_start = min(dates).to_period("Q").start_time
    lo = q_start - pd.Timedelta(days=170)
    hi = max(dates)
    worker_path = (Path(FEATURE_CACHE).parent / "tmp"
                   / f"worker_{q_start.year}Q{q_start.quarter}.py")
    worker_path.parent.mkdir(parents=True, exist_ok=True)

    attempts = _worker_attempts(kernels)
    last_err = ""
    for i, (k, timeout_s) in enumerate(attempts, 1):
        worker_path.write_text(_QUARTER_WORKER.format(
            project_root=str(PROJECT_ROOT), kernels=k,
            instruments=instruments, lo=str(lo.date()), hi=str(hi.date()),
            dates=[str(d.date()) for d in dates],
            cache_dir=str(FEATURE_CACHE)), encoding="utf-8")
        t0 = time.time()
        try:
            proc = subprocess.run(
                [sys.executable, "-u", str(worker_path)],
                capture_output=True, text=True, timeout=timeout_s,
                env=_worker_env(),
            )
        except subprocess.TimeoutExpired:
            last_err = f"第 {i} 次（kernels={k}）{timeout_s}s 未返回"
            if i < len(attempts):
                print(f"[features] {last_err} —— 降并发重试", flush=True)
                continue
            break
        if proc.returncode != 0:
            out = f"{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
            if "MemoryError" in out and i < len(attempts):
                last_err = f"第 {i} 次（kernels={k}）内存不足"
                print(f"[features] {last_err} —— 降并发重试", flush=True)
                continue
            raise RuntimeError(
                f"quarter worker failed ({dates[0].date()}..{hi.date()}):\n{out}"
            )
        if verbose:
            wrote = (proc.stdout.strip().splitlines()[-1]
                     if proc.stdout.strip() else "")
            print(f"[features] {q_start.date()}..{hi.date()}: "
                  f"{len(instruments)} instruments in {time.time()-t0:.0f}s "
                  f"(kernels={k}, {wrote})", flush=True)
        return

    raise RuntimeError(
        f"quarter worker failed ({dates[0].date()}..{hi.date()}) after "
        f"{len(attempts)} attempts: {last_err}")


def compute_features(
    instruments: List[str],
    dates: List[pd.Timestamp],
    cache: bool = True,
    verbose: bool = True,
    kernels: int = 10,
) -> Dict[pd.Timestamp, pd.DataFrame]:
    """Compute Alpha158 features at the given dates.

    Dates are grouped by quarter; the handler runs once per quarter over
    [quarter_start-lookback, quarter_end], and month-end rows are sliced.
    Results cached to data/derived/features/YYYY-MM.parquet (DERIVED layer).
    """
    global ALPHA158_COLS
    FEATURE_CACHE.mkdir(parents=True, exist_ok=True)
    out: Dict[pd.Timestamp, pd.DataFrame] = {}
    todo: List[pd.Timestamp] = []
    for d in dates:
        f = FEATURE_CACHE / f"{d.strftime('%Y-%m')}.parquet"
        if cache and f.exists():
            sub = pd.read_parquet(f)
            # older cache files may carry the (label, LABEL0) column
            label_cols = [c for c in sub.columns if str(c[0]) == "label"]
            if label_cols:
                sub = sub.drop(columns=label_cols)
            out[d] = sub
        else:
            todo.append(d)

    if not todo:
        return out

    # group by quarter
    groups: Dict[str, List[pd.Timestamp]] = {}
    for d in todo:
        groups.setdefault(f"{d.year}-Q{d.quarter}", []).append(d)

    conn = db.connect()
    for _, gd in sorted(groups.items()):
        q_start = min(gd).to_period("Q").start_time
        lo = q_start - pd.Timedelta(days=170)  # ~120 trading days of history
        hi = max(gd)
        # only instruments that actually have bars in this quarter's window:
        # avoids the slow NaN path for names listed later / long suspended
        have_bars = conn.execute(
            "SELECT DISTINCT symbol FROM daily_bars WHERE trade_date BETWEEN ? AND ? "
            "AND symbol IN (SELECT unnest(?::VARCHAR[]))",
            [str(lo.date()), str(hi.date()), list(instruments)],
        ).fetch_df()["symbol"].tolist()
        q_insts = sorted(set(instruments) & set(have_bars))
        if verbose:
            print(f"[features] {q_start.date()}..{hi.date()}: "
                  f"{len(q_insts)}/{len(instruments)} instruments", flush=True)
        _compute_quarter_subprocess(q_insts, gd, kernels=kernels, verbose=verbose)
        for d in gd:
            out[d] = pd.read_parquet(
                FEATURE_CACHE / f"{d.strftime('%Y-%m')}.parquet"
            )
            if ALPHA158_COLS is None:
                ALPHA158_COLS = list(out[d].columns)
    return out


def compute_labels(
    symbols: List[str],
    dates: List[pd.Timestamp],
    horizon_days: int = 20,
) -> Dict[pd.Timestamp, pd.Series]:
    """Adjusted 20-trading-day forward return per (date, symbol).

    label(t) uses close/factor at t+20 only — never t or earlier data beyond
    the base close at t.
    """
    LABEL_CACHE.mkdir(parents=True, exist_ok=True)
    days = trading_days()
    day_idx = {d: i for i, d in enumerate(days)}
    out: Dict[pd.Timestamp, pd.Series] = {}
    for d in dates:
        # keyed by exact date: a monthly key would let different dates within
        # the same month overwrite each other (label cache corruption)
        f = LABEL_CACHE / f"{d.strftime('%Y-%m-%d')}_h{horizon_days}.parquet"
        if f.exists():
            out[d] = pd.read_parquet(f).iloc[:, 0]
            continue
        i = day_idx.get(d)
        if i is None or i + horizon_days >= len(days):
            out[d] = pd.Series(dtype=float)
            continue
        d2 = days[i + horizon_days]
        conn = db.connect()
        base = conn.execute(
            "SELECT symbol, close * factor AS adj0 FROM daily_bars "
            "WHERE trade_date = ? AND symbol IN (SELECT unnest(?::VARCHAR[]))",
            [d, list(symbols)],
        ).fetch_df().set_index("symbol")["adj0"]
        fwd = conn.execute(
            "SELECT symbol, close * factor AS adj1 FROM daily_bars "
            "WHERE trade_date = ? AND symbol IN (SELECT unnest(?::VARCHAR[]))",
            [d2, list(symbols)],
        ).fetch_df().set_index("symbol")["adj1"]
        label = (fwd / base - 1.0).dropna()
        label.name = "label"
        out[d] = label
        label.to_frame().to_parquet(
            LABEL_CACHE / f"{d.strftime('%Y-%m-%d')}_h{horizon_days}.parquet"
        )
    return out


def build_training_data(
    instruments: List[str],
    dates: List[pd.Timestamp],
    horizon_days: int = 20,
    date_universes: Optional[Dict[pd.Timestamp, List[str]]] = None,
) -> pd.DataFrame:
    """Feature matrix + labels joined per date (one row per (date, symbol)).

    date_universes: optional per-date symbol lists (the PIT universe at each
    date). When given, training rows are restricted to those symbols — e.g.
    stocks listed <180 days at the date are excluded from training entirely.
    """
    feats = compute_features(instruments, dates)
    labels = compute_labels(instruments, dates, horizon_days)
    frames = []
    for d in dates:
        f = feats.get(d)
        lab = labels.get(d)
        if f is None or f.empty or lab is None or lab.empty:
            continue
        m = flatten_columns(f).copy()
        m["label"] = lab
        m = m.dropna(subset=["label"])
        if date_universes:
            univ = date_universes.get(d)
            if univ:
                m = m[m.index.isin(univ)]
        m["date"] = d
        frames.append(m)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames).reset_index()
