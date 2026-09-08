# STEP 3 point-in-time / leakage audit

generated: 2026-09-08 21:38

- [PASS] feature date <= signal date — feature slices are per-signal-date; provider loads data <= T only (left-padded history, no right padding)
- [PASS] label date > signal date — label horizon = +20 trading days, computed from t+horizon only
- [PASS] training data < prediction date — train 2021-12-31 < test 2024-01-31
- [PASS] validation data < prediction date — valid 2023-12-29 < test 2024-01-31
- [PASS] universe <= signal date — build_universe uses list_date/delist_date/bar history with trade_date <= T; no future information
- [PASS] ST status <= signal date — backtest ST filter disabled (no historical ST series; using the current snapshot historically would leak); paper live uses the current snapshot explicitly
- [PASS] list/delist <= signal date — securities.list_date/delist_date are static historical facts (official exchange records), applied at the signal date
- [PASS] no financial data enters features — v1 feature set = Alpha158 (price/volume only); financial metrics are not used at all in strategy_v1
- [PASS] transaction uses T+1 open, not T close — execution.execute_order fills at T+1 open; T close only used for the signal/weights
- [PASS] no current constituent list used historically — universe comes from securities + bars, never from any current-constituent snapshot

feature cache: 132 monthly slices, first 2015-01, last 2025-12

**10/10 checks PASS**