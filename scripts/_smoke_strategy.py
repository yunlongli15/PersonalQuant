# -*- coding: utf-8 -*-
"""Temp: end-to-end smoke test of the strategy pipeline (small scale)."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from personal_quant.strategy import benchmarks as bm
from personal_quant.strategy import metrics as mt
from personal_quant.strategy.backtest import MonthlyBacktest
from personal_quant.strategy.costs import TransactionCostModel
from personal_quant.strategy.features import build_training_data, compute_features
from personal_quant.strategy.model import AlphaModel, compute_ic
from personal_quant.strategy.qlib_provider import init_qlib_with_canonical
from personal_quant.strategy.rebalance import rebalance_dates
from personal_quant.strategy.universe import build_universe

config = __import__("yaml").safe_load(
    Path("config/strategy_v1.yaml").read_text(encoding="utf-8")
)

t0 = time.time()
init_qlib_with_canonical()
print(f"init: {time.time()-t0:.1f}s")

# universe across the smoke period
train_dates = rebalance_dates("2015-06-01", "2015-10-31")
test_dates = rebalance_dates("2015-11-01", "2015-12-31")
insts = set()
for d in train_dates + test_dates:
    insts.update(build_universe(d, config)["symbol"].tolist())
instruments = sorted(insts)
print(f"instruments: {len(instruments)}, train dates: {len(train_dates)}")

t1 = time.time()
feats = compute_features(instruments, train_dates + test_dates, cache=False)
print(f"features: {time.time()-t1:.1f}s, dates: {len(feats)}")

train_df = build_training_data(instruments, train_dates)
print("train rows:", len(train_df))
model = AlphaModel(dict(config["model"]["params"]), seed=42)
model.fit(train_df.drop(columns=["label", "date", "symbol"]), train_df["label"])
print("model fitted")

# predictions on test dates with labels for IC
from personal_quant.strategy.features import compute_labels

frames = []
for d in test_dates:
    f = feats.get(d)
    if f is None or f.empty:
        continue
    lab = compute_labels(instruments, [d])[d]
    m = f.join(lab.rename("label"), how="inner")
    m["prediction"] = model.predict(m[model.feature_columns])
    m["date"] = d
    frames.append(m.reset_index()[["date", "symbol", "prediction", "label"]])
preds = pd.concat(frames)
ic = compute_ic(preds)
print("IC:", ic[["ic", "rank_ic"]].mean().to_dict() if len(ic) else "empty")

# backtest
bt = MonthlyBacktest(config, TransactionCostModel.from_config(config), 1_000_000)
res = bt.run("2015-11-01", "2015-12-31",
             lambda d, syms: model.predict_series(
                 feats[d].reindex(syms)[model.feature_columns].fillna(0.0),
                 syms) if d in feats and not feats[d].empty else pd.Series(dtype=float))
print("nav points:", len(res.nav), "| trades:", len(res.trades),
      "| final:", float(res.nav.iloc[-1]))
print("monthly turnover:", res.turnover.to_dict() if len(res.turnover) else {})

# momentum baseline
mom = bm.momentum_scores
res_mom = bt.run("2015-11-01", "2015-12-31",
                 lambda d, syms: mom(d, syms, 60))
print("momentum nav final:", float(res_mom.nav.iloc[-1]),
      "| trades:", len(res_mom.trades))

# benchmarks
idx300 = bm.index_nav("000300.SH", "2015-11-01", "2015-12-31")
print("csi300 final:", float(idx300.iloc[-1]))
print("strategy summary:", {k: round(v, 4) for k, v in
      mt.summarize(res.nav, idx300, res.turnover, len(res.trades)).items()
      if isinstance(v, float)})
print(f"TOTAL: {time.time()-t0:.1f}s")
