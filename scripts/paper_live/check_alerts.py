# -*- coding: utf-8 -*-
"""告警检查（spec §29 / §42）。只报警，不交易、不改参数。

    python scripts/paper_live/check_alerts.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _runner
from paper_live import metrics as pm
from paper_live.alerts import check_alerts, summarize
from paper_live.drift import (load_model_baseline, model_drift,
                              strategy_drift)


def main() -> int:
    cfg, store, provider = _runner.build()
    met = pm.metrics_frame(store)
    preds = pm.predictions_frame(store)
    nav = pm.nav_series(store)

    drift = {"strategy": strategy_drift(cfg)}
    if not preds.empty:
        drift["model"] = model_drift(preds["predicted_return"],
                                     load_model_baseline())

    history = {}
    if not met.empty and len(met) > 3:
        history["turnover_median"] = float(met["turnover"].median())

    alerts = check_alerts(metrics=met.iloc[-1].to_dict() if not met.empty
                          else {}, drift=drift, audit={}, cfg=cfg,
                          history=history)
    s = summarize(alerts)
    print(f"forward holdout: {store.summary()}")
    print(f"净值点 {len(nav)}")
    if not alerts:
        print("无告警。")
    for a in alerts:
        print(f"[{a['level']}] {a['code']}: {a['detail']}")
    print(f"合计 {s['n']} 条 {s['by_level']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
