# -*- coding: utf-8 -*-
"""服务层共用小工具：安全取数 + 统一"没数据"形状。

§51 要求 GUI 在空账户 / 缺价格 / 缺基准 / 缺策略 / 缺新闻时都不能崩。
统一约定：任何一步取不到数据，返回 {"available": False, "reason": "..."}，
页面显示明确原因，而不是抛 Traceback（§67）。
"""

from __future__ import annotations

import functools
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def unavailable(reason: str, **extra) -> dict:
    return {"available": False, "reason": reason, **extra}


def safe(default: Any = None, label: str = "") -> Callable:
    """装饰器：任何异常都降级成 unavailable()，绝不让页面崩。"""
    def deco(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            try:
                return fn(*a, **kw)
            except Exception as e:                            # noqa: BLE001
                return unavailable(f"{label or fn.__name__} 不可用："
                                   f"{type(e).__name__}: {e}")
        return wrapper
    return deco


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(
        timespec="seconds")


def read_json(path) -> Optional[dict]:
    import json

    p = Path(path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:                                          # noqa: BLE001
        return None


def read_parquet(path, **kw) -> Optional[pd.DataFrame]:
    p = Path(path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    if not p.exists():
        return None
    try:
        return pd.read_parquet(p, **kw)
    except Exception:                                          # noqa: BLE001
        return None


def to_float(v, default: float = 0.0) -> float:
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return default
        return float(v)
    except (TypeError, ValueError):
        return default
