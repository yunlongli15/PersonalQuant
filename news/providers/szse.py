# -*- coding: utf-8 -*-
"""SZSE official announcement provider (szse.cn annList API).

Per-day or per-stock queries; publishTime is Asia/Shanghai with real
timestamps ('2018-01-31 20:19:20') or date-only ('00:00:00' ->
time_known=False, conservative next-trading-day availability).
Historical depth >= 2018 (probed 2026-09-09).
"""

from __future__ import annotations

from typing import List, Optional

import pandas as pd

from personal_quant.symbols import normalize_symbol

from ..schema import MARKET_TZ, NewsDocument, hash_text, make_document_id
from .base import BaseNewsProvider, register

URL = "http://www.szse.cn/api/disc/announcement/annList"
HEADERS = {"Referer": "https://www.szse.cn/disclosure/notice/company/index.html"}
PAGE_SIZE = 30


@register
class SZSEProvider(BaseNewsProvider):
    name = "szse"
    official = True
    exchanges = ("SZ",)

    def fetch_announcements(self, start: str, end: str,
                            symbol: Optional[str] = None) -> List[NewsDocument]:
        out: List[NewsDocument] = []
        page = 1
        while True:
            cache_key = f"ann_{start}_{end}_{symbol or 'ALL'}_p{page}"
            if self.use_cache:
                cached = self.load_cache(cache_key)
            else:
                cached = None
            if cached is not None:
                rows = cached["rows"]
                total = cached["total"]
            else:
                body = {"seDate": [start, end],
                        "channelCode": ["listedNotice_disc"],
                        "pageSize": PAGE_SIZE, "pageNum": page}
                if symbol:
                    body["stock"] = [symbol.split(".")[0]]
                resp = self.post(URL, json=body, headers=HEADERS)
                d = resp.json()
                rows = d.get("data") or []
                total = d.get("announceCount") or 0
                self.save_cache(cache_key, {"rows": rows, "total": total})
            for row in rows:
                code = row.get("secCode")
                if isinstance(code, list):   # API returns a one-element list
                    code = code[0] if code else None
                code = str(code or "").strip()
                if not (code and code.isdigit()):
                    continue
                try:
                    sym = normalize_symbol(code)
                except Exception:
                    continue
                title = str(row.get("title") or "").strip()
                if not title:
                    continue
                raw_dt = row.get("publishTime")
                pub, time_known = _parse_dt(raw_dt)
                attach = row.get("attachPath") or ""
                source_url = ("https://disc.static.szse.cn/download"
                              + attach if attach else "")
                rh = hash_text(title, str(pub), "szse")
                out.append(NewsDocument(
                    document_id=make_document_id("szse", rh),
                    symbol=sym, source="szse", source_url=source_url,
                    title=title, published_at=pub, time_known=time_known,
                    raw_hash=rh, document_type="announcement",
                ))
            if not rows or len(rows) < PAGE_SIZE or page * PAGE_SIZE >= total:
                break
            page += 1
        return out


def _parse_dt(raw):
    if not raw:
        return None, False
    try:
        ts = pd.Timestamp(str(raw))
        if ts.tzinfo is None:
            ts = ts.tz_localize(MARKET_TZ)
    except (ValueError, TypeError):
        return None, False
    return ts, ts.time() != pd.Timestamp("00:00:00").time()
