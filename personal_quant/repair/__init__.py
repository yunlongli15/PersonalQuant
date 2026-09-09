# -*- coding: utf-8 -*-
"""Canonical-layer repair pipelines (STEP 4).

raw -> detection -> repair -> validation, with original/repaired/reason/
repair_version recorded. Canonical daily_bars are never modified in place;
repairs produce registered calibration tables consumed by the factor
engine (see docs/step4_market_data_quality.md).
"""
