# -*- coding: utf-8 -*-
"""CNINFO (巨潮资讯) announcement provider — fallback + per-stock history.

Per-stock queries use the stock=<code>,<orgId> form where orgId is
derivable as gs{sse|szse}{code} (probed 2026-09-09). announcementTime is
epoch milliseconds (Asia/Shanghai). Whole-market queries support
searchkey (company name / keyword).
"""

from __future__ import annotations

from typing import List, Optional

import pandas as pd

from personal_quant.symbols import normalize_symbol

from ..schema import MARKET_TZ, NewsDocument, hash_text, make_document_id
from .base import BaseNewsProvider, register

URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
HEADERS = {"Referer": "http://www.cninfo.com.cn/new/disclosure/stock"}
PAGE_SIZE = 30


@register
class CNINFOProvider(BaseNewsProvider):
    name = "cninfo"
    official = False
    exchanges = ("SH", "SZ")

    def fetch_announcements(self, start: str, end: str,
                            symbol: Optional[str] = None,
                            keyword: str = "") -> List[NewsDocument]:
        column = _column_for(symbol)
        stock_param = ""
        if symbol is not None:
            code = symbol.split(".")[0]
            exchange = symbol.split(".")[1].lower()
            stock_param = f"{code},gs{exchange}{code}"
        out: List[NewsDocument] = []
        page = 1
        while True:
            cache_key = (f"ann_{start}_{end}_{symbol or keyword or 'ALL'}"
                         f"_p{page}")
            if self.use_cache:
                cached = self.load_cache(cache_key)
            else:
                cached = None
            if cached is not None:
                anns = cached["anns"]
                total = cached["total"]
            else:
                data = {"pageNum": str(page), "pageSize": str(PAGE_SIZE),
                        "column": column, "tabName": "fulltext",
                        "plate": "", "stock": stock_param,
                        "searchkey": keyword, "secid": "",
                        "category": "", "trade": "",
                        "seDate": f"{start}~{end}",
                        "sortName": "", "sortType": "", "isHLtitle": "true"}
                resp = self.post(URL, data=data, headers=HEADERS)
                d = resp.json()
                anns = d.get("announcements") or []
                total = d.get("totalAnnouncement") or 0
                self.save_cache(cache_key, {"anns": anns, "total": total})
            for a in anns:
                code = str(a.get("secCode") or "").strip()
                if not (code and code.isdigit()):
                    continue
                try:
                    sym = normalize_symbol(code)
                except Exception:
                    continue
                title = str(a.get("announcementTitle") or "").strip()
                if not title:
                    continue
                pub, time_known = _parse_ms(a.get("announcementTime"))
                adj = a.get("adjunctUrl") or ""
                source_url = ("https://static.cninfo.com.cn/" + adj
                              if adj else "")
                rh = hash_text(title, str(pub), "cninfo")
                out.append(NewsDocument(
                    document_id=make_document_id("cninfo", rh),
                    symbol=sym, source="cninfo", source_url=source_url,
                    title=title, published_at=pub, time_known=time_known,
                    raw_hash=rh, document_type="announcement",
                ))
            if len(anns) < PAGE_SIZE or page * PAGE_SIZE >= total:
                break
            page += 1
        return out

    def search(self, keyword: str, start: str, end: str) -> List[NewsDocument]:
        """Whole-market keyword search (company name / terms)."""
        return self.fetch_announcements(start, end, symbol=None,
                                        keyword=keyword)


def _column_for(symbol: Optional[str]) -> str:
    if symbol is None:
        return "sse"
    return {"SH": "sse", "SZ": "szse"}.get(symbol.split(".")[1], "sse")


def _parse_ms(raw):
    if not raw:
        return None, False
    try:
        ms = int(raw)
        ts = pd.Timestamp(ms, unit="ms", tz=MARKET_TZ)
    except (ValueError, TypeError, OverflowError):
        return None, False
    return ts, ts.time() != pd.Timestamp("00:00:00").time()
