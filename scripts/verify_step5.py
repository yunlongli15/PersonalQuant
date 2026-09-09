# -*- coding: utf-8 -*-
"""STEP 5 acceptance verification (22 checks).

    python scripts/verify_step5.py

Checks: provider abstraction, announcement/news ingestion, timestamp
normalization, PIT, dedup, symbol mapping, event extraction, event
aggregation, novelty, time decay, rule-based factors, LLM pipeline, LLM
cache, budget control, factor evaluation, ablation, leakage audit,
reproducibility, cost report, news strategy, 2026 paper-live.
PASS/FAIL per item; exit 0 only when all pass.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NEWS_RUN = PROJECT_ROOT / "experiments" / "news" / "news_factor_run_001"
NEWS_ABL = PROJECT_ROOT / "experiments" / "news" / "ablation"
NEWS_STRAT = PROJECT_ROOT / "experiments" / "news" / "strategy"
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}"
          + (f" -- {detail}" if detail else ""))


def main() -> int:
    print("=" * 64)
    print("STEP 5 verification: news and alternative-data factor system")
    print("=" * 64)

    # 1. provider abstraction
    try:
        from news.providers import BaseNewsProvider, PROVIDERS

        ok = len(PROVIDERS) >= 4 and all(
            hasattr(BaseNewsProvider, m) for m in
            ("fetch_announcements", "fetch_news", "audit"))
        check("provider abstraction", bool(ok),
              f"{len(PROVIDERS)} providers: {sorted(PROVIDERS)}")
    except Exception as e:
        check("provider abstraction", False, str(e))

    # 2. announcement ingestion (canonical documents present)
    try:
        import duckdb

        from personal_quant import db

        conn = db.connect()
        n = conn.execute("SELECT COUNT(*) FROM news_documents").fetchone()[0]
        check("announcement ingestion (canonical documents)", n > 0,
              f"{n:,} documents")
    except duckdb.IOException:
        check("announcement ingestion (canonical documents)", False,
              "DuckDB locked by a running backfill — rerun after")
    except Exception as e:
        check("announcement ingestion (canonical documents)", False, str(e))

    # 3. news ingestion pipeline (update_news CLI + state)
    try:
        from scripts.news.update_news import main as _  # noqa: F401

        state = PROJECT_ROOT / "data" / "derived" / "news" / \
            "update_state.json"
        check("news ingestion pipeline (update_news CLI)",
              state.exists(), str(state))
    except Exception as e:
        check("news ingestion pipeline (update_news CLI)", False, str(e))

    # 4. timestamp normalization
    try:
        from news.schema import NewsDocument

        d = NewsDocument(document_id="x", source="sse", source_url="u",
                         title="t", published_at="2025-04-01 19:30")
        check("timestamp normalization (tz-aware Asia/Shanghai)",
              d.published_at.tzinfo is not None
              and str(d.published_at.tzinfo) == "Asia/Shanghai")
    except Exception as e:
        check("timestamp normalization (tz-aware Asia/Shanghai)", False,
              str(e))

    # 5. PIT
    try:
        from news.pit import availability_time

        tz = "Asia/Shanghai"
        a1 = availability_time(pd.Timestamp("2025-04-01 19:30")
                               .tz_localize(tz), True)
        a2 = availability_time(pd.Timestamp("2025-04-01 10:00")
                               .tz_localize(tz), True)
        a3 = availability_time(pd.Timestamp("2025-04-01")
                               .tz_localize(tz), False)
        check("PIT rules", a1 == pd.Timestamp("2025-04-02 09:30")
              .tz_localize(tz) and a2 == pd.Timestamp("2025-04-01 10:00")
              .tz_localize(tz) and a3 == pd.Timestamp("2025-04-02 09:30")
              .tz_localize(tz))
    except Exception as e:
        check("PIT rules", False, str(e))

    # 6. dedup
    try:
        from news.dedup import title_key, title_similarity

        check("deduplication",
              title_key("公告", "600519.SH", "d")
              != title_key("公告", "000001.SZ", "d")
              and title_similarity("关于回购的公告", "关于回购的公告") == 1.0)
    except Exception as e:
        check("deduplication", False, str(e))

    # 7. symbol mapping
    try:
        from personal_quant.symbols import normalize_symbol

        check("symbol mapping", normalize_symbol("600519") == "600519.SH"
              and normalize_symbol("000001") == "000001.SZ")
    except Exception as e:
        check("symbol mapping", False, str(e))

    # 8. event extraction
    try:
        from news.events import classify_title

        cases = [("关于股份回购的公告", "share_buyback"),
                 ("关于减持的公告", "shareholder_change"),
                 ("2024年年度报告", "earnings"),
                 ("关于收到行政处罚决定书的公告", "penalty"),
                 ("关于收到中标通知书的公告", "major_contract")]
        ok = all(classify_title(t)[0] == et for t, et in cases)
        check("event extraction (rule tier)", bool(ok))
    except Exception as e:
        check("event extraction (rule tier)", False, str(e))

    # 9. event aggregation
    try:
        from news.aggregation import aggregate

        ev = pd.DataFrame([
            {"direction": "positive", "importance": 0.5, "risk": 0.0},
            {"direction": "negative", "importance": 0.8, "risk": 0.7},
        ])
        out = aggregate(ev)
        check("event aggregation",
              np.isclose(out["positive_event_score"], 0.5)
              and np.isclose(out["negative_event_score"], 0.8)
              and np.isclose(out["net_score"], -0.3))
    except Exception as e:
        check("event aggregation", False, str(e))

    # 10. novelty
    try:
        from news.dedup import novelty_scores

        nov = novelty_scores(["关于回购的公告", "关于回购的公告"],
                             [pd.Timestamp("2025-01-01")] * 2)
        check("novelty", nov[0] == 1.0 and nov[1] == 0.0)
    except Exception as e:
        check("novelty", False, str(e))

    # 11. time decay
    try:
        from news.decay import decay_weights

        w = decay_weights(np.array([0.0, 5.0]), 5)
        check("time decay", w[0] == 1.0 and abs(w[1] - 0.5) < 1e-12)
    except Exception as e:
        check("time decay", False, str(e))

    # 12. rule-based factors (synthetic)
    try:
        from factors.base import FactorData
        from factors.registry import FACTORS
        import factors.news_factors  # noqa: F401

        cal = pd.date_range("2019-10-01", periods=110, freq="B")
        syms = ["AAA.SH", "BBB.SZ"]
        close = pd.DataFrame(10.0, index=cal, columns=syms)
        vol = pd.DataFrame(1e6, index=cal, columns=syms)
        events = pd.DataFrame([{
            "symbol": "AAA.SH", "event_type": "share_buyback",
            "availability_time": "2020-01-03 10:00", "direction": "positive",
            "importance": 0.5, "sentiment": None, "novelty": 0.9,
            "confidence": None, "risk": None, "extraction_method": "rule"}])
        cov = pd.DataFrame({"symbol": syms,
                            "start_date": [pd.Timestamp("2019-01-01")] * 2})
        data = FactorData(calendar=cal, bars=pd.DataFrame(), adj_close=close,
                          close_raw=close, volume_raw=vol, volume_shares=vol,
                          amount_cny=vol * close, scale=pd.DataFrame(),
                          financial=pd.DataFrame(),
                          industries=pd.Series(dtype=object),
                          news=events, news_cov=cov, scale_available=False)
        p = FACTORS["news_count_5d"](data, dates=[pd.Timestamp("2020-01-06")])
        check("rule-based news factors",
              p.loc["2020-01-06", "AAA.SH"] == 1)
    except Exception as e:
        check("rule-based news factors", False, str(e))

    # 13. LLM factor pipeline (auto-detect, structured output)
    try:
        from news.llm import LLMNewsAnalyzer
        from news.llm.analyzer import _parse_json

        a = LLMNewsAnalyzer()
        ok = (a.model == "deepseek-chat"
              and _parse_json('{"event_type":"earnings","sentiment":0.5,'
                              '"importance":0.5,"novelty":0.5,'
                              '"financial_impact":0.0,"risk":0.2,'
                              '"confidence":0.8}') is not None)
        check("LLM factor pipeline", bool(ok),
              f"enabled={a.enabled} (RULE_BASED_ONLY when no key)")
    except Exception as e:
        check("LLM factor pipeline", False, str(e))

    # 14. LLM cache
    try:
        from news.llm import cache

        key = cache.cache_key("h", "v", "m")
        cache.put("h", "v", "m", {"ok": True})
        ok = cache.get("h", "v", "m") == {"ok": True}
        check("LLM cache", bool(ok))
    except Exception as e:
        check("LLM cache", False, str(e))

    # 15. budget control
    try:
        from news.budget import Budget
        import tempfile

        import news.budget as bmod

        old = bmod.STATE_PATH
        bmod.STATE_PATH = Path(tempfile.mkdtemp()) / "b.json"
        try:
            b = Budget(max_calls=1)
            b.record()
            ok = not b.available()
        finally:
            bmod.STATE_PATH = old
        check("budget control", bool(ok))
    except Exception as e:
        check("budget control", False, str(e))

    # 16. factor evaluation (news factor run artifacts)
    try:
        mf = NEWS_RUN / "manifest.json"
        lb = NEWS_RUN / "leaderboard_news.csv"
        pack = NEWS_RUN / "factor_pack_news_v1.json"
        ok = mf.exists() and lb.exists() and pack.exists()
        detail = ""
        if ok:
            m = json.loads(mf.read_text(encoding="utf-8"))
            detail = f"{m.get('n_news_factors')} factors, " \
                     f"{m.get('news_events_rows')} events"
        check("news factor evaluation", bool(ok), detail)
    except Exception as e:
        check("news factor evaluation", False, str(e))

    # 17. ablation
    try:
        comp = NEWS_ABL / "comparison.csv"
        ok = comp.exists()
        detail = ""
        if ok:
            df = pd.read_csv(comp)
            detail = "variants: " + ", ".join(df["variant"])
        check("news ablation", bool(ok), detail)
    except Exception as e:
        check("news ablation", False, str(e))

    # 18. leakage audit
    try:
        audit = PROJECT_ROOT / "reports" / "step5_news_pit_audit.md"
        check("leakage audit", audit.exists(), str(audit))
    except Exception as e:
        check("leakage audit", False, str(e))

    # 19. reproducibility (manifest fields)
    try:
        mf = NEWS_RUN / "manifest.json"
        ok = mf.exists()
        detail = ""
        if ok:
            m = json.loads(mf.read_text(encoding="utf-8"))
            ok = bool(m.get("created") and m.get("n_news_factors"))
            detail = str(m.get("created"))
        check("reproducibility", bool(ok), detail)
    except Exception as e:
        check("reproducibility", False, str(e))

    # 20. cost report
    try:
        cr = PROJECT_ROOT / "reports" / "step5_news_cost.md"
        check("cost report", cr.exists(), str(cr))
    except Exception as e:
        check("cost report", False, str(e))

    # 21. news strategy
    try:
        cfg = PROJECT_ROOT / "config" / "strategy_v1_news.yaml"
        summary = NEWS_STRAT / "summary.json"
        check("news strategy (strategy_v1_news)",
              cfg.exists() and summary.exists(), str(summary))
    except Exception as e:
        check("news strategy (strategy_v1_news)", False, str(e))

    # 22. 2026 paper-live
    try:
        pl = PROJECT_ROOT / "reports" / "paper_live" / \
            "latest_recommendation_news.csv"
        check("2026 paper-live (news)", pl.exists(), str(pl))
    except Exception as e:
        check("2026 paper-live (news)", False, str(e))

    n_pass = sum(1 for _, ok in RESULTS if ok)
    n_fail = len(RESULTS) - n_pass
    print("-" * 64)
    print(f"SUMMARY: {n_pass} PASS / {n_fail} FAIL")
    print("OVERALL: PASS" if n_fail == 0 else "OVERALL: FAIL")
    for name, ok in RESULTS:
        if not ok:
            print(f"  FAILED: {name}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
