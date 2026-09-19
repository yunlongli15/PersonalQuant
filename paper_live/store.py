# -*- coding: utf-8 -*-
"""Forward holdout 存储：append-only + revision_id。

铁律（spec §25 / §33 / §34）
--------------------------
1. **不可覆盖**：已经写下的某一天的预测/组合/成交，永远不再修改。
2. **不可回写**：用今天的数据去"修正"历史 forward 记录是不允许的。
   唯一例外是真正的数据源 bug，且**旧版本必须保留** —— 这时写一个新
   revision 文件，基础文件不动，并在 `revisions.jsonl` 里留下原因。
3. **revision 需要理由**：`write_frame(..., allow_revision=True, reason=...)`
   必须显式给出原因，否则拒绝写入并报错。这样"悄悄改一下"在代码层面
   就不可能发生。
4. **时间严格递增**：新写入的日期不得早于已存在的最大 forward 日期。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import pandas as pd

KINDS = ("observations", "predictions", "portfolio", "trades", "metrics",
         "manifests", "reports", "alerts", "state")
FRAME_KINDS = ("predictions", "portfolio", "trades", "metrics")
JSON_KINDS = ("observations", "manifests", "alerts", "state")


@dataclass
class WriteResult:
    kind: str
    date: str
    path: Optional[Path]
    revision: int
    written: bool
    reason: str = ""

    def as_dict(self) -> dict:
        return {"kind": self.kind, "date": self.date,
                "path": str(self.path) if self.path else None,
                "revision": self.revision, "written": self.written,
                "reason": self.reason}


def _frame_digest(df: pd.DataFrame) -> str:
    """内容摘要：列名 + 排序后的值。用于判断"是否真的变了"。"""
    if df is None or df.empty:
        return hashlib.sha256(b"empty").hexdigest()
    norm = df.reindex(sorted(df.columns), axis=1)
    try:
        norm = norm.sort_values(list(norm.columns)).reset_index(drop=True)
    except TypeError:
        pass
    payload = norm.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class ForwardStore:
    """forward holdout 的目录布局与写入纪律。"""

    def __init__(self, root: Path, forward_start: Optional[str] = None):
        self.root = Path(root)
        self.forward_start = pd.Timestamp(forward_start) \
            if forward_start else None
        for d in KINDS:
            (self.root / d).mkdir(parents=True, exist_ok=True)
        self.revision_log = self.root / "revisions.jsonl"

    # ------------------------------------------------------------------ 路径
    def path_for(self, kind: str, date, revision: int = 0) -> Path:
        d = str(pd.Timestamp(date).date())
        if kind in FRAME_KINDS:
            name = f"{d}.parquet" if revision == 0 else f"{d}__rev{revision}.parquet"
        else:
            name = f"{d}.json" if revision == 0 else f"{d}__rev{revision}.json"
        return self.root / kind / name

    def revisions_of(self, kind: str, date) -> List[int]:
        d = str(pd.Timestamp(date).date())
        out = []
        for rev in range(0, 100):
            if self.path_for(kind, date, rev).exists():
                out.append(rev)
        return out

    def latest_revision(self, kind: str, date) -> Optional[int]:
        revs = self.revisions_of(kind, date)
        return max(revs) if revs else None

    # ------------------------------------------------------------------ 写入
    def write_frame(self, kind: str, date, df: pd.DataFrame,
                    allow_revision: bool = False, reason: str = "",
                    dry_run: bool = False) -> WriteResult:
        assert kind in FRAME_KINDS, f"未知的 frame 类型 {kind}"
        cur = self.latest_revision(kind, date)
        if cur is None:
            p = self.path_for(kind, date, 0)
            if not dry_run:
                df.to_parquet(p, index=False)
            return WriteResult(kind, str(pd.Timestamp(date).date()), p, 0,
                               True)
        old = pd.read_parquet(self.path_for(kind, date, cur))
        if _frame_digest(old) == _frame_digest(df):
            return WriteResult(kind, str(pd.Timestamp(date).date()),
                               self.path_for(kind, date, cur), cur, False,
                               "unchanged")
        # 内容不同 —— 默认拒绝，必须显式要求并给出原因
        if not allow_revision:
            raise PermissionError(
                f"{kind} {pd.Timestamp(date).date()} 已经写过（revision "
                f"{cur}），append-only 不允许覆盖。若确认是数据源 bug，"
                f"传 allow_revision=True 并给出 reason。")
        if not reason:
            raise ValueError("allow_revision=True 必须给出 reason")
        nxt = cur + 1
        p = self.path_for(kind, date, nxt)
        if not dry_run:
            df.to_parquet(p, index=False)
            self._log_revision(kind, date, cur, nxt, reason)
        return WriteResult(kind, str(pd.Timestamp(date).date()), p, nxt, True,
                           reason)

    def write_json(self, kind: str, date, payload: dict,
                   allow_revision: bool = False, reason: str = "",
                   dry_run: bool = False) -> WriteResult:
        assert kind in JSON_KINDS, f"未知的 json 类型 {kind}"
        cur = self.latest_revision(kind, date)
        text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
        if cur is None:
            p = self.path_for(kind, date, 0)
            if not dry_run:
                p.write_text(text, encoding="utf-8")
            return WriteResult(kind, str(pd.Timestamp(date).date()), p, 0, True)
        old = self.path_for(kind, date, cur).read_text(encoding="utf-8")
        # created_at 是墙钟时间，不参与"是否变了"的比较：
        # 同一天用同样输入重跑应当是无操作，而不是产生一个新 revision。
        # 内容真的变了（数据/预测不同）时其余字段仍会不同，照样会被拦下。
        def _stable(o):
            return {k: v for k, v in o.items() if k != "created_at"}
        if _stable(json.loads(old)) == _stable(json.loads(text)):
            return WriteResult(kind, str(pd.Timestamp(date).date()),
                               self.path_for(kind, date, cur), cur, False,
                               "unchanged")
        if not allow_revision:
            raise PermissionError(
                f"{kind} {pd.Timestamp(date).date()} 已经写过（revision "
                f"{cur}），append-only 不允许覆盖。")
        if not reason:
            raise ValueError("allow_revision=True 必须给出 reason")
        nxt = cur + 1
        p = self.path_for(kind, date, nxt)
        if not dry_run:
            p.write_text(text, encoding="utf-8")
            self._log_revision(kind, date, cur, nxt, reason)
        return WriteResult(kind, str(pd.Timestamp(date).date()), p, nxt, True,
                           reason)

    def _log_revision(self, kind: str, date, old: int, new: int,
                      reason: str) -> None:
        rec = {"at": datetime.now(timezone.utc).isoformat(),
               "kind": kind, "date": str(pd.Timestamp(date).date()),
               "from_revision": old, "to_revision": new, "reason": reason}
        with open(self.revision_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------------ 读取
    def read_frame(self, kind: str, date,
                   revision: Optional[int] = None) -> Optional[pd.DataFrame]:
        rev = revision if revision is not None else \
            self.latest_revision(kind, date)
        if rev is None:
            return None
        return pd.read_parquet(self.path_for(kind, date, rev))

    def read_json(self, kind: str, date,
                  revision: Optional[int] = None) -> Optional[dict]:
        rev = revision if revision is not None else \
            self.latest_revision(kind, date)
        if rev is None:
            return None
        return json.loads(self.path_for(kind, date, rev).read_text(
            encoding="utf-8"))

    # ------------------------------------------------------------------ 状态
    def state_path(self, name: str) -> Path:
        return self.root / "state" / f"{name}.json"

    def read_state(self, name: str) -> Optional[dict]:
        """账户当前状态（按名字索引，不是按日期）。

        状态是**指针**，不是记录：它允许被更新。真正的历史在
        portfolio/ 与 observations/ 里，那些是 append-only 的。
        每次更新都把旧版本追加进 state/state_log.jsonl，改了什么可查。
        """
        p = self.state_path(name)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def write_state(self, name: str, payload: dict,
                    dry_run: bool = False) -> WriteResult:
        p = self.state_path(name)
        text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
        old = p.read_text(encoding="utf-8") if p.exists() else None
        if not dry_run:
            p.parent.mkdir(parents=True, exist_ok=True)
            if old is not None and json.loads(old) != json.loads(text):
                with open(self.root / "state" / "state_log.jsonl", "a",
                          encoding="utf-8") as f:
                    f.write(json.dumps(
                        {"at": datetime.now(timezone.utc).isoformat(),
                         "name": name, "previous": json.loads(old)},
                        ensure_ascii=False, default=str) + "\n")
            p.write_text(text, encoding="utf-8")
        return WriteResult("state", name, p, 0, old != text)

    # ------------------------------------------------------------------ 时间线
    def observation_dates(self) -> List[pd.Timestamp]:
        d = self.root / "observations"
        return sorted(pd.Timestamp(p.stem) for p in d.glob("*.json")
                      if "__rev" not in p.stem)

    def assert_time_order(self, date) -> None:
        """新写入的 forward 日期不得早于已存在的最大日期（§33）。"""
        dates = self.observation_dates()
        if dates and pd.Timestamp(date) < max(dates):
            raise ValueError(
                f"{pd.Timestamp(date).date()} 早于已记录的最新 forward 日期 "
                f"{max(dates).date()} —— 时间必须严格向前，禁止回填。")

    def all_revisions(self) -> List[dict]:
        if not self.revision_log.exists():
            return []
        return [json.loads(line) for line in
                self.revision_log.read_text(encoding="utf-8").splitlines()
                if line.strip()]

    def summary(self) -> dict:
        n_days = len(self.observation_dates())
        return {
            "root": str(self.root),
            "n_observation_days": n_days,
            "first_date": str(min(self.observation_dates()).date())
            if n_days else None,
            "last_date": str(max(self.observation_dates()).date())
            if n_days else None,
            "n_revisions": len(self.all_revisions()),
        }
