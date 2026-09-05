# -*- coding: utf-8 -*-
"""Canonical symbol handling.

Canonical form: DIGITS.EXCHANGE, e.g. ``600519.SH``, ``000001.SZ``,
``430017.BJ``. Qlib uses the market-prefix form (``SH600519``); both are
accepted as input, as are bare 6-digit codes with an unambiguous market.
Mixing formats inside the database is forbidden.
"""

import re

from .errors import InvalidSymbolError

_VALID_MARKETS = ("SH", "SZ", "BJ")

# First digits -> default market (used only for bare codes)
_SH_PREFIXES = ("600", "601", "603", "605", "688", "689")
_SZ_PREFIXES = ("000", "001", "002", "003", "300", "301")
_BJ_PREFIXES = ("43", "83", "87", "92")

_SYMBOL_RE = re.compile(r"^\d{6}$")
_QLIB_RE = re.compile(r"^(SH|SZ|BJ)(\d{6})$", re.IGNORECASE)
_CANON_RE = re.compile(r"^(\d{6})\.(SH|SZ|BJ)$", re.IGNORECASE)


def infer_market(digits: str) -> str:
    """Infer the market from the numeric code. Raises if ambiguous/unknown."""
    if digits.startswith(_SH_PREFIXES):
        return "SH"
    if digits.startswith(_SZ_PREFIXES):
        return "SZ"
    if digits.startswith(_BJ_PREFIXES):
        return "BJ"
    raise InvalidSymbolError(
        f"cannot infer market for code {digits!r}; pass the explicit form "
        "e.g. 'SH600519' or '600519.SH'"
    )


def normalize_symbol(symbol: str) -> str:
    """Normalize any supported symbol spelling to canonical ``DIGITS.EXCHANGE``.

    Accepted inputs: ``600519.SH`` / ``SH600519`` / ``sh600519`` / ``600519``
    (bare codes need an unambiguous market prefix).
    """
    if symbol is None:
        raise InvalidSymbolError("symbol is None")
    s = str(symbol).strip()
    if _CANON_RE.match(s):
        digits, market = s.split(".")
        return f"{digits}.{market.upper()}"
    m = _QLIB_RE.match(s)
    if m:
        market, digits = m.groups()
        return f"{digits}.{market.upper()}"
    if _SYMBOL_RE.match(s):
        return f"{s}.{infer_market(s)}"
    raise InvalidSymbolError(
        f"invalid symbol {symbol!r}; expected '600519.SH', 'SH600519' or '600519'"
    )


def qlib_symbol(symbol: str) -> str:
    """Convert to the Qlib instrument spelling (market prefix, e.g. SH600519)."""
    digits, market = normalize_symbol(symbol).split(".")
    return f"{market}{digits}"


def bare_code(symbol: str) -> str:
    """Return the 6-digit code only."""
    return normalize_symbol(symbol).split(".")[0]


def exchange_of(symbol: str) -> str:
    return normalize_symbol(symbol).split(".")[1]


def is_valid_symbol(symbol: str) -> bool:
    try:
        normalize_symbol(symbol)
        return True
    except InvalidSymbolError:
        return False
