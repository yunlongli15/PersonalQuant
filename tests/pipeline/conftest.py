# -*- coding: utf-8 -*-
"""Pipeline tests use a temporary job store and synthetic parquet trees —
never the real data/ directories, and never the network."""

from pathlib import Path

import pandas as pd
import pytest

from pipeline import jobs


@pytest.fixture
def jobstore(tmp_path):
    conn = jobs.connect(tmp_path / "jobs_test.db")
    yield conn
    conn.close()


@pytest.fixture
def fake_data_tree(tmp_path, monkeypatch):
    """A miniature data/ tree so freshness probes have something to read."""
    root = tmp_path / "data"
    (root / "parquet" / "daily").mkdir(parents=True)
    (root / "parquet" / "valuation").mkdir(parents=True)
    (root / "derived" / "factors").mkdir(parents=True)
    (root / "derived" / "news").mkdir(parents=True)

    cal = pd.DataFrame({"trade_date": pd.bdate_range("2026-08-31",
                                                     "2026-09-10")})
    cal.to_parquet(root / "derived" / "factors" / "calendar.parquet",
                   index=False)
    pd.DataFrame({
        "symbol": ["600519.SH"] * 3,
        "trade_date": pd.to_datetime(["2026-09-08", "2026-09-09",
                                      "2026-09-10"]),
        "close": [1700.0, 1710.0, 1725.0],
    }).to_parquet(root / "parquet" / "daily" / "part.parquet", index=False)
    pd.DataFrame({
        "symbol": ["600519.SH"],
        "trade_date": pd.to_datetime(["2026-09-10"]),
        "pe": [30.0],
    }).to_parquet(root / "parquet" / "valuation" / "part.parquet",
                  index=False)
    pd.DataFrame({
        "symbol": ["600519.SH"], "fiscal_year": [2025],
        "availability_date": pd.to_datetime(["2026-04-01"]),
        "metric_name": ["revenue"], "metric_value": [1.0e11],
    }).to_parquet(root / "derived" / "factors" / "financial_metrics.parquet",
                  index=False)
    pd.DataFrame({
        "event_id": ["e1"], "symbol": ["600519.SH"],
        "publication_time": pd.to_datetime(["2026-09-09 19:30:00"]),
        "availability_time": pd.to_datetime(["2026-09-10 09:30:00"]),
    }).to_parquet(root / "derived" / "news" / "news_events.parquet",
                  index=False)

    from pipeline import freshness

    monkeypatch.setattr(freshness, "PARQUET", root / "parquet")
    monkeypatch.setattr(freshness, "DERIVED", root / "derived")
    monkeypatch.setattr(freshness, "PROJECT_ROOT", tmp_path)
    return root
