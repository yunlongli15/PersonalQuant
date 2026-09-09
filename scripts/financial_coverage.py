# -*- coding: utf-8 -*-
"""Financial factor coverage report -> reports/step4_financial_factor_coverage.md.

For each financial factor and each year: available stocks / financial
universe size / coverage ratio, plus the missing-reason breakdown on one
representative date (last trading day of June). Missing reasons:
  - not_yet_announced: report for the latest needed fiscal year exists but
    its announcement is later than the date (PIT)
  - unknown_announcement: report metadata lacks a reliable announcement date
  - extraction_missing: report announced, but metrics not yet extracted
    (lazy pipeline has not reached it)
  - extraction_failed/not_applicable: extraction attempted but the metric
    is absent (e.g. banks have no gross_margin)

Never guesses values to raise coverage.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from factors.base import DERIVED, load_financial
from factors.fundamental import pit_metric_panel
from factors.registry import FACTOR_REGISTRY

PROJECT_ROOT = Path(__file__).resolve().parents[1]

FIN_METRICS = {
    "roe": ["roe", "net_profit", "net_assets"],
    "roa": ["roa"],
    "gross_margin": ["gross_margin"],
    "net_margin": ["net_margin"],
    "debt_to_asset": ["debt_to_asset"],
    "revenue_growth": ["revenue_growth"],
    "net_profit_growth": ["net_profit_growth"],
    "operating_cash_flow": ["operating_cash_flow"],
    "ocf_to_assets": ["operating_cash_flow", "total_assets"],
    "ocf_to_net_profit": ["operating_cash_flow", "net_profit"],
    "pe": ["eps"], "pb": ["eps"], "ps": ["eps"],
    "earnings_yield": ["eps"],
    "turnover_20": ["eps"],
    "turnover_60": ["eps"],
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2018")
    ap.add_argument("--end", default="2025")
    args = ap.parse_args()

    univ = pd.read_parquet(DERIVED / "universes.parquet")
    univ["date"] = pd.to_datetime(univ["date"])
    fin = univ[univ["universe"] == "financial"]
    fin_dates = sorted(fin["date"].unique())
    fin_sets = {d: set(g["symbol"]) for d, g in fin.groupby("date")}

    lines = ["# STEP 4 financial factor coverage", "",
             "Financial universe = top-300 A-shares by current market cap "
             "(large-cap sample; survivorship/large-cap caveat). Coverage "
             "counts stocks whose PIT annual-report value exists at the "
             "month-end signal dates.", ""]
    rows = []
    for name, metrics in FIN_METRICS.items():
        if name not in FACTOR_REGISTRY:
            continue
        years = range(int(args.start), int(args.end) + 1)
        for year in years:
            dates = [d for d in fin_dates if d.year == year]
            if not dates:
                continue
            covered = 0
            total = 0
            for d in dates:
                if d not in fin_sets:
                    continue
                universe_syms = fin_sets[d]
                panel, _ = pit_metric_panel(
                    type("D", (), {"financial": load_financial()})(),
                    metrics[0], [d])
                cov = set(panel.iloc[-1].dropna().index)
                covered += len(cov & universe_syms)
                total += len(universe_syms)
            rows.append({
                "year": year,
                "factor": name,
                "available_stocks": covered,
                "coverage_ratio": covered / total if total else 0.0,
            })
    cov = pd.DataFrame(rows)
    cov.to_csv(PROJECT_ROOT / "reports" / "step4_financial_factor_coverage.csv",
               index=False)

    lines.append("")
    lines.append("| year | factor | available_stocks | coverage_ratio |")
    lines.append("| --- | --- | --- | --- |")
    for _, r in cov.iterrows():
        lines.append(f"| {r['year']} | {r['factor']} | {r['available_stocks']} "
                     f"| {r['coverage_ratio']:.3f} |")

    # missing-reason breakdown on a representative date per year (last
    # trading day of June), attributed from report_documents metadata
    from personal_quant import db

    conn = db.connect()
    lines += ["", "## missing-reason breakdown (representative date: last "
              "trading day of June)", ""]
    reasons_by_year_factor = {}
    for year in range(int(args.start), int(args.end) + 1):
        june = [d for d in fin_dates if d.year == year and d.month == 6]
        d = june[-1] if june else None
        if d is None:
            continue
        universe_syms = fin_sets.get(d, set())
        reports = conn.execute(
            "SELECT symbol, MAX(announcement_date) max_ann, "
            "SUM(CASE WHEN availability_date_unknown THEN 0 ELSE 1 END) n_known "
            "FROM report_documents WHERE document_role='annual_report' "
            "AND symbol IN (SELECT unnest(?::VARCHAR[])) GROUP BY symbol",
            [sorted(universe_syms)],
        ).fetch_df().set_index("symbol")
        lines.append(f"### {year} (universe {len(universe_syms)})")
        lines.append("")
        lines.append("| factor | available | missing | not_yet_announced | "
                     "unknown_announcement | no_extraction |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for name, metrics in FIN_METRICS.items():
            panel, _ = pit_metric_panel(
                type("D", (), {"financial": load_financial()})(),
                metrics[0], [d])
            cov_set = set(panel.iloc[-1].dropna().index) & universe_syms
            missing = universe_syms - cov_set
            n_na = n_unk = n_ext = 0
            for s in missing:
                if s not in reports.index:
                    n_ext += 1  # no annual-report metadata at all
                    continue
                r = reports.loc[s]
                if r["n_known"] and pd.notna(r["max_ann"]) and \
                        pd.Timestamp(r["max_ann"]) <= d:
                    n_ext += 1      # announced before the date, not extracted
                elif r["n_known"] and pd.notna(r["max_ann"]):
                    n_na += 1       # latest report announced after the date
                else:
                    n_unk += 1      # no reliable announcement date
            dom = max(("not_yet_announced", n_na), ("unknown_announcement", n_unk),
                      ("no_extraction", n_ext), key=lambda t: t[1])
            reasons_by_year_factor[(year, name)] = dom[0] if dom[1] else "none"
            lines.append(f"| {name} | {len(cov_set)} | {len(missing)} | "
                         f"{n_na} | {n_unk} | {n_ext} |")
    lines.append("")
    lines.append("(attribution from report_documents metadata; extraction "
                 "failures for specific metrics are recorded per report in "
                 "extraction_audit — never guessed.)")
    # attach the dominant missing reason to the CSV rows
    cov["missing_reason"] = [
        reasons_by_year_factor.get((r["year"], r["factor"]), "")
        for _, r in cov.iterrows()]
    cov.to_csv(PROJECT_ROOT / "reports" / "step4_financial_factor_coverage.csv",
               index=False)

    out = PROJECT_ROOT / "reports" / "step4_financial_factor_coverage.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
