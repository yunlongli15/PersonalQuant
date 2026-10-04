# -*- coding: utf-8 -*-
"""Alpha158 feature pipeline over the canonical layer + 20d label.

- features: qlib official Alpha158 handler, computed per QUARTER (the handler
  needs trailing windows); each slice cached to
  data/derived/features/feature_<YYYY-MM-DD>.parquet
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

#: 缓存文件内部自述日期的列名。文件名的日期只是外壳，内容自己也要能自证 ——
#: 文件被复制、改名、手工搬运之后仍然可以判断它到底是哪一天。
FEATURE_DATE_COL = "feature_date"


def feature_cache_path(date) -> Path:
    """按**日期**命名的特征缓存路径。

    旧格式 `YYYY-MM.parquet` 只带月份，而文件内容其实是"该月最后一次写入
    的那一天"：同月不同日互相覆盖，读取时又无从校验 —— 于是请求
    2026-09-18 会静默拿到 2026-09-29 的横截面（2026-09 实际发生，
    见 reports/前瞻实验-执行链审计.md §3.3）。

    新格式把日期写进文件名，文件内再存一列 `feature_date`，读写两侧都校验。
    旧文件**不删除、不迁移**，保留为历史证据，但新 loader 永不读它们。
    """
    return FEATURE_CACHE / "feature_{}.parquet".format(
        pd.Timestamp(date).strftime("%Y-%m-%d"))


def _date_col_key(df: pd.DataFrame):
    """`feature_date` 列在（可能是 MultiIndex 的）列索引里的实际键。"""
    for c in df.columns:
        name = c[0] if isinstance(c, tuple) else c
        if str(name) == FEATURE_DATE_COL:
            return c
    return None


def strip_cache_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """摘掉缓存自带的 `feature_date` 列，还原成"纯特征矩阵"。

    调用方拿到的东西必须和加这列之前一模一样（158 列 Alpha158），
    否则模型的特征列校验与 `n_features` 统计都会被这列污染。
    """
    key = _date_col_key(df)
    return df.drop(columns=[key]) if key is not None else df


def read_feature_cache(date) -> Optional[pd.DataFrame]:
    """读某一天的日期化缓存；任何不自洽都视为**未命中**。

    唯一的放行条件：文件名日期 == 文件内 `feature_date` == 请求日期。
    不一致 -> 打印警告并返回 None（调用方会重算），
    **绝不返回错误日期的特征**。

    返回的是**剥离了元数据列**的纯特征矩阵 —— 调用方拿到的东西与加
    `feature_date` 之前完全一致，不需要记得再摘一次。

    非交易日不落盘（见 worker），所以这里返回 None 是正常情况，不是错误。
    """
    p = feature_cache_path(date)
    if not p.exists():
        return None
    want = pd.Timestamp(date).strftime("%Y-%m-%d")
    sub = pd.read_parquet(p)
    key = _date_col_key(sub)
    stored = str(sub[key].iloc[0]) if key is not None and len(sub) else None
    if stored != want:
        print(f"[features] WARNING 缓存日期不匹配：请求 {want}，"
              f"{p.name} 内记录的是 {stored!r} —— 视为未命中并重算"
              f"（绝不返回错误日期的特征）", flush=True)
        return None
    return strip_cache_metadata(sub)


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
    written = 0
    for d in dates:
        sub = raw[raw["datetime"] == d].drop(columns=["datetime"])
        sub = sub.set_index("symbol").sort_index()
        # DROP the handler's label column: in qlib semantics
        # Ref($close,-2)/Ref($close,-1) is the 2-day FORWARD return (future
        # data). It must never enter the feature matrix.
        label_cols = [c for c in sub.columns if str(c[0]) == "label"]
        if label_cols:
            sub = sub.drop(columns=label_cols)
        # 非交易日 / 股票池当天没有行情 -> **不落盘**。写一个空文件会让
        # 后续读者把它当成有效缓存（2024-01 被覆盖成 2 行就是这样发生的）。
        if len(sub) == 0:
            continue
        # 日期写进文件内部：文件名只是外壳，内容自己也要能自证。
        sub[("feature_date", "")] = d.strftime("%Y-%m-%d")
        name = "feature_" + d.strftime("%Y-%m-%d") + ".parquet"
        sub.to_parquet(Path(r"{cache_dir}") / name)
        written += 1
    print("WROTE", written)


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
    [quarter_start-lookback, quarter_end], and the requested rows are sliced.
    Results cached to data/derived/features/feature_<YYYY-MM-DD>.parquet
    (DERIVED layer) — one file per DATE, self-describing (see
    `read_feature_cache`).

    `cache=False` 表示"不读缓存"，但计算结果**仍然只写它自己那一天的文件** ——
    它绝不覆盖别的日期的缓存（旧实现的 `cache=False` 会把共享的月文件改写掉，
    这正是 2026-09-18/09-24 两次前瞻观测吃到错误日期特征的机制）。
    """
    global ALPHA158_COLS
    FEATURE_CACHE.mkdir(parents=True, exist_ok=True)
    out: Dict[pd.Timestamp, pd.DataFrame] = {}
    todo: List[pd.Timestamp] = []
    for d in dates:
        sub = read_feature_cache(d) if cache else None
        if sub is not None:
            out[d] = strip_cache_metadata(sub)
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
            sub = read_feature_cache(d)
            if sub is None:
                # 该日没有行情（非交易日 / 整池停牌）：worker 不落盘，
                # 这里也不编造空文件 —— 调用方按"这天没有特征"处理。
                out[d] = pd.DataFrame()
                continue
            out[d] = strip_cache_metadata(sub)
            if ALPHA158_COLS is None and not out[d].empty:
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
