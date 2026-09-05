# -*- coding: utf-8 -*-
"""SSE annual-report metadata provider + lazy CNINFO PDF fetcher.

Metadata comes from the sse-reports-archive project (metadata-only; the
archive's bulk PDF download phase3b is NEVER run here). PDFs are fetched
on demand, one at a time, from CNINFO (static.cninfo.com.cn), validated
(%PDF magic + SHA256), and returned in memory. LEVEL-3 disk caching is off
by default.
"""

from __future__ import annotations

import random
import re
import sqlite3
import time
from dataclasses import asdict
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

from .. import config
from ..errors import FetchError, NotAvailableError
from ..symbols import normalize_symbol
from .base import FetchedPdf, ReportMetadata

_ANNOUNCE_RE = re.compile(r"finalpage/(\d{4}-\d{2}-\d{2})/")
_SSE_DATE_RE = re.compile(r"/c/(?:new/)?(\d{4}-\d{2}-\d{2})/")

STATUS_MAP = {
    "VERIFIED": "verified",
    "AVAILABLE": "available",
    "SOURCE_UNAVAILABLE": "source_unavailable",
    "MISSING": "missing",
    "NOT_APPLICABLE": "not_applicable",
}


class SSEReportsProvider:
    """ReportDocumentProvider for SSE annual reports (metadata + on-demand PDF)."""

    def __init__(self, archive_dir: Optional[Path] = None):
        self.archive_dir = Path(archive_dir) if archive_dir else config.SSE_ARCHIVE_DIR
        self._db = self.archive_dir / "sse_reports" / "data" / "reports.db"
        self._metadata_csv = self.archive_dir / "sse_reports" / "data" / "market_metadata.csv"
        self._lifecycle_csv = self.archive_dir / "sse_reports" / "data" / "company_lifecycle.csv"
        if not self._db.exists():
            raise FileNotFoundError(f"SSE archive database not found: {self._db}")

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------
    def load_report_metadata(self) -> pd.DataFrame:
        """Return canonical report_documents rows (DataFrame)."""
        con = sqlite3.connect(str(self._db))
        cov = pd.read_sql_query(
            "SELECT * FROM coverage", con
        )
        rep = pd.read_sql_query(
            "SELECT stock_code, report_year, report_type, announcement_date, "
            "title, source AS rep_source, pdf_url AS rep_pdf_url, bulletin_type, "
            "document_role, downloaded, verified, created_at, updated_at "
            "FROM reports",
            con,
        )
        con.close()

        out = cov.copy()
        out["announcement_date"] = None
        out["announcement_date_source"] = None
        out["title"] = None
        out["document_role"] = "annual_report"  # coverage matrix = annual reports
        out["bulletin_type"] = None
        out["role_source"] = "coverage"

        # Merge the 35 discovery rows (better role/date/title) on (stock, year).
        rep = rep.rename(columns={"report_year": "fiscal_year"})
        merged = cov[["stock_code", "fiscal_year"]].merge(
            rep, on=["stock_code", "fiscal_year"], how="left"
        )
        # Only use reports-table rows that carry real extra info
        mask = merged["document_role"].notna()
        for idx, row in merged[mask].iterrows():
            code, fy = str(row["stock_code"]), int(row["fiscal_year"])
            loc = (out["stock_code"] == code) & (out["fiscal_year"] == fy)
            # add extra rows for non-annual_report roles instead of overwriting
            role = row["document_role"]
            if role == "annual_report":
                out.loc[loc, "announcement_date"] = row["announcement_date"]
                out.loc[loc, "announcement_date_source"] = "sse_api"
                out.loc[loc, "title"] = row["title"]
                out.loc[loc, "bulletin_type"] = row["bulletin_type"]
                out.loc[loc, "role_source"] = "discovery"
            elif role is not None and out.loc[loc].any(axis=None):
                # append exactly one extra row for this (stock, year, role);
                # loc may already match multiple rows after earlier appends
                extra = out.loc[loc].iloc[[0]].copy()
                extra["document_role"] = role
                extra["announcement_date"] = row["announcement_date"]
                extra["announcement_date_source"] = "sse_api"
                extra["title"] = row["title"]
                extra["bulletin_type"] = row["bulletin_type"]
                extra["role_source"] = "discovery"
                out = pd.concat([out, extra], ignore_index=True)

        # Derive announcement dates from URL patterns where not yet known.
        no_date = out["announcement_date"].isna()
        cn = out.loc[no_date, "cninfo_pdf_url"].str.extract(_ANNOUNCE_RE, expand=False)
        out.loc[no_date & cn.notna(), "announcement_date"] = cn[cn.notna()]
        out.loc[no_date & cn.notna(), "announcement_date_source"] = "cninfo_url"
        still = out["announcement_date"].isna()
        se = out.loc[still, "sse_pdf_url"].str.extract(_SSE_DATE_RE, expand=False)
        out.loc[still & se.notna(), "announcement_date"] = se[se.notna()]
        out.loc[still & se.notna(), "announcement_date_source"] = "sse_url"

        return out

    def build_report_documents(self) -> pd.DataFrame:
        """Full canonical report_documents DataFrame (63k rows)."""
        m = self.load_report_metadata()
        from ..symbols import normalize_symbol

        def to_sym(code):
            try:
                return normalize_symbol(str(code))
            except Exception:
                return None

        sym = m["stock_code"].map(to_sym)
        rows = {
            "document_id": (
                "sse-" + m["stock_code"].astype(str) + "-" + m["fiscal_year"].astype(str)
                + "-" + m["document_role"].astype(str)
            ),
            "symbol": sym,
            "exchange": sym.map(lambda s: s.split(".")[1] if s else None),
            "fiscal_year": m["fiscal_year"],
            "report_type": "annual",
            "document_role": m["document_role"],
            "title": m["title"],
            "announcement_date": m["announcement_date"],
            "announcement_date_source": m["announcement_date_source"],
            "availability_date": pd.to_datetime(m["announcement_date"], errors="coerce"),
            "availability_date_unknown": m["announcement_date"].isna(),
            "source": m["actual_download_source"].fillna(
                m["cninfo_pdf_url"].notna().map({True: "cninfo", False: None})
            ).fillna(m["sse_pdf_url"].notna().map({True: "sse", False: None})),
            "source_url": m["cninfo_pdf_url"].map(
                lambda u: f"{config.CNINFO_STATIC_BASE}/{u}" if pd.notna(u) else None
            ),
            "local_path": None,  # archive PDFs are not present in our copy
            "status": m["status"].map(STATUS_MAP).fillna(m["status"]),
            "sha256": m["sha256"],
            "file_size": m["file_size"],
            "retrieval_timestamp": None,
            "first_seen": pd.to_datetime(m["created_at"], errors="coerce"),
            "last_seen": pd.to_datetime(m["updated_at"], errors="coerce"),
            "extraction_status": "not_started",
        }
        df = pd.DataFrame(rows)
        # The archive may record the same (stock, year, role) from both the
        # SSE and CNINFO discovery paths; keep the row with the richest info.
        df = (
            df.sort_values("announcement_date", na_position="last")
            .drop_duplicates(subset=["document_id"], keep="first")
            .reset_index(drop=True)
        )
        # PIT validity guard: an annual report for fiscal year N must have
        # been announced strictly after N-12-31 and by N+1-06-30. Dates
        # outside that window are unreliable -> flag unknown (never guess).
        # (Applies to annual_report rows only; corrections etc. are excluded.)
        ann = pd.to_datetime(df["announcement_date"], errors="coerce")
        lo = pd.to_datetime(df["fiscal_year"].astype("Int64").astype(str) + "-12-31")
        hi = pd.to_datetime((df["fiscal_year"] + 1).astype("Int64").astype(str) + "-06-30")
        is_annual = df["document_role"] == "annual_report"
        bad = is_annual & ann.notna() & ((ann <= lo) | (ann > hi))
        df.loc[bad, "announcement_date_source"] = "derived_invalid"
        df.loc[bad, "announcement_date"] = None
        df.loc[bad, "availability_date"] = pd.NaT
        df.loc[bad, "availability_date_unknown"] = True
        return df

    def load_lifecycle(self) -> pd.DataFrame:
        """Company lifecycle observations (SSE discovery windows)."""
        lc = pd.read_csv(self._lifecycle_csv, dtype=str)
        sym = lc["stock_code"].map(
            lambda c: normalize_symbol(str(c)) if str(c).isdigit() and len(str(c)) == 6 else None
        )
        first_seen = pd.to_numeric(lc["first_seen_year"], errors="coerce")
        last_seen = pd.to_numeric(lc["last_seen_year"], errors="coerce")
        last_year = int(last_seen.max())
        df = pd.DataFrame(
            {
                "symbol": sym,
                "effective_date": pd.to_datetime(
                    first_seen.astype("Int64").astype(str) + "-01-01", errors="coerce"
                ),
                "end_date": pd.to_datetime(
                    last_seen.astype("Int64").astype(str) + "-12-31", errors="coerce"
                ).where(last_seen < last_year, None),
                "status": "listed",
                "reason": None,
                "source": "sse_reports_archive",
            }
        ).dropna(subset=["symbol"])
        return df

    # ------------------------------------------------------------------
    # On-demand PDF fetching (single connection, polite, validated)
    # ------------------------------------------------------------------
    def get_report_metadata(
        self, symbol: str, fiscal_year: int, report_type: str = "annual_report"
    ) -> Optional[dict]:
        """Look up one report's metadata; None when not present in the archive."""
        sym = normalize_symbol(symbol)
        m = self.load_report_metadata()
        mask = (m["stock_code"] == sym.split(".")[0]) & (m["fiscal_year"] == fiscal_year)
        if not mask.any():
            return None
        row = m[mask]
        if report_type == "annual_report":
            row = row[row["document_role"] == "annual_report"]
        if row.empty:
            return None
        r = row.iloc[0]
        url = r["cninfo_pdf_url"]
        source_url = f"{config.CNINFO_STATIC_BASE}/{url}" if pd.notna(url) else None
        return {
            "document_id": f"sse-{sym.split('.')[0]}-{fiscal_year}-{r['document_role']}",
            "symbol": sym,
            "fiscal_year": int(fiscal_year),
            "report_type": "annual",
            "document_role": r["document_role"],
            "title": r["title"] if pd.notna(r["title"]) else None,
            "announcement_date": r["announcement_date"],
            "announcement_date_source": r["announcement_date_source"],
            "source": "cninfo" if pd.notna(url) else "sse",
            "source_url": source_url,
            "status": STATUS_MAP.get(r["status"], r["status"]),
        }

    def _sleep_politely(self) -> None:
        time.sleep(random.uniform(config.MIN_DELAY_SECONDS, config.MAX_DELAY_SECONDS))

    def fetch_pdf(self, url: str) -> FetchedPdf:
        """Fetch and fully validate one PDF. Raises FetchError/NotAvailableError."""
        config.require_online(f"fetch_pdf({url})")
        headers = {
            "User-Agent": config.USER_AGENT,
            "Referer": "https://www.cninfo.com.cn/",
            "Accept": "application/pdf,*/*",
        }
        last_err: Optional[Exception] = None
        for attempt in range(1, config.MAX_RETRIES + 1):
            self._sleep_politely()
            try:
                resp = requests.get(url, headers=headers, timeout=config.HTTP_TIMEOUT)
                if resp.status_code == 404:
                    raise NotAvailableError(f"PDF not found (404): {url}")
                if resp.status_code != 200:
                    raise FetchError(f"HTTP {resp.status_code} for {url}")
                content = resp.content
                if not content.startswith(b"%PDF-"):
                    raise FetchError(
                        f"not a PDF (magic bytes check failed): {url} "
                        f"got {content[:32]!r}"
                    )
                if len(content) < 10_000:
                    raise FetchError(f"suspiciously small PDF ({len(content)} bytes): {url}")
                return FetchedPdf.from_bytes(
                    url=url, http_status=resp.status_code, content=content
                )
            except NotAvailableError:
                raise
            except (requests.RequestException, FetchError) as e:
                last_err = e
                if attempt < config.MAX_RETRIES:
                    time.sleep(config.BACKOFF_FACTOR**attempt)
        raise FetchError(f"fetch failed after {config.MAX_RETRIES} attempts: {last_err}")

    def get_report(
        self,
        symbol: str,
        fiscal_year: int,
        report_type: str = "annual_report",
        cache: bool = False,
    ) -> FetchedPdf:
        """Find the report in metadata and fetch its PDF on demand.

        cache=True additionally persists the PDF to the LEVEL-3 cache
        (data/raw/reports/<sha256>.pdf); default off.
        """
        meta = self.get_report_metadata(symbol, fiscal_year, report_type)
        if meta is None:
            raise NotAvailableError(
                f"no {report_type} metadata for {normalize_symbol(symbol)} FY{fiscal_year}"
            )
        if not meta.get("source_url"):
            raise NotAvailableError(
                f"no fetchable URL for {meta['symbol']} FY{fiscal_year} "
                f"(source={meta['source']}, status={meta['status']})"
            )
        pdf = self.fetch_pdf(meta["source_url"])
        if cache or config.PDF_CACHE_ENABLED:
            config.ensure_dirs()
            dest = config.PDF_CACHE_DIR / f"{pdf.sha256}.pdf"
            if not dest.exists():
                dest.write_bytes(pdf.content)
            pdf.local_path = str(dest)
        return pdf
