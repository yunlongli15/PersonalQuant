# -*- coding: utf-8 -*-
"""Online market-data ingest: securities master, valuation snapshot,
industry membership, corporate actions, calendar cross-check.

All online fetches go through the AkShare/Tencent/exchange providers and
are raw-cached; each table records its provenance in source_registry.
"""

from __future__ import annotations

import pandas as pd

from .. import db
from ..providers.akshare_market import AkShareMarketProvider
from ..storage.parquet import register_source, write_parquet, write_table


def ingest_securities(provider: AkShareMarketProvider | None = None) -> pd.DataFrame:
    """securities master = official exchange lists + qlib availability windows."""
    provider = provider or AkShareMarketProvider()
    sse = provider.fetch_sse_stock_list()
    szse = provider.fetch_szse_stock_list()
    try:
        bj = provider.fetch_bj_stock_list()
    except Exception:
        bj = pd.DataFrame(
            columns=["symbol", "name", "list_date", "delist_date",
                     "industry_code", "industry_name"]
        )
    snap = provider.fetch_valuation_snapshot()

    merged = pd.concat([sse, szse, bj], ignore_index=True)
    merged["exchange"] = merged["symbol"].str.split(".").str[1]
    merged["list_date"] = pd.to_datetime(merged["list_date"], errors="coerce")
    merged["delist_date"] = pd.to_datetime(merged["delist_date"], errors="coerce")
    # names: snapshot names for active stocks win (current naming incl. ST)
    snap_names = snap[["symbol", "name", "is_st"]].set_index("symbol")
    merged = merged.merge(snap_names, on="symbol", how="left", suffixes=("", "_snap"))
    merged["name"] = merged["name_snap"].fillna(merged["name"])
    merged["is_st"] = merged["is_st"].fillna(False)
    merged["is_active"] = True
    # mark delisted: SSE DELIST_DATE not null, or name in exchange list is the
    # only signal available; anything absent from the snapshot is inactive.
    merged["is_active"] = merged["symbol"].isin(snap["symbol"]) & merged["delist_date"].isna()

    # first_seen/last_seen: qlib data availability window (not list dates!)
    from ..providers.qlib_baseline import load_instruments
    from ..symbols import normalize_symbol

    inst = load_instruments()
    inst["symbol"] = inst["qlib_symbol"].map(
        lambda s: normalize_symbol(s) if isinstance(s, str) else None
    )
    windows = inst.set_index("symbol")
    merged["first_seen_year"] = (
        merged["symbol"].map(lambda s: windows.at[s, "start_date"].year if s in windows.index else None)
    )
    merged["last_seen_year"] = (
        merged["symbol"].map(lambda s: windows.at[s, "end_date"].year if s in windows.index else None)
    )
    merged["source"] = "sse_szse_bse_official+tencent_rank"

    cols = ["symbol", "exchange", "name", "list_date", "delist_date", "is_active",
            "is_st", "first_seen_year", "last_seen_year", "source"]
    out = merged[cols].drop_duplicates(subset=["symbol"])

    # instruments that have bars in the Qlib baseline but are absent from the
    # current official exchange lists (mostly delisted): include them with
    # list_date=NULL — we never fabricate listing dates.
    missing = windows.index.difference(out["symbol"])
    if len(missing):
        extra = pd.DataFrame(
            {
                "symbol": list(missing),
                "exchange": [s.split(".")[1] for s in missing],
                "name": None,
                "list_date": pd.NaT,
                "delist_date": pd.NaT,
                "is_active": False,
                "is_st": False,
                "first_seen_year": [windows.at[s, "start_date"].year for s in missing],
                "last_seen_year": [windows.at[s, "end_date"].year for s in missing],
                "source": "qlib_chenditc",
            }
        )
        out = pd.concat([out, extra], ignore_index=True)

    write_table(out, "securities")
    write_parquet(out, "securities", "securities")
    register_source(
        source_name="sse_szse_bse_official",
        data_type="securities",
        url="query.sse.com.cn / www.szse.cn / tencent rank",
        version="2026-09-05",
        file="data/raw/sse/stock_list.json + akshare caches",
        parser_version="1.0",
    )
    return out


def ingest_valuation(provider: AkShareMarketProvider | None = None) -> pd.DataFrame:
    provider = provider or AkShareMarketProvider()
    snap = provider.fetch_valuation_snapshot()
    out = pd.DataFrame(
        {
            "symbol": snap["symbol"],
            "trade_date": snap["trade_date"],
            "pe": snap["pe"],
            "pb": snap["pb"],
            "ps": None,  # Tencent rank API has no PS field; left NULL on purpose
            "total_market_cap": snap["total_market_cap"],
            "float_market_cap": snap["float_market_cap"],
            "turnover": snap["turnover"],
            "source": snap["source"],
        }
    )
    write_table(out, "daily_valuation")
    write_parquet(out, "valuation", "daily_valuation")
    register_source(
        source_name="tencent_rank",
        data_type="daily_valuation",
        url="https://proxy.finance.qq.com/cgi/cgi-bin/rank/hs/getBoardRankList",
        version=str(out["trade_date"].iloc[0]),
        file="data/raw/akshare/valuation_snapshot.json",
        parser_version="1.0",
    )
    return out


def ingest_industry(use_cache: bool = True) -> pd.DataFrame:
    """industry_membership from official CSRC classifications (SSE + SZSE)."""
    provider = AkShareMarketProvider()
    sse = provider.fetch_sse_stock_list(use_cache=use_cache)
    szse = provider.fetch_szse_stock_list(use_cache=use_cache)
    today = pd.Timestamp.now().normalize()
    rows = []
    for _, r in pd.concat([sse, szse]).iterrows():
        if pd.isna(r["industry_name"]):
            continue
        rows.append(
            {
                "symbol": r["symbol"],
                "industry_code": r["industry_code"],
                "industry_name": str(r["industry_name"]).strip(),
                "classification": "csrc",
                "effective_date": today,
                "end_date": None,
                "source": "sse_szse_official",
            }
        )
    out = pd.DataFrame(rows).drop_duplicates(subset=["symbol", "classification"])
    write_table(out, "industry_membership")
    write_parquet(out, "industry", "industry_membership")
    register_source(
        source_name="sse_szse_official",
        data_type="industry_membership",
        url="query.sse.com.cn / www.szse.cn",
        version=str(today),
        parser_version="1.0",
    )
    return out


def ingest_corporate_actions(
    report_years=(2023, 2024), use_cache: bool = True
) -> pd.DataFrame:
    """Dividend/split actions from EastMoney datacenter-web via akshare."""
    provider = AkShareMarketProvider()
    frames = []
    for year in report_years:
        try:
            raw = provider.fetch_dividends(year, use_cache=use_cache)
        except Exception as e:  # one interface failing must not kill the stage
            print(f"[actions] {year}: skipped ({type(e).__name__}: {e})")
            continue
        df = _parse_dividends(raw, year)
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    write_table(out, "corporate_actions")
    write_parquet(out, "corporate_actions", "corporate_actions")
    register_source(
        source_name="eastmoney_datacenter",
        data_type="corporate_actions",
        url="https://datacenter-web.eastmoney.com (RPT_SHAREBONUS_DET)",
        version=f"report_years={report_years}",
        parser_version="1.0",
    )
    return out


def _parse_dividends(raw: pd.DataFrame, report_year: int) -> pd.DataFrame:
    """Map akshare stock_fhps_em output to canonical corporate_actions rows."""
    colmap = {}
    for target, candidates in [
        ("code", ["代码"]),
        ("name", ["名称"]),
        ("cash_div_per_10", ["现金分红-现金分红比例", "派息比例"]),
        ("ex_date", ["除权除息日"]),
        ("record_date", ["股权登记日"]),
        ("plan_date", ["预案公告日", "公告日期"]),
        ("progress", ["方案进度"]),
        ("send_convert", ["送转股份-送转总比例"]),
    ]:
        for c in candidates:
            if c in raw.columns:
                colmap[target] = c
                break
    rows = []
    for _, r in raw.iterrows():
        code = str(r.get(colmap.get("code", ""), "")).zfill(6)
        try:
            from ..symbols import normalize_symbol

            symbol = normalize_symbol(code)
        except Exception:
            continue
        ex_date = pd.to_datetime(r.get(colmap.get("ex_date")), errors="coerce") \
            if colmap.get("ex_date") else pd.NaT
        if pd.isna(ex_date):
            continue  # plan not yet implemented -> not an action yet
        dividend, split_ratio = _parse_ratios(
            r.get(colmap.get("cash_div_per_10")),
            r.get(colmap.get("send_convert")) if colmap.get("send_convert") else None,
        )
        rows.append(
            {
                "symbol": symbol,
                "action_date": pd.to_datetime(
                    r.get(colmap.get("record_date")), errors="coerce"
                ),
                "ex_date": ex_date,
                "action_type": "dividend" if dividend > 0 else "split",
                "dividend": dividend,          # per share, CNY, pre-tax
                "split_ratio": split_ratio,    # shares added per share held
                "rights_ratio": None,
                "source": "eastmoney_datacenter",
            }
        )
    return pd.DataFrame(rows)


def _parse_ratios(cash: object, send_convert: object):
    """Parse '10派5元' / '10送2股' style strings into per-share values."""
    import re

    dividend = 0.0
    split = 0.0

    def num(s):
        if s is None or (isinstance(s, float) and pd.isna(s)):
            return None
        s = str(s).strip()
        m = re.search(r"(\d+(?:\.\d+)?)", s.replace(",", ""))
        return float(m.group(1)) if m else None

    if cash is not None:
        c = num(cash)
        if c is not None:
            dividend = c / 10.0
    if send_convert is not None:
        c = num(send_convert)
        if c is not None:
            split = c / 10.0
    return dividend, split
