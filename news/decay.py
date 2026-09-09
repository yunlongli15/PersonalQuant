# -*- coding: utf-8 -*-
"""Exponential time decay for news signals (spec 26).

weight(age_days) = exp(-ln(2) * age / half_life). Half-life candidates
(1/3/5/10/20 days) are compared on the research period by the decay study
— the data decides; no half-life is assumed best a priori.
"""

from __future__ import annotations

import numpy as np

HALF_LIFE_CANDIDATES = (1, 3, 5, 10, 20)


def decay_weights(ages_days, half_life: float) -> np.ndarray:
    """Vectorized weights; ages must be >= 0."""
    ages = np.asarray(ages_days, dtype=float)
    out = np.exp(-np.log(2.0) * ages / float(half_life))
    return np.where(ages < 0, 0.0, out)


def decayed_sum(values, ages_days, half_life: float) -> float:
    """Sum of values weighted by their age decay."""
    if len(values) == 0:
        return 0.0
    return float(np.sum(np.asarray(values) * decay_weights(ages_days,
                                                           half_life)))
