# -*- coding: utf-8 -*-
"""新闻因子的 PIT / 无未来函数审计 -> reports/news_pit_audit.md

    python scripts/news/audit_news_pit.py

回答一个问题：**在真实数据上，as_of_date=T 的因子读数里到底用到了哪些事件？**

两条独立的检查：

1. **数据级**：事件表里 `availability_time < publication_time` 的（时间倒流），
   以及 `availability_unknown=True` 却仍然带着可用时间的（口径矛盾）。
2. **因子级（截断不变性）**：对每个采样信号日 T，把事件集**砍到**
   `availability_time <= T` 再算一遍因子，与全量事件算出的 T 日读数逐格比对。
   只要有任何一天用到了 T 之后才有的事件，两个数就不相等 —— 这是
   `max(news_event_time_used) <= T` 的直接实现。

只读数据，不写任何东西（除了这份报告）。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd

from factors.base import (cached_rebalance_dates, load_factor_data,
                          set_news_version)
from factors.registry import FACTORS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT = PROJECT_ROOT / "reports" / "news_pit_audit.md"

#: 审计范围 = S3 真正消费的那几个新闻因子（全量审计 28 个没有额外信息量）
AUDIT_FACTORS = ["announcement_count_20d", "news_risk_20d",
                 "shareholder_change_count_20d"]

START = "2015-01-01"
END = "2026-09-30"


def sample_dates() -> list:
    """每年取一个调仓日 —— 覆盖 2015~2026 的每一年。

    **为什么是抽样而不是每个调仓日**：每个采样日都要拿"砍到 T 的事件集"
    重算一遍因子面板（2M 事件 groupby + 全日历 rolling，约 40 秒），
    全量 47 个调仓日 x 3 个因子要跑两个多小时，而边际信息量为零 ——
    因子对未来事件的敏感性不随日期变化，代码路径只有一条。
    合成的穷尽测试在 tests/news/test_news_no_future_leakage.py。
    """
    days = cached_rebalance_dates(START, END)
    seen, out = set(), []
    for d in days:
        y = pd.Timestamp(d).year
        if y not in seen:
            seen.add(y)
            out.append(pd.Timestamp(d))
    return out


def check_availability(events: pd.DataFrame) -> dict:
    """数据级：可用时间不得早于发布时间。"""
    pub = pd.to_datetime(events["publication_time"], errors="coerce")
    avail = pd.to_datetime(events["availability_time"], errors="coerce")
    both = pub.notna() & avail.notna()
    back = both & (avail < pub)
    unknown = events.get("availability_unknown")
    unknown = (unknown.fillna(False).astype(bool) if unknown is not None
               else pd.Series(False, index=events.index))
    return {
        "rows": len(events),
        "availability_unknown": int(unknown.sum()),
        "unknown_but_dated": int((unknown & avail.notna()).sum()),
        "availability_missing": int(avail.isna().sum()),
        "time_travel": int(back.sum()),
        "time_travel_examples": events.loc[back, [
            "symbol", "publication_time", "availability_time"]]
        .head(5).to_dict("records"),
        "max_availability": str(avail.max()),
    }


def truncation_violations(name: str, data, dates, full_panel,
                          events_cut_cache) -> dict:
    """因子级：砍掉 T 之后的事件，T 日的读数必须一模一样。"""
    bad = []
    cells = 0
    # 因子是按**日**分桶的（news_factors._events: avail -> tz 去掉再 normalize），
    # 所以截断也必须在同一口径上做 —— 拿带时区的时间戳去比朴素日期会直接报
    # TypeError，更糟的是"修好"之后口径不一致会让审计本身失去意义。
    avail_day = (pd.to_datetime(data.news["availability_time"], errors="coerce")
                 .dt.tz_localize(None).dt.normalize())
    for d in dates:
        key = pd.Timestamp(d)
        if key not in events_cut_cache:
            events_cut_cache[key] = data.news[avail_day <= key.normalize()]
        cut = events_cut_cache[key]
        probe = _with_events(data, cut)
        got = FACTORS[name](probe, dates=[key])
        want = full_panel.loc[[key]]
        # 列序必须对齐后再比 —— 否则比的是"列名位置"，不是数值
        got = got.reindex(columns=want.columns)
        a, b = want.to_numpy(dtype=float), got.to_numpy(dtype=float)
        both_nan = np.isnan(a) & np.isnan(b)
        cells += int(a.size)
        diff = ~both_nan & ~np.isclose(a, b, rtol=1e-9, atol=1e-12,
                                       equal_nan=True)
        if diff.any():
            syms = want.columns[diff][:5].tolist()
            bad.append({"date": str(key.date()), "n_cells": int(diff.sum()),
                        "symbols": syms,
                        "full": a[diff][:5].tolist(),
                        "cut": b[diff][:5].tolist()})
    return {"factor": name, "cells_compared": cells, "violations": bad,
            "n_dates": len(dates)}


def _with_events(data, events):
    """浅拷贝一份 FactorData，只换掉事件表。"""
    import copy

    probe = copy.copy(data)
    probe.news = events
    return probe


def audit(version: str) -> dict:
    set_news_version(version)
    data = load_factor_data(START, END)
    if data.news is None or data.news.empty:
        return {"version": version, "error": "没有事件快照"}

    dates = sample_dates()
    print(f"[{version}] 事件 {len(data.news):,} 行，采样 {len(dates)} 个信号日",
          flush=True)
    res = {"version": version, "events": len(data.news),
           "symbols": int(data.news["symbol"].nunique()),
           "sample_dates": len(dates), "data_level": check_availability(
               data.news), "factors": []}

    cut_cache = {}
    for name in AUDIT_FACTORS:
        full = FACTORS[name](data, dates=dates)
        r = truncation_violations(name, data, dates, full, cut_cache)
        res["factors"].append(r)
        print(f"  {name}: 对比 {r['cells_compared']:,} 格，"
              f"违约 {sum(v['n_cells'] for v in r['violations'])}", flush=True)
    return res


def render(results: list) -> str:
    L = [
        "# 新闻因子 PIT / 无未来函数审计",
        "",
        "> 生成：`python scripts/news/audit_news_pit.py`",
        "> 目的：证明 `as_of_date = T` 的因子读数**只用到了 T 及之前可用的事件**。",
        "",
        "## 方法",
        "",
        "对每个采样信号日 `T`：把事件集砍到 `availability_time <= T` 重算一遍，",
        "与全量事件算出的 T 日读数**逐格比对**。只要有任何一处在 T 日读到了",
        "T 之后才出现的事件，两个数就不可能相等。",
        "",
        "采样：2015-01 ~ 2026-09 **每年一个调仓日**。抽样而不是全量，是因为"
        "每个采样日都要用砍过的事件集重算一遍面板（约 40 秒），全量跑要两小时"
        "而边际信息量为零 —— 因子对未来事件的敏感性不随日期变化。"
        "穷尽版本是合成数据的单元测试 `tests/news/test_news_no_future_leakage.py`。",
        "",
        "范围：S3 实际消费的三个新闻因子"
        "（`announcement_count_20d` / `news_risk_20d` /"
        " `shareholder_change_count_20d`）。",
        "",
        "---",
        "",
    ]
    for r in results:
        L += [f"## {r['version']}", ""]
        if r.get("error"):
            L += [f"**{r['error']}**", ""]
            continue
        d = r["data_level"]
        L += [f"事件 {r['events']:,} 行 / {r['symbols']:,} 只股票 / "
              f"采样 {r['sample_dates']} 个信号日", "",
              "### 数据级", "", "| 检查项 | 数量 |", "|---|---|",
              f"| 事件总数 | {d['rows']:,} |",
              f"| `availability_unknown=true` | {d['availability_unknown']:,} |",
              f"| 其中却带着可用时间（口径矛盾） | "
              f"{d['unknown_but_dated']:,} |",
              f"| 可用时间缺失（因子直接跳过） | {d['availability_missing']:,} |",
              f"| **可用时间早于发布时间（时间倒流）** | "
              f"**{d['time_travel']:,}** |",
              f"| 最晚可用时间 | {d['max_availability']} |", ""]
        if d["time_travel_examples"]:
            L += ["时间倒流样例：", ""]
            for e in d["time_travel_examples"]:
                L.append(f"- `{e['symbol']}` pub={e['publication_time']} "
                         f"avail={e['availability_time']}")
            L.append("")
        L += ["### 因子级（截断不变性）", "",
              "| 因子 | 比对格数 | 违约格数 |", "|---|---|---|"]
        total = 0
        for f in r["factors"]:
            n = sum(v["n_cells"] for v in f["violations"])
            total += n
            L.append(f"| `{f['factor']}` | {f['cells_compared']:,} | "
                     f"**{n}** |")
        L += ["", f"合计违约 **{total}** 格。", ""]
        for f in r["factors"]:
            for v in f["violations"][:5]:
                L.append(f"- `{f['factor']}` {v['date']}：{v['n_cells']} 格"
                         f"（{v['symbols']}）")
        L += ["", "**结论："
              + ("PASS —— 没有任何一处在 T 日用到了 T 之后的事件。"
                 if total == 0 else f"FAIL —— {total} 格发生未来数据泄漏。")
              + "**", "", "---", ""]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--versions", default="v1,v2")
    args = ap.parse_args()
    results = [audit(v.strip()) for v in args.versions.split(",") if v.strip()]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(results), encoding="utf-8")
    print(f"wrote {OUT}")
    ok = all(not (r.get("error") or
                  any(f["violations"] for f in r.get("factors", [])) or
                  r.get("data_level", {}).get("time_travel", 0))
             for r in results)
    print("AUDIT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
