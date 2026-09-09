# -*- coding: utf-8 -*-
"""Interim market-scale table from the raw calibration caches.

The full calibration run (scripts/calibrate_market_scale.py) writes
data/parquet/market/market_scale.parquet only at the end; this script
builds the same table from the per-stock raw caches already fetched
(data/raw/akshare/kline_cal/*.json), so downstream work (factor universe
prep) can start while the fetch loop continues. DB-free.

    python scripts/build_scale_from_cache.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from personal_quant import config
from personal_quant.repair.market_scale import (calibrate_one, finalize_table,
                                                load_canonical)

RAW_CAL = config.RAW_DIR / "akshare" / "kline_cal"


def main() -> int:
    caches = sorted(RAW_CAL.glob("*.json"))
    if not caches:
        print("no calibration caches yet")
        return 1
    canon = load_canonical("2018-01-01")
    results = []
    for f in caches:
        payload = json.loads(f.read_text(encoding="utf-8"))
        code = f.stem
        symbol = f"{code}.SH" if code.startswith(("6", "9")) else f"{code}.SZ"
        if payload.get("source") == "failed" or not payload.get("rows"):
            results.append({"symbol": symbol, "source": "failed",
                            "n_overlap": 0})
            continue
        res = calibrate_one(canon, symbol, payload)
        results.append(res if res is not None else
                       {"symbol": symbol, "source": payload["source"],
                        "n_overlap": 0})
    out = finalize_table(results)
    path = config.PARQUET_SUBDIRS["market"] / "market_scale.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(path, index=False)
    ok = out[out["n_overlap"] > 0]
    print(f"interim market_scale: {len(out)} rows from {len(caches)} caches, "
          f"{len(ok)} calibrated "
          f"(median scale {ok['scale_volume'].median():.2f}) -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
