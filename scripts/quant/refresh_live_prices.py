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

    from pipeline.signals import load_signals, signals_state
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

    # 判据是"比**信号日**新"，不是"等于今天"。信号日就是本地数据截止的
    # 那一天：只要拿到的收盘价比它新（例如当天已收盘、上游还没发布），
    # 覆盖它才有意义。写死"== 今天"的话，周末/节假日会把 60 个标的全部
    # 记成"失败"，看着像网络故障，其实只是没有更新的数据。
    sig_date = str(signals_state().get("as_of") or "")

    p = AkShareMarketProvider()
    today = time.strftime("%Y-%m-%d")
    start = (time.strftime("%Y-%m-%d",
                           time.localtime(time.time() - 10 * 86400)))
    prices, not_newer, failed = {}, [], []
    latest_bar = ""
    for i, sym in enumerate(symbols, 1):
        try:
            df = p.fetch_daily_history(sym, start, today)
            if df.empty:
                failed.append(sym)
                continue
            row = df.sort_values("trade_date").iloc[-1]
            d = str(row["trade_date"].date())
            latest_bar = max(latest_bar, d)
            if sig_date and d <= sig_date:
                not_newer.append(f"{sym}({d})")
                continue
            prices[sym] = {"close": float(row["close"]), "date": d,
                           "pct_chg": float(row.get("pct_chg") or 0.0)
                           if "pct_chg" in row else None}
        except Exception as e:                               # noqa: BLE001
            failed.append(f"{sym}({type(e).__name__})")
        if i % 10 == 0:
            print(f"  {i}/{len(symbols)} ...", flush=True)
        time.sleep(args.sleep * (0.7 + 0.6 * ((i * 7919) % 100) / 100))

    price_date = max((v["date"] for v in prices.values()), default=None)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "price_date": price_date, "signal_date": sig_date,
        "latest_bar_date": latest_bar or None,
        "n": len(prices), "not_newer": len(not_newer),
        "failed": failed, "prices": prices},
        ensure_ascii=False, indent=2), encoding="utf-8")
    if prices:
        print(f"live prices: {len(prices)}/{len(symbols)} @ {price_date}"
              f" -> {OUT}")
    elif not_newer and not failed:
        print(f"live prices: 无更新 —— 最新 bar {latest_bar} 不晚于信号日 "
              f"{sig_date}，没有更外的价格可用（计划沿用信号日收盘价）")
    else:
        print(f"live prices: 0/{len(symbols)} -> {OUT}")
    if failed:
        print(f"  failed: {len(failed)} ({failed[:5]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
