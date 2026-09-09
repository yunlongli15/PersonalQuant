# -*- coding: utf-8 -*-
"""SSE official announcement provider (query.sse.com.cn).

Per-day whole-market queries (the API ignores per-stock filters — probed
2026-09-09); local filtering by SECURITY_CODE. Timestamps: ADDDATE
(YYYY-MM-DD HH:MM:SS, Asia/Shanghai, time_known=True when a time is
present). Historical depth starts ~2015 (2014 returns near-empty — the
coverage report reflects it).
"""

from __future__ import annotations

from typing import List, Optional

import pandas as pd

from personal_quant.symbols import normalize_symbol

from ..schema import MARKET_TZ, NewsDocument, hash_text, make_document_id
from .base import BaseNewsProvider, register

URL = "https://query.sse.com.cn/security/stock/queryCompanyBulletin.do"
HEADERS = {"Referer": "https://www.sse.com.cn/"}
PAGE_SIZE = 1000
# NOTE (probed 2026-09-09): pageHelp.pageNo is IGNORED by the API —
# pagination works via pageHelp.beginPage/endPage; pageSize=1000 returns
# the whole day in one request for any realistic day.


@register
class SSEProvider(BaseNewsProvider):
    name = "sse"
    official = True
    exchanges = ("SH",)

    def fetch_announcements(self, start: str, end: str,
                            symbol: Optional[str] = None) -> List[NewsDocument]:
        """Whole-market bulletins per day window; filtered locally."""
        out: List[NewsDocument] = []
        page = 1
        while True:
            # cache key includes the page size: the old broken-pagination
            # caches (pageSize=100) are never reused
            cache_key = f"bulletin_{start}_{end}_sz{PAGE_SIZE}_bp{page}"
            if self.use_cache:
                cached = self.load_cache(cache_key)
            else:
                cached = None
            if cached is not None:
                rows = cached["rows"]
                total = cached["total"]
            else:
                params = {
                    "isPagination": "true",
                    "securityType": "0101,120100,020100,020200,120200",
                    "reportType2": "DQBG", "reportType": "ALL",
                    "beginDate": start, "endDate": end,
                    "pageHelp.pageSize": str(PAGE_SIZE),
                    "pageHelp.pageNo": "1",
                    "pageHelp.beginPage": str(page),
                    "pageHelp.endPage": str(page),
                    "pageHelp.cacheSize": "1",
                }
                resp = self.get(URL, params=params, headers=HEADERS)
                d = resp.json()
                ph = (d.get("pageHelp") or {})
                rows = ph.get("data") or []
                total = ph.get("total") or 0
                self.save_cache(cache_key, {"rows": rows, "total": total})
            for row in rows:
                code = str(row.get("SECURITY_CODE") or "").zfill(6)
                if not code.isdigit():
                    continue
                try:
                    sym = normalize_symbol(code)
                except Exception:
                    continue
                if symbol is not None and sym != symbol:
                    continue
                raw_dt = row.get("ADDDATE")  # 'YYYY-MM-DD HH:MM:SS'
                pub, time_known = _parse_dt(raw_dt)
                title = str(row.get("TITLE") or "").strip()
                if not title:
                    continue
                url_path = row.get("URL") or ""
                source_url = (f"https://www.sse.com.cn{url_path}"
                              if url_path.startswith("/") else url_path)
                rh = hash_text(title, str(pub), "sse")
                out.append(NewsDocument(
                    document_id=make_document_id("sse", rh),
                    symbol=sym, source="sse", source_url=source_url,
                    title=title, published_at=pub, time_known=time_known,
                    raw_hash=rh, document_type="announcement",
                ))
            if not rows or len(rows) < PAGE_SIZE:
                break
            page += 1
        return out


def _parse_dt(raw):
    """'2026-08-30 15:31:46' -> (Timestamp tz-aware, time_known)."""
    if not raw:
        return None, False
    s = str(raw).strip()
    try:
        ts = pd.Timestamp(s)
        if ts.tzinfo is None:
            ts = ts.tz_localize(MARKET_TZ)
    except (ValueError, TypeError):
        return None, False
    return ts, ts.time() != pd.Timestamp("00:00:00").time()
