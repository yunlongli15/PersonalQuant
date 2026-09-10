# -*- coding: utf-8 -*-
"""Quant data refresh pipeline (STEP 7C).

Answers two operational questions the GUI must be able to show:

1. **How fresh is each data domain?** (`pipeline/freshness.py`) — reads
   the canonical/DERIVED artifacts and compares their latest date with
   the trading calendar; a stale domain is reported as ⚠ DATA STALE and
   is never silently used (spec §21).
2. **What ran, when, and did it work?** (`pipeline/jobs.py`) — every
   refresh writes a row into a job store (SQLite, data/quant/jobs.db),
   so "why is today's recommendation based on yesterday's factors?" has
   an answer (spec §38).

The refresh entry points (`pipeline/refresh.py`) are thin wrappers over
the existing STEP 2-6 scripts — this package orchestrates, it does not
reimplement data access.
"""
