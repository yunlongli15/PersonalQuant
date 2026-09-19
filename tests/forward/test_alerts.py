# -*- coding: utf-8 -*-
"""§29-§31：告警只报警，绝不交易、绝不改参数。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from paper_live.alerts import check_alerts, summarize
from paper_live.config import load_config

CFG = load_config()


def _codes(alerts):
    return {a["code"] for a in alerts}


def test_no_alerts_on_a_clean_day():
    assert check_alerts(metrics={"drawdown": 0.0, "turnover": 0.1},
                        drift={"strategy": {"status": "OK"}}, audit={},
                        cfg=CFG) == []


def test_pit_failure_is_critical():
    a = check_alerts(audit={"status": "INVALID",
                            "checks": [{"name": "price_pit",
                                        "status": "INVALID"}]}, cfg=CFG)
    assert "PIT_FAILURE" in _codes(a)
    assert any(x["level"] == "CRITICAL" for x in a)


def test_strategy_drift_is_critical():
    a = check_alerts(drift={"strategy": {"status": "DRIFT_DETECTED",
                                         "mismatches": ["model"]}}, cfg=CFG)
    assert "STRATEGY_DRIFT" in _codes(a)


def test_drawdown_thresholds_fire_at_the_configured_levels():
    for dd, expect in ((-0.04, False), (-0.06, True), (-0.11, True),
                       (-0.20, True)):
        a = check_alerts(metrics={"drawdown": dd}, cfg=CFG)
        assert ("DRAWDOWN_ALERT" in _codes(a)) is expect, dd


def test_drawdown_alert_says_it_will_not_act():
    a = check_alerts(metrics={"drawdown": -0.12}, cfg=CFG)
    msg = [x for x in a if x["code"] == "DRAWDOWN_ALERT"][0]["detail"]
    assert "不自动减仓" in msg


def test_concentration_warning_still_uses_the_frozen_strategy():
    a = check_alerts(drift={"concentration": {
        "status": "CONCENTRATION_WARNING", "top1_z": 5.0}}, cfg=CFG)
    msg = [x for x in a if x["code"] == "CONCENTRATION_WARNING"][0]["detail"]
    assert "不调整" in msg


def test_abnormal_turnover_needs_history():
    assert "ABNORMAL_TURNOVER" not in _codes(
        check_alerts(metrics={"turnover": 0.9}, cfg=CFG, history={}))
    a = check_alerts(metrics={"turnover": 0.9}, cfg=CFG,
                     history={"turnover_median": 0.1})
    assert "ABNORMAL_TURNOVER" in _codes(a)


def test_ic_negative_streak_warns_but_does_not_change_the_model():
    a = check_alerts(history={"ic_series": [-0.01, -0.02]}, cfg=CFG)
    hit = [x for x in a if x["code"] == "IC_NEGATIVE_STREAK"]
    assert hit and "不调参" in hit[0]["detail"]


def test_alert_summary_counts_levels():
    a = [{"level": "WARNING", "code": "X", "detail": ""},
         {"level": "WARNING", "code": "Y", "detail": ""},
         {"level": "CRITICAL", "code": "Z", "detail": ""}]
    s = summarize(a)
    assert s["n"] == 3 and s["by_level"]["WARNING"] == 2


def test_alerts_never_contain_trade_instructions():
    """告警里不得出现任何下单动作。"""
    a = check_alerts(metrics={"drawdown": -0.20, "turnover": 5.0},
                     drift={"strategy": {"status": "DRIFT_DETECTED"},
                            "model": {"status": "MODEL_DRIFT_WARNING"},
                            "concentration": {"status": "CONCENTRATION_WARNING"}},
                     audit={"status": "INVALID", "checks": []}, cfg=CFG,
                     history={"turnover_median": 0.1, "ic_series": [-0.1, -0.2]})
    for x in a:
        blob = f"{x['code']} {x['detail']}".upper()
        for verb in ("BUY", "SELL", "ORDER", "EXECUTE", "REBALANCE"):
            assert verb not in blob, x
