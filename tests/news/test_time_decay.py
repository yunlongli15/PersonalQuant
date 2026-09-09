# -*- coding: utf-8 -*-
"""Exponential time decay weights (half-life grid, spec 26)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pytest

from news.decay import HALF_LIFE_CANDIDATES, decay_weights, decayed_sum


def test_half_life_grid():
    assert HALF_LIFE_CANDIDATES == (1, 3, 5, 10, 20)


def test_weight_at_zero_is_one():
    for hl in HALF_LIFE_CANDIDATES:
        assert decay_weights(np.array([0.0]), hl)[0] == pytest.approx(1.0)


def test_weight_at_half_life_is_half():
    for hl in HALF_LIFE_CANDIDATES:
        assert decay_weights(np.array([float(hl)]), hl)[0] == \
            pytest.approx(0.5)


def test_shorter_half_life_decays_faster():
    ages = np.array([5.0, 10.0])
    assert decay_weights(ages, 1).max() < decay_weights(ages, 20).max()


def test_negative_ages_weight_zero():
    assert decay_weights(np.array([-1.0]), 5)[0] == 0.0


def test_decayed_sum_weights_by_age():
    s = decayed_sum([1.0, 1.0], [0.0, 100.0], half_life=5)
    assert s == pytest.approx(1.0)  # ancient event contributes ~nothing
