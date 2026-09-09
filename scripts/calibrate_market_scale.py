# -*- coding: utf-8 -*-
"""STEP 4 market data repair: per-stock volume/amount scale calibration.

Background: the canonical daily_bars volume/amount fields carry a per-stock
multiplicative scale (Yahoo adjustment artifacts in the source pipeline) that
varies ~200x across stocks — within a stock the scale is constant (audit:
within-stock CV of amount/(close*volume) ~ 0.11), but cross-stock comparison
is broken. Prices (close/factor) are unaffected (verified vs Tencent in
STEP 2).

Repair pipeline (raw -> detection -> repair -> validation):

  1. per stock fetch ground-truth daily history:
       - EastMoney push2his via akshare (volume in lots, amount in CNY,
         turnover in %) over the full window; intermittent WAF risk
       - fallback: Tencent kline, most recent 640 trading days (volume only)
     every response is cached under data/raw/akshare/kline_cal/<code>.json
  2. join with canonical bars on trade_date; compute per-stock median
     gt/canonical ratios -> scale_volume (canonical volume * scale = shares),
     scale_amount (canonical amount * scale = CNY; EastMoney only)
  3. stability check: within-stock ratio CV < 0.3 (constant-scale model)
  4. write data/parquet/market/market_scale.parquet (original ratio +
     repaired multiplier + reason + repair_version) and the derived
     turnover cache data/derived/factors/em_turnover.parquet
  5. register the repair in source_registry

Canonical daily_bars are NEVER modified: strategy_v1 stays bit-identical.
The factor engine consumes the calibrated columns (volume_shares =
volume*scale_volume, amount_cny = amount*scale_amount where available,
else volume_shares*close).

    python scripts/calibrate_market_scale.py --limit 60          # smoke test
    python scripts/calibrate_market_scale.py                     # full run
"""

import argparse
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from personal_quant import config, db
from personal_quant.repair.market_scale import (calibrate_one, finalize_table,
                                                load_canonical)
from personal_quant.storage.parquet import register_source

RAW_CAL = config.RAW_DIR / "akshare" / "kline_cal"
SCALE_PATH = config.PARQUET_SUBDIRS["market"] / "market_scale.parquet"
TURNOVER_PATH = Path(config.PARQUET_SUBDIRS["market"].parent.parent) \
    / "derived" / "factors" / "em_turnover.parquet"


# load_canonical / calibrate_one live in personal_quant/repair/market_scale.py
# (shared with scripts/build_scale_from_cache.py)


def fetch_eastmoney(code: str) -> dict:
    """Full-window EM push2his history: volume(lots), amount(CNY), turnover(%)."""
    import akshare as ak

    df = ak.stock_zh_a_hist(
        symbol=code, period="daily",
        start_date="20180101", end_date=datetime.now().strftime("%Y%m%d"),
        adjust="",
    )
    df = df.rename(columns={
        "日期": "trade_date", "成交量": "volume_lot",
        "成交额": "amount", "换手率": "turnover_pct",
    })
    rows = df[["trade_date", "volume_lot", "amount", "turnover_pct"]].copy()
    rows["trade_date"] = pd.to_datetime(rows["trade_date"]).dt.strftime("%Y-%m-%d")
    return {"source": "eastmoney", "rows": rows.to_dict("records")}


def fetch_tencent(symbol: str) -> dict:
    """Recent 640 trading days from Tencent kline (volume in lots, no amount)."""
    import requests

    prefix = symbol.split(".")[1].lower()
    code = symbol.split(".")[0]
    param = f"{prefix}{code},day,2018-01-01,2099-12-31,640,"
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={param}"
    resp = requests.get(url, headers={
        "User-Agent": config.USER_AGENT,
        "Referer": "https://stockapp.finance.qq.com/",
    }, timeout=config.HTTP_TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(f"tencent kline HTTP {resp.status_code}")
    data = resp.json()
    node = (data.get("data") or {}).get(f"{prefix}{code}") or {}
    rows = node.get("day") or node.get("qfqday") or []
    if not rows:
        raise RuntimeError(f"tencent kline returned no rows for {symbol}")
    out = []
    for r in rows:
        out.append({
            "trade_date": r[0],
            "volume_lot": float(r[5]),
            "amount": None,
            "turnover_pct": None,
        })
    return {"source": "tencent", "rows": out}


def fetch_history(symbol: str, source: str, resume: bool) -> tuple:
    """Return (payload, em_failed)."""
    code = symbol.split(".")[0]
    cache = RAW_CAL / f"{code}.json"
    if resume and cache.exists():
        try:
            payload = json.loads(cache.read_text(encoding="utf-8"))
            if payload.get("rows"):
                return payload, False
        except (ValueError, KeyError):
            pass
    payload = None
    em_failed = False
    if source in ("auto", "eastmoney"):
        try:
            payload = fetch_eastmoney(code)
        except Exception as e:
            em_failed = True
            print(f"[calibrate] eastmoney failed for {symbol}: "
                  f"{type(e).__name__}", flush=True)
    if payload is None and source in ("auto", "tencent"):
        try:
            payload = fetch_tencent(symbol)
        except Exception as e:
            print(f"[calibrate] tencent failed for {symbol}: "
                  f"{type(e).__name__}", flush=True)
    if payload is None:
        return {"source": "failed", "rows": []}, em_failed
    cache.parent.mkdir(parents=True, exist_ok=True)
    payload["fetched_at"] = datetime.now().isoformat(timespec="seconds")
    cache.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload, em_failed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0,
                    help="only process the first N stocks (0 = all)")
    ap.add_argument("--source", default="auto",
                    choices=["auto", "eastmoney", "tencent"])
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument("--no-sleep", action="store_true",
                    help="skip the polite delay (smoke tests only)")
    args = ap.parse_args()

    # securities list: one short DuckDB burst, then close the DB so other
    # processes (PDF fetcher etc.) can use it during the long fetch loop
    conn = db.connect()
    sec = conn.execute(
        "SELECT symbol FROM securities WHERE exchange IN ('SH','SZ') "
        "ORDER BY symbol"
    ).fetch_df()["symbol"].tolist()
    db.close()

    canon = load_canonical(args.start)
    print(f"[calibrate] canonical rows 2018+: {len(canon):,}", flush=True)
    symbols = sec[:args.limit] if args.limit else sec

    done = 0
    results = []
    em_fail_streak = 0
    em_disabled = False
    t0 = time.time()
    for i, symbol in enumerate(symbols):
        # circuit breaker: consecutive eastmoney failures mean the interface
        # is WAF-blocked for this IP; stop paying the failure cost
        source_eff = "tencent" if (em_disabled and args.source == "auto") \
            else args.source
        payload, em_failed = fetch_history(symbol, source_eff,
                                           resume=not args.no_resume)
        if em_failed:
            em_fail_streak += 1
            if em_fail_streak >= 20 and args.source == "auto":
                em_disabled = True
                print("[calibrate] 20 consecutive eastmoney failures: "
                      "disabling eastmoney for the rest of this run", flush=True)
        else:
            em_fail_streak = 0
        if payload["source"] == "failed":
            results.append({"symbol": symbol, "source": "failed", "n_overlap": 0})
            continue
        res = calibrate_one(canon, symbol, payload)
        if res is None:
            results.append({"symbol": symbol, "source": payload["source"],
                            "n_overlap": 0})
        else:
            results.append(res)
        done += 1
        if not args.no_sleep:
            time.sleep(random.uniform(config.MIN_DELAY_SECONDS,
                                      config.MAX_DELAY_SECONDS))
        if done % 100 == 0:
            rate = done / max(time.time() - t0, 1)
            print(f"[calibrate] {done}/{len(symbols)} ({rate:.2f}/s, "
                  f"eta {(len(symbols)-done)/rate/60:.0f}min)", flush=True)

    out = finalize_table(results)
    SCALE_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(SCALE_PATH, index=False)

    ok = out[(out["n_overlap"] > 0)]
    print("\n===== calibration summary =====")
    print(f"stocks: {len(out)}, calibrated: {len(ok)}, "
          f"eastmoney: {(ok['source']=='eastmoney').sum()}, "
          f"tencent: {(ok['source']=='tencent').sum()}")
    if len(ok):
        print(f"scale_volume: p10={ok['scale_volume'].quantile(.1):.3f} "
              f"median={ok['scale_volume'].median():.3f} "
              f"p90={ok['scale_volume'].quantile(.9):.3f}")
        print(f"ratio_cv < 0.3 (stable constant scale): "
              f"{(ok['ratio_cv'] < 0.3).mean():.1%}")
        em = ok[ok["source"] == "eastmoney"].dropna(subset=["scale_amount"])
        if len(em):
            print(f"scale_amount: p10={em['scale_amount'].quantile(.1):.3f} "
                  f"median={em['scale_amount'].median():.3f} "
                  f"p90={em['scale_amount'].quantile(.9):.3f}")
            print(f"implied-amount vs EM amount median rel diff: "
                  f"{em['amount_implied_check'].median():.4f}")
    if args.limit:
        print("\nper-stock:")
        print(out[out["n_overlap"] > 0].to_string(index=False))
        return 0

    # derived turnover cache (EastMoney 换手率, per-day pct) from raw caches
    turn_rows = []
    for code_file in sorted(RAW_CAL.glob("*.json")):
        payload = json.loads(code_file.read_text(encoding="utf-8"))
        if payload.get("source") != "eastmoney":
            continue
        code = code_file.stem
        for r in payload["rows"]:
            if r.get("turnover_pct") is None:
                continue
            turn_rows.append({
                "symbol": f"{code}.SH" if code.startswith(("6", "9"))
                else f"{code}.SZ",
                "trade_date": pd.Timestamp(r["trade_date"]),
                "turnover_pct": float(r["turnover_pct"]),
            })
    if turn_rows:
        turn = pd.DataFrame(turn_rows)
        turn["source"] = "eastmoney_push2his"
        TURNOVER_PATH.parent.mkdir(parents=True, exist_ok=True)
        turn.to_parquet(TURNOVER_PATH, index=False)
        print(f"derived turnover cache: {len(turn)} rows -> {TURNOVER_PATH}")
    else:
        print("derived turnover cache: no eastmoney rows available")

    try:
        conn = db.connect()
        register_source(
            source_name="market_scale_repair_v1",
            data_type="daily_bars.volume_scale/daily_bars.amount_scale",
            url="local repair script scripts/calibrate_market_scale.py "
                "(ground truth: eastmoney push2his / tencent kline)",
            version=REPAIR_VERSION,
            file=str(SCALE_PATH),
            parser_version=REPAIR_VERSION,
        )
        db.close()
        print(f"wrote {SCALE_PATH}; registered in source_registry")
    except Exception as e:
        print(f"WARNING: source_registry write failed ({type(e).__name__}: "
              f"{e}); re-run the tail of this script to register")
    return 0


if __name__ == "__main__":
    sys.exit(main())
