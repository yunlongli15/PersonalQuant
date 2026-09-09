# -*- coding: utf-8 -*-
"""AkShare news provider wrappers (fallback tier).

stock_notice_report(symbol='全部', date=...) covers the whole market for
one day (巨潮 via akshare); stock_news_em covers EastMoney per-stock news
(WAF-intermittent — the pipeline falls back per the STEP 2 policy).
"""

from __future__ import annotations

from typing import List, Optional

import pandas as pd

from personal_quant.symbols import normalize_symbol

from ..schema import MARKET_TZ, NewsDocument, hash_text, make_document_id
from .base import BaseNewsProvider, register


@register
class AkShareNewsProvider(BaseNewsProvider):
    name = "akshare"
    official = False
    exchanges = ("SH", "SZ")

    def fetch_announcements(self, start: str, end: str,
                            symbol: Optional[str] = None) -> List[NewsDocument]:
        import akshare as ak

        out: List[NewsDocument] = []
        for d in pd.date_range(start, end, freq="D"):
            cache_key = f"notice_{d.date()}_{symbol or 'ALL'}"
            if self.use_cache:
                cached = self.load_cache(cache_key)
            else:
                cached = None
            if cached is not None:
                rows = cached
            else:
                df = ak.stock_notice_report(symbol=symbol or "全部",
                                            date=d.strftime("%Y-%m-%d"))
                rows = df.to_dict("records")
                self.save_cache(cache_key, rows)
            for row in rows:
                code = str(row.get("代码") or row.get("code") or "").zfill(6)
                if not code.isdigit():
                    continue
                try:
                    sym = normalize_symbol(code)
                except Exception:
                    continue
                title = str(row.get("公告标题") or row.get("名称") or "").strip()
                if not title:
                    continue
                pub = pd.Timestamp(str(d.date())).tz_localize(MARKET_TZ)
                rh = hash_text(title, str(pub), "akshare")
                out.append(NewsDocument(
                    document_id=make_document_id("akshare", rh),
                    symbol=sym, source="akshare", source_url="",
                    title=title, published_at=pub, time_known=False,
                    raw_hash=rh, document_type="announcement",
                ))
        return out
