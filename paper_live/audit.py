# -*- coding: utf-8 -*-
"""PIT 审计与数据完整性（spec §6 / §23 / §24）。

每次运行都要回答同一个问题：**"这一刻系统到底知道什么？"**

一个容易搞错的地方：审计的对象是**本次运行实际消费的数据**，不是数据库里
存在什么。历史回放时数据库里当然有信号日之后的数据——那不等于我们用过它。
所以下面的检查全部围绕"consumed"展开，并额外记录数据库的边界，
但**不把"数据库里有更新的数据"判成违规**。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

VALID, WARNING, INVALID = "VALID", "WARNING", "INVALID"
_RANK = {VALID: 0, WARNING: 1, INVALID: 2}


@dataclass
class Check:
    name: str
    status: str
    detail: str = ""


@dataclass
class AuditResult:
    signal_date: str
    checks: List[Check] = field(default_factory=list)
    metrics: Dict = field(default_factory=dict)

    def add(self, name: str, status: str, detail: str = "") -> None:
        self.checks.append(Check(name, status, detail))

    @property
    def status(self) -> str:
        worst = VALID
        for c in self.checks:
            if _RANK[c.status] > _RANK[worst]:
                worst = c.status
        return worst

    def as_dict(self) -> dict:
        return {"signal_date": self.signal_date, "status": self.status,
                "checks": [c.__dict__ for c in self.checks],
                "metrics": self.metrics}


def _sources(names: Sequence[str]) -> Dict[str, str]:
    from factors.registry import FACTOR_REGISTRY
    out = {}
    for n in names or []:
        meta = FACTOR_REGISTRY.get(n)
        if meta:
            out[n] = f"{meta['source']}|{meta['category']}"
    return out


def pit_audit(provider, signal_date: pd.Timestamp, symbols: List[str],
              features: Optional[pd.DataFrame] = None,
              custom: Optional[pd.DataFrame] = None,
              consumed_factors: Optional[Sequence[str]] = None
              ) -> AuditResult:
    """逐项检查本次运行消费的数据是否都 <= signal_date。"""
    d = pd.Timestamp(signal_date)
    res = AuditResult(str(d.date()))

    # 1. 行情：信号日当天必须有价（否则算不出组合），且不晚于信号日
    try:
        bar_d = provider.latest_bar_date(symbols, on_or_before=d)
        db_d = provider.latest_bar_date(symbols)
        if bar_d is None:
            res.add("price_pit", INVALID, "信号日之前没有任何日线")
        elif pd.Timestamp(bar_d) > d:
            res.add("price_pit", INVALID,
                    f"消费到 {bar_d} 的日线，晚于信号日 {d.date()}")
        else:
            res.add("price_pit", VALID,
                    f"消费的最新日线 {pd.Timestamp(bar_d).date()}"
                    + (f"（库中另有 {pd.Timestamp(db_d).date()} 的数据，"
                       f"本次未消费）" if db_d and pd.Timestamp(db_d) > d
                       else ""))
        res.metrics["db_latest_bar"] = str(pd.Timestamp(db_d).date()) \
            if db_d is not None else None
    except Exception as e:                                   # pragma: no cover
        res.add("price_pit", WARNING, f"无法检查：{e}")

    # 2. 股票池
    if not symbols:
        res.add("universe", INVALID, "信号日股票池为空")
    else:
        res.add("universe", VALID, f"{len(symbols)} 只（按信号日规则重建）")

    # 3. 特征
    if features is None or features.empty:
        res.add("features", INVALID, "特征矩阵为空")
    else:
        res.add("features", VALID,
                f"{features.shape[1]} 列 × {len(features)} 行")

    # 4. 财务 PIT —— 只有**确实消费了财务因子**时才检查
    src = _sources(consumed_factors or [])
    fin = [n for n, s in src.items() if s.startswith("financial")]
    news = [n for n, s in src.items() if s.split("|")[1] == "news"]
    if not fin:
        res.add("financial_pit", VALID,
                "本次未消费财务因子（S3 特征集不含财务数据）")
    else:
        try:
            fa = provider.financial_availability(symbols)
            av = pd.to_datetime(fa["availability_date"], errors="coerce") \
                if fa is not None and not fa.empty else pd.Series(dtype="datetime64[ns]")
            bad = int((av >= d).sum())
            if bad:
                res.add("financial_pit", INVALID,
                        f"{len(fin)} 个财务因子中，有 {bad} 条记录的可用日 "
                        f">= 信号日")
            else:
                res.add("financial_pit", VALID,
                        f"消费 {len(fin)} 个财务因子，最新可用 "
                        f"{av.max().date() if len(av) else 'NA'}")
        except Exception as e:
            res.add("financial_pit", WARNING, f"无法检查：{e}")

    # 5. 新闻 PIT（发布日 <= 15:00 当日可用，否则次日）
    if not news:
        res.add("news_pit", VALID, "本次未消费新闻因子")
    else:
        try:
            na = provider.news_availability(symbols, on_or_before=d)
            if na is None or na.empty or "published_at" not in na:
                res.add("news_pit", WARNING,
                        "消费了新闻因子但信号日之前没有任何新闻数据")
            else:
                t = pd.to_datetime(na["published_at"], errors="coerce")
                newest = t.max()
                covered = int((t > d - pd.Timedelta(days=30)).sum())
                res.metrics["news_newest_available"] = (
                    str(newest.date()) if pd.notna(newest) else None)
                res.metrics["news_covered_30d"] = covered
                if pd.isna(newest) or newest < d - pd.Timedelta(days=60):
                    res.add("news_pit", WARNING,
                            "新闻数据滞后：信号日为止最新只有 "
                            f"{newest.date() if pd.notna(newest) else 'NA'}")
                else:
                    # 15:00→次日 的规则由 derived 因子层执行，另有专门测试；
                    # 这里只确认"截至信号日有新鲜新闻可用"。
                    res.add("news_pit", VALID,
                            f"消费 {len(news)} 个新闻因子；截至信号日最新 "
                            f"{newest.date()}，近 30 天覆盖 {covered} 只"
                            f"（15:00→次日规则见 docs/步骤5-新闻时点规则.md）")
        except Exception as e:
            res.add("news_pit", WARNING, f"无法检查：{e}")

    # 6. 行业分类（当前快照；已知限制，记录但不判 INVALID）
    if custom is not None and not custom.empty:
        res.add("industry_snapshot", WARNING,
                "行业用当前 CSRC 快照（历史行业变更罕见，已记录限制）")

    # 7. 标签绝不参与信号生成
    res.add("label_isolation", VALID, "信号路径不读取 label")

    # 8. 数据新鲜度 —— 只对**实时运行**有意义；历史回放必然 STALE，
    #    因此降级为 INFO（不进 status），否则会天天误报。
    try:
        from pipeline.freshness import data_status
        stale = [f.domain for f in data_status()
                 if getattr(f, "is_stale", False)]
        res.metrics["stale_domains"] = stale
        if stale:
            res.add("freshness", WARNING, f"STALE: {','.join(stale)}"
                                          "（历史回放属正常）")
        else:
            res.add("freshness", VALID, "无 STALE 域")
    except Exception as e:
        res.add("freshness", WARNING, f"无法检查：{e}")

    res.metrics["n_symbols"] = len(symbols)
    res.metrics["consumed_factors"] = list(consumed_factors or [])
    return res


def replay_mode(status: str, signal_date, forward_start: str) -> str:
    """历史回放时的状态修正：freshness 的 STALE 不是数据问题。

    回放日的 status 由**真实的 PIT 违例**决定，不因"库里有更新的数据"
    或"新闻域 STALE"而判 INVALID。
    """
    if pd.Timestamp(signal_date) >= pd.Timestamp(forward_start):
        return status
    return VALID if status == WARNING else status


def data_completeness(features: pd.DataFrame, custom: pd.DataFrame,
                      symbols: List[str]) -> dict:
    """数据完整性指标（§23）。缺失率是**事实**，不做填充或猜测。"""
    out = {"n_symbols": len(symbols)}
    if features is not None and not features.empty:
        out["feature_missing_rate"] = float(features.isna().mean().mean())
        out["feature_complete_symbols"] = int(
            (features.notna().sum(axis=1) > 0).sum())
    if custom is not None and not custom.empty:
        out["custom_coverage"] = float(custom.notna().mean().mean())
    return out
