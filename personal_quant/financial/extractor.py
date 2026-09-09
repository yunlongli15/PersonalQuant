# -*- coding: utf-8 -*-
"""FinancialDocumentExtractor: PDF -> structured metric values.

Strategy (SSE annual reports have a mandated layout):
1. locate the "主要会计数据" (key accounting data) section pages;
2. parse ruled tables with pdfplumber, fall back to line-based regex
   over PyMuPDF text for layouts without ruled lines;
3. determine the table unit (单位：万元 etc.) from the section text;
4. map columns by fiscal-year headers; when headers are unusable, assume
   [current, previous] column order and record that assumption;
5. per metric: match the row label, parse, normalize to CNY / fraction.

Honesty contract: never guess. Missing/unparseable => EXTRACTION_FAILED with
a recorded reason (audit trail).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from .metrics import METRICS, MetricDef, parse_number, parse_unit

EXTRACTION_VERSION = "1.1"  # 1.1: adds per-share metrics (eps, bps)

_YEAR_RE = re.compile(r"20\d{2}")


@dataclass
class ExtractionResult:
    metric: str
    raw_value: Optional[str] = None
    value: Optional[float] = None          # normalized (CNY or fraction)
    unit: Optional[str] = None             # "CNY" | "fraction"
    page: Optional[int] = None
    section: Optional[str] = None
    method: str = "not_attempted"
    status: str = "EXTRACTION_FAILED"      # VALID / VALIDATION_WARNING / EXTRACTION_FAILED
    note: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in
                ("metric", "raw_value", "value", "unit", "page", "section",
                 "method", "status", "note")}


class FinancialDocumentExtractor:
    """Uniform interface over PDF text/table extraction (PyMuPDF + pdfplumber)."""

    def __init__(self, pdf_bytes: bytes):
        import pymupdf

        self.pdf_bytes = pdf_bytes
        self.doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        self._text_cache: dict[int, str] = {}

    # -- basic interfaces ------------------------------------------------
    def extract_text(self, pages: Optional[List[int]] = None) -> List[str]:
        """Full text per page (0-indexed)."""
        if pages is None:
            pages = list(range(len(self.doc)))
        return [self._page_text(p) for p in pages]

    def _page_text(self, page_no: int) -> str:
        if page_no not in self._text_cache:
            try:
                self._text_cache[page_no] = self.doc[page_no].get_text("text")
            except Exception:
                self._text_cache[page_no] = ""
        return self._text_cache[page_no]

    def extract_tables(self, pages: Optional[List[int]] = None) -> List[dict]:
        """pdfplumber tables with page numbers: [{'page': n, 'table': [...]}]."""
        import io

        import pdfplumber

        out = []
        with pdfplumber.open(io.BytesIO(self.pdf_bytes)) as pdf:
            for n, page in enumerate(pdf.pages):
                if pages is not None and n not in pages:
                    continue
                for table in page.extract_tables():
                    out.append({"page": n, "table": table})
        return out

    # -- section discovery ------------------------------------------------
    def find_section(self, keyword: str, max_pages: int = 30,
                     start_page: int = 0,
                     secondary: Optional[str] = None) -> Optional[int]:
        """First 0-indexed page (from start_page) containing the keyword.

        When `secondary` is given, prefer pages that also contain it (used to
        skip TOC/cross-reference hits and land on the actual statement page);
        if none qualify, fall back to the plain first hit.
        """
        candidates = []
        for p in range(start_page, min(start_page + max_pages, len(self.doc))):
            text = self._page_text(p)
            if keyword in text:
                if secondary and secondary in text:
                    return p
                candidates.append(p)
        return candidates[0] if candidates else None

    def find_keyword(self, keyword: str, max_pages: Optional[int] = None) -> Optional[int]:
        return self.find_section(keyword, max_pages or len(self.doc))

    # -- metric extraction --------------------------------------------------
    # Which report sections are searched per metric, in priority order:
    #   A = 主要会计数据 (key accounting data, compact table)
    #   B = 合并资产负债表 (consolidated balance sheet)
    #   C = 合并利润表 (consolidated income statement)
    SECTION_PRIORITY = {
        "revenue": ["A", "C"],
        "cost_of_revenue": ["A", "C"],
        "net_profit": ["A", "C"],
        "total_assets": ["A", "B"],
        "total_liabilities": ["B"],
        "net_assets": ["A", "B"],
        "operating_cash_flow": ["A"],
        "roe": ["A"],
        "eps": ["A"],
        "bps": ["A"],
    }

    def _is_htc_version(self) -> bool:
        """H-share (Traditional Chinese) version of a dual-listed issuer:
        its statement sections use different titles/units and the keyword
        hits land on MD&A cross-references — only the financial-summary
        section (A) is reliably parseable, so B/C results are dropped."""
        head = "\n".join(self._page_text(p) for p in
                         range(min(8, len(self.doc))))
        return ("合併財務狀況表" in head or "股份代號" in head
                or "財務摘要" in head)

    def extract_all(self, fiscal_year: int) -> dict[str, ExtractionResult]:
        results: dict[str, ExtractionResult] = {}
        htc = self._is_htc_version()
        sections = self._locate_sections()
        spans = {"A": 4, "B": 6, "C": 3}
        # candidate windows per section: every anchor page yields a window;
        # the metric search below evaluates them in page order and the first
        # window that actually contains the target row wins
        windows: dict[str, List[List[int]]] = {}
        units: dict[str, List] = {}
        tables: dict[str, List] = {}
        for sec, anchors in sections.items():
            wins = [
                list(range(a, min(a + spans[sec], len(self.doc))))
                for a in (anchors or [])[:8]
            ]
            windows[sec] = wins
            units[sec] = [self._detect_unit(w[0]) if w else (None, None) for w in wins]
            tables[sec] = [self.extract_tables(w) if w else [] for w in wins]

        for name, mdef in METRICS.items():
            results[name] = self._extract_metric_multi(
                mdef, fiscal_year, tables, self.SECTION_PRIORITY[name],
                units, windows,
            )
        # previous-year values for growth metrics (revenue_growth,
        # net_profit_growth); None when the report lacks a usable prior column
        for prev_name, mdef_name in (("revenue_prev", "revenue"),
                                     ("net_profit_prev", "net_profit")):
            results[prev_name] = self._extract_metric_multi(
                METRICS[mdef_name], fiscal_year, tables, ["A"],
                units, windows, use_previous=True,
            )

        if htc:
            # H-share version guard: B/C anchors match MD&A cross-references
            # (wrong scale/unit) — keep only summary-section values with a
            # detected unit; everything else is honestly EXTRACTION_FAILED
            for name, r in results.items():
                if name not in METRICS:  # revenue_prev / net_profit_prev
                    continue
                mdef = METRICS[name]
                bad = (r.status == "VALID" and
                       (r.section != "A" or
                        (mdef.kind == "amount"
                         and "unit_assumed" in (r.note or ""))))
                if bad:
                    results[name] = ExtractionResult(
                        metric=name, method="htc_guarded",
                        status="EXTRACTION_FAILED",
                        note="H-share (Traditional Chinese) version: "
                             "statement sections skipped (unit/label "
                             "mismatch risk); only the financial summary "
                             "is used",
                    )
        return results

    def _locate_sections(self) -> dict[str, Optional[List[int]]]:
        """All candidate anchor pages per section (page lists, 0-indexed).

        Financial statements sit beyond the TOC (~page 40 to ~page 150); the
        key accounting data section is in the first ~15 pages. Candidates
        include cross-reference hits (audit reports, notes) — the metric
        search evaluates each window and stops at the first real match.
        Simplified- and Traditional-Chinese variants are both searched
        (some dual-listed issuers publish the H-share (繁体) version on
        their CNINFO URL).
        """
        def _hits(keywords: tuple, start: int, max_pages: int) -> List[int]:
            for keyword in keywords:
                found = [
                    p for p in range(start,
                                      min(start + max_pages, len(self.doc)))
                    if keyword in self._page_text(p)
                ]
                if found:
                    return found
            return []

        return {
            "A": (_hits(("主要会计数据和财务指标", "主要會計數據和財務指標"), 0, 15)
                  or _hits(("主要会计数据", "主要會計數據"), 0, 15)
                  or _hits(("财务摘要", "財務摘要"), 0, 15)),
            "B": _hits(("合并资产负债表", "合併資產負債表",
                        "合并财务状况表", "合併財務狀況表"), 10, 200),
            "C": _hits(("合并利润表", "合并损益表", "合併利潤表", "合併損益表"),
                       10, 200),
        }

    def _detect_unit(self, anchor: Optional[int]) -> tuple[Optional[float], Optional[str]]:
        if anchor is None:
            return None, None
        for p in range(anchor, min(anchor + 4, len(self.doc))):
            mult, label = parse_unit(self._page_text(p))
            if mult is not None:
                return mult, label
        return None, None

    def _extract_metric_multi(
        self,
        mdef: MetricDef,
        fiscal_year: int,
        tables: dict,
        priority: List[str],
        units: dict,
        windows: dict,
        use_previous: bool = False,
    ) -> ExtractionResult:
        for sec in priority:
            for wi, win in enumerate(windows.get(sec, [])):
                unit_mult, unit_label = units[sec][wi]
                if unit_mult is None:
                    unit_label = "CNY"
                for t in tables[sec][wi]:
                    res = self._search_table(mdef, fiscal_year, t, unit_mult,
                                             unit_label, sec, use_previous=use_previous)
                    if res is not None:
                        return res
                res = self._search_lines(mdef, fiscal_year, win,
                                         unit_mult, unit_label, sec,
                                         use_previous=use_previous)
                if res is not None:
                    return res
        return ExtractionResult(
            metric=mdef.name, section=",".join(priority),
            method="pdf_table+pdf_text_line",
            note=f"label not found: {mdef.labels[0]}",
        )

    # -- table strategy ----------------------------------------------------
    def _search_table(
        self,
        mdef: MetricDef,
        fiscal_year: int,
        t: dict,
        unit_mult: Optional[float],
        unit_label: str,
        section: Optional[str],
        use_previous: bool = False,
    ) -> Optional[ExtractionResult]:
        table = t["table"]
        if not table:
            return None
        # map fiscal_year / fiscal_year-1 to real column indices
        col_map = self._map_year_columns(table, fiscal_year)
        if use_previous and (col_map is None or col_map["previous"] is None):
            return None  # no reliable prior-year column -> do not guess
        for row in table:
            if not row or not row[0]:
                continue
            label = str(row[0]).replace("\n", "").strip()
            if not mdef.match_label(label):
                continue
            assumed = False
            if use_previous:
                raw_cell = row[col_map["previous"]]
            elif col_map is not None:
                raw_cell = row[col_map["current"]]
            else:
                # header unusable: assume the first data column is current year
                raw_cell = row[1]
                assumed = True
            raw = parse_number(raw_cell)
            if raw is None:
                continue
            mult = unit_mult or 1.0
            if mdef.kind == "amount":
                value = raw * mult
                unit = unit_label
            elif mdef.kind == "percent":
                value = raw / 100.0
                unit = "fraction"
            else:  # per_share: reported in 元/股, unit multiplier does not apply
                value = raw
                unit = "CNY_per_share"
            notes = [n for n in ("column_order_assumed" if assumed else None,
                                 "unit_assumed" if unit_mult is None
                                 and mdef.kind == "amount" else None) if n]
            return ExtractionResult(
                metric=mdef.name,
                raw_value=str(raw_cell).strip(),
                value=value,
                unit=unit,
                page=t["page"] + 1,
                section=section,
                method="pdf_table",
                status="VALID",
                note=";".join(notes) if notes else None,
            )
        return None

    def _map_year_columns(self, table: List, fiscal_year: int) -> Optional[dict]:
        """Map current/previous-period columns to table column indices.

        Supports two header conventions:
        - explicit years ('2023年' / '2022年') as in the key accounting data;
        - relative labels ('期末余额'/'期初余额', '本期发生额'/'上期发生额') as
          in the balance sheet / income statement.
        Columns like '本期比上年同期增减(%)' are never data columns.
        """
        cur = prev = None
        for row in table[:3]:
            for j, c in enumerate(row[1:], start=1):
                if cur is not None and prev is not None:
                    return {"current": cur, "previous": prev}
                cell = str(c or "")
                if "增减" in cell:
                    continue
                years = [int(y) for y in _YEAR_RE.findall(cell)]
                for y in years:
                    if y == fiscal_year and cur is None:
                        cur = j
                    elif y == fiscal_year - 1 and prev is None:
                        prev = j
                if cur is None and ("期末" in cell or "本期" in cell or "本年" in cell):
                    cur = j
                if prev is None and ("期初" in cell or "上期" in cell or "上年" in cell):
                    prev = j
        if cur is None:
            return None
        return {"current": cur, "previous": prev}

    # -- line-based fallback ------------------------------------------------
    def _search_lines(
        self,
        mdef: MetricDef,
        fiscal_year: int,
        pages: Optional[List[int]],
        unit_mult: Optional[float],
        unit_label: str,
        section: Optional[str],
        use_previous: bool = False,
    ) -> Optional[ExtractionResult]:
        if not pages:
            return None
        for p in pages:
            lines = self._page_text(p).splitlines()
            for i, line in enumerate(lines):
                tokens = line.split()
                if not mdef.match_label(tokens[0] if tokens else line):
                    # label may appear as any token in the line; strict
                    # boundary semantics only (never bare substring)
                    hit = any(mdef.match_label(tok) for tok in tokens)
                    if not hit:
                        continue
                # values may live on the label line or a few lines below
                # (some PDF layouts emit label / blank / value lines, one
                # value per line)
                numbers = []
                for j in range(i, min(i + 6, len(lines))):
                    numbers.extend(
                        n for n in (
                            parse_number(s) for s in
                            re.findall(r"-?[\d,]+(?:\.\d+)?", lines[j])
                        ) if n is not None
                    )
                    if numbers and (not use_previous or len(numbers) >= 2):
                        break
                if not numbers:
                    continue
                if use_previous and len(numbers) < 2:
                    continue
                raw = numbers[1] if use_previous else numbers[0]
                mult = unit_mult or 1.0
                if mdef.kind == "amount":
                    value = raw * mult
                    unit = unit_label
                elif mdef.kind == "percent":
                    value = raw / 100.0
                    unit = "fraction"
                else:  # per_share: 元/股, unit multiplier does not apply
                    value = raw
                    unit = "CNY_per_share"
                notes = ["line_fallback_first_number"]
                if unit_mult is None and mdef.kind == "amount":
                    notes.append("unit_assumed")
                return ExtractionResult(
                    metric=mdef.name,
                    raw_value=str(raw),
                    value=value,
                    unit=unit,
                    page=p + 1,
                    section=section,
                    method="pdf_text_line",
                    status="VALID",
                    note=";".join(notes),
                )
        return None
