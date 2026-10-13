# -*- coding: utf-8 -*-
"""Whole-market **batch** quote provider, two sources (Tencent + Sina).

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

Why two sources (2026-10-13)
----------------------------
A single source is a single point of failure for the whole evening's
ranking, and the failure mode is not hypothetical: on 2026-10-13 GitHub was
unreachable for 100 seconds and the snapshot download died. The overlay is
what kept that evening usable -- so the overlay itself should not hinge on
one host.

Measured 2026-10-13 (after the close, full market):

    source            batch cap   full market   note
    ----------------- ----------- ------------- ---------------------------
    qt.gtimg.cn       900/req     ~15 s (12)    primary
    hq.sinajs.cn      800/req     ~6 s (7)      fallback; 1500 codes -> HTTP
                                                431 (URL too long)
    push2.eastmoney   n/a         FAILED        WAF: dropped with no response
    fqkline (per stk) n/a         >45 min       rate-limits after ~200 req

Both Chinese sources are already used elsewhere in this project (Tencent
backs the valuation snapshot and the daily-history fallback; Sina backs the
calendar cross-check), so neither is a new vendor relationship.

**The two sources agree**, which is what makes a per-chunk fallback safe
rather than merely convenient. Checked on 300 main-board names, same
session, both decoded independently:

    field        agreement
    -----------  ---------------------------------------------------------
    close        100.0% bit-identical
    open/high/   >=99.7% bit-identical, max relative difference 7e-07
      low/prev
    amount       median relative difference 1.8e-05
    volume       ratio 1.0000 at every percentile; the only 100x outlier
                 was 000300.SH -- the CSI 300 INDEX, which this project
                 already excludes as an index pseudo-symbol

Field semantics (VERIFIED against canonical, not assumed)
---------------------------------------------------------
* RAW prices in CNY. Tencent quote vs canonical agreed on a 229-symbol
  sample to a median relative difference of 3e-8 with a **maximum of 0.0**.
* `prev` is the previous close, EXCEPT on an ex-rights/ex-dividend day,
  where BOTH sources publish the exchange's **除权除息参考价**. Verified
  for both: on 2026-10-13, the four non-action names matched canonical's
  T-1 close to 0.000000, and all eight action names differed by clean
  round dividend amounts (11.360-11.260=0.10, 27.790-27.290=0.50, ...).
  The names also carry the `XD`/`DR` prefix.
  Consequence: `close/prev - 1` is the **true total return** on both
  sources, so the bridge is source-agnostic.
* Units differ between the sources and are NORMALISED HERE to real units:
  volume -> **shares**, amount -> **yuan**. Sina reports 股 / 元
  throughout; Tencent reports 万元 for amount and **手 for volume on every
  board EXCEPT 688/689, where it reports 股** (see `_volume_unit`).
  Normalising at the edge (rather than carrying a `lots`/`wan` convention
  inward) removes a conversion from every consumer and avoids the rounding
  that shares->lots->shares would introduce.
* KNOWN, BOUNDED INCONSISTENCY: the index pseudo-symbols (000300.SH,
  000852.SH, 000905.SH, 000906.SH …) report volume in units that differ
  between the two sources by exactly 100x. An index has no share count, so
  there is no "correct" unit to normalise to; these symbols are excluded
  from the factor universe by `config index_exclude` and never reach the
  model. They are the only remaining cross-source outlier (4 of 5,563).

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
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd
import requests

from .. import config
from ..errors import FetchError
from ..symbols import normalize_symbol

RAW_DIR = config.RAW_DIR / "batch_quote"

TENCENT_URL = "https://qt.gtimg.cn/q="
TENCENT_HEADERS = {
    "User-Agent": config.USER_AGENT,
    "Referer": "https://gu.qq.com/",
}
#: Tencent serves GBK. Requests guesses ISO-8859-1 for text/* without a
#: charset, which turns every stock name into mojibake — decode explicitly.
TENCENT_ENCODING = "gbk"

SINA_URL = "https://hq.sinajs.cn/list="
SINA_HEADERS = {
    "User-Agent": config.USER_AGENT,
    "Referer": "https://finance.sina.com.cn/",
}
SINA_ENCODING = "gbk"

#: Output columns. **Real units**: shares and yuan, not 手 / 万元.
COLUMNS = ["symbol", "name", "close", "prev_close", "open", "high", "low",
           "volume_shares", "amount_yuan", "quote_time", "source"]

#: Per-source chunk size. Tencent answered 900 codes in 0.4 s; Sina returns
#: HTTP 431 (request header fields too large — it is a GET) at 1500 and is
#: fine at 800. Both values leave margin under the observed limit.
TENCENT_CHUNK = 500
SINA_CHUNK = 800


def _chunks(seq: Sequence[str], n: int) -> Iterable[Sequence[str]]:
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def _code(symbol: str) -> str:
    """`600519.SH` -> `sh600519`."""
    digits, market = normalize_symbol(symbol).split(".")
    return f"{market.lower()}{digits}"


def _symbol_of(code: str) -> Optional[str]:
    """`sh600519` -> `600519.SH`, or None when the code is not A-share-ish."""
    if len(code) < 8 or code[:2].upper() not in ("SH", "SZ", "BJ"):
        return None
    digits = code[2:]
    if len(digits) != 6 or not digits.isdigit():
        return None
    return f"{digits}.{code[:2].upper()}"


def _stamp(date_str: str, time_str: str) -> Optional[str]:
    """`2026-10-13` + `15:34:59` -> `20261013153459` (unified with Tencent)."""
    d = str(date_str).replace("-", "")
    t = str(time_str).replace(":", "")
    if len(d) != 8 or not d.isdigit():
        return None
    if len(t) == 6 and t.isdigit():
        return d + t
    return d + "000000"


# ---------------------------------------------------------------------------
# parsers — one per source
# ---------------------------------------------------------------------------

def _parse_tencent(text: str) -> Tuple[List[dict], List[str]]:
    """`v_sh600519="1~名称~600519~..."` records."""
    rows, bad = [], []
    for line in text.strip().splitlines():
        if '="' not in line or not line.startswith("v_"):
            continue
        head, body = line.split('="', 1)
        p = body.rstrip('";').split("~")
        # 6=成交量(手) 30=时间戳 37=成交额(万元)
        if len(p) <= 37:
            bad.append(head[len("v_"):].strip())
            continue
        symbol = _symbol_of(head[len("v_"):].strip())
        if symbol is None:
            bad.append(head[len("v_"):].strip())
            continue
        rows.append({
            "symbol": symbol, "name": p[1],
            "close": _num(p[3]), "prev_close": _num(p[4]),
            "open": _num(p[5]), "high": _num(p[33]), "low": _num(p[34]),
            "volume_shares": _num(p[6]) * _volume_unit(symbol),
            "amount_yuan": _num(p[37]) * 1e4,
            "quote_time": p[30],
            "source": "tencent_batch_quote",
        })
    return rows, bad


def _parse_sina(text: str) -> Tuple[List[dict], List[str]]:
    """`var hq_str_sh600519="名称,今开,昨收,现价,最高,最低,..."` records.

    Index layout: 0=name 1=open 2=prev_close 3=close 4=high 5=low
    8=volume(股) 9=amount(元) 30=date 31=time.
    BSE lines carry 39 fields instead of 34 — only the tail differs, and we
    never read past index 31, so one parser covers all three exchanges.
    """
    rows, bad = [], []
    for line in text.strip().splitlines():
        if '="' not in line or "hq_str_" not in line:
            continue
        code = line.split("hq_str_")[1].split("=")[0].strip()
        f = line.split('="', 1)[1].rstrip('";').split(",")
        symbol = _symbol_of(code)
        # A halted/unknown code comes back as an empty payload: skip it
        # rather than inventing a zero bar.
        if symbol is None or len(f) < 32 or not f[0]:
            bad.append(code)
            continue
        rows.append({
            "symbol": symbol, "name": f[0],
            "open": _num(f[1]), "prev_close": _num(f[2]), "close": _num(f[3]),
            "high": _num(f[4]), "low": _num(f[5]),
            "volume_shares": _num(f[8]),
            "amount_yuan": _num(f[9]),
            "quote_time": _stamp(f[30], f[31]),
            "source": "sina_hq",
        })
    return rows, bad


def _volume_unit(symbol: str) -> float:
    """腾讯的成交量字段是多少股？**按板块不同。**

    科创板（688/689）报的是**股**，其余板块（沪深主板/创业板/北交所）
    报的是**手**。这个差异是被第二个源逼出来的（2026-10-14）：

        688001.SH  close 55.30  腾讯 f6 = 12,123,933  新浪 = 12,123,933
                   成交额两边都是 6.494e8 元（比值 1.000000）
                   成交额 ÷ 收盘价 ≈ 1.17e7 股 —— 与新新浪一致，
                   而 `f6 × 100` 会得到 1.21e9 股（差 100 倍）

    统一乘 100 会让 621 只科创板标的的 volume 大 100 倍，直接污染
    VMA / VSTD / VSUM 这些绝对量特征。注意：**成交额两个源都是万元/元，
    没有这个问题** —— 差异只在成交量字段。
    """
    return 1.0 if symbol[:3] in ("688", "689") else 100.0


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


# ---------------------------------------------------------------------------
# the batch itself
# ---------------------------------------------------------------------------

@dataclass
class QuoteBatch:
    """One whole-market snapshot plus the provenance needed to audit it."""

    quotes: pd.DataFrame
    fetched_at: datetime
    request_count: int
    failures: List[str] = field(default_factory=list)
    sha256: str = ""
    #: which source each row came from, and how many rows per source
    sources: Dict[str, int] = field(default_factory=dict)
    #: source -> why it was abandoned (None when the primary worked)
    fallback_reason: Optional[str] = None

    @property
    def trade_date(self) -> Optional[str]:
        """The session these quotes describe (from the exchange timestamp).

        Derived from the data, not from the wall clock: a run just after
        midnight, or a holiday, must not label a snapshot with the wrong
        session.
        """
        if self.quotes.empty:
            return None
        t = self.quotes["quote_time"].dropna().astype(str)
        if t.empty:
            return None
        return str(t.str[:8].mode().iloc[0])


@dataclass
class _Source:
    name: str
    url: str
    headers: dict
    encoding: str
    chunk: int
    parse: Callable[[str], Tuple[List[dict], List[str]]]


_SOURCES: Tuple[_Source, ...] = (
    _Source("tencent_batch_quote", TENCENT_URL, TENCENT_HEADERS,
            TENCENT_ENCODING, TENCENT_CHUNK, _parse_tencent),
    _Source("sina_hq", SINA_URL, SINA_HEADERS,
            SINA_ENCODING, SINA_CHUNK, _parse_sina),
)


class BatchQuoteProvider:
    """Whole-market same-session quotes, Tencent first, Sina as fallback.

    The fallback is **per chunk**, so one host wobbling does not discard the
    chunks the other host already delivered. Mixing is safe because the two
    agree field-for-field (see the module docstring); each row still carries
    the source it actually came from.
    """

    name = "batch_quote"

    def __init__(self, attempts: int = 3):
        self.attempts = attempts
        self.failures: List[str] = []

    # ------------------------------------------------------------------
    def fetch_quotes(self, symbols: Sequence[str]) -> QuoteBatch:
        config.require_online("fetch_quotes")
        symbols = list(dict.fromkeys(symbols))
        if not symbols:
            raise ValueError("fetch_quotes called with an empty symbol list")

        self.failures = []
        rows: List[dict] = []
        requests_made = 0
        reasons: List[str] = []

        for source in _SOURCES:
            todo = [s for s in symbols
                    if s not in {r["symbol"] for r in rows}]
            if not todo:
                break
            if rows:
                reasons.append(f"{source.name}: 补 {len(todo)} 只")
            chunks = list(_chunks(todo, source.chunk))
            for i, chunk in enumerate(chunks, 1):
                try:
                    got, bad = self._fetch_chunk(source, chunk)
                except FetchError as e:
                    reasons.append(f"{source.name} 不可用（{e}）")
                    break            # 整个源不可用，交给下一个源
                rows.extend(got)
                requests_made += 1
                self.failures.extend(bad[:50])
                if i < len(chunks):
                    time.sleep(config.MIN_DELAY_SECONDS * 0.3)

        df = pd.DataFrame(rows).drop_duplicates(subset=["symbol"])
        if df.empty:
            raise FetchError(
                f"批量行情两个源都没返回可用数据（{len(symbols)} 个标的）—— "
                f"{'；'.join(reasons)}")
        df = df[[c for c in COLUMNS if c in df.columns]]
        df["exchange"] = df["symbol"].str.split(".").str[1]

        # Drop rows from a DIFFERENT session. Sina keeps serving the last
        # tick a delisted name ever printed: 000004.SZ 国华退 came back
        # stamped 20260713 with open=high=low=close=0.510 and a real
        # volume — it would sail straight through the "is this suspended?"
        # check (all four prices are non-zero) and be written as today's
        # bar at July's price. Tencent's equivalent row is stamped today
        # with all-zero OHLC, which is why the suspension check alone was
        # enough until the second source existed.
        stamps = df["quote_time"].astype(str).str[:8]
        session = stamps.mode().iloc[0] if not stamps.empty else None
        if session:
            stale = stamps != session
            if stale.any():
                self.failures.extend(
                    [f"{s}(session {t})" for s, t in
                     zip(df.loc[stale, "symbol"], stamps[stale])][:50])
                df = df[~stale]
            if df.empty:
                raise FetchError(
                    f"所有行情都属于别的 session（众数 {session}），"
                    f"没有本 session 的数据")

        sources = df["source"].value_counts().to_dict()
        self.failures.extend(
            sorted(set(symbols) - set(df["symbol"]))[:200])
        return QuoteBatch(
            quotes=df, fetched_at=datetime.now(),
            request_count=requests_made, failures=list(self.failures),
            sha256=_content_hash(df), sources=sources,
            fallback_reason="；".join(reasons) or None)

    # ------------------------------------------------------------------
    def _fetch_chunk(self, source: _Source,
                     chunk: Sequence[str]) -> Tuple[List[dict], List[str]]:
        url = source.url + ",".join(_code(s) for s in chunk)
        last: Optional[Exception] = None
        for attempt in range(1, self.attempts + 1):
            try:
                resp = requests.get(url, headers=source.headers,
                                    timeout=config.HTTP_TIMEOUT)
                if resp.status_code != 200:
                    raise FetchError(f"HTTP {resp.status_code}")
                resp.encoding = source.encoding
                rows, bad = source.parse(resp.text)
                if not rows:
                    raise FetchError("返回里没有可解析的记录")
                return rows, bad
            except Exception as e:                              # noqa: BLE001
                last = e
                if attempt < self.attempts:
                    time.sleep(config.BACKOFF_FACTOR ** attempt)
        raise FetchError(
            f"{len(chunk)} 只的批次连续 {self.attempts} 次失败："
            f"{type(last).__name__}: {last}")

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
            "sources": batch.sources,
            "fallback_reason": batch.fallback_reason,
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
            "volume_shares", "amount_yuan"]
    sub = df[sorted(cols)].sort_values("symbol")
    return hashlib.sha256(
        sub.to_csv(index=False).encode("utf-8")).hexdigest()
