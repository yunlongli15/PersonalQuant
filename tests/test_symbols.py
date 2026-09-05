# -*- coding: utf-8 -*-
"""Symbol normalization tests."""

import pytest

from personal_quant.errors import InvalidSymbolError
from personal_quant.symbols import (
    bare_code,
    exchange_of,
    is_valid_symbol,
    normalize_symbol,
    qlib_symbol,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("600519.SH", "600519.SH"),
        ("SH600519", "600519.SH"),
        ("sh600519", "600519.SH"),
        ("600519", "600519.SH"),
        ("000001.SZ", "000001.SZ"),
        ("SZ000001", "000001.SZ"),
        ("000001", "000001.SZ"),
        ("300750.SZ", "300750.SZ"),
        ("688981", "688981.SH"),
        ("430017.BJ", "430017.BJ"),
        ("BJ430017", "430017.BJ"),
        ("430017", "430017.BJ"),
        (" 600519.SH ", "600519.SH"),
    ],
)
def test_normalize_symbol(raw, expected):
    assert normalize_symbol(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "abc", "60051", "6005191", "600519.SS", "SH60051X", "1234.SH", None, "SH600519.SH"],
)
def test_invalid_symbols(raw):
    with pytest.raises(InvalidSymbolError):
        normalize_symbol(raw)


def test_helpers():
    assert qlib_symbol("600519.SH") == "SH600519"
    assert bare_code("SZ000001") == "000001"
    assert exchange_of("430017.BJ") == "BJ"
    assert is_valid_symbol("600519.SH") is True
    assert is_valid_symbol("nonsense") is False


def test_roundtrip():
    for s in ["600519.SH", "000001.SZ", "430017.BJ", "688981.SH", "300750.SZ"]:
        assert normalize_symbol(qlib_symbol(s)) == s
