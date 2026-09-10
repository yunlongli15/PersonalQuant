# -*- coding: utf-8 -*-
"""Cash buffer (spec §20/§42): stock weights sum to 1 - cash_buffer, and
the scarce-candidate scaling keeps cash >= buffer by construction."""

import pytest

from portfolio.backtest import effective_target
from portfolio.constraints import PortfolioConstraints


def test_from_dict_cash_buffer():
    cons = PortfolioConstraints.from_dict({"cash_buffer": 0.05})
    assert abs(cons.invest_target - 0.95) < 1e-12
    cons = PortfolioConstraints.from_dict({"cash_buffer": 0.10})
    assert abs(cons.invest_target - 0.90) < 1e-12


def test_from_dict_explicit_invest_target_wins():
    cons = PortfolioConstraints.from_dict(
        {"cash_buffer": 0.05, "invest_target": 0.90})
    assert abs(cons.invest_target - 0.90) < 1e-12


@pytest.mark.parametrize("cash_buffer", [0.05, 0.10, 0.15])
def test_scaling_keeps_cash_above_buffer(cash_buffer):
    target = 1.0 - cash_buffer
    for n in (1, 2, 5, 19, 20):
        eff = effective_target(n, 20, target)
        assert eff <= target + 1e-12
        # every pick targets target/top_k, so the invested fraction is
        # n/top_k of the target and cash is at least the buffer
        assert (1.0 - eff) >= cash_buffer - 1e-12
