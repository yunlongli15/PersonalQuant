# -*- coding: utf-8 -*-
"""Symbol mapping: raw provider codes -> canonical 600519.SH form."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from news.providers.cninfo import _column_for
from news.providers.sse import _parse_dt as sse_parse
from news.providers.szse import _parse_dt as szse_parse


def test_canonical_symbol_via_providers(monkeypatch):
    from personal_quant.symbols import normalize_symbol

    # SSE/SZSE providers map 6-digit codes through normalize_symbol
    from news.providers.sse import SSEProvider

    p = SSEProvider.__new__(SSEProvider)
    assert normalize_symbol("600519") == "600519.SH"
    assert normalize_symbol("000001") == "000001.SZ"


def test_cninfo_column_selection():
    assert _column_for("600519.SH") == "sse"
    assert _column_for("000001.SZ") == "szse"
    assert _column_for(None) == "sse"


def test_sse_timestamp_parse():
    ts, known = sse_parse("2026-08-30 15:31:46")
    assert known and ts.strftime("%H:%M") == "15:31"
    ts2, known2 = sse_parse("2026-08-30 00:00:00")
    assert not known2


def test_szse_timestamp_parse():
    ts, known = szse_parse("2018-01-31 20:19:20")
    assert known and ts.strftime("%H:%M") == "20:19"
    ts2, known2 = szse_parse("2026-09-05 00:00:00")
    assert not known2


def test_cninfo_epoch_ms_parse():
    from news.providers.cninfo import _parse_ms

    import pandas as pd

    # a real intraday time (2026-09-01 10:00 +08) in epoch milliseconds
    ms = pd.Timestamp("2026-09-01 10:00").tz_localize(
        "Asia/Shanghai").value // 1_000_000
    ts, known = _parse_ms(ms)
    assert known and ts.year == 2026 and ts.tzinfo is not None
    # midnight timestamps are date-only (conservative next-day rule)
    ms2 = pd.Timestamp("2026-09-01 00:00").tz_localize(
        "Asia/Shanghai").value // 1_000_000
    _, known2 = _parse_ms(ms2)
    assert not known2


def test_bad_inputs_do_not_crash():
    assert sse_parse(None) == (None, False)
    assert szse_parse("garbage") == (None, False)
    from news.providers.cninfo import _parse_ms

    assert _parse_ms(None) == (None, False)
