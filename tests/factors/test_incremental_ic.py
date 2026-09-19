# -*- coding: utf-8 -*-
"""DeltaIC 必须是真的配对差：IC1 − IC0，逐日计算，不是 mean(IC1) − mean(IC0)。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from incremental.engine import candidate_metrics, delta_ic_table


def _preds(seed: int, n_dates: int = 6, n_stocks: int = 200,
           signal: float = 1.0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2021-01-31", periods=n_dates, freq="ME")
    rows = []
    for d in dates:
        label = rng.normal(0, 0.1, n_stocks)
        base = label * signal + rng.normal(0, 0.1, n_stocks)
        rows.append(pd.DataFrame({
            "date": d, "symbol": [f"S{i:04d}" for i in range(n_stocks)],
            "prediction": base, "label": label}))
    return pd.concat(rows, ignore_index=True)


def test_delta_ic_is_paired_difference():
    p0, p1 = _preds(1), _preds(2)
    # 让 p1 与 p0 完全一致 -> DeltaIC 必须恒为 0
    tab = delta_ic_table(p0, p0)
    assert (tab["delta_ic"].abs() < 1e-12).all()
    assert (tab["delta_rank_ic"].abs() < 1e-12).all()
    # 与另一个预测比，DeltaIC 必须等于逐日差
    tab = delta_ic_table(p0, p1)
    assert np.allclose(tab["delta_ic"], tab["ic1"] - tab["ic0"])
    assert np.allclose(tab["delta_rank_ic"],
                       tab["rank_ic1"] - tab["rank_ic0"])


def test_delta_ic_is_not_the_difference_of_means():
    """mean(IC1) − mean(IC0) 与 mean(DeltaIC) 在样本不齐时并不相等；
    协议要的是后者（逐日配对）。"""
    p0, p1 = _preds(3), _preds(4)
    tab = delta_ic_table(p0, p1)
    assert tab["delta_ic"].mean() == pytest.approx(
        (tab["ic1"] - tab["ic0"]).mean())


def test_better_prediction_gets_positive_delta():
    label_src = _preds(5, signal=1.0)
    good = label_src.copy()
    good["prediction"] = good["label"] + np.random.default_rng(6).normal(
        0, 0.02, len(good))          # 几乎完美
    weak = label_src.copy()
    weak["prediction"] = np.random.default_rng(7).normal(0, 1, len(weak))
    tab = delta_ic_table(weak, good)
    assert tab["delta_ic"].mean() > 0.5


def test_pairing_requires_same_dates_and_symbols():
    p0, p1 = _preds(8), _preds(9)
    # 砍掉 p1 一半的行，merge 后只应保留交集
    p1_small = p1[p1["symbol"] < "S0100"]
    tab = delta_ic_table(p0, p1_small)
    assert tab["n"].max() <= 100


def test_candidate_metrics_reports_incremental_fields():
    p0 = _preds(10)
    p1 = p0.copy()
    p1["prediction"] = p1["prediction"] + 0.05 * p1["label"]
    tabs = {"fold1": delta_ic_table(p0, p1)}
    m = candidate_metrics(tabs, [])
    for key in ("delta_ic_mean", "delta_ic_median", "delta_ic_std",
                "delta_icir", "delta_ic_positive_ratio",
                "delta_rank_ic_mean", "delta_rank_ic_median",
                "delta_rank_ic_std", "delta_rank_icir",
                "delta_rank_ic_positive_ratio",
                "positive_fold_ratio", "n_positive_folds"):
        assert key in m, key
    assert m["delta_ic_mean"] > 0
    assert m["ic1_mean"] > m["ic0_mean"]
