# -*- coding: utf-8 -*-
"""Expression parser/evaluator: grammar, depth limit, operator whitelist."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from factors.mining import MiningError, eval_expr, parse

ATOMS = {"roe", "momentum_60", "volatility_20", "earnings_yield"}


def test_roundtrip_render():
    for s in ("rank(roe)+rank(momentum_60)",
              "rank(roe)*rank(momentum_60)",
              "log(abs(volatility_20))",
              "rank(roe)/rank(earnings_yield)",
              "(rank(roe)+rank(momentum_60))*rank(volatility_20)"):
        e = parse(s, depth_max=3, atom_names=ATOMS)
        assert parse(e.render(), depth_max=3, atom_names=ATOMS).render() == \
            e.render(), s


def test_depth_limit_enforced():
    with pytest.raises(MiningError, match="depth"):
        parse("rank(a)*rank(b)*rank(c)*rank(d)", depth_max=3,
              atom_names={"a", "b", "c", "d"})
    # depth-3 tree is allowed
    parse("(rank(a)*rank(b))+rank(c)", depth_max=3,
          atom_names={"a", "b", "c"})


def test_operator_whitelist():
    with pytest.raises(MiningError):
        parse("rank(a) @ rank(b)", depth_max=3, atom_names={"a", "b"})
    with pytest.raises(MiningError):
        parse("mean(a)", depth_max=3, atom_names={"a"})  # not a whitelisted unary


def test_unknown_atom_rejected():
    with pytest.raises(MiningError, match="unknown atom"):
        parse("rank(not_a_factor)", depth_max=3, atom_names=ATOMS)


def test_unbalanced_parentheses():
    with pytest.raises(MiningError):
        parse("rank(a", depth_max=3, atom_names={"a"})
    with pytest.raises(MiningError):
        parse("rank(a))", depth_max=3, atom_names={"a"})


def test_eval_arithmetic():
    idx = pd.date_range("2020-01-31", periods=3, freq="ME")
    p = {"a": pd.DataFrame({"x": [1.0, 2.0, 3.0], "y": [4.0, 8.0, 12.0]},
                           index=idx),
         "b": pd.DataFrame({"x": [10.0, 10.0, 10.0], "y": [1.0, 1.0, 1.0]},
                           index=idx)}
    e = parse("rank(a)+rank(b)", depth_max=2, atom_names={"a", "b"})
    r = eval_expr(e, p)
    # rank(x) per row: a ranks {1,4}->[1/2,1]; b ranks {10,1}->[1,1/2]
    assert r.iloc[0]["x"] == pytest.approx(0.5 + 1.0)
    assert r.iloc[0]["y"] == pytest.approx(1.0 + 0.5)


def test_eval_division_by_zero_is_nan():
    idx = pd.date_range("2020-01-31", periods=1, freq="ME")
    p = {"a": pd.DataFrame({"x": [1.0], "y": [1.0]}, index=idx),
         "b": pd.DataFrame({"x": [1.0], "y": [0.0]}, index=idx)}
    e = parse("a/b", depth_max=2, atom_names={"a", "b"})
    r = eval_expr(e, p)
    assert np.isnan(r.iloc[0]["y"])  # 1/0 -> NaN
    assert r.iloc[0]["x"] == 1.0


def test_eval_log_of_negative_is_nan():
    idx = pd.date_range("2020-01-31", periods=1, freq="ME")
    p = {"a": pd.DataFrame({"x": [-5.0]}, index=idx)}
    e = parse("log(a)", depth_max=2, atom_names={"a"})
    r = eval_expr(e, p)
    assert np.isnan(r.iloc[0, 0])
