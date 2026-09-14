# -*- coding: utf-8 -*-
"""Fetch today's closes for a candidate list (used when the upstream
snapshot has not published the current session yet).

    python scripts/quant/refresh_live_prices.py --top 60

The signal date stays at the last COMPLETE data day; only prices move.
Polite by construction: single connection, one request per symbol, with
the project's standard random delay, and the raw response cached by the
provider.
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT = PROJECT_ROOT / "data" / "quant" / "live_prices.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=60,
                    help="how many top-ranked symbols to refresh")
    ap.add_argument("--symbols", default=None,
                    help="explicit comma-separated list (overrides --top)")
    ap.add_argument("--sleep", type=float, default=1.2)
    args = ap.parse_args()

    from pipeline.signals import load_signals
    from trade_plan.plan import _index_like

    sig = load_signals()
    if sig.empty:
        print("no signal snapshot — run signal_refresh first")
        return 1
    sig = sig[~sig["symbol"].isin(_index_like())]
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",")]
    else:
        symbols = sig.sort_values("prediction", ascending=False) \
            .head(args.top)["symbol"].tolist()

    from personal_quant.providers.akshare_market import AkShareMarketProvider

    p = AkShareMarketProvider()
    today = time.strftime("%Y-%m-%d")
    start = (time.strftime("%Y-%m-%d",
                           time.localtime(time.time() - 10 * 86400)))
    prices, failed = {}, []
    for i, sym in enumerate(symbols, 1):
        try:
            df = p.fetch_daily_history(sym, start, today)
            if df.empty:
                failed.append(sym)
                continue
            row = df.sort_values("trade_date").iloc[-1]
            d = str(row["trade_date"].date())
            if d == today:
                prices[sym] = {"close": float(row["close"]), "date": d,
                               "pct_chg": float(row.get("pct_chg") or 0.0)
                               if "pct_chg" in row else None}
            else:
                failed.append(f"{sym}({d})")
        except Exception as e:                               # noqa: BLE001
            failed.append(f"{sym}({type(e).__name__})")
        if i % 10 == 0:
            print(f"  {i}/{len(symbols)} ...", flush=True)
        time.sleep(args.sleep * (0.7 + 0.6 * ((i * 7919) % 100) / 100))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"fetched_at": time.strftime(
        "%Y-%m-%d %H:%M:%S"), "price_date": today,
        "n": len(prices), "failed": failed, "prices": prices},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"live prices: {len(prices)}/{len(symbols)} -> {OUT}")
    if failed:
        print(f"  failed: {len(failed)} ({failed[:5]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
