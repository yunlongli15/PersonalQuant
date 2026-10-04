# -*- coding: utf-8 -*-
"""Online market data providers (polite, single-connection, raw-cached).

Data source map (2026-09-05, verified reachable from this machine):
- securities (SSE): official SSE query API  -> data/raw/sse/stock_list.json
                     (code, name, LIST_DATE, DELIST_DATE, CSRC industry)
- securities (SZ):  SZSE official report via akshare stock_info_sz_name_code
                     (code, name, list date, CSRC industry)
- securities (BJ):  BSE official list via akshare stock_info_bj_name_code
- valuation snapshot: Tencent rank API (proxy.finance.qq.com) — the EastMoney
                     push2 clist API was intermittently WAF-blocked for this
                     IP, so it is not used; Tencent provides pe_ttm, pb (pn),
                     total/float market cap and turnover for all A-shares.
- daily history (cross-check): EastMoney push2his kline API, via akshare
                     stock_zh_a_hist. This IP gets WAF-blocked in bursts
                     (the connection is dropped with no response), so the
                     provider falls back to Tencent kline — once per run,
                     then for the rest of that run (see fetch_daily_history).
- corporate actions: EastMoney datacenter-web (reachable), via akshare
                     stock_fhps_em.
- calendar cross-check: Sina tool_trade_date_hist_sina.

Every raw response is cached under data/raw/ so bootstrap can re-run in
OFFLINE_MODE afterwards.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

from .. import config
from ..errors import FetchError
from ..symbols import normalize_symbol

RAW_CACHE = config.RAW_DIR / "akshare"

TENCENT_RANK_URL = "https://proxy.finance.qq.com/cgi/cgi-bin/rank/hs/getBoardRankList"
TENCENT_HEADERS = {
    "User-Agent": config.USER_AGENT,
    "Referer": "https://stockapp.finance.qq.com/",
}


def _cache_path(name: str) -> Path:
    return RAW_CACHE / f"{name}.json"


def _save_cache(name: str, data: pd.DataFrame) -> Path:
    config.ensure_dirs()
    p = _cache_path(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    data.to_json(p, orient="records", force_ascii=False, date_format="iso")
    return p


def _load_cache(name: str) -> Optional[pd.DataFrame]:
    p = _cache_path(name)
    if not p.exists():
        return None
    try:
        return pd.read_json(p, orient="records")
    except ValueError:
        return None


class AkShareMarketProvider:
    """Online market data provider; every fetch is cached to data/raw/akshare/."""

    name = "akshare"

    def __init__(self):
        # EastMoney's push2his drops the connection without responding once
        # this IP trips its WAF, and it stays that way for a while — asking
        # again for every symbol in a 60-symbol loop just burns 60 failed
        # requests and prints 60 identical lines. So: try it once per run,
        # and if it fails, serve the rest of that run from the Tencent
        # fallback. One attempt still notices if EastMoney comes back.
        # None = not tried yet; str = the reason it is out for this run.
        self.eastmoney_blocked: Optional[str] = None

    # ------------------------------------------------------------------
    # Valuation snapshot (Tencent rank API, ~24 pages for the full market)
    # ------------------------------------------------------------------
    def fetch_valuation_snapshot(self, use_cache: bool = True,
                                 trade_date=None) -> pd.DataFrame:
        """Full-market snapshot: pe/pb/market caps/turnover (+names, is_st).

        `trade_date` = the session the snapshot represents. Defaults to
        today, but on a weekend/holiday the caller must pass the last
        trading day — otherwise the snapshot invents a session that does
        not exist.
        """
        if use_cache:
            cached = _load_cache("valuation_snapshot")
            if cached is not None and not cached.empty:
                return cached
        config.require_online("fetch_valuation_snapshot")
        rows = []
        offset = 0
        page_size = 200
        while True:
            params = {
                "board_code": "aStock",
                "sort_type": "Price",
                "direct": "down",
                "offset": offset,
                "count": page_size,
            }
            resp = requests.get(TENCENT_RANK_URL, params=params,
                                headers=TENCENT_HEADERS, timeout=config.HTTP_TIMEOUT)
            if resp.status_code != 200:
                raise FetchError(f"tencent rank HTTP {resp.status_code}")
            data = resp.json()
            if data.get("code") != 0:
                raise FetchError(f"tencent rank API error: {data.get('msg')}")
            items = data["data"]["rank_list"]
            if not items:
                break
            rows.extend(items)
            offset += page_size
            if offset >= int(data["data"]["total"]):
                break
            time.sleep(config.MIN_DELAY_SECONDS)
        df = pd.DataFrame(rows)
        # keep only A-share common stocks (the board list may include other
        # listed securities); codes come with a market prefix (sz300300)
        stock_re = (r"^(600|601|603|605|688|689)\d{3}$|"
                    r"^(000|001|002|003|300|301)\d{3}$|"
                    r"^(43|83|87|92)\d{4}$")
        df = df[df["code"].astype(str).str.slice(2).str.match(stock_re)]
        df["symbol"] = df["code"].map(
            lambda c: normalize_symbol(c[2:] if c[:2] in ("sh", "sz", "bj") else c)
        )
        # build explicitly: the raw payload also has a 'turnover' column
        # (turnover amount), so renaming 'hsl' to 'turnover' would collide
        num = lambda col: pd.to_numeric(df[col], errors="coerce")  # noqa: E731
        out = pd.DataFrame(
            {
                "code": df["code"],
                "symbol": df["symbol"],
                "name": df["name"],
                "pe": num("pe_ttm"),
                "pb": num("pn"),
                # Tencent caps are in 1e8 CNY; canonical unit is CNY.
                "total_market_cap": num("zsz") * 1e8,
                "float_market_cap": num("ltsz") * 1e8,
                "turnover": num("hsl") / 100.0,  # ratio
                "pct_chg": num("zdf"),
            }
        )
        out["is_st"] = out["name"].str.contains("ST", na=False)
        out["trade_date"] = (pd.Timestamp(trade_date).normalize()
                             if trade_date is not None
                             else pd.Timestamp.now().normalize())
        out["source"] = "tencent_rank"
        out = out.drop_duplicates(subset=["symbol"])
        _save_cache("valuation_snapshot", out)
        return out

    # ------------------------------------------------------------------
    # Securities master: official exchange lists
    # ------------------------------------------------------------------
    def fetch_sse_stock_list(self, use_cache: bool = True) -> pd.DataFrame:
        """Official SSE stock list (incl. list/delist dates, CSRC industry)."""
        raw = config.RAW_DIR / "sse" / "stock_list.json"
        if use_cache and raw.exists():
            return self._parse_sse_list(raw)
        config.require_online("fetch_sse_stock_list")
        url = (
            "https://query.sse.com.cn/sseQuery/commonQuery.do"
            "?sqlId=COMMON_SSE_CP_GPJCTPZ_GPLB_GP_L&type=inParams&isPagination=true"
            "&pageHelp.pageSize=3000&pageHelp.pageNo=1&pageHelp.beginPage=1&pageHelp.endPage=1"
        )
        resp = requests.get(url, headers={"Referer": "https://www.sse.com.cn/",
                                          "User-Agent": config.USER_AGENT},
                            timeout=config.HTTP_TIMEOUT)
        if resp.status_code != 200:
            raise FetchError(f"sse stock list HTTP {resp.status_code}")
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(resp.content)
        return self._parse_sse_list(raw)

    @staticmethod
    def _parse_sse_list(raw: Path) -> pd.DataFrame:
        data = json.loads(raw.read_text(encoding="utf-8"))
        rows = (data.get("pageHelp") or {}).get("data") or []
        df = pd.DataFrame(rows)
        df = df.rename(
            columns={
                "A_STOCK_CODE": "code",
                "COMPANY_ABBR": "name",
                "LIST_DATE": "list_date",
                "DELIST_DATE": "delist_date",
                "CSRC_CODE": "industry_code",
                "CSRC_CODE_DESC": "industry_name",
            }
        )
        df["list_date"] = pd.to_datetime(df["list_date"], errors="coerce")
        df["delist_date"] = pd.to_datetime(
            df["delist_date"].replace("-", None), errors="coerce"
        )
        # keep only rows with a real 6-digit A-share code (list may contain
        # placeholders like '-' for non-A-share rows)
        df = df[df["code"].astype(str).str.match(r"^\d{6}$")]
        df["symbol"] = df["code"].map(
            lambda c: normalize_symbol(str(c).zfill(6)) if pd.notna(c) else None
        )
        return df[["symbol", "name", "list_date", "delist_date",
                   "industry_code", "industry_name"]]

    def fetch_szse_stock_list(self, use_cache: bool = True) -> pd.DataFrame:
        """Official SZSE stock list via akshare (incl. list date, CSRC industry)."""
        if use_cache:
            cached = _load_cache("szse_stock_list")
            if cached is not None and not cached.empty:
                return cached
        config.require_online("fetch_szse_stock_list")
        import akshare as ak

        df = ak.stock_info_sz_name_code(symbol="A股列表")
        df = df.rename(
            columns={
                "A股代码": "code",
                "A股简称": "name",
                "A股上市日期": "list_date",
                "所属行业": "industry_name",
            }
        )
        df["list_date"] = pd.to_datetime(df["list_date"], errors="coerce")
        df["delist_date"] = pd.NaT
        df["industry_code"] = df["industry_name"].str.extract(r"^([A-Z])", expand=False)
        # keep only real SZ A-share stock codes (the SZSE list may contain
        # bonds / funds / preferred shares)
        df = df[df["code"].astype(str).str.match(r"^(000|001|002|003|300|301)\d{3}$")]
        df["symbol"] = df["code"].map(
            lambda c: normalize_symbol(str(c).zfill(6)) if pd.notna(c) else None
        )
        df["name"] = df["name"].str.replace(r"\s+", "", regex=True)
        out = df[["symbol", "name", "list_date", "delist_date",
                  "industry_code", "industry_name"]]
        _save_cache("szse_stock_list", out)
        return out

    def fetch_bj_stock_list(self, use_cache: bool = True) -> pd.DataFrame:
        """BSE stock list via akshare (name/code; list date if available)."""
        if use_cache:
            cached = _load_cache("bj_stock_list")
            if cached is not None and not cached.empty:
                return cached
        config.require_online("fetch_bj_stock_list")
        import akshare as ak

        df = ak.stock_info_bj_name_code()
        cols = {c: c for c in df.columns}
        code_col = next((c for c in df.columns if "代码" in c), None)
        name_col = next((c for c in df.columns if "简称" in c), None)
        if code_col is None:
            raise FetchError(f"bse stock list columns unexpected: {list(df.columns)}")
        out = pd.DataFrame(
            {
                "symbol": df[code_col].map(
                    lambda c: normalize_symbol(str(c).zfill(6))
                ),
                "name": df[name_col] if name_col else None,
                "list_date": pd.NaT,
                "delist_date": pd.NaT,
                "industry_code": None,
                "industry_name": None,
            }
        )
        _save_cache("bj_stock_list", out)
        return out

    # ------------------------------------------------------------------
    # Daily history (for the independent cross-check vs Qlib baseline)
    # ------------------------------------------------------------------
    def fetch_daily_history(self, symbol: str, start: str, end: str,
                            adjust: str = "") -> pd.DataFrame:
        """Per-stock daily bars: EastMoney push2his via akshare, with a
        Tencent kline fallback (the EastMoney API hosts intermittently
        WAF-block this IP; the pipeline must not stop because one interface
        is down).

        下面的 source 列是可信的：调用方要区分数据到底来自哪一家，
        不能再靠"我们本来想用 EastMoney"来标注（EastMoney 失败时整轮
        都走 Tencent）。
        """
        config.require_online(f"fetch_daily_history({symbol})")
        code = symbol.split(".")[0]
        if self.eastmoney_blocked is not None:
            df = self._fetch_daily_history_tencent(symbol, start, end)
        else:
            try:
                import akshare as ak

                df = ak.stock_zh_a_hist(
                    symbol=code, period="daily",
                    start_date=start.replace("-", ""), end_date=end.replace("-", ""),
                    adjust=adjust,
                )
                df = df.rename(
                    columns={
                        "日期": "trade_date", "开盘": "open", "收盘": "close",
                        "最高": "high", "最低": "low", "成交量": "volume",
                        "成交额": "amount", "振幅": "amplitude", "涨跌幅": "pct_chg",
                    }
                )
                df["source"] = "eastmoney_push2his"
            except Exception as e:
                self.eastmoney_blocked = f"{type(e).__name__}: {e}"
                print(f"[fetch_daily_history] eastmoney 本轮不可用"
                      f"（{type(e).__name__}）—— 其余标的改用 tencent kline")
                df = self._fetch_daily_history_tencent(symbol, start, end)
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df["symbol"] = normalize_symbol(symbol)
        return df

    def _fetch_daily_history_tencent(self, symbol: str, start: str,
                                     end: str) -> pd.DataFrame:
        """Unadjusted daily bars from Tencent's kline API (1 request/stock)."""
        prefix = symbol.split(".")[1].lower()
        code = symbol.split(".")[0]
        param = f"{prefix}{code},day,{start},{end},640,"
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={param}"
        resp = requests.get(url, headers=TENCENT_HEADERS,
                            timeout=config.HTTP_TIMEOUT)
        if resp.status_code != 200:
            raise FetchError(f"tencent kline HTTP {resp.status_code}")
        data = resp.json()
        node = (data.get("data") or {}).get(f"{prefix}{code}") or {}
        rows = node.get("day") or node.get("qfqday") or []
        if not rows:
            raise FetchError(f"tencent kline returned no rows for {symbol}")
        df = pd.DataFrame(
            [r[:6] for r in rows],
            columns=["trade_date", "open", "close", "high", "low", "volume"],
        )
        for c in ["open", "close", "high", "low", "volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["amount"] = None
        df["source"] = "tencent_kline"
        return df

    # ------------------------------------------------------------------
    def fetch_calendar_crosscheck(self, use_cache: bool = True) -> pd.DataFrame:
        """Sina full trade-date history (single request)."""
        if use_cache:
            cached = _load_cache("sina_trade_dates")
            if cached is not None and not cached.empty:
                return cached
        config.require_online("fetch_calendar_crosscheck")
        import akshare as ak

        df = ak.tool_trade_date_hist_sina()
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        _save_cache("sina_trade_dates", df)
        return df

    # ------------------------------------------------------------------
    def fetch_dividends(self, report_year: int, use_cache: bool = True) -> pd.DataFrame:
        """Dividend/split plans for one annual report period (all A-shares)."""
        name = f"dividends_{report_year}"
        if use_cache:
            cached = _load_cache(name)
            if cached is not None and not cached.empty:
                return cached
        config.require_online(f"fetch_dividends({report_year})")
        import akshare as ak

        df = ak.stock_fhps_em(date=f"{report_year}1231")
        _save_cache(name, df)
        return df
