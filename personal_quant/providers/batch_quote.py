# -*- coding: utf-8 -*-
"""Whole-market **batch** quote provider (same-session OHLCV).

Why this exists (2026-10-12)
----------------------------
The canonical daily layer is built from the `chenditc/investment_data`
snapshot, whose newest data is the PREVIOUS session (the release for trade
date T is published around 00:40 CST on T+1). So on any evening the model
could only rank with T-1 data, while tomorrow's fills happen at T+1 open —
the entry band was stale by one session (2026-09-22 user feedback, and
again 2026-10-12).

`refresh_live_prices.py` patched this for a handful of candidate symbols by
fetching one stock at a time. That cannot fix the *ranking*: Alpha158 needs
the whole cross-section, and fetching ~5,500 names one by one at the
project's politeness delay takes 1.5-2.5 hours (measured: 0.48 s/symbol
even with a 0.12 s sleep).

This provider fetches the whole market in **one pass of ~7 requests**.

Measured 2026-10-12 21:xx CST, after the close:

    source                 batch size   full market   note
    ---------------------- -----------  ------------  ---------------------
    qt.gtimg.cn            900/request  6.9 s         <- used here
    hq.sinajs.cn           800/request  2.5 s         cross-check only
    push2.eastmoney.com    n/a          FAILED        WAF: connection dropped
                                                      with no response, even
                                                      at pz=5 (it had worked
                                                      3 minutes earlier)
    push2his (per stock)   n/a          FAILED        WAF
    web.ifzq... /fqkline   per stock    ~45 min       also rate-limits after
                                                      ~200 requests

So: EastMoney is the *documented* preferred source in the STEP 2 notes but
is not dependable, and per-stock kline is excluded by construction. Tencent
`qt.gtimg.cn` is already an approved source in this project (it backs the
valuation snapshot and the daily-history fallback), so the batch layer
reuses it rather than introducing a new vendor.

Field semantics (VERIFIED against canonical, not assumed)
---------------------------------------------------------
* `close`, `open`, `high`, `low` are RAW prices in CNY, 0.01 tick — the
  exchange's own values. Verified on 2026-10-09 for a 229-symbol sample:
  Tencent kline vs canonical agreed to a median relative difference of
  3e-8 and a **maximum of 0.0**.
* `prev` is the previous close, EXCEPT on an ex-rights/ex-dividend day,
  where it is the exchange's **除权除息参考价** (reference price). Verified
  on 2026-10-12: 5,549 of 5,564 symbols had `prev` equal to canonical's raw
  T-1 close (99.7% within 0.1%), and the 15 that did not were exactly the
  day's corporate actions — their names carried the `XD`/`DR` prefix and
  e.g. 688110.SH had canonical T-1 close 104.38 vs `prev` 69.65
  (ratio 1.4986 = a 10送5 split).
  Consequence: `close/prev - 1` is the **true total return**, already
  adjusted for the action. That is what the overlay bridges on.
* `volume` is in 手 (lots of 100 shares) — cross-checked against the kline
  endpoint, which returns the same number.
* `amount` (index 37) is in 万元; index 57 carries the same figure with two
  more digits.

Nothing here writes to the canonical layer; the caller decides what to do
with the numbers.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import pandas as pd
import requests

from .. import config
from ..errors import FetchError
from ..symbols import normalize_symbol

RAW_DIR = config.RAW_DIR / "batch_quote"

QUOTE_URL = "https://qt.gtimg.cn/q="
HEADERS = {
    "User-Agent": config.USER_AGENT,
    "Referer": "https://gu.qq.com/",
}

#: Tencent serves GBK. Requests guesses ISO-8859-1 for text/* without a
#: charset, which turns every stock name into mojibake — decode explicitly.
ENCODING = "gbk"

#: codes per request. 900 answered in 0.4 s during probing; 500 leaves
#: margin and keeps the URL well inside any proxy/GET length limit.
CHUNK = 500

#: index -> output column, per the verified layout above
_FIELDS = {
    1: "name",
    2: "code",
    3: "close",
    4: "prev_close",
    5: "open",
    6: "volume_lots",
    30: "quote_time",
    31: "change",
    32: "pct_chg",
    33: "high",
    34: "low",
    37: "amount_wan",
    38: "turnover",
    49: "volume_ratio",
}


@dataclass
class QuoteBatch:
    """One whole-market snapshot plus the provenance needed to audit it."""

    quotes: pd.DataFrame
    fetched_at: datetime
    request_count: int
    failures: List[str] = field(default_factory=list)
    sha256: str = ""

    @property
    def trade_date(self) -> Optional[str]:
        """The session these quotes describe (from the exchange timestamp).

        Derived from the data, not from the wall clock: a run just after
        midnight, or a holiday, must not label a snapshot with the wrong
        session.
        """
        if self.quotes.empty:
            return None
        t = self.quotes["quote_time"].dropna()
        if t.empty:
            return None
        return str(t.mode().iloc[0])[:8]


def _chunks(seq: Sequence[str], n: int) -> Iterable[Sequence[str]]:
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def _to_tencent(symbol: str) -> str:
    digits, market = normalize_symbol(symbol).split(".")
    return f"{market.lower()}{digits}"


def _parse_line(line: str) -> Optional[dict]:
    """One `v_sh600519="..."` record -> dict, or None if unusable."""
    if '="' not in line or not line.startswith("v_"):
        return None
    head, body = line.split('="', 1)
    parts = body.rstrip('";').split("~")
    if len(parts) <= max(_FIELDS):
        return None                       # short/garbage row: skip, never guess
    tx = head[len("v_"):].strip()
    digits, market = tx[2:], tx[:2].upper()
    if len(digits) != 6 or market not in ("SH", "SZ", "BJ"):
        return None
    row = {"symbol": f"{digits}.{market}", "tencent_code": tx}
    for idx, col in _FIELDS.items():
        row[col] = parts[idx]
    return row


def _numeric(df: pd.DataFrame, cols: Sequence[str]) -> pd.DataFrame:
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


class BatchQuoteProvider:
    """Whole-market same-session quotes via Tencent's batch endpoint."""

    name = "tencent_batch_quote"

    def __init__(self, chunk: int = CHUNK, attempts: int = 3):
        self.chunk = chunk
        self.attempts = attempts
        #: filled by fetch_quotes(); surfaced in the manifest so a silently
        #: partial run can never look like a complete one
        self.failures: List[str] = []

    # ------------------------------------------------------------------
    def fetch_quotes(self, symbols: Sequence[str]) -> QuoteBatch:
        """Fetch quotes for `symbols` (canonical spelling).

        Raises FetchError when an entire chunk is unreachable after retries —
        a partial cross-section must never be mistaken for the market.
        """
        config.require_online("fetch_quotes")
        symbols = list(dict.fromkeys(symbols))
        if not symbols:
            raise ValueError("fetch_quotes called with an empty symbol list")

        self.failures = []
        rows: List[dict] = []
        requests_made = 0
        chunks = list(_chunks(symbols, self.chunk))
        for i, chunk in enumerate(chunks, 1):
            rows.extend(self._fetch_chunk(chunk))
            requests_made += 1
            if i < len(chunks):
                # polite, deterministic spacing between requests
                time.sleep(config.MIN_DELAY_SECONDS * 0.3)

        df = pd.DataFrame(rows).drop_duplicates(subset=["symbol"])
        if df.empty:
            raise FetchError(
                f"batch quote returned no usable rows for {len(symbols)} "
                f"symbols ({len(chunks)} requests)")
        df = _numeric(df, ["close", "prev_close", "open", "high", "low",
                           "volume_lots", "amount_wan", "change", "pct_chg",
                           "turnover", "volume_ratio"])
        df["exchange"] = df["symbol"].str.split(".").str[1]
        df["source"] = self.name

        missing = sorted(set(symbols) - set(df["symbol"]))
        self.failures.extend(missing[:200])
        return QuoteBatch(quotes=df, fetched_at=datetime.now(),
                          request_count=requests_made,
                          failures=list(self.failures),
                          sha256=_content_hash(df))

    # ------------------------------------------------------------------
    def _fetch_chunk(self, chunk: Sequence[str]) -> List[dict]:
        url = QUOTE_URL + ",".join(_to_tencent(s) for s in chunk)
        last: Optional[Exception] = None
        for attempt in range(1, self.attempts + 1):
            try:
                resp = requests.get(url, headers=HEADERS,
                                    timeout=config.HTTP_TIMEOUT)
                if resp.status_code != 200:
                    raise FetchError(f"batch quote HTTP {resp.status_code}")
                resp.encoding = ENCODING
                out = []
                for line in resp.text.strip().splitlines():
                    row = _parse_line(line)
                    if row is not None:
                        out.append(row)
                if not out:
                    raise FetchError("batch quote returned no parsable rows")
                return out
            except Exception as e:                              # noqa: BLE001
                last = e
                if attempt < self.attempts:
                    time.sleep(config.BACKOFF_FACTOR ** attempt)
        raise FetchError(
            f"batch quote chunk of {len(chunk)} symbols failed after "
            f"{self.attempts} attempts: {type(last).__name__}: {last}")

    # ------------------------------------------------------------------
    def save_raw(self, batch: QuoteBatch, trade_date: str) -> Path:
        """Persist the raw snapshot (immutable per trade date).

        Overwriting a stored session would destroy the only independent
        record of what the feed said at the time — the very thing the
        reconciliation against the upstream snapshot needs (§五). A repeat
        run for the same session with different bytes is written alongside
        as `<date>_<n>.json` rather than replacing the first one.
        """
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "provider": self.name,
            "trade_date": trade_date,
            "fetched_at": batch.fetched_at.isoformat(timespec="seconds"),
            "request_count": batch.request_count,
            "failures": batch.failures,
            "sha256": batch.sha256,
            "quotes": json.loads(
                batch.quotes.to_json(orient="records", force_ascii=False,
                                     date_format="iso")),
        }
        base = RAW_DIR / f"quotes_{trade_date}.json"
        target = base
        n = 1
        while target.exists():
            existing = json.loads(target.read_text(encoding="utf-8"))
            if existing.get("sha256") == batch.sha256:
                return target                    # idempotent re-run
            n += 1
            target = RAW_DIR / f"quotes_{trade_date}_{n}.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                          encoding="utf-8")
        return target


def _content_hash(df: pd.DataFrame) -> str:
    """Stable digest of the parsed content (order-independent)."""
    cols = ["symbol", "close", "prev_close", "open", "high", "low",
            "volume_lots", "amount_wan"]
    sub = df[sorted(cols)].sort_values("symbol")
    return hashlib.sha256(
        sub.to_csv(index=False).encode("utf-8")).hexdigest()
