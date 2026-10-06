# -*- coding: utf-8 -*-
"""Price-trend forecast engine (STEP 7D).

Design (deliberately NOT a zoo of models — spec §43):

    ONE frozen model  = the production S3 score (Alpha158 + factor_pack_v1
                        + news, trained 2015-2021 — untouched)
    THREE horizons    = 1D / 5D / 20D conditional distributions, estimated
                        from realized forward returns conditioned on the
                        score's cross-sectional bucket

Why conditional distributions instead of three separately trained
models: the frozen score is the system's validated signal; training extra
models would create signals that never passed the STEP 4-6 acceptance
gates, and stacking unvalidated models is exactly what the spec warns
against. Bucketing is rank-based, so it transfers across score scales.

PIT (spec §44): the calibration sample uses only observations whose
realized outcome was complete strictly BEFORE the forecast date
(`as_of`). Poisoning any bar after `as_of` must not move a single number
(tests/pipeline/test_forecast_pit.py).

Outputs are model estimates, never promises: `expected_return` is a
bucket mean, the interval is the bucket's empirical 5-95% range, and
`p_up` is the bucket's historical hit rate.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUANT_DIR = PROJECT_ROOT / "data" / "quant"
FORECAST_DIR = QUANT_DIR / "forecasts"
CALIBRATION_PATH = QUANT_DIR / "forecast_calibration.parquet"
FORECAST_STATE = QUANT_DIR / "forecast_state.json"

HORIZONS = (1, 5, 20)
#: 20 buckets rather than the classic 10: with Top-K selection the
#: candidates all sit in the top decile, and one bucket for the whole
#: candidate set throws away the ranking information the user is looking
#: at. 20 quantile buckets keep ~20k observations each on the available
#: calibration sample, so the estimates stay well determined.
N_BUCKETS = 20
MIN_BUCKET_OBS = 30
FORECAST_VERSION = "forecast_v1"

LABELS_PATH = PROJECT_ROOT / "data" / "derived" / "factors" / "labels.parquet"
RESEARCH_PREDS = (PROJECT_ROOT / "experiments" / "news" / "strategy"
                  / "research_predictions_s3.parquet")
PROD_PREDS = (PROJECT_ROOT / "experiments" / "news" / "strategy"
              / "predictions.parquet")


def production_preds() -> Path:
    """**当前生产策略**自己的样本外预测。

    以前这里写死 S3_v1 的路径。生产策略换成 production_clean_v1 之后，
    如果再拿 S3 的分数去建条件分布，就是把 clean 模型的分数排名映射到
    污染模型的收益分布上 —— 校准和打分函数不是一回事，预测会静默错位。
    """
    from pipeline.signals import PRODUCTION_STRATEGY, strategy_spec

    return strategy_spec(PRODUCTION_STRATEGY)["model_path"].parent         / "predictions.parquet"


def research_walkforward_applies() -> bool:
    """走查研究段（2018-2021）只对 S3 成立 —— 那是 S3 的分数。

    换成别的打分函数时必须整段丢弃，不能"补一段"进来：
    两种分数分布混在一张校准表里，等于让分位数桶同时代表两件事。
    """
    from pipeline.signals import PRODUCTION_STRATEGY

    return PRODUCTION_STRATEGY == "S3_v1"


@dataclass
class ForecastModelInfo:
    """Versioning metadata (spec §43)."""
    name: str = "forecast_v1"
    base_model: str = "strategy_v2/S3 (Alpha158+factor_pack_v1+news)"
    model_file: str = "experiments/news/strategy/model.txt"
    training_period: str = "2015-01-01..2021-12-31 (ES 2022) — frozen"
    features: str = "Alpha158 + factor_pack_v1 + factor_pack_news_v1"
    method: str = ("rank-bucket conditional distribution of realized "
                   "forward returns given the frozen score")
    horizons: tuple = HORIZONS
    n_buckets: int = N_BUCKETS

    def as_dict(self) -> dict:
        d = self.__dict__.copy()
        d["horizons"] = list(self.horizons)
        return d


def model_info() -> ForecastModelInfo:
    """按**当前生产策略**填版本信息（而不是写死 S3）。

    改生产策略时这份元数据跟着走 —— 否则预测文件里会写着
    "base_model: S3"，而分数其实来自 clean 模型。
    """
    try:
        from pipeline.signals import PRODUCTION_STRATEGY, strategy_spec

        spec = strategy_spec(PRODUCTION_STRATEGY)
        label = spec.get("features_label") or spec["feature_version"]
        return ForecastModelInfo(
            name=f"forecast_v1[{PRODUCTION_STRATEGY}]",
            base_model=f"{PRODUCTION_STRATEGY} ({label})",
            model_file=spec["model"],
            features=label)
    except Exception:                                          # noqa: BLE001
        return ForecastModelInfo()


# ---------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------

def load_labels(horizons: Sequence[int] = HORIZONS) -> pd.DataFrame:
    """Cached realized forward returns (date, symbol, horizon, label)."""
    df = pd.read_parquet(LABELS_PATH)
    df = df[df["horizon"].isin(list(horizons))].copy()
    df["date"] = pd.to_datetime(df["date"])
    return df


def load_score_history() -> pd.DataFrame:
    """OOS score history: walk-forward research (2018-2021) + production
    model predictions (2022+). Both are out-of-sample by construction."""
    sources = [("production_model", production_preds())]
    if research_walkforward_applies():
        sources.insert(0, ("research_walkforward", RESEARCH_PREDS))
    frames = []
    for label, p in sources:
        if not p.exists():
            continue
        d = pd.read_parquet(p, columns=["date", "symbol", "prediction"])
        d["date"] = pd.to_datetime(d["date"])
        d["source"] = label
        frames.append(d)
    if not frames:
        return pd.DataFrame(columns=["date", "symbol", "prediction",
                                     "source"])
    out = pd.concat(frames, ignore_index=True)
    # earlier sources win on overlap (research walk-forward is the
    # genuinely OOS one); duplicates are dropped, never averaged
    out = out.drop_duplicates(subset=["date", "symbol"], keep="first")
    return out.sort_values(["date", "symbol"]).reset_index(drop=True)


def current_scores(signal_date: Optional[str] = None) -> pd.DataFrame:
    """Today's scores from the signal snapshot (pipeline/signals.py)."""
    from pipeline.signals import load_signals

    df = load_signals()
    if df.empty:
        return df
    if signal_date is not None:
        want = pd.Timestamp(signal_date)
        df = df[pd.to_datetime(df["signal_date"]) == want]
    return df


# ---------------------------------------------------------------------------
# calibration
# ---------------------------------------------------------------------------

def _bucket_labels(scores: pd.Series, n_buckets: int) -> pd.Series:
    """Rank-based bucket id (1..n) — robust to score-scale drift."""
    if scores.nunique() <= 1:
        return pd.Series(1, index=scores.index)
    r = scores.rank(method="first", pct=True)
    b = np.ceil(r * n_buckets).clip(1, n_buckets)
    return b.astype(int)


def build_calibration(as_of: str,
                      horizons: Sequence[int] = HORIZONS,
                      score_history: Optional[pd.DataFrame] = None,
                      labels: Optional[pd.DataFrame] = None,
                      n_buckets: int = N_BUCKETS,
                      embargo_days: int = 20) -> pd.DataFrame:
    """Conditional distributions estimated strictly before `as_of`.

    `embargo_days`: an observation whose forward window had not finished
    by `as_of` is dropped (its realized return needs future prices — the
    standard PIT embargo).

    Returns one row per (horizon, bucket) with the empirical statistics.
    """
    as_of_ts = pd.Timestamp(as_of)
    sh = score_history if score_history is not None else load_score_history()
    lb = labels if labels is not None else load_labels(horizons)
    if sh.empty or lb.empty:
        return pd.DataFrame()

    sh = sh[pd.to_datetime(sh["date"]) < as_of_ts]
    merged = sh.merge(lb, on=["date", "symbol"], how="inner")
    # embargo: the forward window must have closed before as_of
    merged["window_end"] = merged["date"] + pd.to_timedelta(
        merged["horizon"] * 2, unit="D")     # calendar-day slack
    merged = merged[merged["window_end"] < as_of_ts]
    if merged.empty:
        return pd.DataFrame()

    rows = []
    for h, g in merged.groupby("horizon"):
        g = g.dropna(subset=["prediction", "label"])
        if len(g) < MIN_BUCKET_OBS:
            continue
        g = g.copy()
        g["bucket"] = _bucket_labels(g["prediction"], n_buckets)
        for b, gb in g.groupby("bucket"):
            lab = gb["label"]
            rows.append({
                "horizon": int(h), "bucket": int(b), "n_obs": int(len(gb)),
                "expected_return": float(lab.mean()),
                "median_return": float(lab.median()),
                "q05": float(lab.quantile(0.05)),
                "q50": float(lab.quantile(0.50)),
                "q95": float(lab.quantile(0.95)),
                "p_up": float((lab > 0).mean()),
                "std": float(lab.std(ddof=1)) if len(lab) > 1 else None,
                "score_min": float(gb["prediction"].min()),
                "score_max": float(gb["prediction"].max()),
                "calibration_as_of": str(as_of_ts.date()),
            })
    return pd.DataFrame(rows)


def save_calibration(cal: pd.DataFrame) -> Optional[Path]:
    if cal.empty:
        return None
    QUANT_DIR.mkdir(parents=True, exist_ok=True)
    cal.to_parquet(CALIBRATION_PATH, index=False)
    return CALIBRATION_PATH


def load_calibration() -> pd.DataFrame:
    if not CALIBRATION_PATH.exists():
        return pd.DataFrame()
    return pd.read_parquet(CALIBRATION_PATH)


# ---------------------------------------------------------------------------
# forecasts
# ---------------------------------------------------------------------------

def trend_of(expected_return: float, p_up: float) -> str:
    if expected_return > 0.002 and p_up >= 0.5:
        return "up"
    if expected_return < -0.002 and p_up < 0.5:
        return "down"
    return "flat"


CALIB_COLS = ("expected_return", "median_return", "q05", "q50", "q95",
              "p_up", "std")


def _interp_by_percentile(pct: pd.Series, ch: pd.DataFrame) -> pd.DataFrame:
    """Interpolate the calibration statistics across bucket centres.

    Buckets were formed by rank percentile, so bucket b covers
    [(b-1)/n, b/n] of the cross-section. Interpolating at the bucket
    centres keeps the mapping empirical (no extrapolation: values outside
    the range clamp to the nearest bucket) while giving different
    expected returns to ranks that fall in the same coarse bucket — the
    thing that makes a Top-20 list informative rather than 20 identical
    rows.
    """
    n = int(ch["bucket"].max())
    centers = (ch["bucket"].to_numpy() - 0.5) / n
    order = np.argsort(centers)
    centers = centers[order]
    out = pd.DataFrame(index=pct.index)
    for col in CALIB_COLS:
        if col not in ch.columns:
            continue
        values = ch[col].to_numpy()[order]
        mask = ~pd.isna(values)
        if mask.sum() < 2:
            out[col] = np.nan
            continue
        out[col] = np.interp(pct.to_numpy(), centers[mask],
                             values[mask].astype(float))
    out["n_obs"] = ch["n_obs"].min()
    return out


def forecast_scores(scores: pd.DataFrame, cal: pd.DataFrame,
                    signal_date: str) -> pd.DataFrame:
    """Map scores to per-horizon forecasts using the calibration table."""
    if scores.empty or cal.empty:
        return pd.DataFrame()
    s = scores.copy()
    s["_pct"] = s["prediction"].rank(method="first", pct=True)
    out = []
    for h in sorted(cal["horizon"].unique()):
        ch = cal[cal["horizon"] == h].sort_values("bucket")
        if ch.empty:
            continue
        b = _bucket_labels(s["prediction"], int(ch["bucket"].max()))
        merged = pd.concat([s.assign(bucket=b),
                            _interp_by_percentile(s["_pct"], ch)], axis=1)
        merged["horizon"] = h
        merged["signal_date"] = signal_date
        merged["trend"] = [
            trend_of(e, p) if pd.notna(e) and pd.notna(p) else "unknown"
            for e, p in zip(merged["expected_return"], merged["p_up"])]
        merged["forecast_version"] = FORECAST_VERSION
        out.append(merged)
    if not out:
        return pd.DataFrame()
    df = pd.concat(out, ignore_index=True)
    cols = ["signal_date", "symbol", "name", "horizon", "prediction",
            "bucket", "expected_return", "median_return", "q05", "q50",
            "q95", "p_up", "std", "n_obs", "trend", "forecast_version"]
    return df[[c for c in cols if c in df.columns]]


def forecast_for_date(signal_date: str,
                      symbols: Optional[Sequence[str]] = None,
                      scores: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Full flow: scores -> calibration (PIT) -> forecasts."""
    sc = scores if scores is not None else current_scores(signal_date)
    if sc.empty:
        return pd.DataFrame()
    if symbols is not None:
        sc = sc[sc["symbol"].isin(list(symbols))]
    cal = build_calibration(signal_date)
    df = forecast_scores(sc, cal, signal_date)
    if not df.empty and "name" in sc.columns:
        df = df.merge(sc[["symbol", "name"]].drop_duplicates(),
                      on="symbol", how="left")
    return df


def refresh_forecasts(signal_date: Optional[str] = None,
                      top_k: int = 200) -> dict:
    """Job entry point: refresh calibration + forecasts for today."""
    from pipeline.freshness import last_trading_day

    as_of = signal_date or str(last_trading_day().date())
    sc = current_scores()
    if sc.empty:
        raise RuntimeError("no signal snapshot — run signal_refresh first")
    # Vintage guard: forecasting at date D from a signal dated earlier
    # would silently label stale scores as D's forecast (this happened on
    # 2026-09-17 when the signal job timed out and the forecast job ran
    # anyway). Refuse rather than mislabel.
    sig_dates = sorted({str(pd.Timestamp(d).date())
                        for d in sc["signal_date"].unique()})
    if sig_dates != [as_of]:
        raise RuntimeError(
            f"signal snapshot is dated {sig_dates}, not {as_of} — "
            f"refusing to label stale scores as today's forecast; "
            f"run signal_refresh first")
    scores = sc.sort_values("prediction", ascending=False).head(top_k)
    cal = build_calibration(as_of)
    if cal.empty:
        raise RuntimeError("calibration sample is empty (need score history "
                           "+ realized labels)")
    save_calibration(cal)
    df = forecast_scores(scores, cal, as_of)
    if not df.empty and "name" in scores.columns:
        df = df.merge(scores[["symbol", "name"]].drop_duplicates(),
                      on="symbol", how="left")
    FORECAST_DIR.mkdir(parents=True, exist_ok=True)
    p = FORECAST_DIR / f"forecast_{as_of}.parquet"
    df.to_parquet(p, index=False)
    df.to_parquet(FORECAST_DIR / "forecast_latest.parquet", index=False)
    # **版本化副本**（与 signals 同一套思路）。条件分布是"给定某个模型
    # 分数的收益分布"——换模型就换了一份东西。不做版本化的话，切换生产
    # 策略会把正在跑的前瞻实验读到的 target/stop 悄悄换掉：2026-10-06
    # 实测就是这样，`forecast_2026-09-30.parquet` 被 clean 的校准覆盖了，
    # 而 daily_exit_paper_v1 钉的是 S3_v1。
    from pipeline.signals import PRODUCTION_STRATEGY

    (FORECAST_DIR / f"forecast_{PRODUCTION_STRATEGY}_{as_of}.parquet") \
        .write_bytes(p.read_bytes())
    info = model_info()
    state = {"as_of": as_of,
             "computed_at": datetime.now().isoformat(timespec="seconds"),
             "n_symbols": int(df["symbol"].nunique()) if len(df) else 0,
             "n_rows": int(len(df)),
             "calibration_obs": int(cal["n_obs"].sum()),
             "model": info.as_dict()}
    FORECAST_STATE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    return state


def load_forecasts() -> pd.DataFrame:
    p = FORECAST_DIR / "forecast_latest.parquet"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_parquet(p)


def forecast_state() -> dict:
    if not FORECAST_STATE.exists():
        return {}
    return json.loads(FORECAST_STATE.read_text(encoding="utf-8"))


def forecast_for_symbol(symbol: str,
                        signal_date: Optional[str] = None) -> pd.DataFrame:
    """Per-horizon forecast rows for one stock (GUI drill-down)."""
    df = load_forecasts()
    if df.empty:
        return df
    if signal_date:
        df = df[df["signal_date"] == signal_date]
    return df[df["symbol"] == symbol].sort_values("horizon")
