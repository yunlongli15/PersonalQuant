# -*- coding: utf-8 -*-
"""walk-forward 折：严格时间外推 + 标签越界保护。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from incremental.engine import build_folds, label_safe_dates


def _calendar(start="2018-01-01", end="2023-12-31"):
    return pd.DatetimeIndex(pd.bdate_range(start, end))


def _month_ends(cal):
    s = pd.Series(cal, index=cal)
    return list(s.groupby(cal.to_period("M")).last())


def _cfg(folds):
    return {"factor_selection_v2": {"walk_forward": {
        "folds": folds, "drop_labels_crossing_fold_end": True}}}


FOLDS = [
    {"name": "fold1", "train": ["2018-01-01", "2019-12-31"],
     "valid": ["2020-01-01", "2020-12-31"]},
    {"name": "fold2", "train": ["2018-01-01", "2020-12-31"],
     "valid": ["2021-01-01", "2021-12-31"]},
]


def test_train_always_precedes_validation():
    cal = _calendar()
    folds = build_folds(_cfg(FOLDS), cal, _month_ends(cal), 20)
    for f in folds:
        assert pd.Timestamp(f.train_end) < pd.Timestamp(f.valid_start)
        assert max(f.train_dates) < min(f.valid_dates)


def test_expanding_window_not_sliding():
    """§4：训练集是**扩张**窗口（都从 2018-01 开始），不是滑动。"""
    cal = _calendar()
    folds = build_folds(_cfg(FOLDS), cal, _month_ends(cal), 20)
    starts = {f.train_start for f in folds}
    assert starts == {"2018-01-01"}
    assert len(folds[1].train_dates) > len(folds[0].train_dates)


def test_train_end_after_valid_start_is_rejected():
    bad = [{"name": "bad", "train": ["2018-01-01", "2021-06-30"],
            "valid": ["2021-01-01", "2021-12-31"]}]
    cal = _calendar()
    with pytest.raises(ValueError, match="必须"):
        build_folds(_cfg(bad), cal, _month_ends(cal), 20)


def test_labels_crossing_fold_end_are_dropped():
    """2021-12-31 的 20 日前瞻收益落到 2022 年，必须剔除。"""
    cal = _calendar("2021-01-01", "2022-06-30")
    ends = _month_ends(cal)
    kept = label_safe_dates(ends, cal, 20, pd.Timestamp("2021-12-31"))
    assert pd.Timestamp("2021-12-31") not in kept
    assert pd.Timestamp("2021-11-30") in kept
    # 每个保留的日期的标签窗口都必须在折内结束
    pos = {d: i for i, d in enumerate(cal)}
    for d in kept:
        assert cal[pos[d] + 20] <= pd.Timestamp("2021-12-31")


def test_dropping_the_boundary_date_loses_exactly_one_month():
    cal = _calendar()
    folds = build_folds(_cfg(FOLDS), cal, _month_ends(cal), 20)
    for f in folds:
        assert len(f.valid_dates) == 11      # 12 个月减掉越界的那一个


def test_all_fold_dates_lie_in_selection_window():
    cal = _calendar()
    folds = build_folds(_cfg(FOLDS), cal, _month_ends(cal), 20)
    for f in folds:
        for d in f.train_dates + f.valid_dates:
            assert pd.Timestamp("2018-01-01") <= d <= pd.Timestamp("2023-12-31")


def test_valid_dates_never_used_for_training_of_a_later_fold_within_itself():
    """同一折内训练与验证不得重叠。"""
    cal = _calendar()
    folds = build_folds(_cfg(FOLDS), cal, _month_ends(cal), 20)
    for f in folds:
        assert not set(f.train_dates) & set(f.valid_dates)


# ---------------------------------------------------------------------------
# 设计矩阵的方向陷阱（踩过两次：step9 的 rank 轴、驱动里的 normalize_panel）
# ---------------------------------------------------------------------------

def _panels(seed=0, n_dates=4, n_syms=120):
    """日期 × 股票的因子面板（与 FACTORS 输出同向）。"""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2021-01-29", periods=n_dates, freq="ME")
    syms = [f"S{i:04d}" for i in range(n_syms)]
    panel = pd.DataFrame(rng.normal(0, 1, (n_dates, n_syms)),
                         index=dates, columns=syms)
    return panel, dates, syms


def test_custom_frames_rank_across_stocks_not_across_factors():
    """每个日期切片必须是**沿股票方向**的横截面 rank。

    如果误用 DataFrame.rank(axis=1)（跨列），单列框架会整体退化成 1.0，
    特征变成常数，DeltaIC 精确为 0 —— 看起来像"因子没用"，其实是没进去。
    """
    from incremental.engine import build_custom_frames

    panel, dates, syms = _panels(seed=1)
    universes = {d: syms for d in dates}
    frames = build_custom_frames({"F": panel}, universes, dates, ["F"])
    for d in dates:
        col = frames[d]["F"]
        assert col.std() > 0, f"{d} 的截面退化成常数"
        assert col.min() > 0 and col.max() <= 1.0
        # 与直接对当日横截面排名一致
        expected = panel.loc[d].reindex(syms).rank(pct=True)
        assert np.allclose(col.to_numpy(), expected.to_numpy())


def test_custom_frames_orientation_matches_the_panel():
    from incremental.engine import build_custom_frames

    panel, dates, syms = _panels(seed=2)
    universes = {d: syms for d in dates}
    frames = build_custom_frames({"F": panel}, universes, dates, ["F"])
    assert set(frames) == set(dates)
    assert list(frames[dates[0]].index) == syms


def test_custom_frames_drops_dates_without_a_universe():
    from incremental.engine import build_custom_frames

    panel, dates, syms = _panels(seed=3)
    universes = {dates[0]: syms}          # 只有一个日期有股票池
    frames = build_custom_frames({"F": panel}, universes, dates, ["F"])
    assert list(frames) == [dates[0]]
