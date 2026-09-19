# -*- coding: utf-8 -*-
"""冻结配置的读取与哈希校验（spec §20 / §37）。

冻结的意义不是"文件设成只读"，而是**能证明它没变**：
每次运行都重算 config / model / feature pack 的 sha256，与 freeze 时记录的
值比对；不一致就是 DRIFT_DETECTED，该日不得作为 clean forward observation。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "paper_live.yaml"

# §38 代码级守卫：forward holdout 只读。任何"用它去选"的调用都会被拦下。
FORWARD_HOLDOUT_READ_ONLY = True


def load_config(path: Optional[Path] = None) -> dict:
    p = Path(path) if path else CONFIG_PATH
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def spec(cfg: Optional[dict] = None) -> dict:
    return (cfg or load_config())["paper_live"]


def sha256_file(path) -> str:
    p = Path(path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    if not p.exists():
        return "MISSING"
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _strip_freeze_block(text: str) -> str:
    """去掉 freeze 块之后再哈希。

    否则会出现自指：把 freeze 写进 config 会改变 config 自己的哈希，
    下一次校验必然报 drift。真正要冻结的是**freeze 块以外的内容**。
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
        return "MISSING"
    return hashlib.sha256(
        _strip_freeze_block(p.read_text(encoding="utf-8")).encode("utf-8")
    ).hexdigest()


def freeze_hashes(cfg: Optional[dict] = None) -> Dict[str, str]:
    """所有参与冻结的工件的 sha256。"""
    s = spec(cfg)
    out = {
        "paper_live_config": config_sha256(),
        "model": sha256_file(s["alpha"]["model"]),
        "model_params": sha256_file(s["paths"]["model_params"]),
        "universe_config": sha256_file(s["paths"]["universe_config"]),
    }
    for i, p in enumerate(s["alpha"]["feature_packs"]):
        out[f"feature_pack_{i}"] = sha256_file(p)
    return out


def verify_freeze(cfg: Optional[dict] = None) -> dict:
    """当前哈希 vs 冻结哈希。返回 {drift, mismatches, current, frozen}。"""
    s = spec(cfg)
    frozen = s.get("freeze") or {}
    current = freeze_hashes(cfg)
    if not frozen:
        return {"drift": None, "is_frozen": False, "mismatches": [],
                "new_keys": [], "current": current, "frozen_hashes": {},
                "detail": "尚未冻结：先跑 scripts/paper_live/freeze.py"}
    mismatches = [k for k, v in current.items()
                  if k in frozen and frozen[k] != v]
    missing = [k for k in current if k not in frozen]
    return {
        "drift": bool(mismatches) or bool(missing),
        "is_frozen": True,
        "mismatches": mismatches,
        "new_keys": missing,
        "current": current,
        "frozen_hashes": frozen,
        "detail": ("一致" if not mismatches and not missing else
                   f"不一致 {mismatches}；新增未冻结项 {missing}"),
    }


def write_freeze(cfg_path: Optional[Path] = None) -> dict:
    """把当前哈希写进 config/paper_live.yaml 的 freeze 块。

    **只替换 freeze 块本身**，其余文本逐字保留 —— 用 yaml.safe_dump 整份重写
    会把这些注释全部抹掉，而注释正是"为什么这么冻结"的记录。
    """
    p = Path(cfg_path) if cfg_path else CONFIG_PATH
    cfg = load_config(p)
    hashes = freeze_hashes(cfg)
    text = p.read_text(encoding="utf-8")

    block = yaml.safe_dump({"freeze": hashes}, allow_unicode=True,
                           sort_keys=False, default_flow_style=False).rstrip()
    indented = "\n".join("  " + ln for ln in block.splitlines())

    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines)
                  if ln.startswith("  freeze:")), None)
    if start is None:
        text = text.rstrip() + "\n" + indented + "\n"
    else:
        end = start + 1
        while end < len(lines) and (not lines[end].strip()
                                    or lines[end].startswith("    ")):
            end += 1
        text = "\n".join(lines[:start] + indented.splitlines()
                         + lines[end:]).rstrip() + "\n"
    p.write_text(text, encoding="utf-8")
    return hashes


def is_forward_date(date, cfg: Optional[dict] = None) -> bool:
    return pd.Timestamp(date) >= pd.Timestamp(
        spec(cfg)["forward_start_date"])


def is_historical_test(date, cfg: Optional[dict] = None) -> bool:
    lo, hi = (pd.Timestamp(x) for x in spec(cfg)["historical_test"])
    d = pd.Timestamp(date)
    return lo <= d <= hi


def assert_not_used_for_selection(dates, context: str = "") -> None:
    """forward holdout 数据不得流入任何选择路径（§38）。

    这是 **DISCOVERY / SELECTION / OBSERVATION 不混用** 的代码级实现：
    历史研究负责发现，validation 负责选择，forward 只负责观察。
    """
    if not FORWARD_HOLDOUT_READ_ONLY:                        # pragma: no cover
        raise RuntimeError("FORWARD_HOLDOUT_READ_ONLY 被关掉了 —— "
                           "forward holdout 必须只读")
    bad = [pd.Timestamp(d) for d in pd.DatetimeIndex(dates)
           if is_forward_date(d)]
    if bad:
        raise ValueError(
            f"{context}: {len(bad)} 个日期落在 clean forward holdout"
            f"（{spec()['forward_start_date']} 起）。forward 数据只能 "
            f"record/observe/evaluate，禁止用于因子/模型/优化器选择："
            f"{[str(d.date()) for d in bad[:5]]}")


def to_jsonable(d: dict) -> dict:
    return json.loads(json.dumps(d, ensure_ascii=False, default=str))
