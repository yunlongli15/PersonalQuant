# -*- coding: utf-8 -*-
"""news_documents -> news_events (+ LLM tier when enabled).

    python scripts/news/build_events.py [--llm] [--dry-run]

1. load canonical documents, compute per-symbol novelty (bigram TF-IDF
   vs the previous 30 days' titles)
2. rule classification -> NewsEvent (direction candidates, importance,
   availability per the PIT rules)
3. LLM tier (only when DEEPSEEK_API_KEY is set AND --llm passed): tier-1
   documents only, strict JSON, cache + daily budget; failures fall back
   to the rule result (extraction_method records the actual tier)
4. replace news_events (DuckDB) + export the parquet snapshot +
   news_coverage for the factor engine
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

from personal_quant import db

from news.dedup import novelty_scores
from news.events import extract_events
from news.storage import (export_events_snapshot, replace_events,
                          write_coverage)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_documents(table: str = "news_documents") -> pd.DataFrame:
    """默认读 canonical 的 news_documents；v2 重建读 news_documents_v2。"""
    conn = db.connect()
    return conn.execute(
        f"SELECT * FROM {table} WHERE status != 'failed' "
        "ORDER BY published_at"
    ).fetch_df()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true",
                    help="enable the LLM tier (requires DEEPSEEK_API_KEY)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--version", default="v1", choices=["v1", "v2"],
                    help="v2 = 从 news_documents_v2 重建，写 news_events_v2"
                         "（绝不覆盖 v1 的表与快照）")
    args = ap.parse_args()

    doc_table = "news_documents" if args.version == "v1"         else f"news_documents_{args.version}"
    ev_table = "news_events" if args.version == "v1"         else f"news_events_{args.version}"
    print(f"[build-events] 版本 {args.version}: {doc_table} -> {ev_table}")
    docs_df = load_documents(doc_table)
    print(f"documents: {len(docs_df)}")
    if docs_df.empty:
        print("no documents yet — run scripts/news/update_news.py first")
        return 1

    docs_df["published_at"] = pd.to_datetime(docs_df["published_at"],
                                             errors="coerce")
    # per-symbol novelty (title similarity vs previous 30 days)
    docs_df = docs_df.sort_values(["symbol", "published_at"])
    t0 = time.time()
    novelty = []
    for sym, g in docs_df.groupby("symbol", dropna=False):
        titles = g["title"].tolist()
        dates = [pd.Timestamp(d) for d in g["published_at"]]
        novelty.extend(novelty_scores(titles, dates))
    docs_df["novelty"] = novelty
    print(f"novelty computed in {time.time()-t0:.0f}s")

    from news.schema import NewsDocument

    docs = []
    for _, r in docs_df.iterrows():
        pub = r["published_at"]
        docs.append(NewsDocument(
            document_id=r["document_id"], symbol=r["symbol"],
            source=r["source"], source_url=r["source_url"] or "",
            title=r["title"], published_at=pub if pd.notna(pub) else None,
            time_known=bool(r["time_known"]),
            raw_hash=r["raw_hash"], content_hash=r["content_hash"],
            status=r["status"] or "new", org_id=r["org_id"],
        ))

    events = extract_events(docs)
    # attach novelty to the events
    nov_map = {r["document_id"]: r["novelty"] for _, r in docs_df.iterrows()}
    for e in events:
        e.novelty = nov_map.get(e.document_id)

    # LLM tier (opt-in + auto-detect; rule tier always covers everything)
    llm_calls = llm_hits = 0
    if args.llm:
        from news.budget import Budget
        import yaml

        cfg = yaml.safe_load(
            (PROJECT_ROOT / "config" / "news_v1.yaml").read_text(
                encoding="utf-8"))["news"]["llm"]
        budget = Budget(int(cfg["daily_budget_calls"]),
                        int(cfg["daily_budget_tokens"]))
        from news.llm import LLMNewsAnalyzer

        analyzer = LLMNewsAnalyzer(budget=budget,
                                   temperature=float(cfg["temperature"]),
                                   max_tokens=int(cfg["max_tokens"]))
        print(f"LLM tier enabled: {analyzer.enabled} (model "
              f"{analyzer.model})")
        if analyzer.enabled:
            by_id = {e.document_id: e for e in events}
            tier1 = [d for d in docs if analyzer.should_analyze(d)]
            print(f"tier-1 documents for LLM: {len(tier1)}")
            for d in tier1:
                ev = by_id[d.document_id]
                new_ev = analyzer.analyze(d)
                ev.sentiment = new_ev.sentiment
                ev.importance = new_ev.importance
                ev.novelty = new_ev.novelty or ev.novelty
                ev.financial_impact = new_ev.financial_impact
                ev.risk = new_ev.risk
                ev.confidence = new_ev.confidence
                ev.event_type = new_ev.event_type
                ev.extraction_method = new_ev.extraction_method
                ev.extraction_model = new_ev.extraction_model
                ev.extraction_version = new_ev.extraction_version
            llm_calls = analyzer.calls
            llm_hits = analyzer.cache_hits
            print(f"LLM: {llm_calls} calls, {llm_hits} cache hits, "
                  f"{analyzer.failures} failures, budget {budget.summary()}")
        else:
            print("LLM tier disabled (no DEEPSEEK_API_KEY) — "
                  "RULE_BASED_ONLY, per spec")

    if args.dry_run:
        from news.events import rule_stats

        stats = rule_stats([d.title for d in docs])
        print("event-type distribution:", dict(sorted(
            stats.items(), key=lambda kv: -kv[1])))
        print(f"would write {len(events)} events (dry run)")
        return 0

    n = replace_events(events, table=ev_table)
    export_events_snapshot(events, version=args.version)
    # coverage: fetched symbols with their dataset start (first publication)
    cov = docs_df.groupby("symbol")["published_at"].min().reset_index()
    cov.columns = ["symbol", "start_date"]
    write_coverage(cov, version=args.version)
    print(f"events: {n} -> DuckDB + snapshot; coverage: {len(cov)} symbols")
    return 0


if __name__ == "__main__":
    sys.exit(main())
