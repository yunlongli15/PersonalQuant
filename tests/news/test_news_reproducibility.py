# -*- coding: utf-8 -*-
"""News pipeline reproducibility: same inputs -> identical events and
factors; novelty deterministic."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

from news.dedup import novelty_scores
from news.events import extract_events
from news.schema import NewsDocument


def make_docs():
    titles = ["关于股份回购的公告", "2024年年度报告", "关于减持的公告"]
    syms = ["600519.SH", "600519.SH", "000001.SZ"]
    times = ["2025-01-01 10:00", "2025-02-01 10:00", "2025-02-02 10:00"]
    return [NewsDocument(document_id=f"d{i}", source="sse", source_url="u",
                         title=t, symbol=s, published_at=ts)
            for i, (t, s, ts) in enumerate(zip(titles, syms, times))]


def test_event_extraction_deterministic():
    a = extract_events(make_docs())
    b = extract_events(make_docs())
    for x, y in zip(a, b):
        assert x.to_dict() == y.to_dict()


def test_event_ids_deterministic():
    a = extract_events(make_docs())
    b = extract_events(make_docs())
    assert [e.event_id for e in a] == [e.event_id for e in b]


def test_novelty_deterministic():
    titles = ["a公告", "b公告", "a公告进展"]
    dates = [pd.Timestamp("2025-01-01")] * 3
    n1 = novelty_scores(titles, dates)
    n2 = novelty_scores(titles, dates)
    assert n1 == n2
