# -*- coding: utf-8 -*-
"""Same-session daily bar **overlay** (fixes the one-session signal lag).

    python scripts/quant/update_daily_overlay.py --check
    python scripts/quant/update_daily_overlay.py                # today's session
    python scripts/quant/update_daily_overlay.py --date 2026-10-12 --force

The problem
-----------
Canonical `daily_bars` is built from the `chenditc/investment_data` snapshot.
That snapshot's newest session is T-1 when we run on the evening of T (the
release carrying trade date T appears ~00:40 CST on T+1). So an evening run
could only rank with T-1 data while tomorrow's fills happen at T+1's open —
the ranking was one session stale. `refresh_live_prices.py` papered over this
for a handful of candidate symbols, but the *ranking* needs the whole
cross-section (Alpha158 is cross-sectional and the liquidity filter needs
every name), and the batch endpoint retrieves that in ~15 s.

What this writes
----------------
`data/parquet/overlay/` — NEVER the canonical files:

    daily_overlay.parquet   the new session, canonical schema & units
    calendar_extra.parquet  sessions the overlay contributed
    overlay_manifest.json   provenance + validation results
    market_anchor.parquet   per-symbol unit constants (see below)

`db.daily_bars` and `CanonicalFeatureProvider` then serve canonical ∪
overlay, so the overlay is one duckdb view away from being removable and the
upstream snapshot files stay byte-identical.

Bridging live quotes onto the canonical scale
---------------------------------------------
Two different unit systems have to be reconciled, and both were verified
against real data rather than assumed (see `providers/batch_quote.py`).

**Prices.** Canonical stores RAW prices plus a `factor` column; the feature
provider serves `raw * factor`. The invariant that matters is that the
ADJUSTED series stays continuous, so the bridge anchors on it:

    A(T-1) = close_canonical(T-1) * factor_canonical(T-1)
    r      = live_close / live_prev_close - 1
    A(T)   = A(T-1) * (1 + r)
    factor(T) = A(T) / live_close
    X(T)   = live_X * factor(T)          for open/high/low/close/vwap

`live_prev_close` is the exchange's 除权除息参考价 on an ex-rights day, so
`r` is already correct across corporate actions without a separate table
(verified: 5,549/5,564 symbols matched canonical's T-1 close; the 15 that
did not were exactly that day's actions, whose names carried the XD/DR
prefix). Cross-source price agreement is checked on every run anyway.

**Volume.** Canonical volume is NOT in shares and not even a fixed multiple
of shares across stocks — it is Yahoo's per-stock artifact, coupled to the
adjustment factor:

    canonical_volume(t) = C(sym) * real_shares(t) / factor(t)

with `C(sym)` constant in time. Measured 2026-10-12: 600519.SH held
C = 0.00999998 across a factor change of 2.4% (the ratio inverted the factor
change to six digits), and the same relation reproduced 000002.SZ and
688110.SH exactly.

`C` is recovered from the existing `market_scale.parquet` WITHOUT any extra
request. That table stored `median_t(real/canonical)`, and since
`real/canonical = factor/C`, its median is `median_t(factor)/C`:

    C(sym) = median_window(factor) / scale_volume(sym)

This matters: using the table's scale directly would be wrong by the ratio
`factor_now / median_window(factor)`, which over the market is a median 1.1%
error but p90 20% and max 207% — 21% of names would carry a >5% volume
error into VMA/VSTD/VSUM. Recovering `C` instead makes it exact.

**Amount.** `canonical_amount ≈ U(sym) * canonical_volume * canonical_vwap`
with a per-stock constant `U` (measured CV ~0.008, the residual being the
source's own rounding). Alpha158 does not read `$amount` at all — verified
against `Alpha158DL.get_feature_config` — but `build_universe` filters on a
20-day mean of it, so it is written rather than left NULL; one approximate
day in a 20-day mean moves the filter by ~0.05%.

Safety rules
------------
- The overlay never invents a bar. A suspended name (no trades: Tencent
  returns open/high/low = 0) is OMITTED and listed in the manifest. A name
  with no canonical T-1 anchor is omitted for the same reason — there is no
  scale to bridge onto.
- Validation gates run before anything is published, and a failure means NO
  overlay row for that session at all (§四: a stale ranking must not be
  dressed up as a fresh one). `pipeline/signals` re-checks independently.
- Writes are atomic (temp file + os.replace) and idempotent per session.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OVERLAY_DIR = PROJECT_ROOT / "data" / "parquet" / "overlay"
OVERLAY_BARS = OVERLAY_DIR / "daily_overlay.parquet"
CALENDAR_EXTRA = OVERLAY_DIR / "calendar_extra.parquet"
ANCHOR_PATH = OVERLAY_DIR / "market_anchor.parquet"
MANIFEST = OVERLAY_DIR / "overlay_manifest.json"

DAILY_DIR = PROJECT_ROOT / "data" / "parquet" / "daily"
SCALE_PATH = PROJECT_ROOT / "data" / "parquet" / "market" / "market_scale.parquet"

#: A live `prev_close` that disagrees with canonical's T-1 close by more than
#: this is a corporate action, not a data error. Measured 2026-10-12:
#: 99.73% of the market sat within 1e-7 (float noise), with a clean gap to
#: the action cases (smallest real action was 0.95%).
ACTION_TOL = 2e-3

#: Publish gates. Coverage is computed against the symbols that traded at
#: T-1, because those are exactly the names the model could have ranked.
MIN_COVERAGE = 0.90
MIN_TRADED = 1000


class OverlayRefused(RuntimeError):
    """Raised when validation fails — nothing is published."""


# ---------------------------------------------------------------------------
# anchor: per-symbol unit constants, derived from canonical + market_scale
# ---------------------------------------------------------------------------

def build_anchor(rebuild: bool = False) -> pd.DataFrame:
    """Per-symbol `C` (volume scale) and `U` (amount scale).

    Recomputed only when canonical or the scale table changes; the inputs'
    digest is stored next to the result.
    """
    inputs = _anchor_inputs_digest()
    if not rebuild and ANCHOR_PATH.exists():
        try:
            have = json.loads(
                (OVERLAY_DIR / "market_anchor.json").read_text(encoding="utf-8"))
            if have.get("inputs") == inputs:
                return pd.read_parquet(ANCHOR_PATH)
        except Exception:                                       # noqa: BLE001
            pass

    scale = pd.read_parquet(SCALE_PATH)
    scale = scale[scale["scale_volume"].notna() & (scale["scale_volume"] > 0)]
    scale = scale.drop_duplicates("symbol")
    bars = _read_canonical(cols=["symbol", "trade_date", "factor", "volume",
                                 "amount", "vwap"], min_year=2020)

    # C = median_window(factor) / scale_volume, using each row's OWN window
    # (the table has a few rows calibrated over a different span).
    med_frames = []
    for (lo, hi), grp in scale.groupby(["window_start", "window_end"],
                                       dropna=False):
        if pd.isna(lo) or pd.isna(hi):
            continue
        w = bars[(bars["trade_date"] >= pd.Timestamp(lo))
                 & (bars["trade_date"] <= pd.Timestamp(hi))]
        if w.empty:
            continue
        m = w.groupby("symbol")["factor"].median().rename("f_med")
        sub = grp[["symbol"]].copy()
        sub["f_med"] = sub["symbol"].map(m)
        med_frames.append(sub)
    if not med_frames:
        raise OverlayRefused("market_scale 表没有可用的窗口，无法推导 volume 锚点")
    f_med = pd.concat(med_frames).dropna().drop_duplicates("symbol") \
        .set_index("symbol")["f_med"]

    anchor = scale.set_index("symbol")[["scale_volume"]].copy()
    anchor["f_med"] = f_med
    anchor = anchor.dropna()
    anchor["C"] = anchor["f_med"] / anchor["scale_volume"]
    anchor["C_source"] = "market_scale"

    # U: canonical_amount / (canonical_volume * canonical_vwap). Median over
    # the stock's own history, so one odd day cannot set the constant.
    good = bars[(bars["volume"] > 0) & (bars["vwap"] > 0)
                & (bars["amount"] > 0)].copy()
    good["U"] = good["amount"] / (good["volume"] * good["vwap"])
    anchor["U"] = good.groupby("symbol")["U"].median()
    anchor["n_U"] = good.groupby("symbol")["U"].size()
    anchor["U"] = anchor["U"].where(anchor["n_U"] >= 5)

    # Symbols the 2026-09-04 calibration never saw (286北交所 + ~70 new
    # listings on 2026-10-12) have no C at all. Recover them for free from a
    # PREVIOUS run's raw snapshot: C = canonical_volume * factor / real_shares
    # for any session the snapshot covered and canonical still holds. Exact,
    # no request, and it accumulates — a symbol only ever needs this once.
    anchor = anchor.reset_index()
    recovered = recover_C_from_snapshots(anchor, bars)
    if len(recovered):
        anchor = anchor.merge(recovered, on="symbol", how="outer")
        anchor["C"] = anchor["C"].fillna(anchor["C_snapshot"])
        anchor["C_source"] = anchor["C_source"].fillna("prior_snapshot")
        anchor = anchor.drop(columns=["C_snapshot"])

    anchor = anchor[["symbol", "C", "U", "scale_volume", "f_med", "n_U",
                     "C_source"]]
    anchor["anchor_version"] = 1
    OVERLAY_DIR.mkdir(parents=True, exist_ok=True)
    anchor.to_parquet(ANCHOR_PATH, index=False)
    (OVERLAY_DIR / "market_anchor.json").write_text(
        json.dumps({"inputs": inputs,
                    "built_at": datetime.now().isoformat(timespec="seconds"),
                    "n_symbols": int(len(anchor)),
                    "n_missing_U": int(anchor["U"].isna().sum())},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    return anchor


def recover_C_from_snapshots(anchor: pd.DataFrame,
                             bars: pd.DataFrame) -> pd.DataFrame:
    """Recover `C` for symbols the scale table never covered.

    `C = canonical_volume(t) * factor(t) / real_shares(t)` is exact for ANY
    session where both sides are known. Every run already persists its raw
    quote snapshot (required for audit), so a symbol missing from
    `market_scale` only has to be missing on its FIRST overlay day: after
    that the previous snapshot supplies the observation for free.

    Returns columns [symbol, C_snapshot] for whatever could be recovered.
    """
    from personal_quant.providers.batch_quote import RAW_DIR

    have = set(anchor.loc[anchor["C"].notna(), "symbol"])
    if not RAW_DIR.exists():
        return pd.DataFrame(columns=["symbol", "C_snapshot"])
    need = set(bars["symbol"]) - have
    if not need:
        return pd.DataFrame(columns=["symbol", "C_snapshot"])

    cidx = bars[bars["volume"] > 0].set_index(["symbol", "trade_date"])
    out: Dict[str, float] = {}
    for path in sorted(RAW_DIR.glob("quotes_*.json")):
        try:
            snap = json.loads(path.read_text(encoding="utf-8"))
            rows = pd.DataFrame(snap.get("quotes") or [])
        except Exception:                                       # noqa: BLE001
            continue
        if rows.empty or "volume_lots" not in rows.columns:
            continue
        rows = rows[rows["symbol"].isin(need - set(out))]
        if rows.empty:
            continue
        session = pd.Timestamp(
            f"{str(path.stem.split('_')[1])[:4]}-"
            f"{str(path.stem.split('_')[1])[4:6]}-"
            f"{str(path.stem.split('_')[1])[6:8]}")
        for _, r in rows.iterrows():
            key = (r["symbol"], session)
            if key not in cidx.index:
                continue                     # that session is not in canonical
            lots = float(r["volume_lots"])
            if lots <= 0:
                continue
            row = cidx.loc[key]
            out[r["symbol"]] = (float(row["volume"]) * float(row["factor"])
                                / (lots * 100.0))
    if not out:
        return pd.DataFrame(columns=["symbol", "C_snapshot"])
    return pd.DataFrame({"symbol": list(out), "C_snapshot": list(out.values())})


def _anchor_inputs_digest() -> str:
    h = hashlib.sha256()
    from personal_quant.providers.batch_quote import RAW_DIR

    for p in sorted(DAILY_DIR.glob("*.parquet")) + [SCALE_PATH] \
            + sorted(RAW_DIR.glob("quotes_*.json")):
        if p.exists():
            st = p.stat()
            h.update(f"{p.name}:{st.st_size}:{int(st.st_mtime)}".encode())
    return h.hexdigest()[:16]


# ---------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------

def _read_canonical(cols=None, min_year: Optional[int] = None) -> pd.DataFrame:
    parts = []
    for p in sorted(DAILY_DIR.glob("*.parquet")):
        if min_year is not None and p.stem[-4:].isdigit() \
                and int(p.stem[-4:]) < min_year:
            continue
        parts.append(pd.read_parquet(p, columns=cols))
    if not parts:
        raise OverlayRefused("canonical daily 目录为空")
    df = pd.concat(parts, ignore_index=True)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def canonical_last_date() -> Optional[pd.Timestamp]:
    """Newest session present in the CANONICAL layer (overlay excluded)."""
    best = None
    for p in sorted(DAILY_DIR.glob("*.parquet")):
        d = pd.read_parquet(p, columns=["trade_date"])["trade_date"]
        if len(d):
            m = pd.Timestamp(d.max())
            best = m if best is None or m > best else best
    return best


def _known_sessions() -> pd.DatetimeIndex:
    """Sessions the system already believes in (calendar + overlay extras)."""
    from pipeline.freshness import trading_calendar

    return trading_calendar()


#: The A-share continuous session ends at 15:00 Asia/Shanghai (the closing
#: auction print lands at 15:00). A feed whose newest timestamp is earlier
#: than this is showing a session still in progress.
SESSION_CLOSE = "150000"


def feed_session(batch) -> Tuple[pd.Timestamp, str]:
    """The session the feed itself claims, plus its newest timestamp.

    The session is taken FROM THE DATA rather than from the wall clock or
    the trading calendar. Neither of those can answer "is today a session?":
    the calendar ships with the snapshot and ends at T-1 by construction, and
    the wall clock says nothing about holidays.
    """
    stamps = batch.quotes["quote_time"].dropna().astype(str)
    if stamps.empty:
        raise OverlayRefused("行情里没有可用时间戳，无法确认 session")
    newest = stamps.max()
    if len(newest) < 14:
        raise OverlayRefused(f"行情时间戳格式异常：{newest!r}")
    day = newest[:8]
    if stamps.str[:8].value_counts().idxmax() != day:
        raise OverlayRefused(
            f"行情时间戳跨了多个 session（最新 {newest}），拒绝猜测目标日")
    return pd.Timestamp(f"{day[:4]}-{day[4:6]}-{day[6:]}"), newest


def ensure_session(target: pd.Timestamp, newest_stamp: str) -> None:
    """`target` must be a session that has actually CLOSED.

    An intraday run would otherwise freeze a half-formed bar into the layer
    the model ranks on — a far worse error than being one session behind.
    """
    if target.weekday() >= 5:
        raise OverlayRefused(
            f"{target.date()} 是周末，不是交易日；overlay 不会凭空造出一个 session")
    if newest_stamp[8:] < SESSION_CLOSE:
        raise OverlayRefused(
            f"{target.date()} 尚未收盘（行情最新时间戳 {newest_stamp}，"
            f"收盘价为 {SESSION_CLOSE[:2]}:{SESSION_CLOSE[2:4]}）—— "
            f"拒绝把盘中的半截 bar 写进模型输入")


# ---------------------------------------------------------------------------
# the bridge
# ---------------------------------------------------------------------------

def bridge(prev: pd.DataFrame, quotes: pd.DataFrame,
           anchor: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    """Turn one whole-market quote set into canonical-schema bars for T."""
    q = quotes.set_index("symbol")
    base = prev.set_index("symbol")
    # build_anchor returns a `symbol` COLUMN (parquet-friendly). Reindexing a
    # RangeIndex against symbol names yields an all-NaN anchor silently, so
    # index it here — and assert, because a silent NaN would have written
    # empty volume/amount throughout.
    anchor = anchor.set_index("symbol")

    common = q.index.intersection(base.index)
    missing_anchor = sorted(q.index.difference(base.index))

    df = pd.DataFrame(index=common)
    df["live_close"] = q.loc[common, "close"]
    df["live_prev"] = q.loc[common, "prev_close"]
    df["live_open"] = q.loc[common, "open"]
    df["live_high"] = q.loc[common, "high"]
    df["live_low"] = q.loc[common, "low"]
    df["lots"] = q.loc[common, "volume_lots"]
    df["amount_wan"] = q.loc[common, "amount_wan"]
    df["name"] = q.loc[common, "name"]
    df["prev_close"] = base.loc[common, "close"]
    df["prev_factor"] = base.loc[common, "factor"]

    # suspension / no-trade: the exchange feed reports prices as 0. These are
    # NOT zero-price bars, they are absent bars — omit, never fabricate.
    # `amount_wan > 0` belongs here too: shares cannot trade for zero turnover,
    # so a row with volume but no amount is a broken source row, and letting
    # it through would write vwap = 0.
    traded = ((df["live_close"] > 0) & (df["live_open"] > 0)
              & (df["live_high"] > 0) & (df["live_low"] > 0)
              & (df["lots"] > 0) & (df["amount_wan"] > 0)
              & (df["prev_close"] > 0) & (df["prev_factor"] > 0))
    suspended = sorted(df.index[~traded])
    df = df[traded].copy()
    if df.empty:
        raise OverlayRefused("没有任何标的满足「当日有成交且 T-1 有 canonical 锚点」")

    # --- corporate-action detection: prev_close is the reference price
    action = (df["live_prev"] - df["prev_close"]).abs() / df["prev_close"] \
        > ACTION_TOL

    # --- price bridge
    # Canonical stores RAW prices plus a `factor` column (adjusted = raw *
    # factor) and the feature provider serves raw*factor. Prices are exact
    # cross-source (measured max deviation 0.0 on the overlap day), so the
    # ONLY quantity the overlay has to derive is `factor`: whatever value
    # makes the ADJUSTED series continuous across the gap.
    a1 = df["prev_close"] * df["prev_factor"]                  # adjusted T-1
    ret = df["live_close"] / df["live_prev"] - 1.0
    df["factor"] = (a1 * (1.0 + ret)) / df["live_close"]
    # raw columns pass through untouched
    df["open"] = df["live_open"]
    df["high"] = df["live_high"]
    df["low"] = df["live_low"]
    df["close"] = df["live_close"]
    df["vwap"] = df["amount_wan"] * 1e4 / (df["lots"] * 100.0)

    # --- volume & amount bridge
    c = anchor["C"].reindex(df.index)
    u = anchor["U"].reindex(df.index)
    df["volume"] = c * (df["lots"] * 100.0) / df["factor"]
    df["amount"] = u * df["volume"] * df["vwap"]   # vwap is raw here, and
    # canonical_amount is in canonical units, consistent with volume above.

    # A missing C (or U) means the symbol has no unit calibration at all.
    # The PRICES are still exact — they come from the quote plus the T-1
    # factor — so the bar is kept and only the volume-derived columns go
    # NaN. Writing a guessed scale would be worse than NaN: it would inject
    # a wrong VMA/VSTD for that name, and NaN is what the model already
    # treats as "unknown". Self-heals from the next session onward, because
    # the previous run's snapshot then supplies the exact C.
    no_c = df["volume"].isna()
    symbols = df.index
    report = {
        "corporate_actions": int(action.sum()),
        "corporate_action_symbols": sorted(symbols[action])[:50],
        "suspended": len(suspended),
        "suspended_symbols": suspended[:50],
        "no_anchor": len(missing_anchor),
        "no_anchor_symbols": missing_anchor[:50],
        "missing_C": int(no_c.sum()),
        "missing_C_symbols": sorted(symbols[no_c])[:50],
        "missing_U": int(u.isna().sum()),
    }
    df["symbol"] = symbols
    return df.reset_index(drop=True), report


def validate(df: pd.DataFrame, report: dict, target: pd.Timestamp,
             expected: int) -> dict:
    """Gates that must all pass before anything is published."""
    errs = []

    if len(df) < MIN_TRADED:
        errs.append(f"成交标的只有 {len(df)} 个（下限 {MIN_TRADED}）")
    coverage = len(df) / expected if expected else 0.0
    if coverage < MIN_COVERAGE:
        errs.append(f"覆盖率 {coverage:.1%} 低于下限 {MIN_COVERAGE:.0%}"
                    f"（{len(df)}/{expected}）")

    if df["symbol"].duplicated().any():
        errs.append("symbol 有重复")
    if not (df["factor"] > 0).all():
        errs.append(f"有 {int((df['factor'] <= 0).sum())} 个非正 factor")
    for col in ("open", "high", "low", "close", "vwap"):
        if df[col].isna().any():
            errs.append(f"{col} 有 NaN")

    # OHLC geometry: the bridge scales all four by one positive factor, so a
    # violation here means the SOURCE was broken, not the arithmetic.
    bad_hi = df["high"] < df[["open", "close"]].max(axis=1) - 1e-6
    bad_lo = df["low"] > df[["open", "close"]].min(axis=1) + 1e-6
    if bad_hi.any():
        errs.append(f"{int(bad_hi.sum())} 个标的 high < max(open, close)"
                    f"：{sorted(df.loc[bad_hi, 'symbol'])[:5]}")
    if bad_lo.any():
        errs.append(f"{int(bad_lo.sum())} 个标的 low > min(open, close)"
                    f"：{sorted(df.loc[bad_lo, 'symbol'])[:5]}")

    # The ADJUSTED series is what the model sees, so that is what has to be
    # continuous: adjusted(T)/adjusted(T-1) must equal the live return. This
    # is true by construction, so a violation means the columns got mixed up
    # (raw vs adjusted) rather than a data problem.
    lhs = (df["close"] * df["factor"]) / (df["prev_close"] * df["prev_factor"])
    rhs = df["live_close"] / df["live_prev"]
    drift = (lhs - rhs).abs().max()
    if drift > 1e-6:
        errs.append(f"复权序列不连续：最大漂移 {drift:.2e}")

    # The session must be PROVEN by the feed itself (see ensure_session).
    return {"ok": not errs, "errors": errs, "coverage": round(coverage, 4),
            "n_bars": int(len(df))}


# ---------------------------------------------------------------------------
# writing
# ---------------------------------------------------------------------------

def _atomic_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".parquet.tmp")
    df.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def write_overlay(bars: pd.DataFrame, target: pd.Timestamp,
                  report: dict, validation: dict, batch,
                  raw_path: Optional[Path]) -> pd.DataFrame:
    """Merge this session into the overlay table (idempotent per session)."""
    cols = ["symbol", "trade_date", "open", "high", "low", "close",
            "volume", "amount", "vwap", "factor", "source"]
    out = bars.copy()
    out["trade_date"] = target
    out["source"] = "tencent_batch_quote"
    out = out[cols]

    if OVERLAY_BARS.exists():
        old = pd.read_parquet(OVERLAY_BARS)
        old["trade_date"] = pd.to_datetime(old["trade_date"])
        old = old[old["trade_date"] != target]      # replace this session only
        out = pd.concat([old, out], ignore_index=True)
    out = out.sort_values(["trade_date", "symbol"]).reset_index(drop=True)
    _atomic_parquet(out, OVERLAY_BARS)

    sessions = sorted(out["trade_date"].unique())
    _atomic_parquet(pd.DataFrame({"trade_date": pd.to_datetime(sessions)}),
                    CALENDAR_EXTRA)

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "trade_date": str(target.date()),
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "provider": "tencent_batch_quote",
        "requests": batch.request_count,
        "fetched_at": batch.fetched_at.isoformat(timespec="seconds"),
        "quote_sha256": batch.sha256,
        "raw_snapshot": str(raw_path) if raw_path else None,
        "bars_sha256": hashlib.sha256(
            out[out["trade_date"] == target][cols]
            .to_csv(index=False).encode("utf-8")).hexdigest(),
        "n_bars": int(len(out[out["trade_date"] == target])),
        "coverage": validation["coverage"],
        "report": {k: v for k, v in report.items()},
        "feed_failures": batch.failures[:50],
    }
    hist = []
    if MANIFEST.exists():
        try:
            hist = json.loads(MANIFEST.read_text(encoding="utf-8"))
        except Exception:                                       # noqa: BLE001
            hist = []
    if not isinstance(hist, list):
        hist = []
    hist = [h for h in hist if h.get("trade_date") != str(target.date())]
    hist.append(entry)
    hist.sort(key=lambda h: h["trade_date"])
    MANIFEST.write_text(json.dumps(hist, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    return out


def sync_calendar(target: pd.Timestamp) -> None:
    """Make the new session visible to every calendar consumer.

    `trading_calendar` feeds `factor_prepare` -> `data/derived/factors/
    calendar.parquet` -> `freshness.last_trading_day()` -> the default signal
    date. Without this row the signal refresh would keep asking for T-1 and
    the overlay would never be used. `ingest_calendar()` re-applies the
    overlay's extras after a snapshot swap (see personal_quant.ingest).
    """
    from personal_quant import db

    with db.transaction() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO trading_calendar (exchange, trade_date, "
            "is_open) VALUES ('CN', ?, TRUE)", [target.date()])
    # the view has to be rebuilt or a cached DuckDB connection keeps serving
    # the pre-overlay definition for the rest of the process
    db.refresh_daily_bars_view()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

RECON_PATH = OVERLAY_DIR / "reconciliation.json"


def reconcile(retire: bool = True) -> list:
    """Compare overlay sessions the upstream snapshot has since caught up on.

    `daily_bars` gives the overlay priority on a (symbol, trade_date)
    collision, which is right while the snapshot lags — but the moment the
    snapshot carries session T, the overlay row would SHADOW the
    authoritative one indefinitely. So each session is compared, recorded,
    and then retired from the overlay.

    The comparison is the real deliverable (§五): it is the only direct
    measurement of how far the bridged bar is from the vendor's own, and it
    is what makes the unit constants in this module falsifiable rather than
    merely asserted.
    """
    if not OVERLAY_BARS.exists():
        return []
    ov = pd.read_parquet(OVERLAY_BARS)
    ov["trade_date"] = pd.to_datetime(ov["trade_date"])
    canon = _read_canonical(cols=["symbol", "trade_date", "open", "high",
                                  "low", "close", "volume", "amount", "vwap",
                                  "factor"])
    covered = sorted(set(ov["trade_date"]) & set(canon["trade_date"]))
    if not covered:
        return []

    out, keep = [], ov
    for d in covered:
        o = ov[ov["trade_date"] == d].set_index("symbol")
        c = canon[canon["trade_date"] == d].drop_duplicates("symbol") \
            .set_index("symbol")
        common = o.index.intersection(c.index)
        if not len(common):
            continue
        j = o.loc[common].join(c.loc[common], lsuffix="_o", rsuffix="_c")
        rec = {
            "trade_date": str(pd.Timestamp(d).date()),
            "reconciled_at": datetime.now().isoformat(timespec="seconds"),
            "overlay_rows": int(len(o)),
            "snapshot_rows": int(len(c)),
            "overlap": int(len(common)),
        }
        for col in ("open", "high", "low", "close"):
            a, b = j[f"{col}_o"].astype(float), j[f"{col}_c"].astype(float)
            m = (b > 0) & a.notna()
            if m.any():
                rel = ((a[m] - b[m]).abs() / b[m])
                rec[f"{col}_median_reldiff"] = round(float(rel.median()), 8)
                rec[f"{col}_p99_reldiff"] = round(float(rel.quantile(.99)), 8)
        for col in ("volume", "amount", "factor"):
            a, b = j[f"{col}_o"].astype(float), j[f"{col}_c"].astype(float)
            m = (b > 0) & a.notna()
            if m.any():
                ratio = a[m] / b[m]
                rec[f"{col}_median_ratio"] = round(float(ratio.median()), 6)
                rec[f"{col}_p01_ratio"] = round(float(ratio.quantile(.01)), 6)
                rec[f"{col}_p99_ratio"] = round(float(ratio.quantile(.99)), 6)
        out.append(rec)
        if retire:
            keep = keep[keep["trade_date"] != d]

    if retire and len(keep) != len(ov):
        _atomic_parquet(keep, OVERLAY_BARS)
        sessions = sorted(keep["trade_date"].unique()) if len(keep) else []
        _atomic_parquet(pd.DataFrame({"trade_date": pd.to_datetime(sessions)}),
                        CALENDAR_EXTRA)

    hist = []
    if RECON_PATH.exists():
        try:
            hist = json.loads(RECON_PATH.read_text(encoding="utf-8"))
        except Exception:                                       # noqa: BLE001
            hist = []
    if not isinstance(hist, list):
        hist = []
    done = {h["trade_date"] for h in out}
    hist = [h for h in hist if h.get("trade_date") not in done] + out
    hist.sort(key=lambda h: h["trade_date"])
    RECON_PATH.write_text(json.dumps(hist, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    return out


def overlay_last_date() -> Optional[pd.Timestamp]:
    if not OVERLAY_BARS.exists():
        return None
    d = pd.read_parquet(OVERLAY_BARS, columns=["trade_date"])["trade_date"]
    return pd.Timestamp(d.max()) if len(d) else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None,
                    help="session to build (default: newest calendar session)")
    ap.add_argument("--check", action="store_true",
                    help="report state without fetching or writing")
    ap.add_argument("--force", action="store_true",
                    help="rebuild even if this session is already present")
    ap.add_argument("--rebuild-anchor", action="store_true")
    ap.add_argument("--keep-reconciled", action="store_true",
                    help="对账但保留 overlay 行（默认交还给上游快照）")
    ap.add_argument("--reconcile-only", action="store_true",
                    help="只与上游快照对账，不抓新行情")
    args = ap.parse_args()

    # §五: retire any overlay session the upstream snapshot has caught up on
    # BEFORE reading state, so the numbers printed below describe the
    # post-reconcile layer.
    for rec in reconcile(retire=not args.keep_reconciled):
        print(f"上游快照已包含 {rec['trade_date']}，与本层对账后交还权威："
              f"close 中位相对差 {rec.get('close_median_reldiff')}，"
              f"factor 中位比 {rec.get('factor_median_ratio')}，"
              f"volume 中位比 {rec.get('volume_median_ratio')}")

    last = canonical_last_date()
    ol = overlay_last_date()
    cal = _known_sessions()
    print(f"canonical 最新: {last.date() if last is not None else '—'}")
    print(f"overlay  最新: {ol.date() if ol is not None else '—'}")
    print(f"日历     最新: {cal[-1].date() if len(cal) else '—'}")
    if args.check:
        return 0

    if last is None:
        raise OverlayRefused("canonical 没有任何行情，先跑 market_update")

    anchor = build_anchor(rebuild=args.rebuild_anchor)
    print(f"锚点: {len(anchor)} 个标的（U 缺失 {int(anchor['U'].isna().sum())}）")

    bars = _read_canonical(cols=["symbol", "trade_date", "close", "factor"])
    prev = bars[bars["trade_date"] == last].drop_duplicates("symbol")
    if prev.empty:
        raise OverlayRefused(f"canonical 在 {last} 没有横截面，无法建立锚点")
    print(f"T-1 = {last.date()}，锚定 {len(prev)} 个标的")

    from personal_quant.providers.batch_quote import BatchQuoteProvider

    provider = BatchQuoteProvider()
    batch = provider.fetch_quotes(sorted(prev["symbol"]))
    target, newest_stamp = feed_session(batch)
    print(f"批量行情: {len(batch.quotes)} 只 / {batch.request_count} 次请求；"
          f"行情自称 session = {target.date()}（最新戳 {newest_stamp}）")

    if target <= last:
        print(f"\n行情源最新 session {target.date()} 不晚于 canonical "
              f"{last.date()} —— 没有更新的成交日可补，overlay 不变。")
        return 0

    ensure_session(target, newest_stamp)
    if args.date and pd.Timestamp(args.date) != target:
        raise OverlayRefused(
            f"--date 指定 {args.date}，但行情源返回的是 {target.date()} —— 拒绝")
    if ol is not None and target <= ol and not args.force:
        print(f"overlay 已有 {target.date()}（--force 可重建）")
        return 0

    df, report = bridge(prev, batch.quotes, anchor)
    validation = validate(df, report, target, expected=len(prev))
    print(f"\n桥接: {len(df)} 根 bar，覆盖率 {validation['coverage']:.1%}；"
          f"除权除息 {report['corporate_actions']}，停牌 {report['suspended']}，"
          f"无锚点 {report['no_anchor']}")
    if report["corporate_action_symbols"]:
        print(f"  当日除权除息（prev_close 是参考价）: "
              f"{report['corporate_action_symbols'][:8]}")
    if not validation["ok"]:
        for e in validation["errors"]:
            print(f"  [X] {e}", flush=True)
        raise OverlayRefused(
            f"{target.date()} 的 overlay 未通过校验，**不发布任何数据** —— "
            f"信号日将保持在 {last.date()}，报告会标明它是旧信号。")

    raw_path = provider.save_raw(batch, batch.trade_date)
    out = write_overlay(df, target, report, validation, batch, raw_path)
    sync_calendar(target)
    print(f"\n已写入 {OVERLAY_BARS}（共 {len(out)} 行，"
          f"{len(out['trade_date'].unique())} 个 session）")
    print(f"原始快照 {raw_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
