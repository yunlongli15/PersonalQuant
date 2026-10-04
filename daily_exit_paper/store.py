# -*- coding: utf-8 -*-
"""实验目录布局、元数据与不可变快照。

目录
----
    experiments/daily_exit_paper_v1/
      experiment.json                  实验元数据（首次创建后**不再修改**）
      state.json                       当前状态**指针**（允许更新）
      ledger.jsonl                     **append-only** 账本
      recommendations/<signal_date>.json   ① 系统建议（写后只读）
      decisions/<signal_date>.json         ② 用户决定（可选）
      executions/<signal_date>.json        ③ 实际执行（可选）
      daily/<run_date>.json                每日运行快照

两条纪律
--------
1. **不可变**：同一天的建议一旦写下就不再改。内容真的变了也必须开新版本，
   绝不原地覆盖（`write_immutable` 会拒绝）。
2. **原子写**：状态文件先写临时文件再 `os.replace`，崩溃不会留下半截 JSON。
   `state.json` 只是指针，真正的历史在 `ledger.jsonl` 里。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

SUBDIRS = ("recommendations", "decisions", "executions", "daily")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _date(d) -> str:
    return str(pd.Timestamp(d).date())


def _stable(obj: dict) -> dict:
    """比较"内容有没有变"时，把墙钟时间排除在外。"""
    return {k: v for k, v in obj.items() if k != "created_at"}


class AlreadyWritten(RuntimeError):
    """同一天的内容已经写过且与新内容不同 —— 不可变铁律。"""


class ExperimentStore:
    def __init__(self, root):
        self.root = Path(root)

    # ------------------------------------------------------------------ 布局
    def ensure(self) -> "ExperimentStore":
        for d in SUBDIRS:
            (self.root / d).mkdir(parents=True, exist_ok=True)
        return self

    def path(self, *parts) -> Path:
        return self.root.joinpath(*parts)

    def _write_json(self, path: Path, payload: dict) -> None:
        """原子写：临时文件 + os.replace。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2,
                                  default=str), encoding="utf-8")
        os.replace(tmp, path)

    # ------------------------------------------------------------ 实验元数据
    def read_experiment(self) -> Optional[dict]:
        p = self.root / "experiment.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def create_experiment(self, payload: dict) -> dict:
        """首次创建实验元数据。已存在则原样返回（绝不改写本金/哈希）。

        同时建好 `incidents.md`（spec §25）：任何 bug / 人工干预 / 数据中断 /
        漏跑 / 异常成交都往里追加。**错误也必须保留**，绝不用删记录来"修正"。
        """
        cur = self.read_experiment()
        if cur is not None:
            return cur
        self.ensure()
        rec = dict(payload)
        rec.setdefault("created_at", _now())
        self._write_json(self.root / "experiment.json", rec)
        p = self.root / "incidents.md"
        if not p.exists():
            p.write_text(
                "# daily_exit_paper_v1 — Incident Log\n\n"
                f"实验创建于 {rec['created_at']}，本金 "
                f"{rec.get('initial_capital')}。\n\n"
                "任何 **bug / 人工干预 / 数据中断 / 漏跑 / 异常成交** 都追加到\n"
                "本文件。规则：\n\n"
                "1. 错误也必须保留 —— 绝不用删记录来\"修正\"收益。\n"
                "2. 已经影响成交/现金/持仓的 bug 必须 **STOP EXPERIMENT**，\n"
                "   先审计再决定；不得手工改 ledger。\n"
                "3. 只影响未来、不影响历史状态的 bug：修复 + 新 commit +\n"
                "   在本文件留下 incident 记录后才继续。\n"
                "4. **不得**因为最近几笔盈亏而调参（spec §24）。\n\n"
                "| 日期 | 类型 | 摘要 | 是否影响历史状态 | commit |\n"
                "|---|---|---|---|---|\n",
                encoding="utf-8")
        return rec

    # ------------------------------------------------------------------ 快照
    def write_immutable(self, kind: str, date, payload: dict) -> tuple:
        """写一份不可变快照。返回 (path, written)。

        已存在且内容相同 -> 无操作（幂等重跑）；内容不同 -> raise。

        `created_at` 是墙钟时间、不参与"是否变了"的比较：同一天用同样输入
        重跑应当是无操作，而不是撞上不可变铁律。内容真的变了（资金、持仓、
        订单不同）时其余字段仍然不同，照样会被拦下。
        """
        if kind not in SUBDIRS:
            raise ValueError(f"未知快照类型 {kind!r}")
        p = self.root / kind / f"{_date(date)}.json"
        text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
        if p.exists():
            old = json.loads(p.read_text(encoding="utf-8"))
            if _stable(old) == _stable(json.loads(text)):
                return p, False
            raise AlreadyWritten(
                f"{kind}/{_date(date)}.json 已经写过，且内容不同 —— "
                f"不可变快照不允许覆盖。需要新结果请新建实验版本。")
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, p)
        return p, True

    def read_snapshot(self, kind: str, date) -> Optional[dict]:
        p = self.root / kind / f"{_date(date)}.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def snapshot_dates(self, kind: str) -> List[str]:
        d = self.root / kind
        if not d.exists():
            return []
        return sorted(p.stem for p in d.glob("*.json"))

    # ------------------------------------------------------------------ 状态
    def read_state(self) -> Optional[dict]:
        p = self.root / "state.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def write_state(self, payload: dict, dry_run: bool = False) -> None:
        if dry_run:
            return
        self.root.mkdir(parents=True, exist_ok=True)
        self._write_json(self.root / "state.json", payload)

    # ------------------------------------------------------------------ 账本
    def append_ledger(self, events: List[dict], dry_run: bool = False) -> int:
        """追加事件到 append-only 账本。返回写入条数。

        账本是**只增不改**的历史：任何"修正"都必须是一条新事件，
        绝不回头改旧行。
        """
        if not events:
            return 0
        if dry_run:
            return 0
        self.root.mkdir(parents=True, exist_ok=True)
        p = self.root / "ledger.jsonl"
        seq = self.ledger_len()
        lines = []
        for e in events:
            seq += 1
            rec = {"seq": seq, "at": _now()}
            rec.update(e)
            lines.append(json.dumps(rec, ensure_ascii=False, default=str))
        with open(p, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return len(lines)

    def read_ledger(self) -> List[dict]:
        p = self.root / "ledger.jsonl"
        if not p.exists():
            return []
        return [json.loads(ln) for ln in
                p.read_text(encoding="utf-8").splitlines() if ln.strip()]

    def ledger_len(self) -> int:
        p = self.root / "ledger.jsonl"
        if not p.exists():
            return 0
        return sum(1 for ln in p.read_text(encoding="utf-8").splitlines()
                   if ln.strip())

    # ------------------------------------------------------------------ 汇总
    def summary(self) -> Dict:
        exp = self.read_experiment() or {}
        st = self.read_state() or {}
        return {
            "root": str(self.root),
            "experiment_id": exp.get("experiment_id"),
            "initial_capital": exp.get("initial_capital"),
            "created_at": exp.get("created_at"),
            "config_sha256": exp.get("config_sha256"),
            "n_ledger_events": self.ledger_len(),
            "n_recommendation_days": len(self.snapshot_dates(
                "recommendations")),
            "n_daily_runs": len(self.snapshot_dates("daily")),
            "as_of": st.get("as_of"),
            "cash": st.get("cash"),
            "n_positions": len(st.get("positions") or {}),
            "n_pending": len(st.get("pending_entries") or []),
        }
