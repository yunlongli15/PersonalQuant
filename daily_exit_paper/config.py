# -*- coding: utf-8 -*-
"""daily_exit_paper_v1 的配置读取与冻结校验。

**与 paper_live 完全独立**（spec §2：不 import paper_live）：这里自己实现
配置哈希与 block 剥离，不共用 paper_live.config 的任何代码。

冻结的意义不是"文件设成只读"，而是**能证明它没变**：每次运行都重算
config 的 sha256 并与实验创建时记录的值比对；不一致就是 DRIFT，拒绝继续。
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "daily_exit_paper_v1.yaml"

#: 参与冻结校验的键（实验中途不得改变的任何东西）。
FROZEN_KEYS = (
    "version", "strategy_version", "base_signal_strategy",
    "signal_horizon_days", "top_k", "risk_profile",
    "entry", "exit", "exit_resolution", "time_stop",
    "sizing", "execution", "transaction_costs",
)


class ConfigError(RuntimeError):
    """配置缺失、自相矛盾或与实验记录不符。"""


class ConfigDrift(ConfigError):
    """配置哈希与实验创建时不一致 —— 实验中途被改过。"""


def load_config(path: Optional[Path] = None) -> dict:
    p = Path(path) if path else CONFIG_PATH
    if not p.exists():
        raise ConfigError(f"配置不存在：{p}")
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def spec(cfg: Optional[dict] = None) -> dict:
    return (cfg or load_config())["daily_exit_paper"]


def _strip_freeze_block(text: str) -> str:
    """去掉 freeze 块之后再哈希。

    否则会自指：把 freeze 写进配置会改变配置自己的哈希，下一次校验必然报
    drift。要冻结的是 freeze 块**以外**的内容。
    """
    lines = text.splitlines()
    out, i = [], 0
    while i < len(lines):
        if lines[i].startswith("  freeze:"):
            i += 1
            while i < len(lines) and (not lines[i].strip()
                                      or lines[i].startswith("    ")):
                i += 1
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def config_sha256(path: Optional[Path] = None) -> str:
    p = Path(path) if path else CONFIG_PATH
    if not p.exists():
        raise ConfigError(f"配置不存在：{p}")
    return hashlib.sha256(
        _strip_freeze_block(p.read_text(encoding="utf-8")).encode("utf-8")
    ).hexdigest()


def trading_spec(cfg: Optional[dict] = None) -> dict:
    """只取参与冻结的那部分配置（用于哈希比对与展示）。"""
    s = spec(cfg)
    return {k: s.get(k) for k in FROZEN_KEYS}


def verify_config(cfg: Optional[dict] = None,
                  expected_sha: Optional[str] = None) -> str:
    """当前配置哈希 vs 实验记录里的哈希。不一致 -> raise ConfigDrift。"""
    current = config_sha256()
    recorded = expected_sha
    if recorded is None:
        recorded = (spec(cfg).get("freeze") or {}).get("config_sha256")
    if recorded and recorded != current:
        raise ConfigDrift(
            f"配置已改动：记录 {recorded[:12]}…，当前 {current[:12]}…。\n"
            f"实验中途不允许改参数 —— 需要新参数请新建版本"
            f"（例如 daily_exit_paper_v1.1），新目录、新账本，"
            f"绝不把改过参数的结果继续称作 v1。")
    return current


def validate(cfg: Optional[dict] = None) -> dict:
    """配置自洽性检查。任何一条不成立都 raise（不静默取默认值）。"""
    s = spec(cfg)
    h = int(s["signal_horizon_days"])
    if h != 20:
        raise ConfigError(f"signal_horizon_days 必须是冻结的 20（得到 {h}）")
    if int(s["top_k"]) != 20:
        raise ConfigError(f"top_k 必须是冻结的 20（得到 {s['top_k']}）")
    if s["risk_profile"] not in ("conservative", "balanced", "aggressive"):
        raise ConfigError(f"未知风险档 {s['risk_profile']!r}")
    if s["entry"]["mode"] != "limit":
        raise ConfigError("entry.mode 目前只支持 limit")
    if s["entry"]["price_field"] != "entry_high":
        raise ConfigError("entry.price_field 目前只支持 entry_high")
    if int(s["entry"]["execution_lag_days"]) != 1:
        raise ConfigError("execution_lag_days 必须是 1（T 日信号 → T+1 执行）")
    if int(s["time_stop"]["days"]) != h * 2:
        raise ConfigError(
            f"time_stop.days 必须等于 signal_horizon_days×2 = {h * 2}"
            f"（得到 {s['time_stop']['days']}）—— 这是既有公式的定义，不是可调项")
    if s["exit_resolution"]["intraday_conflict"] != "stop_first":
        raise ConfigError("v1 固定 intraday_conflict = stop_first（保守）")
    if s["exit_resolution"]["gap_policy"] != "conservative":
        raise ConfigError("v1 固定 gap_policy = conservative")
    if s["execution"]["partial_fill"] != "unsupported":
        raise ConfigError("v1 明确不支持部分成交")
    if s["exit"]["signal_exit_enabled"]:
        raise ConfigError("v1 的 signal_exit_enabled 必须是 false")
    if float(s["sizing"]["invest_target"]) != 0.95:
        raise ConfigError("invest_target 继承 strategy_v2 的 0.95，不可改")
    for k in ("commission_rate", "min_commission", "stamp_duty",
              "transfer_fee", "slippage"):
        if k not in s["transaction_costs"]:
            raise ConfigError(f"transaction_costs 缺键：{k}")
    return s
