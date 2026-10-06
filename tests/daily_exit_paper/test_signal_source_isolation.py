# -*- coding: utf-8 -*-
"""前瞻实验的信号/预测来源必须**只属于自己那个策略**。

2026-10-06 的教训，三件事一起坏了：

1. `LiveMarket.signals()` 在找不到 `signals_<策略>_<日期>.parquet` 时
   会**回退到不带策略名的 `signals_<日期>.parquet`**。那个文件是
   "当前生产策略"的信号 —— 生产还叫 S3_v1 时它无害，生产一换成
   production_clean_v1，它就把 clean 的信号读进一个钉死 S3_v1 的实验里，
   而且完全静默。
2. `config_sha256()` / `verify_config()` 默认走模块常量 `CONFIG_PATH`，
   忽略实验实际用的是哪个配置。两个实验因此记到了**同一个哈希**，
   漂移检测看着在跑，验的却是别人的文件。
3. 运行器的日报目录写死成 v1 的目录，第二个实验启动时覆盖了 v1 的历史日报。

这里把三条都钉住。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from daily_exit_paper import config as C
from daily_exit_paper import engine

V1_CFG = C.PROJECT_ROOT / "config" / "daily_exit_paper_v1.yaml"
CLEAN_CFG = C.PROJECT_ROOT / "config" / "daily_exit_paper_clean_v1.yaml"
#: 一个绝不会有版本化 S3_v1 信号的未来日期 —— 用来稳定地触发回退分支
NO_SIGNAL_DAY = "2026-12-31"


# ---------------------------------------------------------------------------
# 1. 信号与预测不许跨策略回退
# ---------------------------------------------------------------------------

def test_pinned_experiment_refuses_foreign_signals():
    """钉 S3_v1 的实验，在生产已是 clean 时，必须报错而不是读 clean 的信号。"""
    from pipeline.signals import PRODUCTION_STRATEGY

    if PRODUCTION_STRATEGY == "S3_v1":
        pytest.skip("当前生产就是 S3_v1，回退在此配置下是安全的")
    m = engine.LiveMarket(signal_strategy="S3_v1")
    with pytest.raises(engine.SignalSourceError) as e:
        m.signals(NO_SIGNAL_DAY)
    msg = str(e.value)
    assert "S3_v1" in msg and PRODUCTION_STRATEGY in msg
    assert "signals_" in msg


def test_pinned_experiment_refuses_foreign_forecasts():
    """同一条纪律适用于预测：条件分布是"给定某个模型分数"的分布。"""
    from pipeline.signals import PRODUCTION_STRATEGY

    if PRODUCTION_STRATEGY == "S3_v1":
        pytest.skip("当前生产就是 S3_v1")
    m = engine.LiveMarket(signal_strategy="S3_v1")
    with pytest.raises(engine.SignalSourceError):
        m.forecasts(NO_SIGNAL_DAY, horizon=20)


def test_fallback_is_allowed_when_production_is_the_pinned_one(monkeypatch):
    """生产恰好就是本实验那个策略时，回退是安全的 —— 不该报错。

    这条防的是"修得太狠"：回退分支本来是为历史日期留的，
    一刀切掉会让老实验跑不动。
    """
    import pipeline.signals as PS

    monkeypatch.setattr(PS, "PRODUCTION_STRATEGY", "S3_v1")
    m = engine.LiveMarket(signal_strategy="S3_v1")
    # 不应抛异常（该日期没有文件，返回 None 是正常的"无信号"）
    assert m.signals(NO_SIGNAL_DAY) is None


def test_own_strategy_reads_its_versioned_file():
    """实验读自己策略的版本化文件 —— 这条路必须通。"""
    from pipeline.signals import PRODUCTION_STRATEGY

    m = engine.LiveMarket(signal_strategy=PRODUCTION_STRATEGY)
    df = m.signals("2026-09-30")
    if df is None:
        pytest.skip(f"{PRODUCTION_STRATEGY} 没有 2026-09-30 的信号快照")
    assert set(df["symbol"]) and len(df) > 0


# ---------------------------------------------------------------------------
# 2. 配置哈希必须认自己那个文件
# ---------------------------------------------------------------------------

def test_the_two_configs_hash_differently():
    """两个实验的配置不同 -> 哈希必须不同。

    修复前两者都走默认的 CONFIG_PATH，得到**同一个** sha256。
    """
    assert V1_CFG.exists() and CLEAN_CFG.exists()
    a = C.config_sha256(V1_CFG)
    b = C.config_sha256(CLEAN_CFG)
    assert a != b, "两个不同配置得到了相同哈希 —— 校验的是同一个文件"


def test_verify_config_validates_the_given_file():
    """verify_config(path=...) 校验的是传进来的那份，不是模块常量那份。"""
    assert C.verify_config(expected_sha=C.config_sha256(CLEAN_CFG),
                           path=CLEAN_CFG) == C.config_sha256(CLEAN_CFG)
    # 拿 v1 的哈希去校验 clean 的配置 -> 必须报 drift
    with pytest.raises(C.ConfigDrift):
        C.verify_config(expected_sha=C.config_sha256(V1_CFG), path=CLEAN_CFG)


def test_default_config_is_the_production_experiment():
    """默认配置必须指向**当前生产模型**的那个实验。

    2026-10-06 之前默认指向 v1；v1 停掉之后裸跑命令天天报错，
    而"默认跑一个已经停掉的实验"本身就是错的。
    """
    assert C.CONFIG_PATH == CLEAN_CFG, (
        f"默认配置指向 {C.CONFIG_PATH.name}，应指向 clean 那个实验")
    assert C.config_sha256() == C.config_sha256(CLEAN_CFG)
    # v1 仍然可以显式跑，只是不再是默认
    assert C.config_sha256(V1_CFG) != C.config_sha256(CLEAN_CFG)


# ---------------------------------------------------------------------------
# 3. 两个实验彼此独立
# ---------------------------------------------------------------------------

def test_experiments_have_separate_roots_and_identities():
    a, b = C.validate(C.load_config(V1_CFG)), C.validate(C.load_config(CLEAN_CFG))
    assert a["paths"]["root"] != b["paths"]["root"]
    assert a["strategy_version"] != b["strategy_version"]
    assert a["base_signal_strategy"] != b["base_signal_strategy"]
    # v1 的配置里**没有** signal_strategy —— 缺省即 S3_v1，口径不变
    assert "signal_strategy" not in a
    assert b["signal_strategy"] == "production_clean_v1"
    assert a["base_signal_strategy"] == "strategy_v2"


def test_v1_config_is_untouched():
    """v1 的配置哈希必须还是实验创建时记录的那个值。

    给 v1 加任何键都会改哈希 -> 已在跑的实验下次启动就 ConfigDrift。
    这条是"别顺手把新字段加到老配置上"的看门人。
    """
    exp = C.PROJECT_ROOT / "experiments" / "daily_exit_paper_v1" / "experiment.json"
    if not exp.exists():
        pytest.skip("v1 实验尚未创建")
    import json

    recorded = json.loads(exp.read_text(encoding="utf-8"))["config_sha256"]
    assert C.config_sha256(V1_CFG) == recorded, (
        "daily_exit_paper_v1.yaml 被改过了 —— 已在跑的实验会判定 ConfigDrift。"
        "新增字段请加到新实验的配置上，不要动这一份。")


def test_signal_strategy_must_be_registered():
    """配置里写错策略名 -> 报错，而不是静默读不到信号。"""
    cfg = C.load_config(CLEAN_CFG)
    cfg["daily_exit_paper"]["signal_strategy"] = "typo_strategy"
    with pytest.raises(C.ConfigError):
        C.validate(cfg)


# ---------------------------------------------------------------------------
# 4. 日报目录跟着实验身份走
# ---------------------------------------------------------------------------

def test_report_dirs_are_per_experiment():
    """两个实验的日报目录必须不同 —— 否则后启动的会覆盖前一个的历史。"""
    a, b = C.validate(C.load_config(V1_CFG)), C.validate(C.load_config(CLEAN_CFG))

    def rep(s):
        return (s.get("paths") or {}).get("reports") or s["strategy_version"]

    assert rep(a) != rep(b)
    assert rep(a) == "daily_exit_paper_v1"      # v1 的目录名不变
