# -*- coding: utf-8 -*-
"""STEP 7D: forecast engine — horizons, calibration, trend, and the PIT
guarantee (spec §50 forecast tests: test_horizon, test_no_future_leakage,
test_prediction_timestamp)."""

import numpy as np
import pandas as pd
import pytest

from pipeline import forecast as fc


@pytest.fixture
def synth(tmp_path, monkeypatch):
    """Synthetic score history + labels with a KNOWN relationship:
    higher score -> higher forward return."""
    dates = pd.date_range("2023-01-31", periods=30, freq="ME")
    symbols = [f"S{i:03d}" for i in range(40)]
    rows, lab = [], []
    rng = np.random.RandomState(0)
    for d in dates:
        sc = pd.Series(rng.randn(len(symbols)), index=symbols)
        for s in symbols:
            rows.append({"date": d, "symbol": s, "prediction": sc[s],
                         "source": "test"})
            for h in (1, 5, 20):
                # true signal: score explains the forward return
                noise = rng.randn() * 0.02
                lab.append({"date": d, "symbol": s, "horizon": h,
                            "label": 0.01 * sc[s] + noise})
    return pd.DataFrame(rows), pd.DataFrame(lab), dates, symbols


def test_calibration_learns_the_relationship(synth, monkeypatch):
    sh, lb, dates, symbols = synth
    cal = fc.build_calibration(str((dates[-1] + pd.Timedelta(days=60)).date()),
                               score_history=sh, labels=lb)
    assert set(cal["horizon"].unique()) == {1, 5, 20}
    # top bucket must have a higher expected return than the bottom one
    for h in (1, 5, 20):
        ch = cal[cal["horizon"] == h].sort_values("bucket")
        assert ch["expected_return"].iloc[-1] > ch["expected_return"].iloc[0]
        assert ch["n_obs"].min() > 0
        assert (ch["q05"] <= ch["q50"]).all()
        assert (ch["q50"] <= ch["q95"]).all()
        assert ch["p_up"].between(0, 1).all()


def test_horizons_present_in_forecast(synth):
    sh, lb, dates, symbols = synth
    as_of = str((dates[-1] + pd.Timedelta(days=60)).date())
    cal = fc.build_calibration(as_of, score_history=sh, labels=lb)
    scores = pd.DataFrame({"symbol": symbols,
                           "prediction": np.linspace(-2, 2, len(symbols)),
                           "name": symbols})
    f = fc.forecast_scores(scores, cal, as_of)
    assert sorted(f["horizon"].unique()) == [1, 5, 20]
    top = f[(f["symbol"] == symbols[-1]) & (f["horizon"] == 20)].iloc[0]
    bottom = f[(f["symbol"] == symbols[0]) & (f["horizon"] == 20)].iloc[0]
    assert top["expected_return"] > bottom["expected_return"]
    assert top["trend"] == "up"
    assert set(f["trend"].unique()) <= {"up", "down", "flat", "unknown"}


def test_embargo_drops_open_windows(synth):
    """An observation whose forward window has not closed before as_of is
    excluded — otherwise the calibration would need future prices."""
    sh, lb, dates, symbols = synth
    as_of = pd.Timestamp(dates[-1] + pd.Timedelta(days=3))
    cal = fc.build_calibration(str(as_of.date()), labels=lb,
                               score_history=sh)
    # the embargo uses the same calendar-day slack as the implementation:
    # window_end = signal_date + 2*horizon days must be < as_of
    kept = [d for d in dates
            if d + pd.Timedelta(days=40) < as_of]
    expected_20 = len(kept) * len(symbols)
    got_20 = cal[cal["horizon"] == 20]["n_obs"].sum()
    assert got_20 == expected_20
    assert len(kept) < len(dates)                 # the embargo did bite

    cal_late = fc.build_calibration(
        str((dates[-1] + pd.Timedelta(days=90)).date()), labels=lb,
        score_history=sh)
    assert cal_late[cal_late["horizon"] == 20]["n_obs"].sum() == \
        len(dates) * len(symbols)                 # everything has closed


def test_no_future_leakage_poisoning(synth):
    """Poisoning everything AFTER as_of must not change the calibration."""
    sh, lb, dates, symbols = synth
    as_of = dates[20]
    cal_clean = fc.build_calibration(str(as_of.date()), score_history=sh,
                                     labels=lb)

    sh_poison = sh.copy()
    lb_poison = lb.copy()
    sh_poison.loc[sh_poison["date"] > as_of, "prediction"] *= 1000.0
    lb_poison.loc[lb_poison["date"] > as_of, "label"] *= 1000.0
    cal_poison = fc.build_calibration(str(as_of.date()),
                                      score_history=sh_poison,
                                      labels=lb_poison)
    pd.testing.assert_frame_equal(
        cal_clean.sort_values(["horizon", "bucket"]).reset_index(drop=True),
        cal_poison.sort_values(["horizon", "bucket"]).reset_index(drop=True))


def test_calibration_empty_before_any_history(synth):
    sh, lb, dates, symbols = synth
    cal = fc.build_calibration("2022-01-01", score_history=sh, labels=lb)
    assert cal.empty


def test_forecast_records_timestamp_and_version(synth):
    sh, lb, dates, symbols = synth
    as_of = str((dates[-1] + pd.Timedelta(days=60)).date())
    cal = fc.build_calibration(as_of, score_history=sh, labels=lb)
    scores = pd.DataFrame({"symbol": symbols,
                           "prediction": np.linspace(-1, 1, len(symbols))})
    f = fc.forecast_scores(scores, cal, as_of)
    assert (f["signal_date"] == as_of).all()
    assert (f["forecast_version"] == fc.FORECAST_VERSION).all()


def test_trend_classification():
    assert fc.trend_of(0.02, 0.6) == "up"
    assert fc.trend_of(-0.02, 0.4) == "down"
    assert fc.trend_of(0.0005, 0.51) == "flat"
    assert fc.trend_of(0.02, 0.4) == "flat"        # return up but odds < 50%


def test_model_info_is_versioned():
    info = fc.ForecastModelInfo().as_dict()
    for key in ("name", "base_model", "training_period", "features",
                "method", "horizons"):
        assert info.get(key)
    assert info["horizons"] == [1, 5, 20]


def test_bucket_labels_are_rank_based():
    s = pd.Series([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    b = fc._bucket_labels(s, 5)
    assert b.min() == 1 and b.max() == 5
    assert b.iloc[0] <= b.iloc[-1]
    # rescaled scores give the same buckets (rank-based, scale-free)
    assert (fc._bucket_labels(s * 100, 5) == b).all()


def test_forecast_for_symbol_reads_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(fc, "FORECAST_DIR", tmp_path)
    df = pd.DataFrame({
        "signal_date": ["2026-09-10"] * 3, "symbol": ["600519.SH"] * 3,
        "horizon": [1, 5, 20], "expected_return": [0.003, 0.018, 0.064],
        "p_up": [0.54, 0.61, 0.68], "trend": ["up", "up", "up"]})
    df.to_parquet(tmp_path / "forecast_latest.parquet", index=False)
    got = fc.forecast_for_symbol("600519.SH")
    assert list(got["horizon"]) == [1, 5, 20]
    assert got["expected_return"].iloc[-1] == pytest.approx(0.064)
