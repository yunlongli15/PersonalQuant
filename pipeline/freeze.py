# -*- coding: utf-8 -*-
"""生产冻结（STEP 12, spec §2 / §35 / §36）。

从 STEP 12 起，下列内容全部视为 **FROZEN**：

    strategy version / feature pack / news factor pack / model config /
    portfolio allocation / transaction cost / PIT rules / execution rules /
    forward holdout rules

每天启动 pipeline 之前先校验当前代码与工件的哈希是否与冻结记录一致。
不一致 → **PRODUCTION_DRIFT** → 停止正式 forward observation（但仍然更新
数据、生成报告，用户能看到发生了什么）。

`production_enabled: false` 时（§36），pipeline 照常更新数据与报告，
只是**不产生正式 forward observation** —— 这是"一键停止"。
"""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FREEZE_PATH = PROJECT_ROOT / "config" / "production_freeze.yaml"

# 参与冻结的工件：键 → 相对路径（或从 paper_live 配置里取）
FROZEN_ARTIFACTS = {
    "paper_live_config": "config/paper_live.yaml",
    "strategy_v2_config": "config/strategy_v2.yaml",
    "strategy_v1_config": "config/strategy_v1.yaml",
    "factor_selection_v2_config": "config/factor_selection_v2.yaml",
    "feature_pack_v1": "experiments/factors/factor_run_001/factor_pack_v1.json",
    "news_factor_pack": ("experiments/news/news_factor_run_001/"
                         "factor_pack_news_v1.json"),
    "production_model": "experiments/news/strategy/model.txt",
}


class ProductionDrift(RuntimeError):
    """生产工件与冻结记录不一致。"""


@dataclass
class FreezeStatus:
    frozen: bool
    drift: bool
    mismatches: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    current: Dict[str, str] = field(default_factory=dict)
    recorded: Dict[str, str] = field(default_factory=dict)
    detail: str = ""
    production_enabled: bool = True

    @property
    def ok(self) -> bool:
        return self.frozen and not self.drift

    def as_dict(self) -> dict:
        return {
            "frozen": self.frozen, "drift": self.drift, "ok": self.ok,
            "mismatches": self.mismatches, "missing": self.missing,
            "detail": self.detail,
            "production_enabled": self.production_enabled,
            "current": self.current, "recorded": self.recorded,
        }


def sha256_file(rel: str) -> str:
    p = Path(rel)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    if not p.exists():
        return "MISSING"
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"],
                              capture_output=True, text=True,
                              cwd=PROJECT_ROOT,
                              timeout=15).stdout.strip() or "unknown"
    except Exception:                                          # noqa: BLE001
        return "unknown"


def current_hashes() -> Dict[str, str]:
    return {k: sha256_file(v) for k, v in FROZEN_ARTIFACTS.items()}


def _live_config() -> dict:
    from paper_live.config import load_config
    pl = load_config()["paper_live"]
    cfg = dict(pl)
    try:
        v2 = yaml.safe_load(
            (PROJECT_ROOT / "config" / "strategy_v2.yaml").read_text(
                encoding="utf-8"))
    except Exception:                                          # noqa: BLE001
        v2 = {}
    cfg["_v2"] = v2
    return cfg


def build_record() -> dict:
    """按当前状态生成一份冻结记录（写文件的唯一入口）。"""
    pl = _live_config()
    v2 = pl.get("_v2", {})
    portfolio = pl.get("portfolio", {})
    return {
        "production_freeze": {
            "version": "1.0.0",
            "freeze_date": datetime.now(timezone.utc).astimezone()
            .strftime("%Y-%m-%d"),
            "git_commit": git_commit(),
            "production_enabled": True,

            # --- spec §2 要求记录的字段 ---
            "strategy_version": pl.get("strategy_version"),
            "feature_version": "alpha158+factor_pack_v1",
            "news_feature_version": "factor_pack_news_v1",
            "model_version": pl.get("alpha", {}).get("signal", "s3"),
            "allocation_method": portfolio.get("allocation_method"),
            "execution_model": pl.get("execution", {}).get("model"),
            "forward_holdout_start": pl.get("forward_start_date"),

            # --- 运行参数（冻结后不得由 pipeline 修改）---
            "top_k": portfolio.get("top_k"),
            "rebalance_frequency": portfolio.get("rebalance", {})
            .get("frequency"),
            "transaction_costs": pl.get("transaction_costs"),
            "historical_test": pl.get("historical_test"),

            # --- 工件哈希 ---
            "hashes": current_hashes(),
        }
    }


def write_freeze() -> dict:
    """写入冻结记录。**已冻结且无变化时是幂等的**；有变化则拒绝覆盖。"""
    existing = load_freeze()
    if existing:
        st = verify()
        if st.drift:
            raise ProductionDrift(
                "已存在冻结记录且当前工件不一致，拒绝覆盖："
                f"{st.mismatches}。生产策略不允许直接修改 —— "
                "请新建 experiment config，见 docs/V1_FREEZE.md")
        return existing["production_freeze"]
    rec = build_record()
    FREEZE_PATH.write_text(
        yaml.safe_dump(rec, allow_unicode=True, sort_keys=False),
        encoding="utf-8")
    return rec["production_freeze"]


def load_freeze() -> dict:
    if not FREEZE_PATH.exists():
        return {}
    try:
        return yaml.safe_load(FREEZE_PATH.read_text(encoding="utf-8")) or {}
    except Exception:                                          # noqa: BLE001
        return {}


def verify() -> FreezeStatus:
    """当前工件 vs 冻结记录。"""
    rec = load_freeze().get("production_freeze") or {}
    if not rec:
        return FreezeStatus(frozen=False, drift=False,
                            detail="尚未冻结：先跑 scripts/freeze_production.py")
    recorded = rec.get("hashes") or {}
    current = current_hashes()
    mismatches = [k for k, v in current.items()
                  if k in recorded and recorded[k] != v]
    missing = [k for k in current if k not in recorded]
    enabled = bool(rec.get("production_enabled", True))
    drift = bool(mismatches) or bool(missing)
    return FreezeStatus(
        frozen=True, drift=drift, mismatches=mismatches, missing=missing,
        current=current, recorded=recorded,
        production_enabled=enabled,
        detail=("一致" if not drift else
                f"不一致：{mismatches}"
                + (f"；未冻结项：{missing}" if missing else "")))


def assert_frozen() -> FreezeStatus:
    """不一致就抛 —— 调用方据此停止 forward observation。"""
    st = verify()
    if not st.frozen:
        raise ProductionDrift(st.detail)
    if st.drift:
        raise ProductionDrift(f"PRODUCTION_DRIFT：{st.detail}")
    return st


def production_enabled() -> bool:
    """§36 一键停止：false 时只更新数据与报告，不产生正式 forward observation。"""
    rec = load_freeze().get("production_freeze") or {}
    return bool(rec.get("production_enabled", True))
