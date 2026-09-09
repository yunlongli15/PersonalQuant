# -*- coding: utf-8 -*-
"""Dedup keys, title similarity, novelty."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

from news.dedup import (normalize_title, novelty_scores, title_key,
                        title_similarity)


def test_exact_duplicate_keys_equal():
    k1 = title_key("关于股份回购的公告", "600519.SH", "2025-01-01")
    k2 = title_key("关于股份回购的公告", "600519.SH", "2025-01-01")
    assert k1 == k2


def test_different_symbols_differ():
    assert title_key("公告", "600519.SH", "d") != title_key("公告", "000001.SZ", "d")


def test_similarity_identical_is_one():
    assert title_similarity("关于股份回购的公告", "关于股份回购的公告") == 1.0


def test_similarity_unrelated_is_zero():
    assert title_similarity("关于股份回购的公告", "董事会决议公告") < 0.3


def test_similarity_normalizes_whitespace_and_punct():
    a = "关于股份回购的公告"
    b = " 关于 股份回购 的 公告 "
    assert title_similarity(a, b) > 0.9


def test_novelty_first_occurrence_is_high():
    titles = ["关于股份回购的公告", "董事会决议公告", "监事会决议公告"]
    dates = [pd.Timestamp("2025-01-01")] * 3
    nov = novelty_scores(titles, dates)
    assert nov[0] == 1.0
    assert 0.0 <= nov[1] <= 1.0


def test_novelty_repeat_is_low():
    titles = ["关于股份回购的公告", "关于股份回购的公告（进展）"]
    dates = [pd.Timestamp("2025-01-01"), pd.Timestamp("2025-01-02")]
    nov = novelty_scores(titles, dates)
    assert nov[1] < nov[0]


def test_novelty_window_expires():
    titles = ["关于股份回购的公告", "关于股份回购的公告"]
    dates = [pd.Timestamp("2025-01-01"), pd.Timestamp("2025-03-01")]
    nov = novelty_scores(titles, dates, window_days=30)
    assert nov[1] == 1.0  # outside the window -> novel again
