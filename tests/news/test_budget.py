# -*- coding: utf-8 -*-
"""Daily LLM budget: limits enforce RULE_BASED_ONLY fallback."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from news.budget import Budget


@pytest.fixture
def tmp_state(tmp_path, monkeypatch):
    monkeypatch.setattr("news.budget.STATE_PATH", tmp_path / "budget.json")
    yield tmp_path
    monkeypatch.setattr("news.budget.STATE_PATH",
                        Path(__file__).parent / "nonexistent")


def test_unlimited_budget_available(tmp_state):
    b = Budget()
    assert b.available()
    b.record(100)
    assert b.calls_used == 1


def test_call_limit(tmp_state):
    b = Budget(max_calls=2)
    assert b.available()
    b.record()
    assert b.available()
    b.record()
    assert not b.available()


def test_token_limit(tmp_state):
    b = Budget(max_tokens=1000)
    assert b.available(estimated_tokens=600)
    b.record(600)
    assert not b.available(estimated_tokens=600)
    assert b.available(estimated_tokens=100)


def test_state_persists_across_instances(tmp_state):
    Budget(max_calls=10).record(50)
    b2 = Budget(max_calls=10)
    assert b2.calls_used == 1 and b2.tokens_used == 50


def test_summary(tmp_state):
    b = Budget(max_calls=5, max_tokens=500)
    b.record(10)
    s = b.summary()
    assert s["calls"] == 1 and s["max_calls"] == 5
