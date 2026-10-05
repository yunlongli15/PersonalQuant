# -*- coding: utf-8 -*-
"""SSE official announcement provider (query.sse.com.cn).

Per-day whole-market queries (the API ignores per-stock filters — probed
2026-09-09); local filtering by SECURITY_CODE. Timestamps: ADDDATE
(YYYY-MM-DD HH:MM:SS, Asia/Shanghai, time_known=True when a time is
present). Historical depth starts ~2015 (2014 returns near-empty — the
coverage report reflects it).

2026-10-05 修复：原先请求里写死 `reportType2="DQBG"`（定期报告），
导致**只有年报/半年报/季报进了库**，普通公告一条都没有。已改成 "ALL"，
并把缓存键升到 v2（否则会读回旧参数下的缓存）。详见
reports/news_data_quality_v2.md。
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
#: 请求参数变了就必须升这个版本号 —— 否则会从旧缓存里读回"用旧参数取到的"
#: 数据。2026-10-05 修 reportType2 时正是如此：带 DQBG 的那批缓存里
#: 2026-09-30 存的是 total=0，不换键的话修复会"看起来生效"却一条新数据都没有。
CACHE_VERSION = "v2"
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
            cache_key = (f"bulletin_{CACHE_VERSION}_{start}_{end}"
                         f"_sz{PAGE_SIZE}_bp{page}")
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
                    # securityType 是必需的（不传返回 0），这一组覆盖
                    # A股/科创/基金等；非股票代码由下面的本地 filter 丢掉
                    "securityType": "0101,120100,020100,020200,120200",
                    # ⚠️ 这里曾经写死 reportType2="DQBG"（**定期报告**），
                    # 于是除年报/半年报/季报之外的公告**一条都没进库**。
                    # 2026-10-05 实测（2026-09-29 一天）：
                    #     reportType2=DQBG → total=0
                    #     reportType2=ALL  → total=814
                    # 后果：沪市股票（约半个市场）的质押/减持/诉讼/立案/
                    # 冻结等公告全部缺失，全库负方向事件里沪市只占 **1 条**。
                    # 详见 reports/news_data_quality_v2.md。
                    "reportType2": "ALL", "reportType": "ALL",
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
