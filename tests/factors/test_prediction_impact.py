# -*- coding: utf-8 -*-
"""预测影响：一个候选因子如果根本没改变模型输出，就不该被当成"有增量"。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from incremental.engine import prediction_impact


def _preds(values, dates=None):
    dates = dates or pd.date_range("2021-01-31", periods=4, freq="ME")
    syms = [f"S{i:03d}" for i in range(60)]
    rows = []
    for d in dates:
        rows.append(pd.DataFrame({"date": d, "symbol": syms,
                                  "prediction": values}))
    return pd.concat(rows, ignore_index=True)


def test_identical_predictions_mean_no_impact():
    a = _preds(np.linspace(0, 1, 60))
    r = prediction_impact(a, a.copy())
    assert r["prediction_corr"] == pytest.approx(1.0)
    assert r["prediction_delta"] == pytest.approx(0.0)
    assert r["topk_turnover"] == pytest.approx(0.0)


def test_a_few_changed_names_show_up_as_topk_turnover():
    v = np.linspace(0, 1, 60)
    a = _preds(v)
    v2 = v.copy()
    v2[:5] = v2[:5] + 10.0          # 5 只票被推到最前
    b = _preds(v2)
    r = prediction_impact(a, b, top_k=20)
    assert r["topk_turnover"] == pytest.approx(5 / 20)
    assert r["prediction_corr"] < 1.0
    assert r["prediction_delta"] > 0


def test_rank_based_not_scale_based():
    """整体线性放缩不改变次序 -> corr=1、top-k 不动。

    用 |Δz| 而不是 |Δ原始值|，否则"模型整体放大"会被误判成有影响。
    """
    v = np.linspace(0, 1, 60)
    r = prediction_impact(_preds(v), _preds(v * 100.0 + 7.0))
    assert r["prediction_corr"] == pytest.approx(1.0)
    assert r["topk_turnover"] == pytest.approx(0.0)
    assert r["prediction_delta"] == pytest.approx(0.0, abs=1e-9)


def test_no_dates_returns_empty_marker():
    a = _preds(np.linspace(0, 1, 60))
    b = a[a["symbol"] < "S000"]      # 交集为空
    assert prediction_impact(a, b).get("n_dates", 0) == 0
