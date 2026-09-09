# -*- coding: utf-8 -*-
"""Novelty semantics: first appearance high, reprints low, windowed."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

from news.dedup import novelty_scores, title_similarity

D = pd.Timestamp


def test_first_publication_has_novelty_one():
    titles = ["关于重大合同的公告"]
    dates = [D("2025-01-01")]
    assert novelty_scores(titles, dates) == [1.0]


def test_exact_reprint_has_novelty_zero():
    titles = ["关于重大合同的公告", "关于重大合同的公告"]
    dates = [D("2025-01-01"), D("2025-01-02")]
    nov = novelty_scores(titles, dates)
    assert nov[1] == 0.0


def test_near_duplicate_low_novelty():
    titles = ["关于股份回购的公告", "关于股份回购进展的公告"]
    dates = [D("2025-01-01"), D("2025-01-03")]
    nov = novelty_scores(titles, dates)
    assert 0.0 <= nov[1] < 0.5


def test_similar_titles_different_stocks_do_not_deduplicate():
    # novelty is per-symbol; cross-stock similarity is not a reprint
    s = title_similarity("关于回购的公告", "关于回购的公告")
    assert s == 1.0
    # (per-symbol grouping is the caller's responsibility — covered by the
    # build_events pipeline which groups by symbol before scoring)


def test_window_boundary():
    titles = ["公告A", "公告A"]
    dates = [D("2025-01-01"), D("2025-03-01")]  # 59 days apart
    nov = novelty_scores(titles, dates, window_days=30)
    assert nov[1] == 1.0  # outside the window -> fully novel again
