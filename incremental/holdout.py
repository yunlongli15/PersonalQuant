# -*- coding: utf-8 -*-
"""Forward holdout：clean forward evidence 的登记与只读监控（§25/§26/§29）。

背景：2024-2025 已经被评估过 3 次（STEP 6 终评、step8、step9），
**不能再声称它是 untouched test**。诚实的做法是把它降级为
HISTORICAL TEST（只读、只报告），另外建立一个新的前瞻窗口。

本模块的两条硬约束：
1. holdout 数据**只能记录、监控、评估**，绝不参与选择；
2. 任何把 holdout 日期送进选择路径的调用都必须抛异常
   （`assert_not_selection`），由 tests/factors/test_no_test_usage.py 覆盖。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

HISTORICAL_TEST = ("2024-01-01", "2025-12-31")


@dataclass
class ForwardHoldout:
    start: str
    registry: Path
    mode: str = "record_only"
    records: List[dict] = field(default_factory=list)

    # ------------------------------------------------------------- 边界
    @property
    def start_ts(self) -> pd.Timestamp:
        return pd.Timestamp(self.start)

    def is_holdout(self, date) -> bool:
        return pd.Timestamp(date) >= self.start_ts

    @staticmethod
    def is_historical_test(date) -> bool:
        d = pd.Timestamp(date)
        return pd.Timestamp(HISTORICAL_TEST[0]) <= d <= pd.Timestamp(
            HISTORICAL_TEST[1])

    def assert_not_selection(self, dates, context: str = "") -> None:
        """holdout 日期出现在选择路径上 = 协议违规，直接报错。"""
        bad = [pd.Timestamp(d) for d in pd.DatetimeIndex(dates)
               if self.is_holdout(d)]
        if bad:
            raise ValueError(
                f"{context}: {len(bad)} 个日期落在 forward holdout "
                f"({self.start} 起) 内，holdout 只允许 record/monitor/"
                f"evaluate，禁止参与选择：{[str(d.date()) for d in bad[:5]]}")

    @staticmethod
    def assert_not_historical_test(dates, context: str = "") -> None:
        bad = [pd.Timestamp(d) for d in pd.DatetimeIndex(dates)
               if ForwardHoldout.is_historical_test(d)]
        if bad:
            raise ValueError(
                f"{context}: {len(bad)} 个日期落在 HISTORICAL TEST "
                f"{HISTORICAL_TEST[0]}..{HISTORICAL_TEST[1]}（已被观察多次，"
                f"禁止用于选择）：{[str(d.date()) for d in bad[:5]]}")

    # ------------------------------------------------------------- 登记
    @classmethod
    def load(cls, cfg: dict) -> "ForwardHoldout":
        c = cfg["factor_selection_v2"]["forward_holdout"]
        path = Path(c["registry"])
        if not path.is_absolute():
            path = Path.cwd() / path
        obj = cls(start=str(c["start"]), registry=path,
                  mode=c.get("mode", "record_only"))
        if path.exists():
            obj.records = json.loads(path.read_text(encoding="utf-8")) \
                .get("records", [])
        return obj

    def save(self) -> Path:
        self.registry.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "start": self.start,
            "mode": self.mode,
            "note": ("holdout 只用于记录/监控/评估，绝不参与因子选择。"
                     "2024-2025 为 HISTORICAL TEST（已被观察多次）。"),
            "historical_test": list(HISTORICAL_TEST),
            "n_records": len(self.records),
            "records": self.records,
        }
        self.registry.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8")
        return self.registry

    def record_signal(self, date, predictions_path: str,
                      note: str = "") -> dict:
        """登记一个已冻结的预测快照（只写文件路径，不复制数据）。"""
        d = pd.Timestamp(date)
        if not self.is_holdout(d):
            raise ValueError(f"{d.date()} 早于 holdout 起点 {self.start}，"
                             f"不属于 clean forward evidence")
        rec = {"date": str(d.date()), "predictions": str(predictions_path),
               "realized": None, "ic": None, "note": note}
        self.records = [r for r in self.records if r["date"] != rec["date"]]
        self.records.append(rec)
        self.records.sort(key=lambda r: r["date"])
        return rec

    def update_realized(self, date, realized: Dict[str, float]) -> dict:
        """标签窗口走完后回填已实现收益，并算监控用 IC。"""
        d = str(pd.Timestamp(date).date())
        for r in self.records:
            if r["date"] != d:
                continue
            r["realized"] = {k: float(v) for k, v in realized.items()}
            r["n_realized"] = len(r["realized"])
            return r
        raise KeyError(f"{d} 尚未登记预测快照")

    # ------------------------------------------------------------- 监控
    def summary(self) -> dict:
        done = [r for r in self.records if r.get("realized")]
        return {
            "start": self.start,
            "mode": self.mode,
            "n_records": len(self.records),
            "n_realized": len(done),
            "clean_forward_evidence": "尚无" if not done else f"{len(done)} 期",
            "note": ("holdout 刚开始，样本不足以支持任何结论；"
                     "按协议只记录不评判。" if not done else ""),
        }
