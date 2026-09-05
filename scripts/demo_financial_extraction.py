# -*- coding: utf-8 -*-
"""STEP 2 on-demand financial extraction demo.

Picks a symbol/fiscal year with reliable metadata, then runs the full lazy
pipeline exactly once:

    report_documents -> report URL -> single PDF fetch (LEVEL 3 cache off)
    -> %PDF + SHA256 validation -> text/table extraction -> target metrics
    -> sanity checks -> DuckDB financial_metrics (LEVEL 2 cache)
    -> extraction audit trail -> discard the temporary PDF

Usage:
    source .venv/Scripts/activate
    python scripts/demo_financial_extraction.py [SYMBOL] [FISCAL_YEAR]
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from personal_quant import db
from personal_quant.financial.query import extract_and_store

# companies deliberately spanning different industries and formats
DEFAULT_PICKS = [
    ("600519.SH", 2023),   # 贵州茅台 - 大型消费/制造业
    ("601318.SH", 2023),   # 中国平安 - 金融
    ("600036.SH", 2023),   # 招商银行 - 银行
    ("600519.SH", 2022),   # 同公司不同年度（格式稳定性）
]


def main() -> int:
    args = sys.argv[1:]
    if len(args) == 2:
        picks = [(args[0], int(args[1]))]
    else:
        picks = DEFAULT_PICKS

    for symbol, fy in picks:
        print("=" * 70)
        print(f"DEMO: {symbol} FY{fy}")
        print("=" * 70)
        try:
            result = extract_and_store(symbol, fy, cache=True)
        except Exception as e:
            print(f"FAILED: {type(e).__name__}: {e}")
            continue

        docs = db.query(
            "SELECT announcement_date, source_url FROM report_documents "
            "WHERE document_id=?",
            [result["document_id"]],
        )
        doc = docs[0] if docs else {}
        audits = db.query(
            "SELECT metric_name, page, section, raw_value, normalized_value, "
            "unit, extraction_method, validation_status, source_sha256 "
            "FROM extraction_audit "
            "WHERE source_document_id=? AND metric_name NOT LIKE '%_prev' "
            "ORDER BY id",
            [result["document_id"]],
        )
        print(f"company: {symbol}  fiscal_year: {fy}")
        print(f"announcement_date: {doc.get('announcement_date')}")
        print(f"source_url: {doc.get('source_url')}")
        print(f"source_sha256: {audits[0]['source_sha256'] if audits else 'n/a'}")
        print("-" * 70)
        print(f"{'metric':22s} {'value':>22s} {'unit':8s} {'page':>5s} "
              f"{'method':14s} {'status':18s}")
        for a in audits:
            if a["metric_name"] not in result["metrics"]:
                continue
            print(
                f"{a['metric_name']:22s} "
                f"{str(a['normalized_value']):>22s} "
                f"{str(a['unit'] or ''):8s} "
                f"{str(a['page'] or '-'):>5s} "
                f"{a['extraction_method']:14s} "
                f"{a['validation_status']:18s}"
            )
        n_ok = sum(
            1 for m in result["metrics"].values() if m["status"] != "EXTRACTION_FAILED"
        )
        n_all = len(result["metrics"])
        print("-" * 70)
        print(f"SUCCESS: {n_ok}/{n_all} metrics extracted for {symbol} FY{fy}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
