# -*- coding: utf-8 -*-
"""配置冻结与成本模型（spec §24 / §35 / §46）。

最重要的一条：**实验里的费率必须与生产同一个模型**，不是复制一份数字。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
import yaml

from daily_exit_paper import config as C


def test_config_validates(cfg):
    """配置自洽性。**不写死具体身份值**。

    原先这里断言 `strategy_version == "daily_exit_paper_v1"` —— 那只是
    "默认配置恰好是 v1"的同义反复。默认改成 clean 之后它就红了，
    而它想守的东西（配置自洽）其实与哪个实验无关。
    身份字段改成与**配置文件名**对齐，两个实验各自的配置都受这条约束。
    """
    s = C.validate(cfg)
    assert s["strategy_version"] == C.CONFIG_PATH.stem
    assert s["base_signal_strategy"] in ("strategy_v2", "production_clean_v1")
    # 写了 signal_strategy 就必须与 base 一致 —— 两者分叉意味着
    # "实验自称是什么"和"它实际读哪套信号"不是一回事
    if "signal_strategy" in s:
        assert s["signal_strategy"] == s["base_signal_strategy"]
    assert s["signal_horizon_days"] == 20
    assert s["top_k"] == 20
    assert s["risk_profile"] == "balanced"
    assert s["exit"]["signal_exit_enabled"] is False
    assert s["exit_resolution"]["intraday_conflict"] == "stop_first"
    assert s["execution"]["partial_fill"] == "unsupported"


def test_both_experiment_configs_validate():
    """两个实验的配置**都要**能过校验 —— 别只顾着默认那一个。"""
    root = C.PROJECT_ROOT / "config"
    paths = sorted(root.glob("daily_exit_paper*.yaml"))
    assert len(paths) >= 2, f"只找到 {paths}"
    for p in paths:
        s = C.validate(C.load_config(p))
        assert s["strategy_version"] == p.stem
        assert s["paths"]["root"].endswith(s["strategy_version"]), (
            f"{p.name} 的目录 {s['paths']['root']} 与实验名对不上")


def test_frozen_values_match_the_inherited_sources(cfg):
    """v1 的每个数值都必须与被继承的既有来源一致（不得自行选值）。"""
    s = C.spec(cfg)
    v2 = yaml.safe_load(
        (C.PROJECT_ROOT / "config" / "strategy_v2.yaml").read_text("utf-8"))
    assert s["signal_horizon_days"] == v2["alpha"]["label_horizon_days"]
    assert s["top_k"] == v2["portfolio"]["top_k"]
    assert float(s["sizing"]["invest_target"]) == \
        float(v2["portfolio"]["constraints"]["invest_target"])
    # time_stop 是既有公式 horizon*2 的定义，不是可调项
    assert int(s["time_stop"]["days"]) == s["signal_horizon_days"] * 2


def test_cost_model_is_the_production_model(cfg):
    """费率逐字等于为生产 paper_live 冻结的那一套 —— 禁止第二套费率。"""
    mine = C.spec(cfg)["transaction_costs"]
    prod = yaml.safe_load(
        (C.PROJECT_ROOT / "config" / "paper_live.yaml")
        .read_text("utf-8"))["paper_live"]["transaction_costs"]
    assert mine == prod

    from personal_quant.strategy.costs import TransactionCostModel

    model = TransactionCostModel.from_config({"transaction_costs": mine})
    assert model.commission_rate == 0.00025
    assert model.min_commission == 5.0
    assert model.stamp_duty == 0.0005
    assert model.transfer_fee == 0.00001
    assert model.slippage == 0.0005


def test_sell_costs_more_than_buy_on_the_same_value(cfg):
    """卖出多了印花税 —— 买卖不对称必须由同一个模型给出。"""
    from personal_quant.strategy.costs import TransactionCostModel

    m = TransactionCostModel.from_config(
        {"transaction_costs": C.spec(cfg)["transaction_costs"]})
    assert m.sell_cost(10_000.0) > m.buy_cost(10_000.0)
    assert m.sell_cost(10_000.0) - m.buy_cost(10_000.0) == pytest.approx(
        10_000.0 * m.stamp_duty)


@pytest.mark.parametrize("key,value,msg", [
    ("top_k", 10, "top_k"),
    ("signal_horizon_days", 5, "signal_horizon_days"),
])
def test_validate_rejects_tampered_frozen_values(cfg, key, value, msg):
    bad = {**cfg, "daily_exit_paper": {**C.spec(cfg), key: value}}
    with pytest.raises(C.ConfigError) as e:
        C.validate(bad)
    assert msg in str(e.value)


def test_validate_rejects_tampered_time_stop(cfg):
    s = dict(C.spec(cfg))
    s["time_stop"] = {**s["time_stop"], "days": 30}
    with pytest.raises(C.ConfigError):
        C.validate({**cfg, "daily_exit_paper": s})


def test_validate_rejects_enabling_signal_exit(cfg):
    s = {**C.spec(cfg)}
    s["exit"] = {**s["exit"], "signal_exit_enabled": True}
    with pytest.raises(C.ConfigError):
        C.validate({**cfg, "daily_exit_paper": s})


def test_config_hash_ignores_the_freeze_block(tmp_path):
    """freeze 块不参与自己的哈希（否则自指，必然报 drift）。"""
    a = tmp_path / "a.yaml"
    b = tmp_path / "b.yaml"
    body = "daily_exit_paper:\n  version: '1.0'\n"
    a.write_text(body + "  freeze: {}\n", encoding="utf-8")
    b.write_text(body + "  freeze:\n    config_sha256: deadbeef\n",
                 encoding="utf-8")
    assert C.config_sha256(a) == C.config_sha256(b)


def test_verify_config_refuses_drift():
    with pytest.raises(C.ConfigDrift) as e:
        C.verify_config(expected_sha="0" * 64)
    assert "新建版本" in str(e.value)


def test_verify_config_passes_on_the_recorded_hash():
    assert C.verify_config(expected_sha=C.config_sha256()) == \
        C.config_sha256()
