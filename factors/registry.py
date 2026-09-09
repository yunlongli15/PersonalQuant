# -*- coding: utf-8 -*-
"""Factor registry: metadata + compute function for every factor.

FACTOR_REGISTRY[name] carries the research metadata (category, formula,
source, required fields, PIT requirement, direction, description, version,
status). FACTORS[name] carries the compute function:

    fn(data: FactorData, dates: list[pd.Timestamp]) -> pd.DataFrame
        index = dates, columns = symbols, values = factor value (raw scale)

direction: the ECONOMIC intuition sign (positive/negative/neutral) — the
empirical sign measured by the evaluator is stored separately in the factor
report; direction is never flipped to make IC look better.
"""

from __future__ import annotations

from typing import Callable, Dict

FACTOR_REGISTRY: Dict[str, dict] = {}
FACTORS: Dict[str, Callable] = {}


def register(meta: dict) -> Callable:
    """Register a factor's metadata + compute function (decorator factory)."""
    required = {"factor_name", "category", "formula", "source",
                "required_fields", "pit", "direction", "description",
                "version", "status"}
    missing = required - set(meta)
    if missing:
        raise ValueError(f"factor {meta.get('factor_name')!r} missing: {missing}")
    name = meta["factor_name"]
    if name in FACTOR_REGISTRY:
        raise ValueError(f"duplicate factor name {name!r}")
    if meta["direction"] not in ("positive", "negative", "neutral"):
        raise ValueError(f"bad direction for {name}: {meta['direction']!r}")
    if meta["pit"] not in (True, False):
        raise ValueError(f"bad pit flag for {name}: {meta['pit']!r}")
    FACTOR_REGISTRY[name] = dict(meta)

    def deco(fn: Callable) -> Callable:
        FACTORS[name] = fn
        return fn

    return deco


def registry_df():
    import pandas as pd

    return pd.DataFrame(FACTOR_REGISTRY.values()).set_index("factor_name")


def categories() -> Dict[str, list]:
    out: Dict[str, list] = {}
    for name, meta in FACTOR_REGISTRY.items():
        out.setdefault(meta["category"], []).append(name)
    return out
